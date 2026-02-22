#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ctcp_dispatch
import ctcp_orchestrate


FLOW_GATES: list[dict[str, str]] = [
    {
        "state": "blocked",
        "owner": "Chair/Planner",
        "path": "artifacts/guardrails.md",
        "reason": "waiting for guardrails.md",
    },
    {
        "state": "blocked",
        "owner": "Chair/Planner",
        "path": "artifacts/analysis.md",
        "reason": "waiting for analysis.md",
    },
    {
        "state": "blocked",
        "owner": "Chair/Planner",
        "path": "artifacts/file_request.json",
        "reason": "waiting for file_request.json",
    },
    {
        "state": "blocked",
        "owner": "Local Librarian",
        "path": "artifacts/context_pack.json",
        "reason": "waiting for context_pack.json",
    },
    {
        "state": "blocked",
        "owner": "Chair/Planner",
        "path": "artifacts/PLAN_draft.md",
        "reason": "waiting for PLAN_draft.md",
    },
    {
        "state": "blocked",
        "owner": "Contract Guardian",
        "path": "reviews/review_contract.md",
        "reason": "waiting for review_contract.md",
    },
    {
        "state": "blocked",
        "owner": "Cost Controller",
        "path": "reviews/review_cost.md",
        "reason": "waiting for review_cost.md",
    },
    {
        "state": "blocked",
        "owner": "Chair/Planner",
        "path": "artifacts/PLAN.md",
        "reason": "waiting for PLAN.md",
    },
    {
        "state": "blocked",
        "owner": "PatchMaker",
        "path": "artifacts/diff.patch",
        "reason": "waiting for diff.patch",
    },
]


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _first_non_empty_line(text: str) -> str:
    for raw in (text or "").splitlines():
        line = raw.strip()
        if line:
            return line
    return ""


def _dispatch_config_all_mock() -> dict[str, Any]:
    return {
        "schema_version": "ctcp-dispatch-config-v1",
        "mode": "mock_agent",
        "role_providers": {
            "chair": "mock_agent",
            "planner": "mock_agent",
            "librarian": "mock_agent",
            "contract_guardian": "mock_agent",
            "cost_controller": "mock_agent",
            "patchmaker": "mock_agent",
            "fixer": "mock_agent",
            "researcher": "mock_agent",
        },
        "budgets": {"max_outbox_prompts": 16},
        "providers": {},
    }


def _prepare_run_dir(run_dir: Path, cfg: dict[str, Any]) -> None:
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (run_dir / "reviews").mkdir(parents=True, exist_ok=True)
    (run_dir / "outbox").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "artifacts" / "dispatch_config.json", cfg)


def _validate_artifact_for_gate(run_dir: Path, gate_path: str) -> tuple[bool, str]:
    path_l = gate_path.lower()
    if "guardrails.md" in path_l:
        p = run_dir / "artifacts" / "guardrails.md"
        if not p.exists():
            return False, "missing guardrails.md"
        text = p.read_text(encoding="utf-8", errors="replace")
        return ("find_mode:" in text and "max_iterations:" in text, "invalid guardrails.md")
    if "analysis.md" in path_l:
        p = run_dir / "artifacts" / "analysis.md"
        return (p.exists() and bool(p.read_text(encoding="utf-8", errors="replace").strip()), "invalid analysis.md")
    if "file_request.json" in path_l:
        p = run_dir / "artifacts" / "file_request.json"
        if not p.exists():
            return False, "missing file_request.json"
        try:
            doc = _read_json(p)
        except Exception as exc:
            return False, f"file_request.json parse failed: {exc}"
        ok = (
            doc.get("schema_version") == "ctcp-file-request-v1"
            and isinstance(doc.get("needs"), list)
            and isinstance(doc.get("budget"), dict)
            and "reason" in doc
        )
        return ok, "invalid file_request.json contract"
    if "context_pack.json" in path_l:
        p = run_dir / "artifacts" / "context_pack.json"
        if not p.exists():
            return False, "missing context_pack.json"
        try:
            doc = _read_json(p)
        except Exception as exc:
            return False, f"context_pack.json parse failed: {exc}"
        ok = (
            doc.get("schema_version") == "ctcp-context-pack-v1"
            and isinstance(doc.get("files"), list)
            and isinstance(doc.get("omitted"), list)
            and "summary" in doc
        )
        return ok, "invalid context_pack.json contract"
    if "plan_draft.md" in path_l:
        p = run_dir / "artifacts" / "PLAN_draft.md"
        if not p.exists():
            return False, "missing PLAN_draft.md"
        text = p.read_text(encoding="utf-8", errors="replace")
        return ("Status:" in text and bool(text.strip()), "invalid PLAN_draft.md")
    if "review_contract.md" in path_l:
        p = run_dir / "reviews" / "review_contract.md"
        if not p.exists():
            return False, "missing review_contract.md"
        text = p.read_text(encoding="utf-8", errors="replace")
        return ("Verdict:" in text and "Required Fix/Artifacts:" in text, "invalid review_contract.md")
    if "review_cost.md" in path_l:
        p = run_dir / "reviews" / "review_cost.md"
        if not p.exists():
            return False, "missing review_cost.md"
        text = p.read_text(encoding="utf-8", errors="replace")
        return ("Verdict:" in text and "Required Fix/Artifacts:" in text, "invalid review_cost.md")
    if "plan.md" in path_l:
        p = run_dir / "artifacts" / "PLAN.md"
        if not p.exists():
            return False, "missing PLAN.md"
        text = p.read_text(encoding="utf-8", errors="replace")
        return ("Status: SIGNED" in text, "PLAN.md not signed")
    if "diff.patch" in path_l:
        p = run_dir / "artifacts" / "diff.patch"
        if not p.exists():
            return False, "missing diff.patch"
        first = _first_non_empty_line(p.read_text(encoding="utf-8", errors="replace"))
        return (first.startswith("diff --git"), "invalid diff.patch")
    return True, "ok"


def _dispatch_once(
    *,
    run_dir: Path,
    run_doc: dict[str, Any],
    gate: dict[str, str],
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    if env:
        with mock.patch.dict(os.environ, env, clear=False):
            return ctcp_dispatch.dispatch_once(run_dir, run_doc, gate, ROOT)
    return ctcp_dispatch.dispatch_once(run_dir, run_doc, gate, ROOT)


def _materialize_failure_bundle(
    *,
    run_dir: Path,
    reason: str,
    failed_gate: dict[str, str],
    steps: list[dict[str, Any]],
) -> Path:
    ctcp_orchestrate.ensure_layout(run_dir)
    trace_path = run_dir / "TRACE.md"
    if not trace_path.exists():
        trace_path.write_text("# Mock Fault Trace\n\n", encoding="utf-8")
    with trace_path.open("a", encoding="utf-8") as fh:
        fh.write(f"- failure_reason: {reason}\n")
        fh.write(f"- failed_gate: {failed_gate.get('path', '')}\n")
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        events_path.write_text("", encoding="utf-8")
    for row in steps[-3:]:
        events_path.write_text(
            events_path.read_text(encoding="utf-8", errors="replace")
            + json.dumps(
                {
                    "ts": "2026-01-01T00:00:00",
                    "role": str(row.get("role", "")),
                    "event": "MOCK_STEP",
                    "path": str(row.get("target_path", "")),
                    "provider": str(row.get("provider", "")),
                    "status": str(row.get("status", "")),
                    "reason": str(row.get("reason", "")),
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    verify_report = {
        "result": "FAIL",
        "gate": "mock_fault_injection",
        "iteration": 1,
        "max_iterations": 1,
        "commands": [{"cmd": "mock_fault_iteration", "exit_code": 1}],
        "failures": [{"kind": "mock_provider", "id": "fault", "message": reason}],
        "paths": {
            "trace": "TRACE.md",
            "verify_report": "artifacts/verify_report.json",
            "bundle": "failure_bundle.zip",
        },
    }
    _write_json(run_dir / "artifacts" / "verify_report.json", verify_report)
    (run_dir / "reviews").mkdir(parents=True, exist_ok=True)
    (run_dir / "reviews" / "review_mock_fault.md").write_text(
        "\n".join(
            [
                "# Mock Fault Review",
                "",
                "Verdict: BLOCK",
                f"Reason: {reason}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    bundle, _ = ctcp_orchestrate.ensure_failure_bundle(run_dir)
    return bundle


def _run_flow_with_fault(
    *,
    run_dir: Path,
    run_doc: dict[str, Any],
    fault_mode: str,
    fault_role: str,
    unrecoverable_modes: set[str],
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    for gate in FLOW_GATES:
        env = {
            "CTCP_MOCK_AGENT_FAULT_MODE": fault_mode,
            "CTCP_MOCK_AGENT_FAULT_ROLE": fault_role,
        }
        result = _dispatch_once(run_dir=run_dir, run_doc=run_doc, gate=gate, env=env)
        steps.append(result)

        status = str(result.get("status", ""))
        ok, msg = _validate_artifact_for_gate(run_dir, gate["path"])
        if status == "executed" and ok:
            continue

        if fault_mode not in unrecoverable_modes:
            recovery = _dispatch_once(run_dir=run_dir, run_doc=run_doc, gate=gate, env=None)
            recovery["recovery"] = True
            steps.append(recovery)
            rec_status = str(recovery.get("status", ""))
            rec_ok, rec_msg = _validate_artifact_for_gate(run_dir, gate["path"])
            if rec_status == "executed" and rec_ok:
                continue
            reason = f"recovery_failed: {rec_msg} (status={rec_status})"
        else:
            reason = (
                str(result.get("reason", "")).strip()
                or msg
                or f"fault_mode={fault_mode} gate={gate.get('path', '')}"
            )

        bundle = _materialize_failure_bundle(
            run_dir=run_dir,
            reason=reason,
            failed_gate=gate,
            steps=steps,
        )
        return {
            "completed": False,
            "fault_mode": fault_mode,
            "fault_role": fault_role,
            "failed_gate": gate["path"],
            "reason": reason,
            "bundle": str(bundle),
            "steps": steps,
        }

    return {
        "completed": True,
        "fault_mode": fault_mode,
        "fault_role": fault_role,
        "bundle": "",
        "steps": steps,
    }


class MockAgentPipelineTests(unittest.TestCase):
    def test_linked_flow_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            _prepare_run_dir(run_dir, _dispatch_config_all_mock())
            run_doc = {"goal": "linked flow smoke"}

            step_results: list[dict[str, Any]] = []
            for gate in FLOW_GATES:
                result = _dispatch_once(run_dir=run_dir, run_doc=run_doc, gate=gate, env=None)
                step_results.append(result)
                self.assertEqual(result.get("status"), "executed", msg=str(result))
                self.assertEqual(result.get("provider"), "mock_agent", msg=str(result))
                ok, reason = _validate_artifact_for_gate(run_dir, gate["path"])
                self.assertTrue(ok, msg=f"{gate['path']}: {reason}")

            required = [
                run_dir / "artifacts" / "guardrails.md",
                run_dir / "artifacts" / "analysis.md",
                run_dir / "artifacts" / "file_request.json",
                run_dir / "artifacts" / "context_pack.json",
                run_dir / "artifacts" / "PLAN_draft.md",
                run_dir / "reviews" / "review_contract.md",
                run_dir / "reviews" / "review_cost.md",
                run_dir / "artifacts" / "PLAN.md",
                run_dir / "artifacts" / "diff.patch",
            ]
            for path in required:
                self.assertTrue(path.exists(), msg=str(path))
            for row in step_results:
                provider = str(row.get("provider", "")).strip().lower()
                self.assertTrue(provider and provider != "n/a", msg=str(row))

    def test_routing_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            rows: list[dict[str, str]] = []

            run_default = base / "default"
            (run_default / "artifacts").mkdir(parents=True, exist_ok=True)
            run_doc = {"goal": "routing default"}
            preview_librarian = ctcp_dispatch.dispatch_preview(
                run_default,
                run_doc,
                {
                    "state": "blocked",
                    "owner": "Local Librarian",
                    "path": "artifacts/context_pack.json",
                    "reason": "waiting for context_pack.json",
                },
            )
            preview_chair = ctcp_dispatch.dispatch_preview(
                run_default,
                run_doc,
                {
                    "state": "blocked",
                    "owner": "Chair/Planner",
                    "path": "artifacts/PLAN_draft.md",
                    "reason": "waiting for PLAN_draft.md",
                },
            )
            rows.append(
                {
                    "case": "default_librarian",
                    "expected": "local_exec",
                    "actual": str(preview_librarian.get("provider", "")),
                }
            )
            rows.append(
                {
                    "case": "default_chair",
                    "expected": "manual_outbox",
                    "actual": str(preview_chair.get("provider", "")),
                }
            )

            run_recipe = base / "recipe"
            artifacts_recipe = run_recipe / "artifacts"
            artifacts_recipe.mkdir(parents=True, exist_ok=True)
            _write_json(
                artifacts_recipe / "find_result.json",
                {
                    "schema_version": "ctcp-find-result-v1",
                    "selected_workflow_id": "adlc_self_improve_core",
                },
            )
            preview_guardian = ctcp_dispatch.dispatch_preview(
                run_recipe,
                run_doc,
                {
                    "state": "blocked",
                    "owner": "Contract Guardian",
                    "path": "reviews/review_contract.md",
                    "reason": "waiting for review_contract.md",
                },
            )
            preview_patchmaker = ctcp_dispatch.dispatch_preview(
                run_recipe,
                run_doc,
                {
                    "state": "blocked",
                    "owner": "PatchMaker",
                    "path": "artifacts/diff.patch",
                    "reason": "waiting for diff.patch",
                },
            )
            rows.append(
                {
                    "case": "recipe_guardian",
                    "expected": "local_exec",
                    "actual": str(preview_guardian.get("provider", "")),
                }
            )
            rows.append(
                {
                    "case": "recipe_patchmaker",
                    "expected": "api_agent",
                    "actual": str(preview_patchmaker.get("provider", "")),
                }
            )

            run_fallback = base / "fallback"
            artifacts_fallback = run_fallback / "artifacts"
            artifacts_fallback.mkdir(parents=True, exist_ok=True)
            _write_json(
                artifacts_fallback / "dispatch_config.json",
                {
                    "schema_version": "ctcp-dispatch-config-v1",
                    "mode": "manual_outbox",
                    "role_providers": {
                        "patchmaker": "manual_outbox",
                        "fixer": "manual_outbox",
                    },
                    "budgets": {"max_outbox_prompts": 8},
                },
            )
            preview_patchmaker_fallback = ctcp_dispatch.dispatch_preview(
                run_fallback,
                run_doc,
                {
                    "state": "blocked",
                    "owner": "PatchMaker",
                    "path": "artifacts/diff.patch",
                    "reason": "waiting for diff.patch",
                },
            )
            preview_fixer_fallback = ctcp_dispatch.dispatch_preview(
                run_fallback,
                run_doc,
                {
                    "state": "fail",
                    "owner": "Fixer",
                    "path": "failure_bundle.zip",
                    "reason": "verify_failed",
                },
            )
            rows.append(
                {
                    "case": "fallback_patchmaker",
                    "expected": "api_agent",
                    "actual": str(preview_patchmaker_fallback.get("provider", "")),
                }
            )
            rows.append(
                {
                    "case": "fallback_fixer",
                    "expected": "api_agent",
                    "actual": str(preview_fixer_fallback.get("provider", "")),
                }
            )

            report_path = base / "routing_matrix_report.json"
            _write_json(report_path, {"rows": rows})
            self.assertTrue(report_path.exists())
            report_doc = _read_json(report_path)
            self.assertEqual(len(report_doc.get("rows", [])), len(rows))

            for row in rows:
                self.assertEqual(row["actual"], row["expected"], msg=str(row))
                self.assertTrue(row["actual"] and row["actual"] != "n/a", msg=str(row))

    def test_robustness_fault_injection(self) -> None:
        fault_modes = [
            "drop_output",
            "corrupt_json",
            "missing_field",
            "empty_file",
            "raise_exception",
            "invalid_patch",
        ]
        fault_roles = [
            "chair_file_request",
            "librarian_context_pack",
            "chair_plan_draft",
            "contract_guardian_review_contract",
            "cost_controller_review_cost",
            "patchmaker_make_patch",
        ]
        runs = 20
        unrecoverable_modes = {"raise_exception"}

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            summaries: list[dict[str, Any]] = []
            for idx in range(runs):
                mode = fault_modes[idx % len(fault_modes)]
                role = fault_roles[idx % len(fault_roles)]
                run_dir = base / f"fault_run_{idx:02d}"
                _prepare_run_dir(run_dir, _dispatch_config_all_mock())
                run_doc = {"goal": f"fault-injection-{idx:02d}"}
                result = _run_flow_with_fault(
                    run_dir=run_dir,
                    run_doc=run_doc,
                    fault_mode=mode,
                    fault_role=role,
                    unrecoverable_modes=unrecoverable_modes,
                )
                summaries.append(result)

                for step in result.get("steps", []):
                    provider = str(step.get("provider", "")).strip().lower()
                    self.assertTrue(provider and provider != "n/a", msg=str(step))

                if result.get("completed"):
                    ok, reason = _validate_artifact_for_gate(run_dir, "artifacts/diff.patch")
                    self.assertTrue(ok, msg=reason)
                else:
                    bundle = Path(str(result.get("bundle", "")))
                    self.assertTrue(bundle.exists(), msg=str(result))
                    verify = _read_json(run_dir / "artifacts" / "verify_report.json")
                    self.assertEqual(verify.get("result"), "FAIL")
                    failures = verify.get("failures", [])
                    self.assertTrue(isinstance(failures, list) and failures, msg=str(verify))
                    self.assertIn("message", failures[0], msg=str(verify))
                    trace_text = (run_dir / "TRACE.md").read_text(encoding="utf-8", errors="replace")
                    self.assertIn("failure_reason:", trace_text)

            report_path = base / "robustness_fault_injection_report.json"
            _write_json(
                report_path,
                {
                    "runs": runs,
                    "fault_modes": fault_modes,
                    "summaries": summaries,
                },
            )
            self.assertTrue(report_path.exists())

            covered_modes = {str(x.get("fault_mode", "")) for x in summaries}
            self.assertTrue(set(fault_modes).issubset(covered_modes), msg=str(covered_modes))
            completed_count = sum(1 for x in summaries if bool(x.get("completed")))
            failed_count = runs - completed_count
            self.assertGreater(completed_count, 0, msg=str(summaries))
            self.assertGreater(failed_count, 0, msg=str(summaries))


if __name__ == "__main__":
    unittest.main()
