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


LIVE_KEY = str(os.environ.get("OPENAI_API_KEY", "")).strip() or str(
    os.environ.get("CTCP_OPENAI_API_KEY", "")
).strip()
LIVE_ENABLED = str(os.environ.get("CTCP_LIVE_API", "")).strip() == "1" and bool(LIVE_KEY)

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

ROUTING_GATES: list[dict[str, str]] = [
    {
        "state": "blocked",
        "owner": "Chair/Planner",
        "path": "artifacts/PLAN_draft.md",
        "reason": "waiting for PLAN_draft.md",
    },
    {
        "state": "blocked",
        "owner": "Local Librarian",
        "path": "artifacts/context_pack.json",
        "reason": "waiting for context_pack.json",
    },
    {
        "state": "blocked",
        "owner": "PatchMaker",
        "path": "artifacts/diff.patch",
        "reason": "waiting for diff.patch",
    },
    {
        "state": "fail",
        "owner": "Fixer",
        "path": "failure_bundle.zip",
        "reason": "verify failed; fix required",
    },
]


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            doc = json.loads(text)
        except Exception:
            continue
        if isinstance(doc, dict):
            rows.append(doc)
    return rows


def _first_non_empty_line(text: str) -> str:
    for raw in (text or "").splitlines():
        line = raw.strip()
        if line:
            return line
    return ""


def _live_env(*, force_provider: bool) -> dict[str, str]:
    env = {"CTCP_LIVE_API": "1"}
    key = str(os.environ.get("OPENAI_API_KEY", "")).strip()
    if not key:
        alt = str(os.environ.get("CTCP_OPENAI_API_KEY", "")).strip()
        if alt:
            env["OPENAI_API_KEY"] = alt
    if force_provider:
        env["CTCP_FORCE_PROVIDER"] = "api_agent"
    return env


def _prepare_run_dir(run_dir: Path, *, with_recipe: bool) -> None:
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (run_dir / "reviews").mkdir(parents=True, exist_ok=True)
    (run_dir / "outbox").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    (run_dir / "TRACE.md").write_text("# Live API Trace\n\n", encoding="utf-8")
    if with_recipe:
        _write_json(
            run_dir / "artifacts" / "find_result.json",
            {
                "schema_version": "ctcp-find-result-v1",
                "selected_workflow_id": "live_api_all_roles",
            },
        )


def _dispatch_once(
    *,
    run_dir: Path,
    run_doc: dict[str, Any],
    gate: dict[str, str],
    force_provider: bool,
) -> dict[str, Any]:
    env = _live_env(force_provider=force_provider)
    with mock.patch.dict(os.environ, env, clear=False):
        return ctcp_dispatch.dispatch_once(run_dir, run_doc, gate, ROOT)


def _dispatch_preview(
    *,
    run_dir: Path,
    run_doc: dict[str, Any],
    gate: dict[str, str],
    force_provider: bool,
) -> dict[str, Any]:
    env = _live_env(force_provider=force_provider)
    with mock.patch.dict(os.environ, env, clear=False):
        return ctcp_dispatch.dispatch_preview(run_dir, run_doc, gate)


def _validate_file_request(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing artifacts/file_request.json"
    try:
        doc = _read_json(path)
    except Exception as exc:
        return False, f"file_request.json parse failed: {exc}"
    if doc.get("schema_version") != "ctcp-file-request-v1":
        return False, "file_request schema_version mismatch"
    if not isinstance(doc.get("needs"), list):
        return False, "file_request needs must be list"
    if not isinstance(doc.get("budget"), dict):
        return False, "file_request budget must be object"
    if "reason" not in doc:
        return False, "file_request missing reason"
    return True, "ok"


def _validate_context_pack(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing artifacts/context_pack.json"
    try:
        doc = _read_json(path)
    except Exception as exc:
        return False, f"context_pack.json parse failed: {exc}"
    if doc.get("schema_version") != "ctcp-context-pack-v1":
        return False, "context_pack schema_version mismatch"
    if not isinstance(doc.get("files"), list):
        return False, "context_pack files must be list"
    if not isinstance(doc.get("omitted"), list):
        return False, "context_pack omitted must be list"
    if "summary" not in doc:
        return False, "context_pack missing summary"
    return True, "ok"


def _validate_smoke_artifacts(run_dir: Path) -> tuple[bool, str]:
    md_paths = [
        run_dir / "artifacts" / "guardrails.md",
        run_dir / "artifacts" / "analysis.md",
        run_dir / "artifacts" / "PLAN_draft.md",
        run_dir / "reviews" / "review_contract.md",
        run_dir / "reviews" / "review_cost.md",
        run_dir / "artifacts" / "PLAN.md",
    ]
    for path in md_paths:
        if (not path.exists()) or (not path.read_text(encoding="utf-8", errors="replace").strip()):
            return False, f"missing_or_empty: {path.as_posix()}"

    ok, msg = _validate_file_request(run_dir / "artifacts" / "file_request.json")
    if not ok:
        return False, msg
    ok, msg = _validate_context_pack(run_dir / "artifacts" / "context_pack.json")
    if not ok:
        return False, msg

    patch = run_dir / "artifacts" / "diff.patch"
    if not patch.exists():
        return False, "missing artifacts/diff.patch"
    patch_text = patch.read_text(encoding="utf-8", errors="replace")
    first = _first_non_empty_line(patch_text).lower()
    if not first:
        return False, "diff.patch is empty"
    if not first.startswith("diff --git") and "empty patch" not in first:
        return False, "diff.patch does not look like a valid patch"
    return True, "ok"


def _assert_step_meta_all_api(test: unittest.TestCase, run_dir: Path) -> None:
    rows = _read_jsonl(run_dir / "step_meta.jsonl")
    test.assertTrue(rows, msg="step_meta.jsonl is empty")
    for row in rows:
        provider = str(row.get("provider", "")).strip().lower()
        test.assertEqual(provider, "api_agent", msg=str(row))
        test.assertNotEqual(provider, "n/a", msg=str(row))


def _tail_jsonl(path: Path, limit: int = 5) -> list[dict[str, Any]]:
    rows = _read_jsonl(path)
    if len(rows) <= limit:
        return rows
    return rows[-limit:]


def _expected_provider_for_gate(*, gate: dict[str, str], force_provider: bool) -> str:
    if force_provider:
        return "api_agent"
    gate_path = str(gate.get("path", "")).strip().lower()
    if "context_pack.json" in gate_path:
        return "local_exec"
    if "review_contract.md" in gate_path:
        return "local_exec"
    return "api_agent"


def _write_failure_evidence(run_dir: Path, reason: str) -> Path:
    ctcp_orchestrate.ensure_layout(run_dir)
    trace = run_dir / "TRACE.md"
    if not trace.exists():
        trace.write_text("# Live API Trace\n\n", encoding="utf-8")
    with trace.open("a", encoding="utf-8") as fh:
        fh.write(f"- fault_failure_reason: {reason}\n")
    events = run_dir / "events.jsonl"
    events.write_text(events.read_text(encoding="utf-8", errors="replace") if events.exists() else "", encoding="utf-8")
    _write_json(
        run_dir / "artifacts" / "verify_report.json",
        {
            "result": "FAIL",
            "gate": "live_fault_injection",
            "commands": [{"cmd": "fault_recovery", "exit_code": 1}],
            "failures": [{"kind": "contract_fault", "id": "fault", "message": reason}],
        },
    )
    bundle, _ = ctcp_orchestrate.ensure_failure_bundle(run_dir)
    return bundle


@unittest.skipUnless(LIVE_ENABLED, "requires CTCP_LIVE_API=1 and OPENAI_API_KEY (or CTCP_OPENAI_API_KEY)")
class LiveApiOnlyPipelineTests(unittest.TestCase):
    def test_api_linked_flow_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "smoke"
            _prepare_run_dir(run_dir, with_recipe=True)
            run_doc = {"goal": "live api linked flow smoke"}

            step_rows: list[dict[str, Any]] = []
            for gate in FLOW_GATES:
                result = _dispatch_once(
                    run_dir=run_dir,
                    run_doc=run_doc,
                    gate=gate,
                    force_provider=True,
                )
                step_rows.append(result)
                self.assertEqual(result.get("status"), "executed", msg=str(result))
                self.assertEqual(result.get("provider"), "api_agent", msg=str(result))

            ok, reason = _validate_smoke_artifacts(run_dir)
            self.assertTrue(ok, msg=reason)

            api_rows = _read_jsonl(run_dir / "api_calls.jsonl")
            self.assertGreater(len(api_rows), 0, msg="api_calls.jsonl has no records")
            self.assertTrue(
                any(
                    str(row.get("role", "")).strip().lower() == "chair"
                    and str(row.get("action", "")).strip().lower() == "plan_draft"
                    for row in api_rows
                ),
                msg="missing chair plan_draft API call",
            )
            self.assertTrue(
                any(
                    str(row.get("role", "")).strip().lower() == "chair"
                    and str(row.get("action", "")).strip().lower() == "plan_signed"
                    for row in api_rows
                ),
                msg="missing chair plan_signed API call",
            )

            _assert_step_meta_all_api(self, run_dir)

    def test_api_routing_matrix(self) -> None:
        cases = [
            {"name": "env_only", "force": True, "recipe": False},
            {"name": "recipe_only", "force": False, "recipe": True},
            {"name": "env_and_recipe", "force": True, "recipe": True},
        ]

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            all_rows: list[dict[str, Any]] = []

            for case in cases:
                run_dir = base / case["name"]
                _prepare_run_dir(run_dir, with_recipe=bool(case["recipe"]))
                run_doc = {"goal": f"routing matrix {case['name']}"}
                rows: list[dict[str, Any]] = []
                for gate in ROUTING_GATES:
                    expected_provider = _expected_provider_for_gate(
                        gate=gate,
                        force_provider=bool(case["force"]),
                    )
                    preview = _dispatch_preview(
                        run_dir=run_dir,
                        run_doc=run_doc,
                        gate=gate,
                        force_provider=bool(case["force"]),
                    )
                    row = {
                        "case": case["name"],
                        "gate": gate["path"],
                        "expected_provider": expected_provider,
                        "actual_provider": str(preview.get("provider", "")),
                        "status": str(preview.get("status", "")),
                        "reason": str(preview.get("reason", "")),
                    }
                    rows.append(row)
                    all_rows.append(row)

                report = {
                    "case": case["name"],
                    "rows": rows,
                }
                _write_json(run_dir / "routing_report.json", report)

                for row in rows:
                    if row["actual_provider"] != row["expected_provider"]:
                        tail_step_meta = _tail_jsonl(run_dir / "step_meta.jsonl")
                        tail_api_calls = _tail_jsonl(run_dir / "api_calls.jsonl")
                        self.fail(
                            "routing mismatch "
                            + json.dumps(
                                {
                                    "row": row,
                                    "step_meta_tail": tail_step_meta,
                                    "api_calls_tail": tail_api_calls,
                                },
                                ensure_ascii=False,
                            )
                        )

            self.assertEqual(len(all_rows), len(cases) * len(ROUTING_GATES))

    def test_api_robustness_faults(self) -> None:
        faults = [
            {
                "name": "F1_drop_context_pack",
                "inject": lambda run_dir: (run_dir / "artifacts" / "context_pack.json").unlink(missing_ok=True),
                "start_idx": 3,
            },
            {
                "name": "F2_corrupt_file_request_json",
                "inject": lambda run_dir: (run_dir / "artifacts" / "file_request.json").write_text(
                    '{"schema_version":"ctcp-file-request-v1","needs":[', encoding="utf-8"
                ),
                "start_idx": 2,
            },
            {
                "name": "F3_missing_context_pack_fields",
                "inject": lambda run_dir: _write_json(
                    run_dir / "artifacts" / "context_pack.json",
                    {"schema_version": "ctcp-context-pack-v1", "summary": "fault"},
                ),
                "start_idx": 3,
            },
            {
                "name": "F4_empty_plan_draft",
                "inject": lambda run_dir: (run_dir / "artifacts" / "PLAN_draft.md").write_text("", encoding="utf-8"),
                "start_idx": 4,
            },
        ]

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            outcomes: list[dict[str, Any]] = []
            for idx, fault in enumerate(faults):
                run_dir = base / f"fault_{idx:02d}"
                _prepare_run_dir(run_dir, with_recipe=True)
                run_doc = {"goal": f"live api fault test {fault['name']}"}

                pre_ok = True
                pre_reason = ""
                for gate in FLOW_GATES[: int(fault["start_idx"]) + 1]:
                    result = _dispatch_once(
                        run_dir=run_dir,
                        run_doc=run_doc,
                        gate=gate,
                        force_provider=True,
                    )
                    if result.get("status") != "executed":
                        pre_ok = False
                        pre_reason = f"preparation_failed gate={gate['path']} reason={result}"
                        break
                if not pre_ok:
                    bundle = _write_failure_evidence(run_dir, pre_reason)
                    outcomes.append(
                        {
                            "fault": fault["name"],
                            "completed": False,
                            "reason": pre_reason,
                            "bundle": str(bundle),
                        }
                    )
                    continue

                fault["inject"](run_dir)

                completed = True
                failure_reason = ""
                for gate in FLOW_GATES[int(fault["start_idx"]) :]:
                    result = _dispatch_once(
                        run_dir=run_dir,
                        run_doc=run_doc,
                        gate=gate,
                        force_provider=True,
                    )
                    if result.get("status") != "executed":
                        completed = False
                        failure_reason = (
                            f"recovery_dispatch_failed fault={fault['name']} gate={gate['path']} result={result}"
                        )
                        break

                ok, contract_reason = _validate_smoke_artifacts(run_dir)
                if completed and (not ok):
                    completed = False
                    failure_reason = f"contract_not_recovered fault={fault['name']} reason={contract_reason}"

                if completed:
                    outcomes.append(
                        {
                            "fault": fault["name"],
                            "completed": True,
                            "reason": "",
                            "bundle": "",
                        }
                    )
                else:
                    bundle = _write_failure_evidence(run_dir, failure_reason)
                    trace_text = (run_dir / "TRACE.md").read_text(encoding="utf-8", errors="replace")
                    self.assertIn("fault_failure_reason:", trace_text, msg=fault["name"])
                    outcomes.append(
                        {
                            "fault": fault["name"],
                            "completed": False,
                            "reason": failure_reason,
                            "bundle": str(bundle),
                        }
                    )

                _assert_step_meta_all_api(self, run_dir)

            covered = {str(row.get("fault", "")) for row in outcomes}
            self.assertEqual(covered, {row["name"] for row in faults}, msg=str(outcomes))
            for row in outcomes:
                if row["completed"]:
                    continue
                self.assertTrue(Path(str(row["bundle"])).exists(), msg=str(row))


if __name__ == "__main__":
    unittest.main()
