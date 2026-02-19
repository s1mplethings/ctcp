#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POINTERS_DIR = ROOT / "meta" / "run_pointers"
LAST_RUN_POINTER = POINTERS_DIR / "LAST_RUN.txt"
LAST_BUNDLE_POINTER = POINTERS_DIR / "LAST_BUNDLE.txt"

try:
    from tools.run_paths import get_repo_slug, make_run_dir
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT))
    from tools.run_paths import get_repo_slug, make_run_dir


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def run_cmd(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
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
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-orchestrate")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def normalize_find_mode(value: str) -> str:
    v = (value or "").strip().lower()
    if v in {"resolver_only", "resolver_plus_web"}:
        return v
    return "resolver_only"


def write_pointer(path: Path, target: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(target.resolve()) + "\n", encoding="utf-8")


def resolve_run_dir(raw: str) -> Path:
    if raw.strip():
        return Path(raw).expanduser().resolve()
    if not LAST_RUN_POINTER.exists():
        raise SystemExit("[ctcp_orchestrate] missing LAST_RUN pointer; pass --run-dir")
    pointed = LAST_RUN_POINTER.read_text(encoding="utf-8").strip()
    if not pointed:
        raise SystemExit("[ctcp_orchestrate] LAST_RUN pointer is empty; pass --run-dir")
    return Path(pointed).expanduser().resolve()


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
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    (run_dir / "snapshot").mkdir(parents=True, exist_ok=True)


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


def current_gate(run_dir: Path, run_doc: dict[str, Any]) -> dict[str, str]:
    if str(run_doc.get("status", "")).lower() == "pass":
        return {"state": "pass", "owner": "", "path": "", "reason": "run already pass"}
    if str(run_doc.get("status", "")).lower() == "fail":
        return {"state": "fail", "owner": "Fixer", "path": "failure_bundle.zip", "reason": str(run_doc.get("blocked_reason", "run failed"))}

    artifacts = run_dir / "artifacts"
    reviews = run_dir / "reviews"

    guardrails = artifacts / "guardrails.md"
    analysis = artifacts / "analysis.md"
    find_result = artifacts / "find_result.json"
    find_web = artifacts / "find_web.json"
    file_request = artifacts / "file_request.json"
    context_pack = artifacts / "context_pack.json"
    plan_draft = artifacts / "PLAN_draft.md"
    plan = artifacts / "PLAN.md"
    patch = artifacts / "diff.patch"
    review_contract = reviews / "review_contract.md"
    review_cost = reviews / "review_cost.md"
    patch_marker = artifacts / "patch_apply.json"

    if not guardrails.exists():
        return {"state": "blocked", "owner": "Chair/Planner", "path": "artifacts/guardrails.md", "reason": "missing guardrails"}

    ok, msg, policy = parse_guardrails(guardrails)
    if not ok:
        return {"state": "blocked", "owner": "Chair/Planner", "path": "artifacts/guardrails.md", "reason": msg}

    if not analysis.exists():
        return {"state": "blocked", "owner": "Chair/Planner", "path": "artifacts/analysis.md", "reason": "missing analysis"}

    if not find_result.exists():
        return {"state": "resolve_find_local", "owner": "Local Orchestrator", "path": "artifacts/find_result.json", "reason": "run local resolver"}

    if policy["find_mode"] == "resolver_plus_web":
        ok_web, msg_web = validate_find_web(find_web)
        if not ok_web:
            return {"state": "blocked", "owner": "Researcher", "path": "artifacts/find_web.json", "reason": msg_web}

    if not file_request.exists():
        return {"state": "blocked", "owner": "Chair/Planner", "path": "artifacts/file_request.json", "reason": "missing file_request"}

    if not context_pack.exists():
        return {"state": "blocked", "owner": "Local Librarian", "path": "artifacts/context_pack.json", "reason": "missing context_pack"}

    if not plan_draft.exists():
        return {"state": "blocked", "owner": "Chair/Planner", "path": "artifacts/PLAN_draft.md", "reason": "missing PLAN_draft"}

    if not review_contract.exists():
        return {"state": "blocked", "owner": "Contract Guardian", "path": "reviews/review_contract.md", "reason": "missing contract review"}

    if not review_cost.exists():
        return {"state": "blocked", "owner": "Cost Controller", "path": "reviews/review_cost.md", "reason": "missing cost review"}

    verdict_contract = parse_verdict(review_contract)
    verdict_cost = parse_verdict(review_cost)
    if verdict_contract != "APPROVE" or verdict_cost != "APPROVE":
        return {
            "state": "blocked",
            "owner": "Chair/Planner",
            "path": "reviews/review_contract.md,reviews/review_cost.md",
            "reason": f"review verdicts not APPROVE (contract={verdict_contract}, cost={verdict_cost})",
        }

    if not plan.exists() or not plan_signed(plan):
        return {"state": "blocked", "owner": "Chair/Planner", "path": "artifacts/PLAN.md", "reason": "PLAN.md missing or not SIGNED"}

    if not patch.exists():
        return {"state": "blocked", "owner": "PatchMaker", "path": "artifacts/diff.patch", "reason": "missing diff.patch"}

    if patch_marker.exists():
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


def verify_cmd() -> list[str]:
    if os.name == "nt":
        return ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts" / "verify_repo.ps1")]
    return ["bash", str(ROOT / "scripts" / "verify_repo.sh")]


def cmd_new_run(goal: str, run_id: str) -> int:
    rid = run_id.strip() or default_run_id()
    run_dir = make_run_dir(ROOT, rid)
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
    run_doc = load_run_doc(run_dir)
    gate = current_gate(run_dir, run_doc)
    print(f"[ctcp_orchestrate] run_dir={run_dir}")
    print(f"[ctcp_orchestrate] run_status={run_doc.get('status')}")
    print(f"[ctcp_orchestrate] next={gate['state']}")
    print(f"[ctcp_orchestrate] owner={gate['owner']}")
    print(f"[ctcp_orchestrate] path={gate['path']}")
    print(f"[ctcp_orchestrate] reason={gate['reason']}")
    return 0


def cmd_advance(run_dir: Path, max_steps: int) -> int:
    ensure_layout(run_dir)
    run_doc = load_run_doc(run_dir)
    goal = str(run_doc.get("goal", "")).strip() or "unspecified-goal"
    steps = 0

    while steps < max_steps:
        run_doc = load_run_doc(run_dir)
        if str(run_doc.get("status", "")).lower() == "pass":
            print("[ctcp_orchestrate] run already PASS")
            return 0
        if str(run_doc.get("status", "")).lower() == "fail":
            print("[ctcp_orchestrate] run already FAIL")
            return 1

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
            patch = run_dir / "artifacts" / "diff.patch"
            cmd = ["git", "apply", str(patch)]
            rc, out, err = run_cmd(cmd, ROOT)
            out_log = run_dir / "logs" / "patch_apply.stdout.log"
            err_log = run_dir / "logs" / "patch_apply.stderr.log"
            write_text(out_log, out)
            write_text(err_log, err)
            write_json(
                run_dir / "artifacts" / "patch_apply.json",
                {
                    "patch_sha256": file_sha256(patch),
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
            steps += 1
            continue

        if state == "ready_verify":
            cmd = verify_cmd()
            rc, out, err = run_cmd(cmd, ROOT)
            out_log = run_dir / "logs" / "verify.stdout.log"
            err_log = run_dir / "logs" / "verify.stderr.log"
            write_text(out_log, out)
            write_text(err_log, err)

            report = {
                "result": "PASS" if rc == 0 else "FAIL",
                "gate": "lite",
                "commands": [{"cmd": " ".join(cmd), "exit_code": rc}],
                "failures": [] if rc == 0 else [{"kind": "verify", "id": "verify_repo", "message": "verify_repo returned non-zero"}],
                "artifacts": {
                    "trace": "TRACE.md",
                    "bundle": "failure_bundle.zip" if rc != 0 else "",
                    "stdout_log": out_log.as_posix(),
                    "stderr_log": err_log.as_posix(),
                },
            }
            write_json(run_dir / "artifacts" / "verify_report.json", report)
            append_event(run_dir, "Local Verifier", "verify_complete", "artifacts/verify_report.json", rc=rc)

            if rc != 0:
                run_doc["status"] = "fail"
                run_doc["blocked_reason"] = "verify_failed"
                save_run_doc(run_dir, run_doc)
                bundle = make_failure_bundle(run_dir)
                write_pointer(LAST_BUNDLE_POINTER, bundle)
                append_event(run_dir, "Local Verifier", "failure_bundle_created", "failure_bundle.zip")
                print(f"[ctcp_orchestrate] FAIL: verify failed, bundle={bundle}")
                return 1

            run_doc["status"] = "pass"
            run_doc.pop("blocked_reason", None)
            save_run_doc(run_dir, run_doc)
            append_event(run_dir, "Local Verifier", "run_pass", "artifacts/verify_report.json")
            print("[ctcp_orchestrate] PASS: verify succeeded")
            return 0

        if state in {"pass", "fail"}:
            return cmd_status(run_dir)

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
