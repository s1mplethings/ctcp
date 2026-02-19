#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POINTERS_DIR = ROOT / "meta" / "run_pointers"
LAST_RUN_POINTER = POINTERS_DIR / "LAST_RUN.txt"
FIND_MODE_RESOLVER_ONLY = "resolver_only"
FIND_MODE_RESOLVER_PLUS_WEB = "resolver_plus_web"

try:
    from tools.run_paths import get_repo_slug, make_run_dir
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT))
    from tools.run_paths import get_repo_slug, make_run_dir


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def run_cmd(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout, proc.stderr


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, doc: dict[str, Any]) -> None:
    write_text(path, json.dumps(doc, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_find_mode(raw: str) -> str:
    mode = (raw or "").strip().lower()
    if mode in {FIND_MODE_RESOLVER_ONLY, FIND_MODE_RESOLVER_PLUS_WEB}:
        return mode
    return FIND_MODE_RESOLVER_ONLY


def default_run_id() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-orchestrate")


def resolve_run_dir(raw: str) -> Path:
    if raw.strip():
        return Path(raw).expanduser().resolve()
    if not LAST_RUN_POINTER.exists():
        raise SystemExit("[ctcp_orchestrate] LAST_RUN pointer not found, pass --run-dir")
    pointed = LAST_RUN_POINTER.read_text(encoding="utf-8").strip()
    if not pointed:
        raise SystemExit("[ctcp_orchestrate] LAST_RUN pointer is empty, pass --run-dir")
    return Path(pointed).expanduser().resolve()


def write_pointer(run_dir: Path) -> None:
    POINTERS_DIR.mkdir(parents=True, exist_ok=True)
    write_text(LAST_RUN_POINTER, str(run_dir.resolve()) + "\n")


def git_output(args: list[str]) -> str:
    rc, out, _ = run_cmd(["git", *args], ROOT)
    if rc != 0:
        return "unknown"
    return out.strip() or "unknown"


def git_dirty() -> bool:
    rc, out, _ = run_cmd(["git", "status", "--porcelain"], ROOT)
    if rc != 0:
        return True
    return bool(out.strip())


def ensure_layout(run_dir: Path) -> None:
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (run_dir / "reviews").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)


def append_trace(run_dir: Path, title: str, detail: str = "") -> None:
    trace = run_dir / "TRACE.md"
    line = f"- {now_iso()} | {title}"
    if detail:
        line += f" | {detail}"
    with trace.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def append_event(
    run_dir: Path,
    event_type: str,
    state: str,
    paths: list[str] | None = None,
    note: str = "",
) -> None:
    row: dict[str, Any] = {
        "ts": now_iso(),
        "type": event_type,
        "state": state,
    }
    if paths:
        row["paths"] = paths
    if note:
        row["note"] = note
    events = run_dir / "events.jsonl"
    events.parent.mkdir(parents=True, exist_ok=True)
    with events.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    append_trace(run_dir, f"{event_type}:{state}", note)


def load_run_doc(run_dir: Path) -> dict[str, Any]:
    run_file = run_dir / "RUN.json"
    if not run_file.exists():
        raise SystemExit(f"[ctcp_orchestrate] missing RUN.json: {run_file}")
    return read_json(run_file)


def save_run_doc(run_dir: Path, run_doc: dict[str, Any]) -> None:
    run_doc["updated_at"] = now_iso()
    write_json(run_dir / "RUN.json", run_doc)


def normalize_running(run_doc: dict[str, Any]) -> None:
    run_doc["status"] = "running"
    run_doc.pop("blocked_reason", None)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


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


def review_verdict(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.lower().startswith("verdict:"):
            verdict = line.split(":", 1)[1].strip().upper()
            if verdict in {"APPROVE", "BLOCK"}:
                return verdict
            return "INVALID"
    return "INVALID"


def validate_find_web_doc(path: Path) -> tuple[bool, str]:
    try:
        doc = read_json(path)
    except Exception as exc:
        return False, f"invalid json: {exc}"

    if not isinstance(doc, dict):
        return False, "top-level document must be object"
    if doc.get("schema_version") != "ctcp-find-web-v1":
        return False, "schema_version must be ctcp-find-web-v1"

    constraints = doc.get("constraints")
    if not isinstance(constraints, dict):
        return False, "constraints must be object"
    allow_domains = constraints.get("allow_domains")
    max_queries = constraints.get("max_queries")
    if not isinstance(allow_domains, list) or any(not isinstance(x, str) for x in allow_domains):
        return False, "constraints.allow_domains must be string array"
    if not isinstance(max_queries, int):
        return False, "constraints.max_queries must be integer"

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
        if not isinstance(row.get("risk_flags"), list):
            return False, f"results[{idx}].risk_flags must be array"
    return True, "ok"


def guardrails_template(goal: str, find_mode: str, web_find_policy: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Guardrails",
            "",
            f"- Goal: {goal}",
            f"- find_mode: {find_mode}",
            f"- web_find_policy: {json.dumps(web_find_policy, ensure_ascii=False)}",
            "- Contract: docs/00_CORE.md",
            "- Constraints:",
            "  - find_local is mandatory resolver (workflow_registry + local history)",
            "  - find_web is optional external input, never hardcoded network logic in repo",
            "  - no GUI dependency in default lite path",
            "  - no new dependencies",
            "",
        ]
    )


def analysis_template(goal: str) -> str:
    return "\n".join(
        [
            "# Analysis",
            "",
            f"- Goal: {goal}",
            "- Focus:",
            "  - keep changes minimal and auditable",
            "  - keep TeamNet artifact gates explicit",
            "  - maintain external run-dir default behavior",
            "",
        ]
    )


def file_request_template(goal: str) -> dict[str, Any]:
    return {
        "schema_version": "ctcp-file-request-v1",
        "goal": goal,
        "requested_paths": [
            "docs/00_CORE.md",
            "ai_context/00_AI_CONTRACT.md",
            "README.md",
            "workflow_registry/index.json",
            "scripts/resolve_workflow.py",
            "meta/tasks/CURRENT.md",
        ],
        "deny_paths": [
            ".git/",
            "build*/",
            "simlab/_runs*/",
            "tests/fixtures/adlc_forge_full_bundle/runs/",
        ],
        "max_total_bytes": 200000,
        "notes": "Local Librarian should provide only files relevant to plan/patch gates.",
    }


def plan_template(goal: str, find_result: dict[str, Any], find_mode: str) -> str:
    wf_id = find_result.get("selected_workflow_id")
    wf_ver = find_result.get("selected_version")
    return "\n".join(
        [
            "# PLAN",
            "",
            f"- Goal: {goal}",
            f"- Workflow: {wf_id}@{wf_ver}",
            f"- Find mode: {find_mode}",
            "- Required inputs:",
            "  - artifacts/guardrails.md",
            "  - artifacts/analysis.md",
            "  - artifacts/find_result.json",
            "  - artifacts/find_web.json (resolver_plus_web mode only)",
            "  - artifacts/context_pack.json",
            "- Gates:",
            "  - reviews/review_contract.md (Verdict: APPROVE)",
            "  - reviews/review_cost.md (Verdict: APPROVE)",
            "  - artifacts/diff.patch apply succeeds",
            "  - scripts/verify_repo.* passes",
            "",
        ]
    )


def review_contract_template() -> str:
    return "\n".join(
        [
            "# Contract Review",
            "",
            "Verdict: BLOCK",
            "",
            "Blocking-Reason:",
            "- Fill this section if contract requirements are not met.",
            "",
            "Required-Artifacts:",
            "- artifacts/PLAN.md must reference selected_workflow_id/selected_version from artifacts/find_result.json",
            "- artifacts/context_pack.json must satisfy specs/ctcp_context_pack_v1.json",
            "",
        ]
    )


def review_cost_template() -> str:
    return "\n".join(
        [
            "# Cost Review",
            "",
            "Verdict: BLOCK",
            "",
            "Blocking-Reason:",
            "- Fill this section if budget/scope is not acceptable.",
            "",
            "Required-Artifacts:",
            "- artifacts/file_request.json must define requested_paths/deny_paths/max_total_bytes",
            "- PLAN must keep lite/headless gate and minimal change scope",
            "",
        ]
    )


def run_status_summary(run_dir: Path, run_doc: dict[str, Any]) -> dict[str, str]:
    artifacts = run_dir / "artifacts"
    reviews = run_dir / "reviews"
    find_mode = normalize_find_mode(str(run_doc.get("find_mode", FIND_MODE_RESOLVER_ONLY)))

    if str(run_doc.get("status", "")).lower() == "pass":
        return {
            "status": "pass",
            "next_missing": "(none)",
            "owner": "(none)",
            "hint": "Run already passed.",
        }
    if str(run_doc.get("status", "")).lower() == "fail":
        return {
            "status": "fail",
            "next_missing": "(see failure_bundle.zip)",
            "owner": "Fixer",
            "hint": str(run_doc.get("blocked_reason", "Run failed.")),
        }

    guardrails = artifacts / "guardrails.md"
    analysis = artifacts / "analysis.md"
    find_result = artifacts / "find_result.json"
    find_web = artifacts / "find_web.json"
    file_request = artifacts / "file_request.json"
    context_pack = artifacts / "context_pack.json"
    plan = artifacts / "PLAN.md"
    patch = artifacts / "diff.patch"
    review_contract = reviews / "review_contract.md"
    review_cost = reviews / "review_cost.md"
    patch_marker = artifacts / "patch_apply.json"

    if not guardrails.exists():
        return {
            "status": "running",
            "next_missing": "artifacts/guardrails.md",
            "owner": "DocGatekeeper",
            "hint": "Generate guardrails artifact first.",
        }
    if not analysis.exists():
        return {
            "status": "running",
            "next_missing": "artifacts/analysis.md",
            "owner": "Analyzer",
            "hint": "Generate analysis artifact.",
        }
    if not find_result.exists():
        return {
            "status": "running",
            "next_missing": "artifacts/find_result.json",
            "owner": "Resolver(find)",
            "hint": "Run local workflow resolver.",
        }
    if find_mode == FIND_MODE_RESOLVER_PLUS_WEB:
        if not find_web.exists():
            return {
                "status": "blocked",
                "next_missing": "artifacts/find_web.json",
                "owner": "Researcher",
                "hint": "resolver_plus_web requires Researcher artifact find_web.json.",
            }
        ok, msg = validate_find_web_doc(find_web)
        if not ok:
            return {
                "status": "blocked",
                "next_missing": "valid artifacts/find_web.json",
                "owner": "Researcher",
                "hint": f"find_web.json invalid: {msg}",
            }
    if not file_request.exists():
        return {
            "status": "running",
            "next_missing": "artifacts/file_request.json",
            "owner": "Chair/Planner",
            "hint": "Request paths for Local Librarian context supply.",
        }
    if not context_pack.exists():
        return {
            "status": "blocked",
            "next_missing": "artifacts/context_pack.json",
            "owner": "Local Librarian",
            "hint": "Flow is blocked until context_pack is provided.",
        }
    if not plan.exists():
        return {
            "status": "running",
            "next_missing": "artifacts/PLAN.md",
            "owner": "Planner",
            "hint": "Create plan using selected workflow id/version.",
        }
    if not review_contract.exists() or not review_cost.exists():
        missing = []
        if not review_contract.exists():
            missing.append("reviews/review_contract.md")
        if not review_cost.exists():
            missing.append("reviews/review_cost.md")
        return {
            "status": "blocked",
            "next_missing": ", ".join(missing),
            "owner": "ContractGuardian / CostController",
            "hint": "Review templates/verdicts are required before patch apply.",
        }

    contract_verdict = review_verdict(review_contract)
    cost_verdict = review_verdict(review_cost)
    if contract_verdict != "APPROVE" or cost_verdict != "APPROVE":
        return {
            "status": "blocked",
            "next_missing": "Verdict: APPROVE in both review files",
            "owner": "ContractGuardian / CostController",
            "hint": f"Current verdicts: contract={contract_verdict}, cost={cost_verdict}",
        }

    if not patch.exists():
        return {
            "status": "blocked",
            "next_missing": "artifacts/diff.patch",
            "owner": "PatchMaker",
            "hint": "Patch is required before apply/verify.",
        }
    if not patch_marker.exists():
        return {
            "status": "running",
            "next_missing": "(none)",
            "owner": "Orchestrator",
            "hint": "Ready to apply artifacts/diff.patch.",
        }
    return {
        "status": "running",
        "next_missing": "(none)",
        "owner": "Orchestrator",
        "hint": "Patch applied, ready to run verify.",
    }


def cmd_new_run(
    goal: str,
    run_id: str,
    find_mode: str,
    web_allow_domains: list[str],
    web_max_queries: int,
    web_max_results: int,
) -> int:
    actual_run_id = run_id.strip() or default_run_id()
    run_dir = make_run_dir(ROOT, actual_run_id)
    if run_dir.exists() and any(run_dir.iterdir()):
        print(f"[ctcp_orchestrate] run dir already exists and is not empty: {run_dir}")
        return 1

    ensure_layout(run_dir)
    write_text(
        run_dir / "TRACE.md",
        "\n".join(
            [
                f"# CTCP Orchestrator Trace — {actual_run_id}",
                "",
                f"- Goal: {goal}",
                f"- Find mode: {find_mode}",
                "- Pipeline: doc -> analysis -> find -> plan -> [build <-> verify] -> contrast -> fix -> deploy/merge",
                "",
                "## Events",
                "",
            ]
        ),
    )
    run_doc = {
        "schema_version": "ctcp-run-v1",
        "run_id": actual_run_id,
        "goal": goal,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "status": "running",
        "repo_slug": get_repo_slug(ROOT),
        "repo_root": str(ROOT.resolve()),
        "git_sha": git_output(["rev-parse", "HEAD"]),
        "dirty": git_dirty(),
        "find_mode": find_mode,
        "web_find_policy": {
            "allow_domains": web_allow_domains,
            "max_queries": web_max_queries,
            "max_results": web_max_results,
        },
    }
    repo_ref = {
        "schema_version": "ctcp-repo-ref-v1",
        "repo_slug": get_repo_slug(ROOT),
        "repo_root": str(ROOT.resolve()),
        "git_sha": run_doc["git_sha"],
        "git_branch": git_output(["rev-parse", "--abbrev-ref", "HEAD"]),
        "dirty": run_doc["dirty"],
        "recorded_at": now_iso(),
    }
    write_json(run_dir / "RUN.json", run_doc)
    write_json(run_dir / "repo_ref.json", repo_ref)
    write_pointer(run_dir)
    append_event(
        run_dir,
        event_type="run",
        state="created",
        paths=["RUN.json", "repo_ref.json", "artifacts/", "reviews/", "logs/"],
        note="Initialized orchestrator run directory and pointer.",
    )
    print(f"[ctcp_orchestrate] run_dir={run_dir}")
    return 0


def cmd_status(run_dir: Path) -> int:
    run_doc = load_run_doc(run_dir)
    summary = run_status_summary(run_dir, run_doc)
    print(f"[ctcp_orchestrate] run_dir={run_dir}")
    print(f"[ctcp_orchestrate] run_status={run_doc.get('status')}")
    print(f"[ctcp_orchestrate] next_missing={summary['next_missing']}")
    print(f"[ctcp_orchestrate] owner={summary['owner']}")
    print(f"[ctcp_orchestrate] hint={summary['hint']}")
    return 0


def cmd_advance(run_dir: Path, max_steps: int) -> int:
    if max_steps < 1:
        print("[ctcp_orchestrate] --max-steps must be >= 1")
        return 1

    ensure_layout(run_dir)
    run_doc = load_run_doc(run_dir)
    goal = str(run_doc.get("goal", "")).strip() or "unspecified-goal"
    find_mode = normalize_find_mode(str(run_doc.get("find_mode", FIND_MODE_RESOLVER_ONLY)))
    web_find_policy = run_doc.get("web_find_policy")
    if not isinstance(web_find_policy, dict):
        web_find_policy = {"allow_domains": [], "max_queries": 0, "max_results": 0}
    artifacts = run_dir / "artifacts"
    reviews = run_dir / "reviews"
    logs = run_dir / "logs"
    steps = 0

    while steps < max_steps:
        run_doc = load_run_doc(run_dir)
        status = str(run_doc.get("status", "")).lower()
        if status == "pass":
            print("[ctcp_orchestrate] run already PASS")
            return 0
        if status == "fail":
            print("[ctcp_orchestrate] run is already FAIL")
            return 1

        guardrails = artifacts / "guardrails.md"
        analysis = artifacts / "analysis.md"
        find_result = artifacts / "find_result.json"
        find_web = artifacts / "find_web.json"
        file_request = artifacts / "file_request.json"
        context_pack = artifacts / "context_pack.json"
        plan = artifacts / "PLAN.md"
        patch = artifacts / "diff.patch"
        patch_marker = artifacts / "patch_apply.json"
        review_contract = reviews / "review_contract.md"
        review_cost = reviews / "review_cost.md"

        if not guardrails.exists():
            normalize_running(run_doc)
            write_text(guardrails, guardrails_template(goal, find_mode, web_find_policy))
            save_run_doc(run_dir, run_doc)
            append_event(run_dir, "doc", "generated_guardrails", [guardrails.as_posix()])
            steps += 1
            continue

        if not analysis.exists():
            normalize_running(run_doc)
            write_text(analysis, analysis_template(goal))
            save_run_doc(run_dir, run_doc)
            append_event(run_dir, "analysis", "generated_analysis", [analysis.as_posix()])
            steps += 1
            continue

        if not find_result.exists():
            normalize_running(run_doc)
            save_run_doc(run_dir, run_doc)
            cmd = [sys.executable, str(ROOT / "scripts" / "resolve_workflow.py"), "--goal", goal, "--out", str(find_result)]
            rc, out, err = run_cmd(cmd, ROOT)
            find_out = logs / "find.stdout.log"
            find_err = logs / "find.stderr.log"
            write_text(find_out, out)
            write_text(find_err, err)
            if rc != 0:
                run_doc["status"] = "fail"
                run_doc["blocked_reason"] = "resolve_workflow_failed"
                save_run_doc(run_dir, run_doc)
                append_event(
                    run_dir,
                    "find",
                    "resolve_failed",
                    [find_out.as_posix(), find_err.as_posix()],
                    note=f"rc={rc}",
                )
                return 1
            append_event(
                run_dir,
                "find",
                "resolved",
                [find_result.as_posix(), find_out.as_posix(), find_err.as_posix()],
                note=f"cmd={' '.join(cmd)}",
            )
            steps += 1
            continue

        if find_mode == FIND_MODE_RESOLVER_PLUS_WEB:
            if not find_web.exists():
                run_doc["status"] = "blocked"
                run_doc["blocked_reason"] = "waiting_researcher_find_web"
                save_run_doc(run_dir, run_doc)
                append_event(
                    run_dir,
                    "find_web",
                    "blocked_wait_researcher",
                    [find_web.as_posix()],
                    note="resolver_plus_web requires Researcher artifact find_web.json",
                )
                print("[ctcp_orchestrate] blocked: missing artifacts/find_web.json (owner=Researcher)")
                return 0

            ok, msg = validate_find_web_doc(find_web)
            if not ok:
                run_doc["status"] = "blocked"
                run_doc["blocked_reason"] = f"invalid_find_web_json({msg})"
                save_run_doc(run_dir, run_doc)
                append_event(
                    run_dir,
                    "find_web",
                    "blocked_invalid_contract",
                    [find_web.as_posix()],
                    note=msg,
                )
                print(f"[ctcp_orchestrate] blocked: invalid artifacts/find_web.json ({msg})")
                return 0

        if not file_request.exists():
            normalize_running(run_doc)
            write_json(file_request, file_request_template(goal))
            save_run_doc(run_dir, run_doc)
            append_event(run_dir, "planner", "generated_file_request", [file_request.as_posix()])
            steps += 1
            continue

        if not context_pack.exists():
            run_doc["status"] = "blocked"
            run_doc["blocked_reason"] = "waiting_local_librarian_context_pack"
            save_run_doc(run_dir, run_doc)
            append_event(
                run_dir,
                "gate",
                "blocked_wait_context_pack",
                [context_pack.as_posix()],
                note="Waiting Local Librarian to provide context_pack.json",
            )
            print("[ctcp_orchestrate] blocked: missing artifacts/context_pack.json (owner=Local Librarian)")
            return 0

        if not plan.exists():
            normalize_running(run_doc)
            find_doc = read_json(find_result)
            write_text(plan, plan_template(goal, find_doc, find_mode))
            save_run_doc(run_dir, run_doc)
            append_event(run_dir, "plan", "generated_plan", [plan.as_posix()])
            steps += 1
            continue

        created_reviews: list[str] = []
        if not review_contract.exists():
            write_text(review_contract, review_contract_template())
            created_reviews.append(review_contract.as_posix())
        if not review_cost.exists():
            write_text(review_cost, review_cost_template())
            created_reviews.append(review_cost.as_posix())
        if created_reviews:
            run_doc["status"] = "blocked"
            run_doc["blocked_reason"] = "waiting_teamnet_reviews"
            save_run_doc(run_dir, run_doc)
            append_event(
                run_dir,
                "review",
                "review_templates_created",
                created_reviews,
                note="Waiting ContractGuardian and CostController verdicts.",
            )
            print("[ctcp_orchestrate] blocked: review templates created; waiting APPROVE verdicts")
            return 0

        contract_verdict = review_verdict(review_contract)
        cost_verdict = review_verdict(review_cost)
        if contract_verdict != "APPROVE" or cost_verdict != "APPROVE":
            run_doc["status"] = "blocked"
            run_doc["blocked_reason"] = f"reviews_not_approved(contract={contract_verdict},cost={cost_verdict})"
            save_run_doc(run_dir, run_doc)
            append_event(
                run_dir,
                "review",
                "blocked_review_not_approved",
                [review_contract.as_posix(), review_cost.as_posix()],
                note=run_doc["blocked_reason"],
            )
            print(f"[ctcp_orchestrate] blocked: reviews not APPROVE (contract={contract_verdict}, cost={cost_verdict})")
            return 0

        if not patch.exists():
            run_doc["status"] = "blocked"
            run_doc["blocked_reason"] = "waiting_patchmaker_diff_patch"
            save_run_doc(run_dir, run_doc)
            append_event(
                run_dir,
                "patch",
                "blocked_wait_patch",
                [patch.as_posix()],
                note="Waiting PatchMaker to provide artifacts/diff.patch",
            )
            print("[ctcp_orchestrate] blocked: missing artifacts/diff.patch (owner=PatchMaker)")
            return 0

        patch_hash = sha256_file(patch)
        marker = {}
        if patch_marker.exists():
            try:
                marker = read_json(patch_marker)
            except Exception:
                marker = {}

        already_applied = bool(
            marker
            and marker.get("patch_sha256") == patch_hash
            and int(marker.get("rc", 1)) == 0
        )
        if not already_applied:
            normalize_running(run_doc)
            save_run_doc(run_dir, run_doc)
            cmd = ["git", "apply", str(patch)]
            rc, out, err = run_cmd(cmd, ROOT)
            patch_out = logs / "patch_apply.stdout.log"
            patch_err = logs / "patch_apply.stderr.log"
            write_text(patch_out, out)
            write_text(patch_err, err)
            write_json(
                patch_marker,
                {
                    "patch_path": patch.as_posix(),
                    "patch_sha256": patch_hash,
                    "applied_at": now_iso(),
                    "rc": rc,
                    "stdout_log": patch_out.as_posix(),
                    "stderr_log": patch_err.as_posix(),
                },
            )
            if rc != 0:
                run_doc["status"] = "blocked"
                run_doc["blocked_reason"] = "patch_apply_failed"
                save_run_doc(run_dir, run_doc)
                append_event(
                    run_dir,
                    "patch",
                    "apply_failed",
                    [patch.as_posix(), patch_out.as_posix(), patch_err.as_posix()],
                    note=f"rc={rc}",
                )
                print("[ctcp_orchestrate] blocked: git apply failed, check logs/patch_apply.*.log")
                return 0
            append_event(
                run_dir,
                "patch",
                "applied",
                [patch.as_posix(), patch_marker.as_posix()],
                note=f"cmd={' '.join(cmd)}",
            )
            steps += 1
            continue

        normalize_running(run_doc)
        save_run_doc(run_dir, run_doc)
        vcmd = verify_cmd()
        rc, out, err = run_cmd(vcmd, ROOT)
        verify_out = logs / "verify.stdout.log"
        verify_err = logs / "verify.stderr.log"
        write_text(verify_out, out)
        write_text(verify_err, err)
        verify_report = artifacts / "verify_report.md"
        write_text(
            verify_report,
            "\n".join(
                [
                    "# Verify Report",
                    "",
                    f"- command: `{' '.join(vcmd)}`",
                    f"- rc: `{rc}`",
                    "",
                    "## stdout (tail)",
                    "```",
                    out[-1200:],
                    "```",
                    "",
                    "## stderr (tail)",
                    "```",
                    err[-1200:],
                    "```",
                    "",
                ]
            ),
        )
        append_event(
            run_dir,
            "verify",
            "completed",
            [verify_report.as_posix(), verify_out.as_posix(), verify_err.as_posix()],
            note=f"rc={rc}",
        )
        steps += 1
        if rc != 0:
            run_doc["status"] = "fail"
            run_doc["blocked_reason"] = "verify_failed"
            save_run_doc(run_dir, run_doc)
            bundle = make_failure_bundle(run_dir)
            append_event(
                run_dir,
                "bundle",
                "failure_bundle_created",
                [bundle.as_posix()],
                note="verify failed",
            )
            print(f"[ctcp_orchestrate] FAIL: verify failed, bundle={bundle}")
            return 1

        run_doc["status"] = "pass"
        run_doc.pop("blocked_reason", None)
        save_run_doc(run_dir, run_doc)
        append_event(run_dir, "run", "pass", [verify_report.as_posix()])
        print("[ctcp_orchestrate] PASS: verify succeeded")
        return 0

    print(f"[ctcp_orchestrate] reached max-steps={max_steps}")
    cmd_status(run_dir)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Artifact-driven CTCP orchestrator state machine.")
    sub = ap.add_subparsers(dest="command")

    ap_new = sub.add_parser("new-run", help="Create a new external run directory.")
    ap_new.add_argument("--goal", required=True)
    ap_new.add_argument("--run-id", default="")
    ap_new.add_argument(
        "--find-mode",
        default=FIND_MODE_RESOLVER_ONLY,
        choices=[FIND_MODE_RESOLVER_ONLY, FIND_MODE_RESOLVER_PLUS_WEB],
    )
    ap_new.add_argument("--web-allow-domain", action="append", default=[])
    ap_new.add_argument("--web-max-queries", type=int, default=3)
    ap_new.add_argument("--web-max-results", type=int, default=8)

    ap_status = sub.add_parser("status", help="Show missing artifact and next owner.")
    ap_status.add_argument("--run-dir", default="")

    ap_adv = sub.add_parser("advance", help="Advance state machine by artifact gates.")
    ap_adv.add_argument("--run-dir", default="")
    ap_adv.add_argument("--max-steps", type=int, default=16)

    args = ap.parse_args()
    if args.command == "new-run":
        return cmd_new_run(
            goal=args.goal,
            run_id=args.run_id,
            find_mode=normalize_find_mode(args.find_mode),
            web_allow_domains=list(args.web_allow_domain),
            web_max_queries=max(0, int(args.web_max_queries)),
            web_max_results=max(0, int(args.web_max_results)),
        )
    if args.command == "status":
        return cmd_status(resolve_run_dir(args.run_dir))
    if args.command == "advance":
        return cmd_advance(resolve_run_dir(args.run_dir), args.max_steps)
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
