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
DEFAULT_MAX_ITERATIONS = 3

try:
    from tools.run_paths import get_repo_slug, make_run_dir
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT))
    from tools.run_paths import get_repo_slug, make_run_dir

try:
    import ctcp_dispatch
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ctcp_dispatch


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


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
    artifacts = run_dir / "artifacts"
    reviews = run_dir / "reviews"
    patch = artifacts / "diff.patch"
    patch_marker = artifacts / "patch_apply.json"
    verify_report = artifacts / "verify_report.json"

    if str(run_doc.get("status", "")).lower() == "pass":
        return {"state": "pass", "owner": "", "path": "", "reason": "run already pass"}
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
    if verdict_contract != "APPROVE" or verdict_cost != "APPROVE":
        return {
            "state": "blocked",
            "owner": "Chair/Planner",
            "path": "reviews/review_contract.md,reviews/review_cost.md",
            "reason": f"waiting for APPROVE reviews (contract={verdict_contract}, cost={verdict_cost})",
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
    bundle = run_dir / "failure_bundle.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in run_dir.rglob("*"):
            if p.is_file() and p != bundle:
                zf.write(p, p.relative_to(run_dir).as_posix())
    return bundle


def _required_bundle_entries(run_dir: Path) -> list[str]:
    required = ["TRACE.md", "artifacts/verify_report.json", "events.jsonl"]
    if (run_dir / "artifacts" / "PLAN.md").exists():
        required.append("artifacts/PLAN.md")
    if (run_dir / "artifacts" / "diff.patch").exists():
        required.append("artifacts/diff.patch")
    for rel_dir in ("reviews", "outbox"):
        base = run_dir / rel_dir
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file():
                required.append(p.relative_to(run_dir).as_posix())
    return required


def _bundle_contains(bundle: Path, required_entries: list[str]) -> bool:
    if not bundle.exists():
        return False
    try:
        with zipfile.ZipFile(bundle, "r") as zf:
            names = set(zf.namelist())
    except Exception:
        return False
    return all(x in names for x in required_entries)


def ensure_failure_bundle(run_dir: Path) -> tuple[Path, str]:
    bundle = run_dir / "failure_bundle.zip"
    required_entries = _required_bundle_entries(run_dir)
    if _bundle_contains(bundle, required_entries):
        return bundle, "validated"

    mode = "created" if not bundle.exists() else "recreated"
    bundle = make_failure_bundle(run_dir)
    if not _bundle_contains(bundle, required_entries):
        with zipfile.ZipFile(bundle, "r") as zf:
            names = set(zf.namelist())
        missing = [x for x in required_entries if x not in names]
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


def cmd_new_run(goal: str, run_id: str) -> int:
    rid = run_id.strip() or default_run_id()
    run_dir = make_run_dir(ROOT, rid)
    ensure_external_run_dir(run_dir)
    if run_dir.exists() and any(run_dir.iterdir()):
        print(f"[ctcp_orchestrate] run dir exists and not empty: {run_dir}")
        return 1

    ensure_layout(run_dir)
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

            cmd = ["git", "apply", str(patch)]
            rc, out, err = run_cmd(cmd, ROOT)
            out_log = run_dir / "logs" / "patch_apply.stdout.log"
            err_log = run_dir / "logs" / "patch_apply.stderr.log"
            write_text(out_log, out)
            write_text(err_log, err)
            append_command_trace(
                run_dir,
                phase="patch_apply",
                cmd=cmd,
                rc=rc,
                stdout=out,
                stderr=err,
                stdout_log=out_log,
                stderr_log=err_log,
            )

            if rc != 0 and prev_ok and prev_sha and prev_sha != patch_sha:
                if last_applied_patch.exists():
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
                        cmd = ["git", "apply", str(patch)]
                        rc, out, err = run_cmd(cmd, ROOT)
                        out_log = run_dir / "logs" / "patch_apply_retry.stdout.log"
                        err_log = run_dir / "logs" / "patch_apply_retry.stderr.log"
                        write_text(out_log, out)
                        write_text(err_log, err)
                        append_command_trace(
                            run_dir,
                            phase="patch_apply_retry",
                            cmd=cmd,
                            rc=rc,
                            stdout=out,
                            stderr=err,
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

            write_json(
                run_dir / "artifacts" / "patch_apply.json",
                {
                    "patch_sha256": patch_sha,
                    "cmd": " ".join(cmd),
                    "rc": rc,
                    "stdout_log": out_log.as_posix(),
                    "stderr_log": err_log.as_posix(),
                    "applied_at": now_iso(),
                },
            )
            append_event(run_dir, "Local Orchestrator", "patch_apply", "artifacts/diff.patch", rc=rc)
            if rc != 0:
                run_doc["status"] = "blocked"
                run_doc["blocked_reason"] = "patch_apply_failed"
                save_run_doc(run_dir, run_doc)
                print("[ctcp_orchestrate] blocked: patch apply failed (see logs/patch_apply.*.log)")
                return 0
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
            rc, out, err = run_cmd(cmd, ROOT, env={"CTCP_SKIP_LITE_REPLAY": "1"})
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
                bundle, mode = ensure_failure_bundle(run_dir)
                append_event(
                    run_dir,
                    "Local Verifier",
                    "BUNDLE_CREATED",
                    "failure_bundle.zip",
                    mode=mode,
                )
                write_pointer(LAST_BUNDLE_POINTER, bundle)
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
            run_doc["blocked_reason"] = str(dispatch.get("reason", "local_exec_failed"))
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
            print(f"[ctcp_orchestrate] blocked: {dispatch.get('reason', 'local_exec failed')}")
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

    args = ap.parse_args()
    if args.cmd == "new-run":
        return cmd_new_run(goal=args.goal, run_id=args.run_id)
    if args.cmd == "status":
        return cmd_status(resolve_run_dir(args.run_dir))
    if args.cmd == "advance":
        return cmd_advance(resolve_run_dir(args.run_dir), max_steps=max(1, int(args.max_steps)))

    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
