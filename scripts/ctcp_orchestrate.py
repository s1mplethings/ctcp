#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POINTERS_DIR = ROOT / "meta" / "run_pointers"
LAST_RUN_POINTER = POINTERS_DIR / "LAST_RUN.txt"
LAST_BUNDLE_POINTER = POINTERS_DIR / "LAST_BUNDLE.txt"
TASKS_DIR = ROOT / "meta" / "tasks"
REPORTS_DIR = ROOT / "meta" / "reports"
TASK_TEMPLATE = TASKS_DIR / "TEMPLATE.md"
TASK_CURRENT = TASKS_DIR / "CURRENT.md"
REPORT_LAST = REPORTS_DIR / "LAST.md"
DEFAULT_MAX_ITERATIONS = 3

try:
    from tools.run_paths import get_repo_slug, get_runs_root, make_run_dir
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT))
    from tools.run_paths import get_repo_slug, get_runs_root, make_run_dir

try:
    import ctcp_dispatch
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ctcp_dispatch

try:
    from tools.patch_first import PatchPolicy, apply_patch_safely
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT))
    from tools.patch_first import PatchPolicy, apply_patch_safely

try:
    from tools import scaffold as scaffold_tools
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT))
    from tools import scaffold as scaffold_tools

try:
    from tools import testkit_runner
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT))
    from tools import testkit_runner

try:
    from tools import v2p_fixtures
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT))
    from tools import v2p_fixtures


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_cmd(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    proc_env = os.environ.copy()
    if env:
        for k, v in env.items():
            proc_env[str(k)] = str(v)
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=proc_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return p.returncode, p.stdout, p.stderr


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, doc: dict[str, Any]) -> None:
    write_text(path, json.dumps(doc, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def default_run_id() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f-orchestrate")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def active_patch_candidate(run_dir: Path) -> Path | None:
    artifacts = run_dir / "artifacts"
    patch = artifacts / "diff.patch"
    patch_v2 = artifacts / "diff.patch.v2"
    if patch_v2.exists():
        return patch_v2
    if patch.exists():
        return patch
    return None


def ensure_active_patch(run_dir: Path) -> tuple[Path | None, bool]:
    artifacts = run_dir / "artifacts"
    patch = artifacts / "diff.patch"
    patch_v2 = artifacts / "diff.patch.v2"
    if patch_v2.exists():
        if (not patch.exists()) or file_sha256(patch) != file_sha256(patch_v2):
            shutil.copy2(patch_v2, patch)
            return patch, True
        return patch, False
    if patch.exists():
        return patch, False
    return None, False


def normalize_find_mode(value: str) -> str:
    v = (value or "").strip().lower()
    if v in {"resolver_only", "resolver_plus_web"}:
        return v
    return "resolver_only"


def write_pointer(path: Path, target: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(target.resolve()) + "\n", encoding="utf-8")


def is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def ensure_external_run_dir(run_dir: Path) -> None:
    if is_within(run_dir, ROOT):
        raise SystemExit(
            f"[ctcp_orchestrate] run_dir must be outside repo root; got inside repo: {run_dir}"
        )


def resolve_run_dir(raw: str) -> Path:
    if raw.strip():
        run_dir = Path(raw).expanduser().resolve()
        ensure_external_run_dir(run_dir)
        return run_dir
    if not LAST_RUN_POINTER.exists():
        raise SystemExit("[ctcp_orchestrate] missing LAST_RUN pointer; pass --run-dir")
    pointed = LAST_RUN_POINTER.read_text(encoding="utf-8").strip()
    if not pointed:
        raise SystemExit("[ctcp_orchestrate] LAST_RUN pointer is empty; pass --run-dir")
    run_dir = Path(pointed).expanduser().resolve()
    ensure_external_run_dir(run_dir)
    return run_dir


def resolve_scaffold_runs_root(raw: str) -> Path:
    if str(raw or "").strip():
        return Path(raw).expanduser().resolve()
    env_raw = str(os.environ.get("CTCP_RUNS_ROOT", "")).strip()
    if env_raw:
        return Path(env_raw).expanduser().resolve()
    return (ROOT / "simlab" / "_runs").resolve()


def resolve_scaffold_out_dir(raw: str) -> Path:
    if not str(raw or "").strip():
        raise SystemExit("[ctcp_orchestrate] scaffold requires --out")
    out_dir = Path(raw).expanduser().resolve()
    if is_within(out_dir, ROOT):
        raise SystemExit(
            f"[ctcp_orchestrate] scaffold --out must be outside repo root: {out_dir}"
        )
    return out_dir


def default_scaffold_run_id(project_name: str) -> str:
    slug = goal_slug(project_name or "project")
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return f"{ts}-scaffold-{slug}"


def default_scaffold_pointcloud_run_id(project_name: str) -> str:
    slug = goal_slug(project_name or "project")
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return f"{ts}-scaffold-pointcloud-{slug}"


def append_trace(run_dir: Path, text: str) -> None:
    with (run_dir / "TRACE.md").open("a", encoding="utf-8") as fh:
        fh.write(f"- {now_iso()} | {text}\n")


def append_event(run_dir: Path, role: str, event: str, path: str = "", **extra: Any) -> None:
    row: dict[str, Any] = {"ts": now_iso(), "role": role, "event": event, "path": path}
    for k, v in extra.items():
        row[k] = v
    with (run_dir / "events.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    detail = event if not path else f"{event} ({path})"
    append_trace(run_dir, f"{role}: {detail}")


def ensure_layout(run_dir: Path) -> None:
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (run_dir / "reviews").mkdir(parents=True, exist_ok=True)
    (run_dir / "outbox").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    (run_dir / "snapshot").mkdir(parents=True, exist_ok=True)


def ensure_repo_task_and_report(goal: str) -> None:
    if not TASK_CURRENT.exists():
        if not TASK_TEMPLATE.exists():
            raise SystemExit(f"[ctcp_orchestrate] missing task template: {TASK_TEMPLATE}")
        text = TASK_TEMPLATE.read_text(encoding="utf-8", errors="replace")
        text = text.replace("<topic>", goal)
        goal_line = f"Goal: {goal}\n\n"
        if not text.startswith(goal_line):
            text = goal_line + text
        if "## Acceptance" not in text:
            text = text.rstrip() + "\n\n## Acceptance\n- [ ] Code changes allowed\n"
        elif "Code changes allowed" not in text:
            text = text.rstrip() + "\n- [ ] Code changes allowed\n"
        write_text(TASK_CURRENT, text)

    if not REPORT_LAST.exists():
        write_text(
            REPORT_LAST,
            "\n".join(
                [
                    "# Demo Report - LAST",
                    "",
                    "## Goal",
                    f"- {goal}",
                    "",
                    "## Readlist",
                    "- pending",
                    "",
                    "## Plan",
                    "- pending",
                    "",
                    "## Changes",
                    "- pending",
                    "",
                    "## Verify",
                    "- pending",
                    "",
                ]
            ),
        )


def sync_outbox_fulfilled_events(run_dir: Path) -> None:
    for row in ctcp_dispatch.detect_fulfilled_prompts(run_dir):
        append_event(
            run_dir,
            row.get("role", "") or "manual_outbox",
            "OUTBOX_PROMPT_FULFILLED",
            row["prompt_path"],
            target_path=row["target_path"],
        )


def git_info() -> tuple[str, bool]:
    rc_sha, out_sha, _ = run_cmd(["git", "rev-parse", "HEAD"], ROOT)
    sha = out_sha.strip() if rc_sha == 0 else "unknown"
    rc_dirty, out_dirty, _ = run_cmd(["git", "status", "--porcelain"], ROOT)
    dirty = True if rc_dirty != 0 else bool(out_dirty.strip())
    return sha, dirty


def parse_guardrails(path: Path) -> tuple[bool, str, dict[str, Any]]:
    if not path.exists():
        return False, "missing guardrails", {}
    raw = path.read_text(encoding="utf-8", errors="replace")
    kv: dict[str, str] = {}
    for line in raw.splitlines():
        m = re.match(r"^\s*([A-Za-z0-9_\-]+)\s*:\s*(.+?)\s*$", line)
        if not m:
            continue
        kv[m.group(1).strip().lower()] = m.group(2).strip()

    if "find_mode" not in kv:
        return False, "guardrails missing key: find_mode", {}

    mode = normalize_find_mode(kv.get("find_mode", "resolver_only"))
    policy = {
        "find_mode": mode,
        "max_files": kv.get("max_files", ""),
        "max_total_bytes": kv.get("max_total_bytes", ""),
        "max_iterations": kv.get("max_iterations", ""),
        "allow_domains": [x.strip() for x in kv.get("allow_domains", "").split(",") if x.strip()],
        "max_queries": kv.get("max_queries", ""),
        "max_pages": kv.get("max_pages", ""),
    }
    return True, "ok", policy


def _parse_positive_int(text: str) -> int | None:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except Exception:
        return None
    return value if value > 0 else None


def _parse_plan_max_iterations(path: Path) -> int | None:
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"max_iterations\s*[:=]\s*(\d+)", raw, flags=re.IGNORECASE)
    if not m:
        return None
    return _parse_positive_int(m.group(1))


def resolve_max_iterations(run_dir: Path) -> tuple[int, str]:
    plan_value = _parse_plan_max_iterations(run_dir / "artifacts" / "PLAN.md")
    if plan_value is not None:
        return plan_value, "PLAN.md"

    guardrails = run_dir / "artifacts" / "guardrails.md"
    ok, _, policy = parse_guardrails(guardrails)
    if ok:
        guard_value = _parse_positive_int(str(policy.get("max_iterations", "")))
        if guard_value is not None:
            return guard_value, "guardrails.md"

    return DEFAULT_MAX_ITERATIONS, "default"


def resolve_patch_policy(run_dir: Path) -> tuple[dict[str, Any] | None, str, str]:
    policy_path = run_dir / "artifacts" / "patch_policy.json"
    if not policy_path.exists():
        return None, "default", ""
    try:
        raw = read_json(policy_path)
    except Exception as exc:
        return {}, "artifacts/patch_policy.json", f"invalid patch policy json: {exc}"
    if not isinstance(raw, dict):
        return {}, "artifacts/patch_policy.json", "patch policy json must be an object"
    return raw, "artifacts/patch_policy.json", ""


def write_patch_rejection_review(
    run_dir: Path,
    *,
    patch_sha: str,
    policy_source: str,
    policy_note: str,
    result: Any,
) -> Path:
    review = run_dir / "reviews" / "review_patch.md"
    touched = [str(x) for x in getattr(result, "touched_files", [])]
    touched_lines = "\n".join(f"- {x}" for x in touched) if touched else "- (none)"
    lines = [
        "# Patch Review",
        "",
        "Verdict: BLOCK",
        f"Code: {getattr(result, 'code', '')}",
        f"Stage: {getattr(result, 'stage', '')}",
        f"Reason: {getattr(result, 'message', '')}",
        f"Patch-SHA256: {patch_sha}",
        f"Policy-Source: {policy_source}",
        f"Added-Lines: {int(getattr(result, 'added_lines', 0) or 0)}",
        "",
        "Touched-Files:",
        touched_lines,
        "",
        "Retry-Rule:",
        "1. Only rewrite artifacts/diff.patch.",
        "2. Output unified diff only, first non-empty line must start with diff --git.",
        "3. Do not output prose, JSON, or full-file content dumps.",
    ]
    if policy_note:
        lines.extend(["", f"Policy-Note: {policy_note}"])
    details = getattr(result, "details", {})
    if isinstance(details, dict) and details:
        lines.extend(["", "Details:", json.dumps(details, ensure_ascii=False, indent=2)])
    write_text(review, "\n".join(lines) + "\n")
    return review


def _tail_summary(text: str, *, max_lines: int = 8, max_chars: int = 500) -> str:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        return "(empty)"
    tail = " | ".join(lines[-max_lines:])
    tail = tail.replace("`", "'")
    if len(tail) > max_chars:
        tail = tail[-max_chars:]
    return tail


def append_command_trace(
    run_dir: Path,
    *,
    phase: str,
    cmd: list[str],
    rc: int,
    stdout: str,
    stderr: str,
    stdout_log: Path,
    stderr_log: Path,
) -> None:
    lines = [
        "",
        f"### {phase}",
        f"- ts: {now_iso()}",
        f"- cmd: {' '.join(cmd)}",
        f"- exit_code: {rc}",
        f"- stdout_log: {stdout_log.relative_to(run_dir).as_posix()}",
        f"- stderr_log: {stderr_log.relative_to(run_dir).as_posix()}",
        f"- stdout_tail: {_tail_summary(stdout)}",
        f"- stderr_tail: {_tail_summary(stderr)}",
    ]
    with (run_dir / "TRACE.md").open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def repo_dirty_status() -> tuple[bool, list[str]]:
    rc, out, _ = run_cmd(["git", "status", "--porcelain", "--untracked-files=no"], ROOT)
    if rc != 0:
        return True, ["git status --porcelain failed"]
    rows = [ln.rstrip() for ln in out.splitlines() if ln.strip()]
    return bool(rows), rows


def parse_verdict(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.lower().startswith("verdict:"):
            verdict = line.split(":", 1)[1].strip().upper()
            if verdict in {"APPROVE", "BLOCK"}:
                return verdict
            return "INVALID"
    return "INVALID"


def plan_signed(path: Path) -> bool:
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.lower().startswith("status:"):
            return line.split(":", 1)[1].strip().upper() == "SIGNED"
    return False


def goal_slug(goal: str) -> str:
    text = re.sub(r"[^a-z0-9_-]+", "-", (goal or "").strip().lower())
    text = re.sub(r"-{2,}", "-", text).strip("-_")
    return text or "goal"


def validate_find_web(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing artifacts/find_web.json"
    try:
        doc = read_json(path)
    except Exception as exc:
        return False, f"invalid json: {exc}"

    if doc.get("schema_version") != "ctcp-find-web-v1":
        return False, "schema_version must be ctcp-find-web-v1"

    constraints = doc.get("constraints")
    if not isinstance(constraints, dict):
        return False, "constraints must be object"
    if not isinstance(constraints.get("allow_domains"), list):
        return False, "constraints.allow_domains must be array"
    if not isinstance(constraints.get("max_queries"), int):
        return False, "constraints.max_queries must be int"
    if not isinstance(constraints.get("max_pages"), int):
        return False, "constraints.max_pages must be int"

    results = doc.get("results")
    if not isinstance(results, list):
        return False, "results must be array"

    required = {"url", "locator", "fetched_at", "excerpt", "why_relevant", "risk_flags"}
    for idx, row in enumerate(results):
        if not isinstance(row, dict):
            return False, f"results[{idx}] must be object"
        missing = sorted(required - set(row.keys()))
        if missing:
            return False, f"results[{idx}] missing fields: {', '.join(missing)}"
        loc = row.get("locator")
        if not isinstance(loc, dict):
            return False, f"results[{idx}].locator must be object"
        if not isinstance(row.get("risk_flags"), list):
            return False, f"results[{idx}].risk_flags must be array"
    return True, "ok"


def _validate_externals_pack(path: Path) -> tuple[bool, str]:
    try:
        doc = read_json(path)
    except Exception as exc:
        return False, f"invalid json: {exc}"

    if doc.get("schema_version") != "ctcp-externals-pack-v1":
        return False, "schema_version must be ctcp-externals-pack-v1"

    constraints = doc.get("constraints")
    if not isinstance(constraints, dict):
        return False, "constraints must be object"
    for k in ("max_sources", "allowed_domains", "blocked_domains", "no_login_required", "no_dynamic_only"):
        if k not in constraints:
            return False, f"constraints missing key: {k}"

    sources = doc.get("sources")
    if not isinstance(sources, list):
        return False, "sources must be array"
    for idx, item in enumerate(sources):
        if not isinstance(item, dict):
            return False, f"sources[{idx}] must be object"
        for k in ("url", "title", "why_relevant", "retrieved_at"):
            if k not in item:
                return False, f"sources[{idx}] missing key: {k}"
    return True, "ok"


def validate_externals_pack(goal: str) -> tuple[bool, str, str]:
    externals_root = ROOT / "meta" / "externals"
    candidates: list[Path] = []
    candidates.append(externals_root / goal_slug(goal) / "externals_pack.json")
    if externals_root.exists():
        candidates.extend(sorted(p for p in externals_root.glob("*/externals_pack.json") if p not in candidates))

    for cand in candidates:
        if not cand.exists():
            continue
        ok, msg = _validate_externals_pack(cand)
        if ok:
            return True, str(cand.resolve()), "ok"
    return False, "", "missing valid externals_pack.json"


def current_gate(run_dir: Path, run_doc: dict[str, Any]) -> dict[str, str]:
    # BEHAVIOR_ID: B015
    artifacts = run_dir / "artifacts"
    reviews = run_dir / "reviews"
    patch = artifacts / "diff.patch"
    patch_marker = artifacts / "patch_apply.json"
    verify_report = artifacts / "verify_report.json"

    if str(run_doc.get("status", "")).lower() == "pass":
        return {"state": "pass", "owner": "", "path": "", "reason": "run already pass"}

    blocked_reason = str(run_doc.get("blocked_reason", "")).strip().lower()
    if blocked_reason.startswith("patch_first_rejected"):
        candidate = active_patch_candidate(run_dir)
        if candidate is not None and patch_marker.exists():
            try:
                marker_doc = read_json(patch_marker)
                marker_sha = str(marker_doc.get("patch_sha256", ""))
                marker_rc = int(marker_doc.get("rc", 1))
                candidate_sha = file_sha256(candidate)
                if marker_rc != 0 and marker_sha == candidate_sha:
                    return {
                        "state": "blocked",
                        "owner": "Fixer",
                        "path": "artifacts/diff.patch,reviews/review_patch.md",
                        "reason": "patch-first gate rejected current diff.patch; resubmit unified diff only",
                    }
            except Exception:
                pass

    if str(run_doc.get("status", "")).lower() == "fail":
        candidate = active_patch_candidate(run_dir)
        if candidate is not None:
            candidate_sha = file_sha256(candidate)
            marker_ok = False
            marker_sha = ""
            if patch_marker.exists():
                try:
                    marker_doc = read_json(patch_marker)
                    marker_sha = str(marker_doc.get("patch_sha256", ""))
                    marker_ok = int(marker_doc.get("rc", 1)) == 0
                except Exception:
                    marker_ok = False
                    marker_sha = ""

            if (not marker_ok) or (marker_sha != candidate_sha):
                return {
                    "state": "ready_apply",
                    "owner": "Local Orchestrator",
                    "path": "artifacts/diff.patch",
                    "reason": "new fixer patch detected after failure",
                }

            if not verify_report.exists():
                return {
                    "state": "ready_verify",
                    "owner": "Local Verifier",
                    "path": "artifacts/verify_report.json",
                    "reason": "applied fixer patch pending verify",
                }
            try:
                report = read_json(verify_report)
                report_sha = str(report.get("patch_sha256", ""))
                if report_sha != candidate_sha:
                    return {
                        "state": "ready_verify",
                        "owner": "Local Verifier",
                        "path": "artifacts/verify_report.json",
                        "reason": "applied fixer patch pending verify",
                    }
            except Exception:
                return {
                    "state": "ready_verify",
                    "owner": "Local Verifier",
                    "path": "artifacts/verify_report.json",
                    "reason": "applied fixer patch pending verify",
                }
        return {"state": "fail", "owner": "Fixer", "path": "failure_bundle.zip", "reason": str(run_doc.get("blocked_reason", "run failed"))}

    guardrails = artifacts / "guardrails.md"
    analysis = artifacts / "analysis.md"
    find_result = artifacts / "find_result.json"
    find_web = artifacts / "find_web.json"
    file_request = artifacts / "file_request.json"
    context_pack = artifacts / "context_pack.json"
    plan_draft = artifacts / "PLAN_draft.md"
    plan = artifacts / "PLAN.md"
    review_contract = reviews / "review_contract.md"
    review_cost = reviews / "review_cost.md"

    goal = str(run_doc.get("goal", ""))

    if not guardrails.exists():
        return {"state": "blocked", "owner": "Chair/Planner", "path": "artifacts/guardrails.md", "reason": "waiting for guardrails.md"}

    ok, msg, policy = parse_guardrails(guardrails)
    if not ok:
        return {"state": "blocked", "owner": "Chair/Planner", "path": "artifacts/guardrails.md", "reason": msg}

    if not analysis.exists():
        return {"state": "blocked", "owner": "Chair/Planner", "path": "artifacts/analysis.md", "reason": "waiting for analysis.md"}

    if not find_result.exists():
        return {"state": "resolve_find_local", "owner": "Local Orchestrator", "path": "artifacts/find_result.json", "reason": "run local resolver"}

    if policy["find_mode"] == "resolver_plus_web":
        ok_web, msg_web = validate_find_web(find_web)
        ok_ext, ext_path, _ = validate_externals_pack(goal)
        if not ok_web and not ok_ext:
            return {
                "state": "blocked",
                "owner": "Researcher",
                "path": "artifacts/find_web.json|meta/externals/<goal_slug>/externals_pack.json",
                "reason": "waiting for find_web.json or externals_pack.json",
            }
        if not ok_web and ok_ext:
            pass

    if not file_request.exists():
        return {"state": "blocked", "owner": "Chair/Planner", "path": "artifacts/file_request.json", "reason": "waiting for file_request.json"}

    if not context_pack.exists():
        return {"state": "blocked", "owner": "Local Librarian", "path": "artifacts/context_pack.json", "reason": "waiting for context_pack.json"}

    if not plan_draft.exists():
        return {"state": "blocked", "owner": "Chair/Planner", "path": "artifacts/PLAN_draft.md", "reason": "waiting for PLAN_draft.md"}

    if not review_contract.exists():
        return {"state": "blocked", "owner": "Contract Guardian", "path": "reviews/review_contract.md", "reason": "waiting for review_contract.md"}

    if not review_cost.exists():
        return {"state": "blocked", "owner": "Cost Controller", "path": "reviews/review_cost.md", "reason": "waiting for review_cost.md"}

    verdict_contract = parse_verdict(review_contract)
    verdict_cost = parse_verdict(review_cost)
    if verdict_contract != "APPROVE":
        return {
            "state": "blocked",
            "owner": "Contract Guardian",
            "path": "reviews/review_contract.md",
            "reason": f"waiting for APPROVE review_contract (verdict={verdict_contract})",
        }
    if verdict_cost != "APPROVE":
        return {
            "state": "blocked",
            "owner": "Cost Controller",
            "path": "reviews/review_cost.md",
            "reason": f"waiting for APPROVE review_cost (verdict={verdict_cost})",
        }

    if not plan.exists() or not plan_signed(plan):
        return {"state": "blocked", "owner": "Chair/Planner", "path": "artifacts/PLAN.md", "reason": "waiting for signed PLAN.md"}

    if not patch.exists() and not (artifacts / "diff.patch.v2").exists():
        return {"state": "blocked", "owner": "PatchMaker", "path": "artifacts/diff.patch", "reason": "waiting for diff.patch"}

    if patch.exists() and patch_marker.exists():
        try:
            marker = read_json(patch_marker)
            if marker.get("patch_sha256") == file_sha256(patch) and int(marker.get("rc", 1)) == 0:
                return {"state": "ready_verify", "owner": "Local Verifier", "path": "artifacts/verify_report.json", "reason": "patch already applied"}
        except Exception:
            pass

    return {"state": "ready_apply", "owner": "Local Orchestrator", "path": "artifacts/diff.patch", "reason": "ready to git apply"}


def make_failure_bundle(run_dir: Path) -> Path:
    # BEHAVIOR_ID: B016
    bundle = run_dir / "failure_bundle.zip"
    ensure_layout(run_dir)
    artifacts = run_dir / "artifacts"
    reviews = run_dir / "reviews"
    outbox = run_dir / "outbox"

    # Persist placeholder files on disk so external audits can inspect run_dir directly.
    if not (artifacts / "PLAN.md").exists():
        write_text(artifacts / "PLAN.md", "# placeholder PLAN.md\n")
    if not (artifacts / "diff.patch").exists():
        write_text(artifacts / "diff.patch", "")
    if not (reviews / ".keep").exists():
        write_text(reviews / ".keep", "# placeholder\n")
    if not (outbox / ".keep").exists():
        write_text(outbox / ".keep", "# placeholder\n")

    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
        # Keep directory entries explicit so empty reviews/outbox are still auditable.
        for rel_dir in ("artifacts/", "reviews/", "outbox/"):
            zf.writestr(rel_dir, "")

        for p in run_dir.rglob("*"):
            if p.is_file() and p != bundle:
                rel = p.relative_to(run_dir).as_posix()
                zf.write(p, rel)
    return bundle


def _required_bundle_entries(run_dir: Path) -> list[str]:
    required = [
        "TRACE.md",
        "events.jsonl",
        "artifacts/verify_report.json",
        "artifacts/PLAN.md",
        "artifacts/diff.patch",
        "reviews/",
        "reviews/.keep",
        "outbox/",
        "outbox/.keep",
    ]
    for rel_dir in ("reviews", "outbox"):
        base = run_dir / rel_dir
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file():
                required.append(p.relative_to(run_dir).as_posix())
    return required


def _bundle_contains(bundle: Path, required_entries: list[str], require_outbox_prompt: bool = False) -> bool:
    if not bundle.exists():
        return False
    try:
        with zipfile.ZipFile(bundle, "r") as zf:
            names = set(zf.namelist())
    except Exception:
        return False
    if not all(x in names for x in required_entries):
        return False
    if require_outbox_prompt and (not any(n.startswith("outbox/") and n.endswith(".md") for n in names)):
        return False
    return True


def ensure_fixer_outbox_prompt(run_dir: Path, goal: str, reason: str) -> tuple[str, bool]:
    outbox_dir = run_dir / "outbox"
    outbox_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(p for p in outbox_dir.glob("*.md") if p.is_file())
    if existing:
        return (Path("outbox") / existing[0].name).as_posix(), False

    prompt = outbox_dir / "001_fixer_fix_patch.md"
    prompt_text = "\n".join(
        [
            "# OUTBOX PROMPT",
            "",
            """SYSTEM CONTRACT (EN)

You are a patch-first coding agent. Follow these rules strictly:

Scope: Only make changes that are necessary to fulfill the user’s request. Do not refactor, rename, reformat, or change unrelated logic.

Minimality: Prefer the smallest verified change. Avoid touching files not required by the fix.

Output: Produce exactly ONE unified diff patch that is git apply compatible. No explanations, no extra text.

Verification: If the repository has an existing verification command (tests / lint / verify_repo / CI script), run or specify it in your plan. Do not add new dependencies.

If uncertain: Stop after producing a short PLAN in JSON (see below) and do NOT output a patch.

PLAN JSON schema (only when uncertain):
{
"goal": "...",
"assumptions": ["..."],
"files_to_change": ["..."],
"steps": ["..."],
"verification": ["..."]
}

Additional constraints:

Never modify more than the minimum number of files needed.

Never change formatting outside the prompt/contract text area.

Never change any behavior except prompt/contract enforcement.

END SYSTEM CONTRACT""",
            "",
            f"Run-Dir: {run_dir.resolve()}",
            f"Goal: {goal}",
            "Role: fixer",
            "Action: fix_patch",
            "Provider: manual_outbox_fallback",
            "Target-Path: artifacts/diff.patch",
            "write to: artifacts/diff.patch",
            f"Reason: {reason or 'verify_failed'}",
            "",
            "Inputs:",
            "- failure_bundle.zip",
            "- artifacts/verify_report.json",
            "",
            "Hard Rules:",
            "1. Only write artifacts/diff.patch in run_dir.",
            "2. Output unified diff only (first non-empty line must be diff --git).",
            "3. Do not modify repo files.",
            "",
        ]
    )
    write_text(prompt, prompt_text + "\n")
    return (Path("outbox") / prompt.name).as_posix(), True


def ensure_failure_bundle(run_dir: Path, require_outbox_prompt: bool = False) -> tuple[Path, str]:
    bundle = run_dir / "failure_bundle.zip"
    required_entries = _required_bundle_entries(run_dir)
    if _bundle_contains(bundle, required_entries, require_outbox_prompt=require_outbox_prompt):
        return bundle, "validated"

    mode = "created" if not bundle.exists() else "recreated"
    bundle = make_failure_bundle(run_dir)
    if not _bundle_contains(bundle, required_entries, require_outbox_prompt=require_outbox_prompt):
        with zipfile.ZipFile(bundle, "r") as zf:
            names = set(zf.namelist())
        missing = [x for x in required_entries if x not in names]
        if require_outbox_prompt and any(n.startswith("outbox/") and n.endswith(".md") for n in names):
            raise SystemExit(f"[ctcp_orchestrate] failure_bundle missing required entries: {missing}")
        if require_outbox_prompt:
            raise SystemExit("[ctcp_orchestrate] failure_bundle missing required outbox prompt (*.md)")
        raise SystemExit(f"[ctcp_orchestrate] failure_bundle missing required entries: {missing}")
    return bundle, mode


def _extract_verify_failures(stdout: str, stderr: str) -> list[dict[str, str]]:
    lines: list[str] = []
    merged = f"{stdout}\n{stderr}"
    for raw in merged.splitlines():
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        if ("error" in low) or ("failed" in low):
            lines.append(line)
        if len(lines) >= 8:
            break
    if not lines:
        lines = ["verify_repo returned non-zero"]
    return [
        {
            "kind": "verify",
            "id": f"verify_repo_{idx+1}",
            "message": line[:300],
        }
        for idx, line in enumerate(lines)
    ]


def verify_cmd() -> list[str]:
    if os.name == "nt":
        return ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts" / "verify_repo.ps1")]
    return ["bash", str(ROOT / "scripts" / "verify_repo.sh")]


def verify_run_env() -> dict[str, str]:
    env = {
        "CTCP_SKIP_LITE_REPLAY": "1",
        # Keep verify independent from provider-routing overrides set for dispatch phases.
        "CTCP_FORCE_PROVIDER": "",
        "CTCP_MOCK_AGENT_FAULT_MODE": "",
        "CTCP_MOCK_AGENT_FAULT_ROLE": "",
    }
    if str(os.environ.get("CTCP_VERIFY_ALLOW_LIVE_API", "")).strip() != "1":
        # Default verify path should not trigger live API tests/calls.
        env["CTCP_LIVE_API"] = ""
        env["OPENAI_API_KEY"] = ""
        env["CTCP_OPENAI_API_KEY"] = ""
    return env


def render_scaffold_plan_markdown(*, profile: str, out_dir: Path, project_name: str, force: bool, files: list[str]) -> str:
    lines = [
        "# Scaffold Plan",
        "",
        f"- Profile: {profile}",
        f"- Project-Name: {project_name}",
        f"- Out-Dir: {out_dir.resolve()}",
        f"- Force: {'true' if force else 'false'}",
        f"- Planned-Files: {len(files)}",
        "",
        "## Files",
    ]
    for rel in files:
        lines.append(f"- {rel}")
    lines.append("")
    return "\n".join(lines)


def scaffold_verify_cmd(out_dir: Path) -> tuple[list[str], str]:
    ps1 = out_dir / "scripts" / "verify_repo.ps1"
    sh = out_dir / "scripts" / "verify_repo.sh"
    if os.name == "nt" and ps1.exists():
        return (
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps1.resolve())],
            "scripts/verify_repo.ps1",
        )
    if os.name != "nt" and sh.exists():
        return (["bash", str(sh.resolve())], "scripts/verify_repo.sh")
    return ([], "")


def _is_path_root(path: Path) -> bool:
    resolved = path.resolve()
    return resolved.parent == resolved


def _safe_clear_directory_contents(path: Path) -> list[str]:
    removed: list[str] = []
    for child in sorted(path.iterdir(), key=lambda p: p.name):
        rel = child.relative_to(path).as_posix()
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
        removed.append(rel)
    return removed


def _render_template_to_path(src: Path, dst: Path, tokens: dict[str, str]) -> None:
    raw = src.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(raw)
        return
    rendered = text
    for key, value in tokens.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(rendered, encoding="utf-8")


POINTCLOUD_IGNORED_SEGMENTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "out",
    "fixture",
    "runs",
}
POINTCLOUD_IGNORED_FILENAMES = {
    ".DS_Store",
    "Thumbs.db",
}


def _is_pointcloud_scaffold_file(rel: str) -> bool:
    path = str(rel or "").strip().replace("\\", "/")
    if not path:
        return False
    parts = [p for p in path.split("/") if p]
    if not parts:
        return False
    if any(seg in POINTCLOUD_IGNORED_SEGMENTS for seg in parts):
        return False
    if parts[-1] in POINTCLOUD_IGNORED_FILENAMES:
        return False
    if parts[-1].endswith(".pyc"):
        return False
    return True


def _collect_pointcloud_template_files(profile: str) -> dict[str, Path]:
    profile_name = str(profile or "").strip().lower()
    if profile_name not in {"minimal", "standard"}:
        raise SystemExit(f"[ctcp_orchestrate] unsupported pointcloud profile: {profile}")
    template_root = ROOT / "templates" / "pointcloud_project"
    minimal_root = template_root / "minimal"
    standard_root = template_root / "standard"
    if not minimal_root.exists():
        raise SystemExit(f"[ctcp_orchestrate] missing pointcloud template profile: {minimal_root}")
    roots = [minimal_root] if profile_name == "minimal" else [minimal_root, standard_root]
    rows: dict[str, Path] = {}
    for root in roots:
        if not root.exists():
            raise SystemExit(f"[ctcp_orchestrate] missing pointcloud template profile: {root}")
        for node in root.rglob("*"):
            if not node.is_file():
                continue
            rel = node.relative_to(root).as_posix()
            if not _is_pointcloud_scaffold_file(rel):
                continue
            rows[rel] = node
    if not rows:
        raise SystemExit(f"[ctcp_orchestrate] no template files found for profile={profile_name}")
    return rows


def _write_pointcloud_manifest(
    *,
    out_dir: Path,
    profile: str,
    project_name: str,
    generated_at_utc: str,
    files: list[str],
) -> str:
    rel = "meta/manifest.json"
    manifest_path = out_dir / Path("meta") / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    all_files = sorted(
        set(
            [x for x in files if _is_pointcloud_scaffold_file(x)]
            + [rel]
        )
    )
    doc = {
        "schema_version": "ctcp-pointcloud-manifest-v1",
        "generated_by": "ctcp_orchestrate scaffold-pointcloud",
        "profile": profile,
        "project_name": project_name,
        "generated_at_utc": generated_at_utc,
        "files": all_files,
        "file_count": len(all_files),
    }
    manifest_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rel


def _required_pointcloud_paths(profile: str) -> list[str]:
    required = [
        "README.md",
        ".gitignore",
        "docs/00_CORE.md",
        "meta/tasks/CURRENT.md",
        "meta/reports/LAST.md",
        "meta/manifest.json",
        "scripts/make_synth_fixture.py",
        "scripts/eval_v2p.py",
        "scripts/clean_project.py",
        "scripts/run_v2p.py",
        "scripts/verify_repo.ps1",
        "tests/test_clean_project.py",
        "tests/test_pipeline_synth.py",
        "tests/test_smoke.py",
        "pyproject.toml",
    ]
    if str(profile).strip().lower() == "standard":
        required.extend(
            [
                "docs/behaviors/INDEX.md",
                "workflow_registry/README.md",
            ]
        )
    return required


def render_scaffold_pointcloud_plan_markdown(
    *,
    profile: str,
    out_dir: Path,
    project_name: str,
    force: bool,
    dialogue_mode: str,
    files: list[str],
) -> str:
    lines = [
        "# SCAFFOLD PLAN",
        "",
        f"- Command: scaffold-pointcloud",
        f"- Profile: {profile}",
        f"- Project-Name: {project_name}",
        f"- Out-Dir: {out_dir.resolve()}",
        f"- Force: {'true' if force else 'false'}",
        f"- Dialogue-Mode: {dialogue_mode}",
        f"- Planned-Files: {len(files)}",
        "",
        "## Files",
    ]
    for rel in files:
        lines.append(f"- {rel}")
    lines.append("")
    return "\n".join(lines)


def default_cos_user_run_id(project: str) -> str:
    slug = goal_slug(project or "project")
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return f"{ts}-cos-user-v2p-{slug}"


def resolve_cos_runs_root(raw: str) -> Path:
    if str(raw or "").strip():
        return Path(raw).expanduser().resolve()
    env_raw = str(os.environ.get("CTCP_RUNS_ROOT", "")).strip()
    if env_raw:
        return Path(env_raw).expanduser().resolve()
    return get_runs_root().resolve()


def run_shell_cmd(command: str, cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        str(command),
        cwd=str(cwd),
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return int(proc.returncode), proc.stdout, proc.stderr


def load_dialogue_script_answers(path: Path) -> dict[str, str]:
    if not path.exists() or not path.is_file():
        raise SystemExit(f"[ctcp_orchestrate] dialogue script not found: {path}")
    answers: dict[str, str] = {}
    for idx, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
        except Exception as exc:
            raise SystemExit(f"[ctcp_orchestrate] dialogue script parse failed at line {idx}: {exc}") from exc
        if not isinstance(doc, dict):
            raise SystemExit(f"[ctcp_orchestrate] dialogue script line {idx} must be object")
        qid = str(doc.get("id") or doc.get("qid") or doc.get("question_id") or "").strip()
        ref = str(doc.get("ref") or doc.get("reply_to") or doc.get("question_ref") or "").strip()
        source = str(doc.get("from") or doc.get("role") or "").strip().lower()
        row_type = str(doc.get("type") or "").strip().lower()

        # taskpack JSONL format: explicit answer rows use `ref` to map back to Q id.
        if ref:
            answer = str(doc.get("answer") or doc.get("response") or doc.get("text") or "").strip()
            if answer:
                answers[ref] = answer
            continue

        if not qid:
            continue

        if "answer" in doc or "response" in doc or row_type == "answer" or source == "agent":
            answer = str(doc.get("answer") or doc.get("response") or doc.get("text") or "").strip()
            if answer:
                answers[qid] = answer
            continue

        default_answer = str(doc.get("default") or "").strip()
        if default_answer and qid not in answers:
            answers[qid] = default_answer
    return answers


def ask_dialogue_question(
    *,
    qid: str,
    question: str,
    default_answer: str,
    script_answers: dict[str, str] | None,
    agent_cmd: str,
) -> tuple[str, str]:
    if script_answers is not None:
        return script_answers.get(qid, default_answer), "script"
    if str(agent_cmd or "").strip():
        payload = json.dumps({"qid": qid, "question": question}, ensure_ascii=False) + "\n"
        proc = subprocess.run(
            str(agent_cmd),
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            input=payload,
        )
        if int(proc.returncode) != 0:
            raise SystemExit(
                f"[ctcp_orchestrate] agent command failed for {qid}: rc={proc.returncode}, stderr={proc.stderr.strip()}"
            )
        answer = str(proc.stdout or "").strip() or default_answer
        return answer, "agent_cmd"
    return default_answer, "default"


def parse_semantics_answer(answer: str) -> bool:
    text = str(answer or "").strip().lower()
    if text in {"0", "off", "false", "no", "n"}:
        return False
    if text in {"1", "on", "true", "yes", "y"}:
        return True
    return True


def parse_threshold_answer(answer: str) -> dict[str, float]:
    defaults = {"fps_min": 1.0, "points_min": 10000.0, "fscore_min": 0.85}
    text = str(answer or "").strip()
    if not text:
        return defaults
    try:
        doc = json.loads(text)
    except Exception:
        doc = None
    if isinstance(doc, dict):
        for k in ("fps_min", "points_min", "fscore_min"):
            value = doc.get(k)
            if isinstance(value, (int, float)):
                defaults[k] = float(value)
        return defaults
    nums = re.findall(r"[-+]?\d*\.?\d+", text)
    if len(nums) >= 3:
        defaults["fps_min"] = float(nums[0])
        defaults["points_min"] = float(nums[1])
        defaults["fscore_min"] = float(nums[2])
    return defaults


def resolve_repo_verify_cmd(repo_path: Path) -> tuple[str, str]:
    candidates = [
        (repo_path / "scripts" / "verify_repo.ps1", "scripts/verify_repo.ps1"),
        (repo_path / "scripts" / "verify_repo.sh", "scripts/verify_repo.sh"),
        (repo_path / "verify_repo.ps1", "verify_repo.ps1"),
        (repo_path / "verify_repo.sh", "verify_repo.sh"),
    ]
    ps1_candidates = [(p, rel) for p, rel in candidates if p.suffix.lower() == ".ps1" and p.exists()]
    sh_candidates = [(p, rel) for p, rel in candidates if p.suffix.lower() == ".sh" and p.exists()]
    if os.name == "nt":
        if ps1_candidates:
            p, rel = ps1_candidates[0]
            if rel == "scripts/verify_repo.ps1":
                return ("powershell -ExecutionPolicy Bypass -File scripts\\verify_repo.ps1", rel)
            return (f'powershell -ExecutionPolicy Bypass -File "{p.resolve()}"', rel)
        if sh_candidates:
            p, rel = sh_candidates[0]
            if rel == "scripts/verify_repo.sh":
                return ("bash scripts/verify_repo.sh", rel)
            return (f'bash "{p.resolve()}"', rel)
    else:
        if sh_candidates:
            p, rel = sh_candidates[0]
            if rel == "scripts/verify_repo.sh":
                return ("bash scripts/verify_repo.sh", rel)
            return (f'bash "{p.resolve()}"', rel)
        if ps1_candidates:
            p, rel = ps1_candidates[0]
            if rel == "scripts/verify_repo.ps1":
                return ("powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1", rel)
            return (f'powershell -ExecutionPolicy Bypass -File "{p.resolve()}"', rel)
    return "", ""


def render_user_sim_plan_md(
    *,
    run_id: str,
    repo_path: Path,
    project: str,
    testkit_zip: Path,
    out_root: Path,
    out_note: str,
    copy_csv: str,
    entry: str,
    pre_verify_cmd: str,
    post_verify_cmd: str,
    fixture_mode: str,
    fixture_source: str,
    fixture_path: Path,
    semantics_enabled: bool,
    thresholds: dict[str, float],
    dialogue_mode: str,
) -> str:
    return "\n".join(
        [
            "# USER SIM PLAN",
            "",
            f"- Run-Id: {run_id}",
            f"- Repo: {repo_path.resolve()}",
            f"- Project: {project}",
            f"- Testkit-Zip: {testkit_zip.resolve()}",
            f"- Out-Root: {out_root.resolve()}",
            f"- Out-Root-Note: {out_note or 'none'}",
            f"- Entry: {entry}",
            f"- Copy: {copy_csv}",
            f"- Pre-Verify-Cmd: {pre_verify_cmd or '(disabled)'}",
            f"- Post-Verify-Cmd: {post_verify_cmd or '(disabled)'}",
            f"- Dialogue-Mode: {dialogue_mode}",
            f"- Fixture-Mode: {fixture_mode}",
            f"- Fixture-Source: {fixture_source}",
            f"- Fixture-Path: {fixture_path.resolve()}",
            "",
            "## Decisions",
            f"- Semantics-Enabled: {'true' if semantics_enabled else 'false'}",
            f"- Thresholds: fps_min={thresholds['fps_min']}, points_min={thresholds['points_min']}, fscore_min={thresholds['fscore_min']}",
            "",
            "## Acceptance",
            "- testkit rc == 0",
            "- required copied outputs exist",
            "- if verify enabled: pre_verify rc == 0 and post_verify rc == 0",
            "",
        ]
    )


def render_dialogue_transcript(turns: list[dict[str, Any]]) -> str:
    lines = ["# Dialogue Transcript", ""]
    for idx, row in enumerate(turns, start=1):
        lines.append(f"## Turn {idx} ({row.get('qid', '')})")
        lines.append(f"- Question: {row.get('question', '')}")
        lines.append(f"- Answer: {row.get('answer', '')}")
        lines.append(f"- Source: {row.get('source', '')}")
        lines.append("")
    return "\n".join(lines)


def cmd_scaffold_pointcloud(
    *,
    out: str,
    name: str,
    profile: str,
    force: bool,
    runs_root: str,
    dialogue_script: str,
    agent_cmd: str,
) -> int:
    # BEHAVIOR_ID: B039
    t0 = dt.datetime.now()
    out_dir = resolve_scaffold_out_dir(out)
    profile_name = str(profile or "minimal").strip().lower()
    if profile_name not in {"minimal", "standard"}:
        print(f"[ctcp_orchestrate] unsupported --profile for scaffold-pointcloud: {profile_name}")
        return 1
    project_name = str(name or "").strip() or out_dir.name
    if not project_name:
        print("[ctcp_orchestrate] scaffold-pointcloud requires --name or a resolvable --out folder name")
        return 1

    run_id = default_scaffold_pointcloud_run_id(project_name)
    runs_root_path = resolve_scaffold_runs_root(runs_root)
    run_dir = (runs_root_path / "scaffold_pointcloud" / run_id).resolve()
    if run_dir.exists() and any(run_dir.iterdir()):
        print(f"[ctcp_orchestrate] scaffold-pointcloud run dir exists and not empty: {run_dir}")
        return 1

    ensure_layout(run_dir)
    write_text(
        run_dir / "TRACE.md",
        "\n".join(
            [
                f"# CTCP Pointcloud Scaffold Trace - {run_id}",
                "",
                f"- Out: {out_dir.resolve()}",
                f"- Project: {project_name}",
                f"- Profile: {profile_name}",
                "",
                "## Events",
                "",
            ]
        ),
    )
    write_text(run_dir / "events.jsonl", "")
    write_pointer(LAST_RUN_POINTER, run_dir)
    append_event(run_dir, "Local Orchestrator", "scaffold_pointcloud_run_created", "TRACE.md")

    script_answers: dict[str, str] | None = None
    dialogue_mode = "default"
    if str(dialogue_script or "").strip():
        script_path = Path(dialogue_script).expanduser().resolve()
        script_answers = load_dialogue_script_answers(script_path)
        dialogue_mode = "script"
    elif str(agent_cmd or "").strip():
        dialogue_mode = "agent_cmd"

    q1_text = f"Choose profile minimal|standard (current={profile_name})."
    q2_text = f"Confirm project name (current={project_name})."
    q3_text = f"Confirm output root and force flag: out={out_dir.resolve()}, force={'true' if force else 'false'}."
    q1_answer, q1_source = ask_dialogue_question(
        qid="S1",
        question=q1_text,
        default_answer=profile_name,
        script_answers=script_answers,
        agent_cmd=agent_cmd,
    )
    q2_answer, q2_source = ask_dialogue_question(
        qid="S2",
        question=q2_text,
        default_answer=project_name,
        script_answers=script_answers,
        agent_cmd=agent_cmd,
    )
    q3_answer, q3_source = ask_dialogue_question(
        qid="S3",
        question=q3_text,
        default_answer=str(out_dir.resolve()),
        script_answers=script_answers,
        agent_cmd=agent_cmd,
    )
    turns = [
        {"ts": now_iso(), "qid": "S1", "question": q1_text, "answer": q1_answer, "source": q1_source},
        {"ts": now_iso(), "qid": "S2", "question": q2_text, "answer": q2_answer, "source": q2_source},
        {"ts": now_iso(), "qid": "S3", "question": q3_text, "answer": q3_answer, "source": q3_source},
    ]
    write_text(run_dir / "artifacts" / "dialogue.jsonl", "\n".join(json.dumps(x, ensure_ascii=False) for x in turns) + "\n")
    write_text(run_dir / "artifacts" / "dialogue_transcript.md", render_dialogue_transcript(turns))
    for row in turns:
        append_event(
            run_dir,
            "CTCP",
            "dialogue_turn",
            "artifacts/dialogue.jsonl",
            qid=str(row["qid"]),
            answer=str(row["answer"]),
            source=str(row["source"]),
        )

    profile_from_dialogue = str(q1_answer or "").strip().lower()
    if profile_from_dialogue in {"minimal", "standard"}:
        profile_name = profile_from_dialogue
    project_from_dialogue = str(q2_answer or "").strip()
    if project_from_dialogue:
        project_name = project_from_dialogue

    try:
        template_files = _collect_pointcloud_template_files(profile_name)
    except SystemExit as exc:
        append_event(
            run_dir,
            "Local Orchestrator",
            "scaffold_pointcloud_template_error",
            "artifacts/scaffold_pointcloud_report.json",
            reason=str(exc),
        )
        print(str(exc))
        print(f"[ctcp_orchestrate] run_dir={run_dir.resolve()}")
        return 1

    planned_files = sorted(set(list(template_files.keys()) + ["meta/manifest.json"]))
    plan_md = render_scaffold_pointcloud_plan_markdown(
        profile=profile_name,
        out_dir=out_dir,
        project_name=project_name,
        force=bool(force),
        dialogue_mode=dialogue_mode,
        files=planned_files,
    )
    write_text(run_dir / "artifacts" / "SCAFFOLD_PLAN.md", plan_md + "\n")
    append_event(run_dir, "Local Orchestrator", "scaffold_pointcloud_plan_written", "artifacts/SCAFFOLD_PLAN.md")

    generated_at_utc = now_utc_iso()
    tokens = {
        "PROJECT_NAME": project_name,
        "UTC_ISO": generated_at_utc,
    }

    removed_entries: list[str] = []
    written_files: list[str] = []
    scaffold_error = ""
    try:
        if out_dir.exists():
            if not out_dir.is_dir():
                raise RuntimeError(f"--out exists but is not a directory: {out_dir}")
            if not force:
                raise RuntimeError(f"--out already exists (use --force to overwrite): {out_dir}")
            if _is_path_root(out_dir):
                raise RuntimeError(f"--force refuses drive/filesystem root --out: {out_dir}")
            removed_entries = _safe_clear_directory_contents(out_dir)
        else:
            out_dir.mkdir(parents=True, exist_ok=True)

        for rel in sorted(template_files.keys()):
            src = template_files[rel]
            dst = out_dir / Path(*rel.split("/"))
            _render_template_to_path(src, dst, tokens)
            written_files.append(rel)

        manifest_rel = _write_pointcloud_manifest(
            out_dir=out_dir,
            profile=profile_name,
            project_name=project_name,
            generated_at_utc=generated_at_utc,
            files=written_files,
        )
        if manifest_rel not in written_files:
            written_files.append(manifest_rel)

        missing_required: list[str] = []
        for rel in _required_pointcloud_paths(profile_name):
            path = out_dir / Path(*rel.split("/"))
            if not path.exists():
                missing_required.append(rel)
        if missing_required:
            raise RuntimeError(f"missing required generated files: {', '.join(missing_required)}")
        append_event(run_dir, "Local Orchestrator", "scaffold_pointcloud_written", "meta/manifest.json")
    except Exception as exc:
        scaffold_error = str(exc)
        append_event(
            run_dir,
            "Local Orchestrator",
            "scaffold_pointcloud_failed",
            "artifacts/scaffold_pointcloud_report.json",
            reason=scaffold_error,
        )

    elapsed_ms = int((dt.datetime.now() - t0).total_seconds() * 1000)
    passed = not scaffold_error
    report = {
        "schema_version": "ctcp-pointcloud-scaffold-report-v1",
        "result": "PASS" if passed else "FAIL",
        "run_id": run_id,
        "profile": profile_name,
        "project_name": project_name,
        "dialogue": {
            "mode": dialogue_mode,
            "turn_count": len(turns),
            "script": str(Path(dialogue_script).expanduser().resolve()) if str(dialogue_script or "").strip() else "",
        },
        "paths": {
            "out_dir": str(out_dir.resolve()),
            "run_dir": str(run_dir.resolve()),
            "plan": "artifacts/SCAFFOLD_PLAN.md",
            "dialogue_jsonl": "artifacts/dialogue.jsonl",
            "dialogue_transcript": "artifacts/dialogue_transcript.md",
            "manifest": "meta/manifest.json",
            "report": "artifacts/scaffold_pointcloud_report.json",
        },
        "counts": {
            "planned_files": len(planned_files),
            "written_files": len(written_files),
            "removed_entries": len(removed_entries),
        },
        "written_files": sorted(written_files),
        "removed_entries": sorted(removed_entries),
        "elapsed_ms": elapsed_ms,
        "error": scaffold_error,
    }
    write_json(run_dir / "artifacts" / "scaffold_pointcloud_report.json", report)
    append_event(
        run_dir,
        "Local Orchestrator",
        "scaffold_pointcloud_report_written",
        "artifacts/scaffold_pointcloud_report.json",
        result=report["result"],
    )

    print(f"[ctcp_orchestrate] run_dir={run_dir.resolve()}")
    print(f"[ctcp_orchestrate] out_dir={out_dir.resolve()}")
    if passed:
        return 0
    print(f"[ctcp_orchestrate] scaffold-pointcloud failed: {scaffold_error}")
    return 1


def cmd_cos_user_v2p(
    *,
    repo: str,
    project: str,
    testkit_zip: str,
    out_root: str,
    runs_root: str,
    entry: str,
    copy_csv: str,
    fixture_mode: str,
    fixture_path: str,
    dialogue_script: str,
    agent_cmd: str,
    pre_verify_cmd: str,
    post_verify_cmd: str,
    skip_verify: bool,
    force: bool,
) -> int:
    # BEHAVIOR_ID: B038
    repo_path = Path(str(repo or "").strip()).expanduser().resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        print(f"[ctcp_orchestrate] --repo not found or not directory: {repo_path}")
        return 1
    project_name = str(project or "").strip()
    if not project_name:
        print("[ctcp_orchestrate] --project is required")
        return 1
    zip_path = Path(str(testkit_zip or "").strip()).expanduser().resolve()
    if not zip_path.exists() or not zip_path.is_file():
        print(f"[ctcp_orchestrate] --testkit-zip not found: {zip_path}")
        return 1

    run_id = default_cos_user_run_id(project_name)
    runs_root_path = resolve_cos_runs_root(runs_root)
    run_dir = (runs_root_path / "cos_user_v2p" / run_id).resolve()
    if run_dir.exists() and any(run_dir.iterdir()):
        print(f"[ctcp_orchestrate] run dir exists and not empty: {run_dir}")
        return 1
    if is_within(run_dir, ROOT):
        print(f"[ctcp_orchestrate] cos-user-v2p requires external run_dir (outside CTCP repo): {run_dir}")
        return 1
    if is_within(run_dir, repo_path):
        print(f"[ctcp_orchestrate] cos-user-v2p requires run_dir outside tested repo: {run_dir}")
        return 1
    ensure_external_run_dir(run_dir)
    ensure_layout(run_dir)
    write_text(
        run_dir / "TRACE.md",
        "\n".join(
            [
                f"# CTCP COS User V2P Trace - {run_id}",
                "",
                f"- Repo: {repo_path}",
                f"- Project: {project_name}",
                f"- Testkit-Zip: {zip_path}",
                "",
                "## Events",
                "",
            ]
        ),
    )
    write_text(run_dir / "events.jsonl", "")
    write_pointer(LAST_RUN_POINTER, run_dir)
    append_event(run_dir, "Local Orchestrator", "cos_user_v2p_run_created", "TRACE.md")

    explicit_out = bool(str(out_root or "").strip())
    out_root_path, out_note = testkit_runner.resolve_out_root(out_root, explicit=explicit_out)

    script_answers: dict[str, str] | None = None
    dialogue_mode = "default"
    if str(dialogue_script or "").strip():
        script_path = Path(dialogue_script).expanduser().resolve()
        script_answers = load_dialogue_script_answers(script_path)
        dialogue_mode = "script"
    elif str(agent_cmd or "").strip():
        dialogue_mode = "agent_cmd"

    turns: list[dict[str, Any]] = []

    def _ask_turn(*, qid: str, question: str, default_answer: str) -> str:
        answer, source = ask_dialogue_question(
            qid=qid,
            question=question,
            default_answer=default_answer,
            script_answers=script_answers,
            agent_cmd=agent_cmd,
        )
        turns.append(
            {
                "ts": now_iso(),
                "qid": qid,
                "question": question,
                "answer": answer,
                "source": source,
            }
        )
        return answer

    q1_text = f"Confirm ProjectName + output destination: project={project_name}, out_root={out_root_path}."
    q2_text = "Semantics on/off? (on/off)"
    q3_text = "Thresholds? Provide fps_min,points_min,fscore_min (default 1.0,10000,0.85)."
    q1_answer = _ask_turn(
        qid="Q1",
        question=q1_text,
        default_answer=f"confirm:{project_name}:{out_root_path}",
    )
    q2_answer = _ask_turn(
        qid="Q2",
        question=q2_text,
        default_answer="on",
    )
    q3_answer = _ask_turn(
        qid="Q3",
        question=q3_text,
        default_answer="1.0,10000,0.85",
    )

    semantics_enabled = parse_semantics_answer(q2_answer)
    thresholds = parse_threshold_answer(q3_answer)
    resolved_pre_cmd = str(pre_verify_cmd or "").strip()
    resolved_post_cmd = str(post_verify_cmd or "").strip()
    verify_entry = ""
    if not skip_verify and ((not resolved_pre_cmd) or (not resolved_post_cmd)):
        default_verify_cmd, verify_entry = resolve_repo_verify_cmd(repo_path)
        if not default_verify_cmd:
            print("[ctcp_orchestrate] verify command not found in --repo (expected verify_repo.ps1 or verify_repo.sh).")
            print("[ctcp_orchestrate] use --skip-verify to bypass verify.")
            return 1
        if not resolved_pre_cmd:
            resolved_pre_cmd = default_verify_cmd
        if not resolved_post_cmd:
            resolved_post_cmd = default_verify_cmd

    requested_fixture_mode = str(fixture_mode or "auto").strip().lower() or "auto"
    if requested_fixture_mode not in {"auto", "synth", "path"}:
        print(f"[ctcp_orchestrate] unsupported --fixture-mode: {requested_fixture_mode}")
        return 1

    def _fixture_dialogue(qid: str, question: str, default_answer: str) -> str:
        return _ask_turn(qid=qid, question=question, default_answer=default_answer)

    try:
        fixture_result = v2p_fixtures.ensure_fixture(
            mode=requested_fixture_mode,
            repo=repo_path,
            run_dir=run_dir,
            user_dialogue=_fixture_dialogue,
            fixture_path=str(fixture_path or ""),
            runs_root=runs_root_path,
        )
    except Exception as exc:
        print(f"[ctcp_orchestrate] fixture selection failed: {exc}")
        return 1

    fixture_meta = fixture_result.to_json_dict()
    write_json(run_dir / "artifacts" / "fixture_meta.json", fixture_meta)
    append_event(
        run_dir,
        "Local Orchestrator",
        "fixture_selected",
        "artifacts/fixture_meta.json",
        mode=str(fixture_meta.get("mode", requested_fixture_mode)),
        source=str(fixture_meta.get("source", "")),
        fixture_path=str(fixture_meta.get("path", "")),
    )

    write_text(run_dir / "artifacts" / "dialogue.jsonl", "\n".join(json.dumps(x, ensure_ascii=False) for x in turns) + "\n")
    write_text(run_dir / "artifacts" / "dialogue_transcript.md", render_dialogue_transcript(turns))
    for row in turns:
        append_event(
            run_dir,
            "CTCP",
            "dialogue_turn",
            "artifacts/dialogue.jsonl",
            qid=str(row["qid"]),
            answer=str(row["answer"]),
            source=str(row["source"]),
        )

    plan_md = render_user_sim_plan_md(
        run_id=run_id,
        repo_path=repo_path,
        project=project_name,
        testkit_zip=zip_path,
        out_root=out_root_path,
        out_note=out_note,
        copy_csv=copy_csv,
        entry=entry,
        pre_verify_cmd=resolved_pre_cmd,
        post_verify_cmd=resolved_post_cmd,
        fixture_mode=str(fixture_meta.get("mode", requested_fixture_mode)),
        fixture_source=str(fixture_meta.get("source", "")),
        fixture_path=Path(str(fixture_meta.get("path", ""))),
        semantics_enabled=semantics_enabled,
        thresholds=thresholds,
        dialogue_mode=dialogue_mode,
    )
    write_text(run_dir / "artifacts" / "USER_SIM_PLAN.md", plan_md + "\n")
    append_event(run_dir, "Local Orchestrator", "user_sim_plan_written", "artifacts/USER_SIM_PLAN.md")

    pre_rc: int | None = None
    post_rc: int | None = None
    if not skip_verify:
        pre_rc, pre_out, pre_err = run_shell_cmd(resolved_pre_cmd, repo_path)
        write_text(run_dir / "logs" / "verify_pre.log", pre_out + ("\n" if pre_out and pre_err else "") + pre_err)
        append_event(
            run_dir,
            "Local Verifier",
            "verify_pre_complete",
            "logs/verify_pre.log",
            rc=int(pre_rc),
            cmd=resolved_pre_cmd,
            verify_entry=verify_entry,
        )
    else:
        append_event(run_dir, "Local Verifier", "verify_pre_skipped", "logs/verify_pre.log")

    testkit_result: dict[str, Any]
    testkit_error = ""
    try:
        testkit_result = testkit_runner.run_testkit(
            run_dir=run_dir,
            testkit_zip=zip_path,
            entry_cmd=entry,
            copy_csv=copy_csv,
            out_root=out_root_path,
            project=project_name,
            run_id=run_id,
            force=bool(force),
            semantics_enabled=semantics_enabled,
            fixture_path=Path(str(fixture_meta.get("path", ""))),
            forbidden_roots=[ROOT.resolve(), repo_path.resolve()],
        )
    except Exception as exc:
        testkit_result = {}
        testkit_error = str(exc)
    if testkit_result:
        write_text(run_dir / "logs" / "testkit_stdout.log", str(testkit_result.get("stdout", "")))
        write_text(run_dir / "logs" / "testkit_stderr.log", str(testkit_result.get("stderr", "")))
        append_event(
            run_dir,
            "Local Orchestrator",
            "testkit_run_complete",
            "logs/testkit_stdout.log",
            rc=int(testkit_result.get("testkit_rc", 1)),
            runtime_sec=float(testkit_result.get("runtime_sec", 0.0)),
        )
    else:
        append_event(run_dir, "Local Orchestrator", "testkit_run_failed", "logs/testkit_stderr.log", reason=testkit_error)

    if not skip_verify and not testkit_error:
        post_rc, post_out, post_err = run_shell_cmd(resolved_post_cmd, repo_path)
        write_text(run_dir / "logs" / "verify_post.log", post_out + ("\n" if post_out and post_err else "") + post_err)
        append_event(
            run_dir,
            "Local Verifier",
            "verify_post_complete",
            "logs/verify_post.log",
            rc=int(post_rc),
            cmd=resolved_post_cmd,
            verify_entry=verify_entry,
        )
    elif skip_verify:
        append_event(run_dir, "Local Verifier", "verify_post_skipped", "logs/verify_post.log")

    missing_outputs = list(testkit_result.get("missing_outputs", [])) if testkit_result else ["testkit_not_run"]
    required_outputs_ok = len(missing_outputs) == 0
    testkit_rc = int(testkit_result.get("testkit_rc", 1)) if testkit_result else 1
    verify_ok = True if skip_verify else (pre_rc == 0 and post_rc == 0)
    dialogue_ok = len(turns) >= 3
    passed = (testkit_rc == 0) and required_outputs_ok and verify_ok and (not testkit_error) and dialogue_ok

    report = {
        "schema_version": "ctcp-v2p-report-v1",
        "result": "PASS" if passed else "FAIL",
        "run_id": run_id,
        "rc": {
            "overall": 0 if passed else 1,
            "testkit": testkit_rc,
            "pre_verify": pre_rc,
            "post_verify": post_rc,
        },
        "timestamps": {
            "generated_at": now_iso(),
        },
        "paths": {
            "repo": str(repo_path.resolve()),
            "testkit_zip": str(zip_path.resolve()),
            "run_dir": str(run_dir.resolve()),
            "out_root": str(out_root_path.resolve()),
            "fixture_meta": "artifacts/fixture_meta.json",
            "fixture_path": str(fixture_meta.get("path", "")),
            "sandbox_dir": str(testkit_result.get("sandbox_dir", "")) if testkit_result else "",
            "dest_run_root": str(testkit_result.get("run_root", "")) if testkit_result else "",
            "dest_out_dir": str(testkit_result.get("out_dir", "")) if testkit_result else "",
        },
        "dialogue": {
            "mode": dialogue_mode,
            "turn_count": len(turns),
            "script": str(Path(dialogue_script).expanduser().resolve()) if str(dialogue_script or "").strip() else "",
        },
        "dialogue_turns": len(turns),
        "decisions": {
            "semantics_enabled": bool(semantics_enabled),
            "thresholds": thresholds,
            "fixture_mode": str(fixture_meta.get("mode", requested_fixture_mode)),
        },
        "fixture": fixture_meta,
        "metrics": dict(testkit_result.get("metrics", {})) if testkit_result else {},
        "verify": {
            "skip_verify": bool(skip_verify),
            "pre_cmd": resolved_pre_cmd,
            "post_cmd": resolved_post_cmd,
            "pre_rc": pre_rc,
            "post_rc": post_rc,
            "pre_log": "logs/verify_pre.log",
            "post_log": "logs/verify_post.log",
        },
        "testkit": {
            "entry": entry,
            "copy_csv": copy_csv,
            "rc": testkit_rc,
            "runtime_sec": float(testkit_result.get("runtime_sec", 0.0)) if testkit_result else 0.0,
            "copied": list(testkit_result.get("copied", [])) if testkit_result else [],
            "missing_outputs": missing_outputs,
            "metrics": dict(testkit_result.get("metrics", {})) if testkit_result else {},
            "stdout_log": "logs/testkit_stdout.log",
            "stderr_log": "logs/testkit_stderr.log",
            "error": testkit_error,
        },
        "acceptance": {
            "testkit_rc_zero": testkit_rc == 0,
            "required_outputs_exist": required_outputs_ok,
            "verify_ok": verify_ok,
            "dialogue_turns_at_least_3": dialogue_ok,
        },
    }
    write_json(run_dir / "artifacts" / "v2p_report.json", report)
    append_event(run_dir, "Local Orchestrator", "v2p_report_written", "artifacts/v2p_report.json", result=report["result"])

    print(f"[ctcp_orchestrate] run_dir={run_dir.resolve()}")
    print(f"[ctcp_orchestrate] out_dir={report['paths']['dest_out_dir']}")
    if passed:
        return 0
    return 1


def cmd_scaffold(*, out: str, name: str, profile: str, force: bool, runs_root: str) -> int:
    # BEHAVIOR_ID: B037
    t0 = dt.datetime.now()
    out_dir = resolve_scaffold_out_dir(out)
    project_name = str(name or "").strip() or out_dir.name
    if not project_name:
        print("[ctcp_orchestrate] scaffold requires --name or a resolvable --out folder name")
        return 1

    profile_name = str(profile or "minimal").strip().lower()
    template_root = ROOT / "templates" / "ctcp_ref"
    try:
        profile_doc = scaffold_tools.load_profile_manifest(template_root, profile_name)
        plan = scaffold_tools.build_scaffold_plan(
            out_dir=out_dir,
            project_name=project_name,
            profile_doc=profile_doc,
        )
    except Exception as exc:
        print(f"[ctcp_orchestrate] scaffold setup failed: {exc}")
        return 1

    runs_root_path = resolve_scaffold_runs_root(runs_root)
    run_dir = runs_root_path / get_repo_slug(ROOT) / default_scaffold_run_id(project_name)
    if run_dir.exists() and any(run_dir.iterdir()):
        print(f"[ctcp_orchestrate] scaffold run dir exists and not empty: {run_dir}")
        return 1

    ensure_layout(run_dir)
    write_text(
        run_dir / "TRACE.md",
        "\n".join(
            [
                f"# CTCP Scaffold Trace - {run_dir.name}",
                "",
                f"- Out: {out_dir.resolve()}",
                f"- Project: {project_name}",
                f"- Profile: {profile_name}",
                "",
                "## Events",
                "",
            ]
        ),
    )
    write_text(run_dir / "events.jsonl", "")
    append_event(run_dir, "Local Orchestrator", "scaffold_run_created", "TRACE.md")

    plan_md = render_scaffold_plan_markdown(
        profile=profile_name,
        out_dir=out_dir,
        project_name=project_name,
        force=bool(force),
        files=list(plan.get("files", [])),
    )
    write_text(run_dir / "artifacts" / "scaffold_plan.md", plan_md + "\n")
    append_event(run_dir, "Local Orchestrator", "scaffold_plan_written", "artifacts/scaffold_plan.md")

    tokens = {
        "PROJECT_NAME": project_name,
        "UTC_ISO": now_iso(),
        "PROFILE": profile_name,
    }

    scaffold_error = ""
    scaffold_result: dict[str, Any] = {}
    try:
        scaffold_result = scaffold_tools.scaffold_project(
            template_root=template_root,
            out_dir=out_dir,
            project_name=project_name,
            profile=profile_name,
            force=bool(force),
            tokens=tokens,
        )
        append_event(run_dir, "Local Orchestrator", "scaffold_written", "manifest.json")
    except Exception as exc:
        scaffold_error = str(exc)
        append_event(run_dir, "Local Orchestrator", "scaffold_failed", "artifacts/scaffold_report.json", reason=scaffold_error)

    verify_cmdline, verify_entry = scaffold_verify_cmd(out_dir)
    verify_rc: int | None = None
    verify_stdout_log = ""
    verify_stderr_log = ""
    if not scaffold_error and verify_cmdline:
        verify_rc, verify_out, verify_err = run_cmd(verify_cmdline, out_dir)
        out_log = run_dir / "logs" / "scaffold_verify.stdout.txt"
        err_log = run_dir / "logs" / "scaffold_verify.stderr.txt"
        write_text(out_log, verify_out)
        write_text(err_log, verify_err)
        verify_stdout_log = out_log.relative_to(run_dir).as_posix()
        verify_stderr_log = err_log.relative_to(run_dir).as_posix()
        append_event(
            run_dir,
            "Local Verifier",
            "scaffold_verify_complete",
            "artifacts/scaffold_report.json",
            rc=int(verify_rc),
            verify_entry=verify_entry,
        )

    elapsed_ms = int((dt.datetime.now() - t0).total_seconds() * 1000)
    validation = scaffold_result.get("validation", {"ok": False}) if scaffold_result else {"ok": False}
    passed = (not scaffold_error) and bool(validation.get("ok", False)) and (verify_rc in (None, 0))
    report = {
        "schema_version": "ctcp-scaffold-report-v1",
        "result": "PASS" if passed else "FAIL",
        "profile": profile_name,
        "project_name": project_name,
        "out_dir": str(out_dir.resolve()),
        "run_dir": str(run_dir.resolve()),
        "elapsed_ms": elapsed_ms,
        "written_count": int(scaffold_result.get("written_count", 0) if scaffold_result else 0),
        "written_files": list(scaffold_result.get("written_files", []) if scaffold_result else []),
        "removed_files": list(
            (scaffold_result.get("prepared", {}) or {}).get("removed_files", [])
            if scaffold_result
            else []
        ),
        "validation": validation,
        "verify": {
            "attempted": bool(verify_cmdline),
            "entry": verify_entry,
            "command": " ".join(verify_cmdline) if verify_cmdline else "",
            "exit_code": verify_rc,
            "stdout_log": verify_stdout_log,
            "stderr_log": verify_stderr_log,
        },
        "error": scaffold_error,
        "paths": {
            "trace": "TRACE.md",
            "plan": "artifacts/scaffold_plan.md",
            "report": "artifacts/scaffold_report.json",
        },
    }
    write_json(run_dir / "artifacts" / "scaffold_report.json", report)

    if passed:
        append_event(run_dir, "Local Orchestrator", "scaffold_pass", "artifacts/scaffold_report.json")
        print(f"[ctcp_orchestrate] scaffold out={out_dir.resolve()}")
        print(f"[ctcp_orchestrate] run_dir={run_dir.resolve()}")
        return 0

    append_event(run_dir, "Local Orchestrator", "scaffold_fail", "artifacts/scaffold_report.json")
    print(f"[ctcp_orchestrate] scaffold failed: {scaffold_error or 'validation/verify failed'}")
    print(f"[ctcp_orchestrate] run_dir={run_dir.resolve()}")
    return 1


def cmd_new_run(goal: str, run_id: str) -> int:
    rid = run_id.strip() or default_run_id()
    run_dir = make_run_dir(ROOT, rid)
    ensure_external_run_dir(run_dir)
    if run_dir.exists() and any(run_dir.iterdir()):
        print(f"[ctcp_orchestrate] run dir exists and not empty: {run_dir}")
        return 1

    ensure_layout(run_dir)
    ensure_repo_task_and_report(goal)
    sha, dirty = git_info()
    run_doc = {
        "schema_version": "ctcp-run-v1",
        "run_id": rid,
        "goal": goal,
        "status": "running",
        "verify_iterations": 0,
        "max_iterations": DEFAULT_MAX_ITERATIONS,
        "max_iterations_source": "default",
        "repo_slug": get_repo_slug(ROOT),
        "repo_root": str(ROOT.resolve()),
        "git_sha": sha,
        "dirty": dirty,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    repo_ref = {
        "schema_version": "ctcp-repo-ref-v1",
        "repo_slug": get_repo_slug(ROOT),
        "repo_root": str(ROOT.resolve()),
        "git_sha": sha,
        "dirty": dirty,
        "recorded_at": now_iso(),
    }
    write_json(run_dir / "RUN.json", run_doc)
    write_json(run_dir / "repo_ref.json", repo_ref)
    write_text(
        run_dir / "TRACE.md",
        "\n".join(
            [
                f"# CTCP Orchestrator Trace - {rid}",
                "",
                f"- Goal: {goal}",
                "- Mode: artifact-driven gate",
                "",
                "## Events",
                "",
            ]
        ),
    )
    write_text(
        run_dir / "events.jsonl",
        "",
    )
    ctcp_dispatch.ensure_dispatch_config(run_dir)
    write_text(
        run_dir / "artifacts" / "guardrails.template.md",
        "\n".join(
            [
                "# guardrails template",
                "find_mode: resolver_only",
                "max_files: 20",
                "max_total_bytes: 200000",
                "max_iterations: 3",
                "web_find_policy: allow_domains=..., max_queries=..., max_pages=...",
                "",
            ]
        ),
    )
    write_pointer(LAST_RUN_POINTER, run_dir)
    append_event(run_dir, "Local Orchestrator", "run_created", "RUN.json")
    print(f"[ctcp_orchestrate] run_dir={run_dir}")
    return 0


def load_run_doc(run_dir: Path) -> dict[str, Any]:
    run_file = run_dir / "RUN.json"
    if not run_file.exists():
        raise SystemExit(f"[ctcp_orchestrate] missing RUN.json: {run_file}")
    return read_json(run_file)


def save_run_doc(run_dir: Path, run_doc: dict[str, Any]) -> None:
    run_doc["updated_at"] = now_iso()
    write_json(run_dir / "RUN.json", run_doc)


def cmd_status(run_dir: Path) -> int:
    sync_outbox_fulfilled_events(run_dir)
    run_doc = load_run_doc(run_dir)
    gate = current_gate(run_dir, run_doc)
    max_iterations, max_iterations_source = resolve_max_iterations(run_dir)
    verify_iterations = int(run_doc.get("verify_iterations", 0) or 0)
    preview = ctcp_dispatch.dispatch_preview(run_dir, run_doc, gate)
    latest_outbox = ctcp_dispatch.latest_outbox_prompt_path(run_dir)
    print(f"[ctcp_orchestrate] run_dir={run_dir}")
    print(f"[ctcp_orchestrate] run_status={run_doc.get('status')}")
    print(
        f"[ctcp_orchestrate] iterations={verify_iterations}/{max_iterations} "
        f"(source={max_iterations_source})"
    )
    if gate["state"] == "blocked":
        print(f"[ctcp_orchestrate] blocked: {gate['reason']}")
    if latest_outbox:
        print(f"[ctcp_orchestrate] outbox prompt created: {latest_outbox}")
    if preview.get("status") == "budget_exceeded":
        print(f"[ctcp_orchestrate] STOP: budget_exceeded ({preview.get('reason', '')})")
    if str(run_doc.get("blocked_reason", "")) == "max_iterations_exceeded":
        print("[ctcp_orchestrate] STOP: max_iterations_exceeded")
    print(f"[ctcp_orchestrate] next={gate['state']}")
    print(f"[ctcp_orchestrate] owner={gate['owner']}")
    print(f"[ctcp_orchestrate] path={gate['path']}")
    print(f"[ctcp_orchestrate] reason={gate['reason']}")
    return 0


def cmd_advance(run_dir: Path, max_steps: int) -> int:
    ensure_layout(run_dir)
    sync_outbox_fulfilled_events(run_dir)
    run_doc = load_run_doc(run_dir)
    goal = str(run_doc.get("goal", "")).strip() or "unspecified-goal"
    steps = 0

    while steps < max_steps:
        run_doc = load_run_doc(run_dir)
        if str(run_doc.get("status", "")).lower() == "pass":
            print("[ctcp_orchestrate] run already PASS")
            return 0

        gate = current_gate(run_dir, run_doc)
        state = gate["state"]
        owner = gate["owner"]
        path = gate["path"]
        reason = gate["reason"]

        if state == "resolve_find_local":
            cmd = [sys.executable, str(ROOT / "scripts" / "resolve_workflow.py"), "--goal", goal, "--out", str(run_dir / "artifacts" / "find_result.json")]
            rc, out, err = run_cmd(cmd, ROOT)
            out_log = run_dir / "logs" / "find.stdout.log"
            err_log = run_dir / "logs" / "find.stderr.log"
            write_text(out_log, out)
            write_text(err_log, err)
            append_event(run_dir, "Local Orchestrator", "find_local_run", "artifacts/find_result.json", cmd=" ".join(cmd), rc=rc)
            if rc != 0:
                run_doc["status"] = "fail"
                run_doc["blocked_reason"] = "find_local_failed"
                save_run_doc(run_dir, run_doc)
                bundle = make_failure_bundle(run_dir)
                write_pointer(LAST_BUNDLE_POINTER, bundle)
                append_event(run_dir, "Local Orchestrator", "failure_bundle_created", "failure_bundle.zip")
                print(f"[ctcp_orchestrate] FAIL: local resolver failed, bundle={bundle}")
                return 1
            steps += 1
            continue

        if state == "ready_apply":
            patch, promoted = ensure_active_patch(run_dir)
            if patch is None:
                run_doc["status"] = "blocked"
                run_doc["blocked_reason"] = "missing diff.patch"
                save_run_doc(run_dir, run_doc)
                print("[ctcp_orchestrate] blocked: missing diff.patch for apply")
                return 0

            if promoted:
                append_event(
                    run_dir,
                    "Local Orchestrator",
                    "FIXER_PATCH_PROMOTED",
                    "artifacts/diff.patch",
                    source="artifacts/diff.patch.v2",
                )

            patch_marker_doc: dict[str, Any] = {}
            patch_marker = run_dir / "artifacts" / "patch_apply.json"
            if patch_marker.exists():
                try:
                    patch_marker_doc = read_json(patch_marker)
                except Exception:
                    patch_marker_doc = {}

            patch_sha = file_sha256(patch)
            prev_sha = str(patch_marker_doc.get("patch_sha256", ""))
            prev_ok = int(patch_marker_doc.get("rc", 1)) == 0 if patch_marker_doc else False
            last_applied_patch = run_dir / "artifacts" / "last_applied.patch"
            allow_managed_dirty = (
                str(run_doc.get("status", "")).lower() == "fail"
                and prev_ok
                and bool(prev_sha)
                and prev_sha != patch_sha
                and last_applied_patch.exists()
            )

            if allow_managed_dirty:
                iteration_tag = max(1, int(run_doc.get("verify_iterations", 0) or 0))
                backup = run_dir / "artifacts" / f"diff.patch.iter{iteration_tag}.bak"
                if not backup.exists():
                    shutil.copy2(last_applied_patch, backup)
                    append_event(
                        run_dir,
                        "Local Orchestrator",
                        "PATCH_BACKUP_CREATED",
                        backup.relative_to(run_dir).as_posix(),
                        source="artifacts/last_applied.patch",
                    )

            dirty, dirty_rows = repo_dirty_status()
            if dirty and not allow_managed_dirty:
                run_doc["status"] = "blocked"
                run_doc["blocked_reason"] = "repo_dirty_before_apply"
                save_run_doc(run_dir, run_doc)
                append_event(
                    run_dir,
                    "Local Orchestrator",
                    "APPLY_BLOCKED_DIRTY",
                    "artifacts/diff.patch",
                    dirty_count=len(dirty_rows),
                )
                append_trace(
                    run_dir,
                    "Local Orchestrator: blocked apply due to dirty repo; "
                    f"dirty_preview={_tail_summary(chr(10).join(dirty_rows), max_lines=8, max_chars=320)}",
                )
                print("[ctcp_orchestrate] blocked: repo dirty before apply (clean workspace and retry)")
                return 0

            patch_text = patch.read_text(encoding="utf-8", errors="replace")
            policy_doc, policy_source, policy_note = resolve_patch_policy(run_dir)
            result = apply_patch_safely(ROOT, patch_text, policy_doc)

            out_log = run_dir / "logs" / "patch_apply.stdout.log"
            err_log = run_dir / "logs" / "patch_apply.stderr.log"
            write_text(out_log, result.stdout or "")
            write_text(err_log, result.stderr or "")
            trace_cmd = result.command.split() if result.command else [f"patch_first:{result.stage}"]
            append_command_trace(
                run_dir,
                phase="patch_apply",
                cmd=trace_cmd,
                rc=0 if result.ok else 1,
                stdout=result.stdout,
                stderr=result.stderr,
                stdout_log=out_log,
                stderr_log=err_log,
            )

            if (not result.ok) and prev_ok and prev_sha and prev_sha != patch_sha:
                if last_applied_patch.exists() and result.code in {"PATCH_GIT_CHECK_FAIL", "PATCH_APPLY_FAIL"}:
                    append_event(
                        run_dir,
                        "Local Orchestrator",
                        "PATCH_REVERT_STARTED",
                        "artifacts/last_applied.patch",
                        reason="retry apply after failure",
                    )
                    revert_cmd = ["git", "apply", "-R", str(last_applied_patch)]
                    rr, rout, rerr = run_cmd(revert_cmd, ROOT)
                    revert_out = run_dir / "logs" / "patch_revert.stdout.log"
                    revert_err = run_dir / "logs" / "patch_revert.stderr.log"
                    write_text(revert_out, rout)
                    write_text(revert_err, rerr)
                    append_command_trace(
                        run_dir,
                        phase="patch_revert",
                        cmd=revert_cmd,
                        rc=rr,
                        stdout=rout,
                        stderr=rerr,
                        stdout_log=revert_out,
                        stderr_log=revert_err,
                    )
                    if rr == 0:
                        append_event(
                            run_dir,
                            "Local Orchestrator",
                            "PATCH_REVERTED",
                            "artifacts/last_applied.patch",
                            cmd=" ".join(revert_cmd),
                            rc=rr,
                        )
                        result = apply_patch_safely(ROOT, patch_text, policy_doc)
                        out_log = run_dir / "logs" / "patch_apply_retry.stdout.log"
                        err_log = run_dir / "logs" / "patch_apply_retry.stderr.log"
                        write_text(out_log, result.stdout or "")
                        write_text(err_log, result.stderr or "")
                        trace_cmd = result.command.split() if result.command else [f"patch_first:{result.stage}"]
                        append_command_trace(
                            run_dir,
                            phase="patch_apply_retry",
                            cmd=trace_cmd,
                            rc=0 if result.ok else 1,
                            stdout=result.stdout,
                            stderr=result.stderr,
                            stdout_log=out_log,
                            stderr_log=err_log,
                        )
                    else:
                        append_event(
                            run_dir,
                            "Local Orchestrator",
                            "PATCH_REVERT_FAILED",
                            "artifacts/last_applied.patch",
                            cmd=" ".join(revert_cmd),
                            rc=rr,
                        )

            rc = 0 if result.ok else 1
            write_json(
                run_dir / "artifacts" / "patch_apply.json",
                {
                    "patch_sha256": patch_sha,
                    "cmd": result.command or f"patch_first:{result.stage}",
                    "rc": rc,
                    "stage": result.stage,
                    "code": result.code,
                    "message": result.message,
                    "touched_files": list(result.touched_files),
                    "added_lines": int(result.added_lines),
                    "stdout_log": out_log.as_posix(),
                    "stderr_log": err_log.as_posix(),
                    "applied_at": now_iso(),
                },
            )
            append_event(
                run_dir,
                "Local Orchestrator",
                "patch_apply",
                "artifacts/diff.patch",
                rc=rc,
                stage=result.stage,
                code=result.code,
            )
            if not result.ok:
                review_path = write_patch_rejection_review(
                    run_dir,
                    patch_sha=patch_sha,
                    policy_source=policy_source,
                    policy_note=policy_note,
                    result=result,
                )
                write_json(
                    run_dir / "artifacts" / "patch_rejection.json",
                    {
                        "ts": now_iso(),
                        "patch_sha256": patch_sha,
                        "policy_source": policy_source,
                        "policy_note": policy_note,
                        "result": result.to_dict(),
                        "review_path": review_path.relative_to(run_dir).as_posix(),
                    },
                )

                max_iterations, max_source = resolve_max_iterations(run_dir)
                verify_iteration = int(run_doc.get("verify_iterations", 0) or 0)
                paths = {
                    "trace": "TRACE.md",
                    "verify_report": "artifacts/verify_report.json",
                    "bundle": "failure_bundle.zip",
                    "patch": "artifacts/diff.patch",
                    "patch_review": "reviews/review_patch.md",
                    "stdout_log": out_log.relative_to(run_dir).as_posix(),
                    "stderr_log": err_log.relative_to(run_dir).as_posix(),
                }
                if (run_dir / "artifacts" / "PLAN.md").exists():
                    paths["plan"] = "artifacts/PLAN.md"
                write_json(
                    run_dir / "artifacts" / "verify_report.json",
                    {
                        "result": "FAIL",
                        "gate": "patch_first",
                        "iteration": verify_iteration,
                        "max_iterations": max_iterations,
                        "max_iterations_source": max_source,
                        "patch_sha256": patch_sha,
                        "commands": [
                            {
                                "cmd": result.command or f"patch_first:{result.stage}",
                                "exit_code": 1,
                                "stdout_log": out_log.relative_to(run_dir).as_posix(),
                                "stderr_log": err_log.relative_to(run_dir).as_posix(),
                            }
                        ],
                        "failures": [
                            {
                                "kind": "patch_first",
                                "id": result.code,
                                "message": result.message,
                            }
                        ],
                        "paths": paths,
                        "artifacts": paths,
                    },
                )

                run_doc["status"] = "blocked"
                run_doc["blocked_reason"] = f"patch_first_rejected:{result.code}"
                save_run_doc(run_dir, run_doc)
                append_event(
                    run_dir,
                    "Local Orchestrator",
                    "PATCH_REJECTED",
                    "artifacts/diff.patch",
                    code=result.code,
                    stage=result.stage,
                    review=review_path.relative_to(run_dir).as_posix(),
                )

                bundle, mode_before_dispatch = ensure_failure_bundle(run_dir)
                fail_gate = current_gate(run_dir, run_doc)
                dispatch = ctcp_dispatch.dispatch_once(run_dir, run_doc, fail_gate, ROOT)
                dispatch_status = str(dispatch.get("status", ""))
                if dispatch_status == "outbox_created":
                    outbox_path = str(dispatch.get("path", ""))
                    append_event(
                        run_dir,
                        str(dispatch.get("role", "fixer")),
                        "OUTBOX_PROMPT_CREATED",
                        outbox_path,
                        target_path=str(dispatch.get("target_path", "")),
                        action=str(dispatch.get("action", "")),
                        provider=str(dispatch.get("provider", "")),
                    )
                    print(f"[ctcp_orchestrate] outbox prompt created: {outbox_path}")
                elif dispatch_status == "outbox_exists":
                    outbox_path = str(dispatch.get("path", ""))
                    if outbox_path:
                        print(f"[ctcp_orchestrate] waiting for outbox response: {outbox_path}")
                elif dispatch_status == "budget_exceeded":
                    append_event(
                        run_dir,
                        "Local Orchestrator",
                        "STOP_BUDGET_EXCEEDED",
                        "artifacts/dispatch_config.json",
                        reason=str(dispatch.get("reason", "")),
                        provider=str(dispatch.get("provider", "")),
                    )
                fallback_path, created_fallback = ensure_fixer_outbox_prompt(
                    run_dir,
                    goal=goal,
                    reason=str(run_doc.get("blocked_reason", "patch_first_rejected")),
                )
                if created_fallback:
                    append_event(
                        run_dir,
                        "fixer",
                        "OUTBOX_PROMPT_CREATED",
                        fallback_path,
                        target_path="artifacts/diff.patch",
                        action="fix_patch",
                        provider="manual_outbox_fallback",
                    )
                bundle, mode_after_dispatch = ensure_failure_bundle(run_dir, require_outbox_prompt=True)
                final_mode = (
                    mode_after_dispatch
                    if mode_after_dispatch in {"created", "recreated"}
                    else mode_before_dispatch
                )
                append_event(
                    run_dir,
                    "Local Orchestrator",
                    "BUNDLE_CREATED",
                    "failure_bundle.zip",
                    mode=final_mode,
                )
                write_pointer(LAST_BUNDLE_POINTER, bundle)
                print(f"[ctcp_orchestrate] blocked: patch-first gate rejected diff.patch, bundle={bundle}")
                return 1

            shutil.copy2(patch, run_dir / "artifacts" / "last_applied.patch")
            steps += 1
            continue

        if state == "ready_verify":
            max_iterations, max_source = resolve_max_iterations(run_dir)
            verify_iterations = int(run_doc.get("verify_iterations", 0) or 0)
            if verify_iterations >= max_iterations:
                run_doc["status"] = "blocked"
                run_doc["blocked_reason"] = "max_iterations_exceeded"
                run_doc["max_iterations"] = max_iterations
                run_doc["max_iterations_source"] = max_source
                save_run_doc(run_dir, run_doc)
                append_event(
                    run_dir,
                    "Local Verifier",
                    "STOP_MAX_ITERATIONS",
                    "artifacts/verify_report.json",
                    verify_iterations=verify_iterations,
                    max_iterations=max_iterations,
                    source=max_source,
                )
                print(
                    f"[ctcp_orchestrate] STOP: max_iterations_exceeded "
                    f"({verify_iterations}/{max_iterations}, source={max_source})"
                )
                return 0

            iteration = verify_iterations + 1
            run_doc["verify_iterations"] = iteration
            run_doc["max_iterations"] = max_iterations
            run_doc["max_iterations_source"] = max_source
            save_run_doc(run_dir, run_doc)

            cmd = verify_cmd()
            append_event(
                run_dir,
                "Local Verifier",
                "VERIFY_STARTED",
                "artifacts/verify_report.json",
                cmd=" ".join(cmd),
                iteration=iteration,
                max_iterations=max_iterations,
            )
            rc, out, err = run_cmd(cmd, ROOT, env=verify_run_env())
            out_log = run_dir / "logs" / "verify.stdout.log"
            err_log = run_dir / "logs" / "verify.stderr.log"
            write_text(out_log, out)
            write_text(err_log, err)
            append_command_trace(
                run_dir,
                phase=f"verify(iteration={iteration})",
                cmd=cmd,
                rc=rc,
                stdout=out,
                stderr=err,
                stdout_log=out_log,
                stderr_log=err_log,
            )

            patch, _ = ensure_active_patch(run_dir)
            patch_sha = file_sha256(patch) if patch is not None else ""
            paths = {
                "trace": "TRACE.md",
                "verify_report": "artifacts/verify_report.json",
                "bundle": "failure_bundle.zip" if rc != 0 else "",
                "stdout_log": out_log.relative_to(run_dir).as_posix(),
                "stderr_log": err_log.relative_to(run_dir).as_posix(),
            }
            if (run_dir / "artifacts" / "PLAN.md").exists():
                paths["plan"] = "artifacts/PLAN.md"
            if (run_dir / "artifacts" / "diff.patch").exists():
                paths["patch"] = "artifacts/diff.patch"

            report = {
                "result": "PASS" if rc == 0 else "FAIL",
                "gate": "lite",
                "iteration": iteration,
                "max_iterations": max_iterations,
                "patch_sha256": patch_sha,
                "commands": [
                    {
                        "cmd": " ".join(cmd),
                        "exit_code": rc,
                        "stdout_log": out_log.relative_to(run_dir).as_posix(),
                        "stderr_log": err_log.relative_to(run_dir).as_posix(),
                    }
                ],
                "failures": [] if rc == 0 else _extract_verify_failures(out, err),
                "paths": paths,
                "artifacts": paths,
            }
            write_json(run_dir / "artifacts" / "verify_report.json", report)
            append_event(
                run_dir,
                "Local Verifier",
                "verify_complete",
                "artifacts/verify_report.json",
                rc=rc,
                iteration=iteration,
            )

            if rc != 0:
                append_event(
                    run_dir,
                    "Local Verifier",
                    "VERIFY_FAILED",
                    "artifacts/verify_report.json",
                    rc=rc,
                    iteration=iteration,
                )
                run_doc["status"] = "fail"
                run_doc["blocked_reason"] = "verify_failed"
                save_run_doc(run_dir, run_doc)
                bundle, mode_before_dispatch = ensure_failure_bundle(run_dir)
                fail_gate = current_gate(run_dir, run_doc)
                dispatch = ctcp_dispatch.dispatch_once(run_dir, run_doc, fail_gate, ROOT)
                dispatch_status = str(dispatch.get("status", ""))
                if dispatch_status == "outbox_created":
                    outbox_path = str(dispatch.get("path", ""))
                    append_event(
                        run_dir,
                        str(dispatch.get("role", "fixer")),
                        "OUTBOX_PROMPT_CREATED",
                        outbox_path,
                        target_path=str(dispatch.get("target_path", "")),
                        action=str(dispatch.get("action", "")),
                        provider=str(dispatch.get("provider", "")),
                    )
                    print(f"[ctcp_orchestrate] outbox prompt created: {outbox_path}")
                elif dispatch_status == "outbox_exists":
                    outbox_path = str(dispatch.get("path", ""))
                    if outbox_path:
                        print(f"[ctcp_orchestrate] waiting for outbox response: {outbox_path}")
                elif dispatch_status == "budget_exceeded":
                    append_event(
                        run_dir,
                        "Local Orchestrator",
                        "STOP_BUDGET_EXCEEDED",
                        "artifacts/dispatch_config.json",
                        reason=str(dispatch.get("reason", "")),
                        provider=str(dispatch.get("provider", "")),
                    )
                fallback_path, created_fallback = ensure_fixer_outbox_prompt(
                    run_dir,
                    goal=goal,
                    reason=str(run_doc.get("blocked_reason", "verify_failed")),
                )
                if created_fallback:
                    append_event(
                        run_dir,
                        "fixer",
                        "OUTBOX_PROMPT_CREATED",
                        fallback_path,
                        target_path="artifacts/diff.patch",
                        action="fix_patch",
                        provider="manual_outbox_fallback",
                    )
                bundle, mode_after_dispatch = ensure_failure_bundle(run_dir, require_outbox_prompt=True)
                final_mode = (
                    mode_after_dispatch
                    if mode_after_dispatch in {"created", "recreated"}
                    else mode_before_dispatch
                )
                append_event(
                    run_dir,
                    "Local Verifier",
                    "BUNDLE_CREATED",
                    "failure_bundle.zip",
                    mode=final_mode,
                )
                write_pointer(LAST_BUNDLE_POINTER, bundle)
                print(f"[ctcp_orchestrate] FAIL: verify failed, bundle={bundle}")
                return 1

            run_doc["status"] = "pass"
            run_doc.pop("blocked_reason", None)
            save_run_doc(run_dir, run_doc)
            append_event(
                run_dir,
                "Local Verifier",
                "VERIFY_PASSED",
                "artifacts/verify_report.json",
                rc=rc,
                iteration=iteration,
            )
            append_event(run_dir, "Local Verifier", "run_pass", "artifacts/verify_report.json")
            print("[ctcp_orchestrate] PASS: verify succeeded")
            return 0

        if state == "pass":
            return cmd_status(run_dir)

        dispatch = ctcp_dispatch.dispatch_once(run_dir, run_doc, gate, ROOT)
        dispatch_status = str(dispatch.get("status", ""))

        if dispatch_status == "executed":
            append_event(
                run_dir,
                str(dispatch.get("role", "librarian")),
                "LOCAL_EXEC_COMPLETED",
                str(dispatch.get("target_path", "")),
                provider=str(dispatch.get("provider", "")),
                cmd=str(dispatch.get("cmd", "")),
                rc=int(dispatch.get("rc", 0)),
            )
            steps += 1
            continue

        if dispatch_status == "outbox_created":
            outbox_path = str(dispatch.get("path", ""))
            append_event(
                run_dir,
                str(dispatch.get("role", "manual_outbox")),
                "OUTBOX_PROMPT_CREATED",
                outbox_path,
                target_path=str(dispatch.get("target_path", "")),
                action=str(dispatch.get("action", "")),
                provider=str(dispatch.get("provider", "")),
            )
            run_doc["status"] = "fail" if state == "fail" else "blocked"
            run_doc["blocked_reason"] = reason
            save_run_doc(run_dir, run_doc)
            print(f"[ctcp_orchestrate] blocked: {reason} (owner={owner}, path={path})")
            print(f"[ctcp_orchestrate] outbox prompt created: {outbox_path}")
            return 0

        if dispatch_status == "outbox_exists":
            run_doc["status"] = "fail" if state == "fail" else "blocked"
            run_doc["blocked_reason"] = reason
            save_run_doc(run_dir, run_doc)
            existing_path = str(dispatch.get("path", ""))
            print(f"[ctcp_orchestrate] blocked: {reason} (owner={owner}, path={path})")
            if existing_path:
                print(f"[ctcp_orchestrate] waiting for outbox response: {existing_path}")
            return 0

        if dispatch_status == "budget_exceeded":
            run_doc["status"] = "blocked"
            run_doc["blocked_reason"] = "budget_exceeded"
            save_run_doc(run_dir, run_doc)
            append_event(
                run_dir,
                "Local Orchestrator",
                "STOP_BUDGET_EXCEEDED",
                "artifacts/dispatch_config.json",
                reason=str(dispatch.get("reason", "")),
                provider=str(dispatch.get("provider", "")),
            )
            print(f"[ctcp_orchestrate] STOP: budget_exceeded ({dispatch.get('reason', '')})")
            return 0

        if dispatch_status == "exec_failed":
            run_doc["status"] = "blocked"
            run_doc["blocked_reason"] = str(dispatch.get("reason", "provider_exec_failed"))
            save_run_doc(run_dir, run_doc)
            append_event(
                run_dir,
                str(dispatch.get("role", "librarian")),
                "LOCAL_EXEC_FAILED",
                str(dispatch.get("target_path", "")),
                provider=str(dispatch.get("provider", "")),
                cmd=str(dispatch.get("cmd", "")),
                rc=int(dispatch.get("rc", 1)),
            )
            print(f"[ctcp_orchestrate] blocked: {dispatch.get('reason', 'provider exec failed')}")
            return 0

        if state == "fail":
            print("[ctcp_orchestrate] run already FAIL")
            return 1

        run_doc["status"] = "blocked"
        run_doc["blocked_reason"] = reason
        save_run_doc(run_dir, run_doc)
        append_event(run_dir, "Local Orchestrator", "blocked", path, owner=owner, reason=reason)
        print(f"[ctcp_orchestrate] blocked: {reason} (owner={owner}, path={path})")
        return 0

    print(f"[ctcp_orchestrate] reached max-steps={max_steps}")
    return cmd_status(run_dir)


def main() -> int:
    ap = argparse.ArgumentParser(description="CTCP local orchestrator (artifact-driven state machine)")
    sub = ap.add_subparsers(dest="cmd")

    p_new = sub.add_parser("new-run", help="Create a new external run directory")
    p_new.add_argument("--goal", required=True)
    p_new.add_argument("--run-id", default="")

    p_status = sub.add_parser("status", help="Show current gate and missing artifact")
    p_status.add_argument("--run-dir", default="")

    p_adv = sub.add_parser("advance", help="Advance one-or-more steps by artifact presence")
    p_adv.add_argument("--run-dir", default="")
    p_adv.add_argument("--max-steps", type=int, default=16)

    p_cos = sub.add_parser(
        "cos-user-v2p",
        help="Run external V2P testkit with CTCP dialogue, evidence and fixed destination copy",
    )
    p_cos.add_argument("--repo", required=True, help="Target project repo path to verify before/after testkit run")
    p_cos.add_argument("--project", required=True, help="Project name used for destination folder")
    p_cos.add_argument("--testkit-zip", required=True, help="External testkit zip file path")
    p_cos.add_argument(
        "--out-root",
        default="",
        help="Destination root (default: D:/v2p_tests, with CI-safe fallback when unavailable)",
    )
    p_cos.add_argument(
        "--runs-root",
        default="",
        help="Run evidence root (default: CTCP_RUNS_ROOT or CTCP default runs root)",
    )
    p_cos.add_argument("--entry", default="python run_all.py", help="Testkit entry command")
    p_cos.add_argument(
        "--copy",
        default="out/scorecard.json,out/eval.json,out/cloud.ply,out/cloud_sem.ply",
        help="CSV of relative output files to copy from testkit workspace",
    )
    p_cos.add_argument(
        "--fixture-mode",
        default="auto",
        choices=["auto", "synth", "path"],
        help="Fixture acquisition mode for V2P flow",
    )
    p_cos.add_argument(
        "--fixture-path",
        default="",
        help="Fixture directory path (required when --fixture-mode=path)",
    )
    p_cos.add_argument("--dialogue-script", default="", help="JSONL script for deterministic dialogue answers")
    p_cos.add_argument("--agent-cmd", default="", help="Live agent command for answering dialogue questions")
    p_cos.add_argument("--pre-verify-cmd", default="", help="Verify command executed inside --repo before testkit run")
    p_cos.add_argument("--post-verify-cmd", default="", help="Verify command executed inside --repo after testkit run")
    p_cos.add_argument("--skip-verify", action="store_true", help="Skip repo verify commands")
    p_cos.add_argument("--force", action="store_true", help="Overwrite destination run folder if already exists")

    p_scaffold = sub.add_parser("scaffold", help="Generate a reference CTCP project skeleton")
    p_scaffold.add_argument("--out", required=True, help="Output directory for the generated project")
    p_scaffold.add_argument("--name", default="", help="Project name (default: basename of --out)")
    p_scaffold.add_argument(
        "--profile",
        default="minimal",
        choices=["minimal", "standard", "full"],
        help="Scaffold profile",
    )
    p_scaffold.add_argument("--force", action="store_true", help="Regenerate into an existing output directory")
    p_scaffold.add_argument(
        "--runs-root",
        default="",
        help="Optional run root for scaffold evidence (default: CTCP_RUNS_ROOT or simlab/_runs)",
    )

    p_scaffold_pc = sub.add_parser("scaffold-pointcloud", help="Generate a point-cloud project scaffold from templates")
    p_scaffold_pc.add_argument("--out", required=True, help="Output directory (project root)")
    p_scaffold_pc.add_argument("--name", default="", help="Project name (default: basename of --out)")
    p_scaffold_pc.add_argument(
        "--profile",
        default="minimal",
        choices=["minimal", "standard"],
        help="Pointcloud scaffold profile",
    )
    p_scaffold_pc.add_argument("--force", action="store_true", help="Overwrite existing --out directory contents")
    p_scaffold_pc.add_argument(
        "--runs-root",
        default="",
        help="Optional run root for scaffold evidence (default: CTCP_RUNS_ROOT or simlab/_runs)",
    )
    p_scaffold_pc.add_argument("--dialogue-script", default="", help="JSONL script for deterministic dialogue answers")
    p_scaffold_pc.add_argument("--agent-cmd", default="", help="Live agent command for answering dialogue questions")

    args = ap.parse_args()
    if args.cmd == "new-run":
        return cmd_new_run(goal=args.goal, run_id=args.run_id)
    if args.cmd == "status":
        return cmd_status(resolve_run_dir(args.run_dir))
    if args.cmd == "advance":
        return cmd_advance(resolve_run_dir(args.run_dir), max_steps=max(1, int(args.max_steps)))
    if args.cmd == "cos-user-v2p":
        return cmd_cos_user_v2p(
            repo=args.repo,
            project=args.project,
            testkit_zip=args.testkit_zip,
            out_root=args.out_root,
            runs_root=args.runs_root,
            entry=args.entry,
            copy_csv=args.copy,
            fixture_mode=args.fixture_mode,
            fixture_path=args.fixture_path,
            dialogue_script=args.dialogue_script,
            agent_cmd=args.agent_cmd,
            pre_verify_cmd=args.pre_verify_cmd,
            post_verify_cmd=args.post_verify_cmd,
            skip_verify=bool(args.skip_verify),
            force=bool(args.force),
        )
    if args.cmd == "scaffold":
        return cmd_scaffold(
            out=args.out,
            name=args.name,
            profile=args.profile,
            force=bool(args.force),
            runs_root=args.runs_root,
        )
    if args.cmd == "scaffold-pointcloud":
        return cmd_scaffold_pointcloud(
            out=args.out,
            name=args.name,
            profile=args.profile,
            force=bool(args.force),
            runs_root=args.runs_root,
            dialogue_script=args.dialogue_script,
            agent_cmd=args.agent_cmd,
        )

    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
