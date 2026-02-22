#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    _write_text(path, json.dumps(doc, ensure_ascii=False, indent=2) + "\n")


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _normalize_role(role: str) -> str:
    text = str(role or "").strip().lower()
    if text == "planner":
        return "chair"
    return text


def _parse_ranges(raw: Any) -> list[tuple[int, int]]:
    rows: list[tuple[int, int]] = []
    if not isinstance(raw, list):
        return rows
    for item in raw:
        if not isinstance(item, list) or len(item) != 2:
            continue
        try:
            a = int(item[0])
            b = int(item[1])
        except Exception:
            continue
        if a <= 0 or b <= 0:
            continue
        if a > b:
            a, b = b, a
        rows.append((a, b))
    return rows


def _render_snippets(text: str, ranges: list[tuple[int, int]]) -> str:
    if not ranges:
        return ""
    lines = text.splitlines()
    out: list[str] = []
    for start, end in ranges:
        s = max(1, start)
        e = min(len(lines), end)
        if s > e:
            continue
        out.append(f"# lines {s}-{e}")
        for idx in range(s, e + 1):
            out.append(f"{idx:>6}: {lines[idx - 1]}")
    return "\n".join(out).strip()


def _mock_file_request(goal: str) -> dict[str, Any]:
    return {
        "schema_version": "ctcp-file-request-v1",
        "goal": goal or "mock-goal",
        "needs": [
            {
                "path": "README.md",
                "mode": "snippets",
                "line_ranges": [[1, 24]],
            }
        ],
        "budget": {"max_files": 3, "max_total_bytes": 12000},
        "reason": "mock chair request for deterministic offline flow",
    }


def _mock_context_pack(repo_root: Path, run_dir: Path) -> tuple[dict[str, Any] | None, str]:
    request_path = run_dir / "artifacts" / "file_request.json"
    if not request_path.exists():
        return None, "missing artifacts/file_request.json"
    try:
        request = json.loads(request_path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return None, f"invalid file_request.json: {exc}"

    if str(request.get("schema_version", "")) != "ctcp-file-request-v1":
        return None, "file_request schema_version must be ctcp-file-request-v1"
    needs = request.get("needs", [])
    if not isinstance(needs, list):
        return None, "file_request.needs must be array"

    budget = request.get("budget", {})
    if not isinstance(budget, dict):
        budget = {}
    try:
        max_files = max(1, int(budget.get("max_files", 3)))
    except Exception:
        max_files = 3
    try:
        max_total_bytes = max(1, int(budget.get("max_total_bytes", 12000)))
    except Exception:
        max_total_bytes = 12000

    files: list[dict[str, str]] = []
    omitted: list[dict[str, str]] = []
    used_bytes = 0
    for row in needs:
        if not isinstance(row, dict):
            continue
        rel = str(row.get("path", "")).strip().replace("\\", "/")
        mode = str(row.get("mode", "")).strip().lower()
        if not rel:
            continue
        src = (repo_root / rel).resolve()
        if not _is_within(src, repo_root):
            omitted.append({"path": rel, "reason": "denied"})
            continue
        if not src.exists() or not src.is_file():
            omitted.append({"path": rel, "reason": "denied"})
            continue
        raw = src.read_text(encoding="utf-8", errors="replace")
        if mode == "full":
            content = raw
        elif mode == "snippets":
            content = _render_snippets(raw, _parse_ranges(row.get("line_ranges", [])))
            if not content:
                omitted.append({"path": rel, "reason": "irrelevant"})
                continue
        else:
            omitted.append({"path": rel, "reason": "irrelevant"})
            continue

        size = len(content.encode("utf-8"))
        if len(files) >= max_files or (used_bytes + size) > max_total_bytes:
            omitted.append({"path": rel, "reason": "too_large"})
            continue
        files.append(
            {
                "path": rel,
                "why": f"mock librarian capture mode={mode}",
                "content": content,
            }
        )
        used_bytes += size

    return (
        {
            "schema_version": "ctcp-context-pack-v1",
            "goal": str(request.get("goal", "")).strip(),
            "repo_slug": repo_root.name,
            "summary": (
                f"included={len(files)} omitted={len(omitted)} "
                f"used_bytes={used_bytes} budget_files={max_files} budget_bytes={max_total_bytes}"
            ),
            "files": files,
            "omitted": omitted,
        },
        "",
    )


def _mock_guardrails() -> str:
    return "\n".join(
        [
            "find_mode: resolver_only",
            "max_files: 20",
            "max_total_bytes: 200000",
            "max_iterations: 3",
            "",
        ]
    )


def _mock_analysis(goal: str) -> str:
    return "\n".join(
        [
            "# Analysis",
            "",
            f"- Goal: {goal or 'mock-goal'}",
            "- Strategy: deterministic offline pipeline run",
            "",
        ]
    )


def _mock_plan_draft(goal: str) -> str:
    return "\n".join(
        [
            "Status: DRAFT",
            "Scope-Allow: scripts/,tools/,tests/,artifacts/,meta/",
            "Scope-Deny: .git/,build/,build_lite/,dist/,runs/",
            "Gates: lite,workflow_gate,plan_check,patch_check,behavior_catalog_check,contract_checks,doc_index_check,lite_replay,python_unit_tests",
            "Budgets: max_iterations=3,max_files=20,max_total_bytes=200000",
            "Stop: scope_violation=true,repeated_failure=2,missing_plan_fields=true",
            "Behaviors: B001,B002,B003,B004,B005,B006,B007,B008,B009,B010,B011,B012,B013,B014,B015,B016,B017,B018,B019,B020,B021,B022,B023,B024,B025,B026,B027,B028,B029,B030,B031,B032,B033,B034,B035",
            "Results: R001,R002,R003,R004,R005",
            f"Goal: {goal or 'mock-goal'}",
            "",
        ]
    )


def _mock_plan_signed(goal: str) -> str:
    return "\n".join(
        [
            "Status: SIGNED",
            "Scope-Allow: scripts/,tools/,tests/,artifacts/,meta/",
            "Scope-Deny: .git/,build/,build_lite/,dist/,runs/",
            "Gates: lite,workflow_gate,plan_check,patch_check,behavior_catalog_check,contract_checks,doc_index_check,lite_replay,python_unit_tests",
            "Budgets: max_iterations=3,max_files=20,max_total_bytes=200000",
            "Stop: scope_violation=true,repeated_failure=2,missing_plan_fields=true",
            "Behaviors: B001,B002,B003,B004,B005,B006,B007,B008,B009,B010,B011,B012,B013,B014,B015,B016,B017,B018,B019,B020,B021,B022,B023,B024,B025,B026,B027,B028,B029,B030,B031,B032,B033,B034,B035",
            "Results: R001,R002,R003,R004,R005",
            f"Goal: {goal or 'mock-goal'}",
            "",
        ]
    )


def _mock_review(title: str) -> str:
    return "\n".join(
        [
            f"# {title}",
            "",
            "Verdict: APPROVE",
            "",
            "Blocking Reasons:",
            "- none",
            "",
            "Required Fix/Artifacts:",
            "- none",
            "",
        ]
    )


def _mock_find_web() -> dict[str, Any]:
    return {
        "schema_version": "ctcp-find-web-v1",
        "constraints": {
            "allow_domains": ["example.com"],
            "max_queries": 1,
            "max_pages": 1,
        },
        "results": [
            {
                "url": "https://example.com/mock",
                "locator": {"type": "heading", "value": "Mock Source"},
                "fetched_at": "2026-01-01T00:00:00Z",
                "excerpt": "mock source",
                "why_relevant": "offline deterministic placeholder",
                "risk_flags": [],
            }
        ],
    }


def _mock_patch() -> str:
    return "\n".join(
        [
            "diff --git a/docs/mock_agent_probe.txt b/docs/mock_agent_probe.txt",
            "new file mode 100644",
            "index 0000000..88f4248",
            "--- /dev/null",
            "+++ b/docs/mock_agent_probe.txt",
            "@@ -0,0 +1 @@",
            "+mock agent deterministic patch",
            "",
        ]
    )


def _default_target(role: str, action: str) -> str:
    if role == "chair" and action == "file_request":
        return "artifacts/file_request.json"
    if role == "chair" and action == "plan_signed":
        return "artifacts/PLAN.md"
    if role == "chair":
        return "artifacts/PLAN_draft.md"
    if role == "librarian":
        return "artifacts/context_pack.json"
    if role == "contract_guardian":
        return "reviews/review_contract.md"
    if role == "cost_controller":
        return "reviews/review_cost.md"
    if role in {"patchmaker", "fixer"}:
        return "artifacts/diff.patch"
    if role == "researcher":
        return "artifacts/find_web.json"
    return "artifacts/mock_output.txt"


def _fault_config(config: dict[str, Any]) -> tuple[str, str]:
    providers = config.get("providers", {}) if isinstance(config, dict) else {}
    if not isinstance(providers, dict):
        providers = {}
    mock_cfg = providers.get("mock_agent", {})
    if not isinstance(mock_cfg, dict):
        mock_cfg = {}

    mode = str(mock_cfg.get("fault_mode", "")).strip().lower()
    role = str(mock_cfg.get("fault_role", "")).strip().lower()
    env_mode = str(os.environ.get("CTCP_MOCK_AGENT_FAULT_MODE", "")).strip().lower()
    env_role = str(os.environ.get("CTCP_MOCK_AGENT_FAULT_ROLE", "")).strip().lower()
    if env_mode:
        mode = env_mode
    if env_role:
        role = env_role
    return mode, role


def _fault_applies(*, mode: str, role_selector: str, role: str, action: str, target_rel: str) -> bool:
    if not mode:
        return False
    if not role_selector:
        return True
    tokens = {
        role.lower(),
        action.lower(),
        f"{role.lower()}_{action.lower()}",
        target_rel.lower(),
        Path(target_rel).name.lower(),
    }
    selectors = {x.strip() for x in role_selector.replace("|", ",").split(",") if x.strip()}
    return any(x in tokens for x in selectors)


def _degraded_payload(payload_type: str, role: str, action: str, goal: str) -> tuple[str, dict[str, Any] | str]:
    if payload_type == "json":
        if role == "chair" and action == "file_request":
            return "json", {"schema_version": "ctcp-file-request-v1", "goal": goal or "mock-goal"}
        if role == "librarian":
            return "json", {"schema_version": "ctcp-context-pack-v1", "goal": goal or "mock-goal"}
        return "json", {"schema_version": "mock-v1"}
    if payload_type == "text":
        if role in {"contract_guardian", "cost_controller"}:
            return "text", "# Review\n\nRequired Fix/Artifacts:\n- missing verdict\n"
        if role == "chair" and action == "plan_signed":
            return "text", "Status: DRAFT\n"
        if role == "chair":
            return "text", "# Draft\n"
        if role in {"patchmaker", "fixer"}:
            return "text", "diff --git\n"
    return payload_type, ""


def preview(*, run_dir: Path, request: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    _ = (run_dir, request, config)
    return {"status": "can_exec"}


def execute(
    *,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
    guardrails_budgets: dict[str, str],
) -> dict[str, Any]:
    _ = guardrails_budgets
    role = _normalize_role(str(request.get("role", "")))
    action = str(request.get("action", "")).strip().lower()
    goal = str(request.get("goal", "")).strip()
    target_rel = str(request.get("target_path", "")).strip() or _default_target(role, action)
    target = (run_dir / target_rel).resolve()
    if not _is_within(target, run_dir):
        return {"status": "exec_failed", "reason": f"target_path escapes run_dir: {target_rel}"}

    try:
        payload_type = "text"
        payload: dict[str, Any] | str

        if role == "chair" and action == "file_request":
            payload_type = "json"
            payload = _mock_file_request(goal)
        elif role == "chair" and action == "plan_signed":
            payload = _mock_plan_signed(goal)
        elif role == "chair" and action == "plan_draft":
            lower = target_rel.lower()
            if lower.endswith("guardrails.md"):
                payload = _mock_guardrails()
            elif lower.endswith("analysis.md"):
                payload = _mock_analysis(goal)
            else:
                payload = _mock_plan_draft(goal)
        elif role == "librarian" and action == "context_pack":
            payload_type = "json"
            doc, reason = _mock_context_pack(repo_root, run_dir)
            if doc is None:
                return {"status": "exec_failed", "reason": reason, "target_path": target_rel}
            payload = doc
        elif role == "contract_guardian" and action == "review_contract":
            payload = _mock_review("Contract Review")
        elif role == "cost_controller" and action == "review_cost":
            payload = _mock_review("Cost Review")
        elif role in {"patchmaker", "fixer"} and action in {"make_patch", "fix_patch"}:
            payload = _mock_patch()
        elif role == "researcher" and action == "find_web":
            payload_type = "json"
            payload = _mock_find_web()
        else:
            return {"status": "exec_failed", "reason": f"unsupported mock request: role={role} action={action}"}

        fault_mode, fault_role = _fault_config(config)
        if _fault_applies(
            mode=fault_mode,
            role_selector=fault_role,
            role=role,
            action=action,
            target_rel=target_rel,
        ):
            if fault_mode == "raise_exception":
                raise RuntimeError(f"mock fault injected: mode={fault_mode}")
            if fault_mode == "drop_output":
                return {
                    "status": "executed",
                    "target_path": target_rel,
                    "fault_mode": fault_mode,
                    "fault_role": fault_role,
                    "note": "output intentionally dropped",
                }
            if fault_mode == "corrupt_json":
                _write_text(target, '{"broken_json":')
                return {
                    "status": "executed",
                    "target_path": target_rel,
                    "fault_mode": fault_mode,
                    "fault_role": fault_role,
                }
            if fault_mode == "missing_field":
                payload_type, payload = _degraded_payload(payload_type, role, action, goal)
            elif fault_mode == "empty_file":
                _write_text(target, "")
                return {
                    "status": "executed",
                    "target_path": target_rel,
                    "fault_mode": fault_mode,
                    "fault_role": fault_role,
                }
            elif fault_mode == "invalid_patch":
                _write_text(target, "mock-invalid-patch\n")
                return {
                    "status": "executed",
                    "target_path": target_rel,
                    "fault_mode": fault_mode,
                    "fault_role": fault_role,
                }

        if payload_type == "json":
            if not isinstance(payload, dict):
                return {"status": "exec_failed", "reason": "mock payload type mismatch for json", "target_path": target_rel}
            _write_json(target, payload)
        else:
            if not isinstance(payload, str):
                return {"status": "exec_failed", "reason": "mock payload type mismatch for text", "target_path": target_rel}
            text = payload if payload.endswith("\n") else payload + "\n"
            _write_text(target, text)

        return {
            "status": "executed",
            "target_path": target_rel,
        }
    except Exception as exc:
        return {
            "status": "exec_failed",
            "reason": f"mock_agent exception: {exc}",
            "target_path": target_rel,
        }
