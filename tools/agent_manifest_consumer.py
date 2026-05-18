from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL_FIELDS = (
    "manifest_version",
    "system_name",
    "agents",
    "tools",
    "workflows",
    "memory",
    "permissions",
    "guardrails",
    "test_cases",
)

LIST_FIELDS = ("agents", "tools", "workflows", "memory", "guardrails", "test_cases")
SENTINEL = ".ctcp_agent_scaffold.json"
TEMPLATE_DIR = Path(__file__).resolve().with_name("agent_scaffold_runtime_templates")


class ManifestConsumerError(ValueError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestConsumerError(f"manifest is not valid JSON: {path}: {exc}") from exc
    if not isinstance(doc, dict):
        raise ManifestConsumerError("manifest must be a JSON object")
    return doc


def _write_json(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _template_source(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def _slug(value: Any, fallback: str) -> str:
    text = str(value or fallback).strip().lower()
    text = re.sub(r"[^a-z0-9_.-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("._-")
    return text or fallback


def validate_manifest(manifest: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_TOP_LEVEL_FIELDS if field not in manifest]
    if missing:
        raise ManifestConsumerError(f"manifest missing required fields: {', '.join(missing)}")
    for field in LIST_FIELDS:
        if not isinstance(manifest.get(field), list):
            raise ManifestConsumerError(f"manifest field must be an array: {field}")
    if not isinstance(manifest.get("permissions"), dict):
        raise ManifestConsumerError("manifest field must be an object: permissions")
    for index, agent in enumerate(manifest["agents"]):
        if not isinstance(agent, dict):
            raise ManifestConsumerError(f"agent definition at index {index} must be an object")
        if not agent.get("name"):
            raise ManifestConsumerError(f"agent definition at index {index} missing name")
    for index, tool in enumerate(manifest["tools"]):
        if not isinstance(tool, dict):
            raise ManifestConsumerError(f"tool definition at index {index} must be an object")
        if not tool.get("tool_name"):
            raise ManifestConsumerError(f"tool definition at index {index} missing tool_name")
        if tool.get("side_effect_level") == "high":
            if tool.get("requires_approval") is not True:
                raise ManifestConsumerError(f"high side effect tool must require approval: {tool.get('tool_name')}")
            if tool.get("audit_log_required") is not True:
                raise ManifestConsumerError(f"high side effect tool must require audit log: {tool.get('tool_name')}")


def _prepare_output_dir(output_dir: Path, force: bool) -> Path:
    target = output_dir.resolve()
    if target.exists() and any(target.iterdir()):
        sentinel = target / SENTINEL
        if not force:
            raise ManifestConsumerError(f"output directory is not empty; pass --force to replace a CTCP scaffold: {target}")
        if not sentinel.exists():
            raise ManifestConsumerError(f"refusing to overwrite non-scaffold directory: {target}")
        for child in target.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    target.mkdir(parents=True, exist_ok=True)
    return target


def _write_definition_files(target: Path, manifest: dict[str, Any]) -> dict[str, int]:
    counts = {
        "agents": 0,
        "tools": 0,
        "workflows": len(manifest["workflows"]),
        "memory": len(manifest["memory"]),
        "guardrails": len(manifest["guardrails"]),
    }
    for index, agent in enumerate(manifest["agents"]):
        _write_json(target / "agents" / f"{_slug(agent.get('name'), f'agent_{index}')}.json", agent)
        counts["agents"] += 1
    for index, tool in enumerate(manifest["tools"]):
        _write_json(target / "tools" / f"{_slug(tool.get('tool_name'), f'tool_{index}')}.json", tool)
        counts["tools"] += 1
    _write_json(target / "workflows" / "workflow.json", {"workflows": manifest["workflows"]})
    _write_json(target / "memory" / "memory_schema.json", {"memory": manifest["memory"]})
    _write_json(target / "permissions" / "permissions.json", manifest["permissions"])
    _write_json(target / "guardrails" / "guardrails.json", {"guardrails": manifest["guardrails"]})
    return counts


def _runner_source() -> str:
    return r'''from __future__ import annotations

import argparse
import json
from pathlib import Path

from runtime.runtime_engine import dry_run, run


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a generated CTCP agent scaffold")
    parser.add_argument("--dry-run", action="store_true", help="Preview workflow and permissions without side effects")
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = root / input_path
    try:
        result = dry_run(root, input_path) if args.dry_run else run(root, input_path)
    except Exception as exc:
        result = {
            "mode": "dry-run" if args.dry_run else "run",
            "status": "failed",
            "error": str(exc),
            "runtime_state_path": "runtime_state.json",
            "audit_log_path": "audit/events.jsonl",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("status") not in {"failed"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _runtime_init_source() -> str:
    return ""


def _runtime_tools_source() -> str:
    return r'''from __future__ import annotations

from typing import Any

from .runtime_tool_registry import get_adapter, normalize_tool_contract, supported_local_tool_names


def resolve_local_tool(tool_name: str):
    tool = normalize_tool_contract({"tool_name": tool_name, "side_effect_level": "low", "requires_approval": False})
    return get_adapter(tool)


def execute_tool(tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    tool = normalize_tool_contract({"tool_name": tool_name, "side_effect_level": "low", "requires_approval": False})
    adapter = get_adapter(tool)
    if adapter is None:
        raise ValueError(f"unsupported local tool: {tool_name}")
    return adapter.execute(payload, {"tool_name": tool_name})
'''


def _runtime_permissions_source() -> str:
    return r'''from __future__ import annotations

from typing import Any

from .runtime_tool_policy import can_execute_tool


def permission_decision(tool: dict[str, Any], agent: str) -> dict[str, Any]:
    decision = can_execute_tool(agent, tool, "run", {})
    action = {
        "executed": "execute",
        "blocked": "blocked",
        "pending_approval": "pending",
        "unsupported": "blocked",
    }.get(decision["status"], "blocked")
    return {
        "action": action,
        "reason": decision["reason"],
        "tool": decision["tool_name"],
        "status": decision["status"],
    }
'''


def _runtime_state_source() -> str:
    return r'''from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_state(agent: str, workflow_state: str) -> dict[str, Any]:
    return {
        "current_agent": agent,
        "current_workflow_state": workflow_state,
        "completed_steps": [],
        "executed_tools": [],
        "blocked_tools": [],
        "pending_approvals": [],
        "unsupported_tools": [],
        "last_tool_results": [],
        "memory": {},
        "last_updated_at": utc_now(),
    }


def load_state(root: Path, agent: str, workflow_state: str) -> dict[str, Any]:
    path = root / "runtime_state.json"
    if not path.exists():
        return default_state(agent, workflow_state)
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("runtime_state.json must be a JSON object")
    base = default_state(agent, workflow_state)
    base.update(doc)
    for key in ("completed_steps", "executed_tools", "blocked_tools", "pending_approvals", "unsupported_tools", "last_tool_results"):
        if not isinstance(base.get(key), list):
            base[key] = []
    if not isinstance(base.get("memory"), dict):
        base["memory"] = {}
    return base


def save_state(root: Path, state: dict[str, Any]) -> Path:
    state["last_updated_at"] = utc_now()
    path = root / "runtime_state.json"
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def append_unique(rows: list[Any], row: Any) -> None:
    if row not in rows:
        rows.append(row)
'''


def _runtime_audit_source() -> str:
    return r'''from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_event(root: Path, event_type: str, *, agent: str, tool: str = "", status: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    path = root / "audit" / "events.jsonl"
    existing = 0
    if path.exists():
        existing = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    event_id = f"evt-{existing + 1:06d}"
    detail_doc = details or {}
    event = {
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "agent": agent,
        "tool": tool,
        "status": status,
        "details": detail_doc,
    }
    if event_type == "tool_decision":
        event.update(
            {
                "tool_name": tool,
                "decision": str(detail_doc.get("decision", status)),
                "reason": str(detail_doc.get("reason", "")),
                "side_effect_level": str(detail_doc.get("side_effect_level", "")),
                "requires_approval": bool(detail_doc.get("requires_approval", False)),
                "query": str(detail_doc.get("query", "")),
                "url": str(detail_doc.get("url", "")),
                "sources": detail_doc.get("sources", []),
                "audit_required": bool(detail_doc.get("audit_required", False)),
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event
'''


def _runtime_tool_result_source() -> str:
    return r'''from __future__ import annotations

from typing import Any


TOOL_RESULT_FIELDS = {
    "tool_name",
    "status",
    "reason",
    "side_effect_level",
    "requires_approval",
    "output",
    "audit_event_id",
    "duration_ms",
}

VALID_STATUSES = {"executed", "blocked", "pending_approval", "unsupported", "failed"}


def make_tool_result(
    *,
    tool_name: str,
    status: str,
    reason: str,
    side_effect_level: str,
    requires_approval: bool,
    output: dict[str, Any] | None = None,
    audit_event_id: str = "",
    duration_ms: int = 0,
) -> dict[str, Any]:
    normalized_status = status if status in VALID_STATUSES else "failed"
    return {
        "tool_name": tool_name,
        "status": normalized_status,
        "reason": reason,
        "side_effect_level": side_effect_level,
        "requires_approval": bool(requires_approval),
        "output": output or {},
        "audit_event_id": audit_event_id,
        "duration_ms": max(0, int(duration_ms)),
    }


def is_tool_result(value: Any) -> bool:
    return isinstance(value, dict) and TOOL_RESULT_FIELDS.issubset(value) and value.get("status") in VALID_STATUSES
'''


def _runtime_tool_registry_source() -> str:
    return _template_source("runtime_tool_registry.py.tpl")


def _runtime_tool_policy_source() -> str:
    return r'''from __future__ import annotations

from typing import Any

from .runtime_tool_registry import WEB_RUNTIME_ADAPTERS, normalize_tool_contract


PROHIBITED_ACTIONS = {
    "rollback": "prohibited_action",
    "refund": "prohibited_action",
    "legal admission": "prohibited_action",
    "legal_admission": "prohibited_action",
    "compensation promise": "prohibited_action",
    "compensation_promise": "prohibited_action",
    "disable audit log": "prohibited_action",
    "audit disable": "prohibited_action",
    "audit_log_disable": "prohibited_action",
    "bypass approval": "prohibited_action",
    "approval bypass": "prohibited_action",
    "approval_bypass": "prohibited_action",
    "permanent ban": "prohibited_action",
    "delete account": "prohibited_action",
    "diagnosis": "prohibited_action",
    "prescription": "prohibited_action",
    "direct buy": "prohibited_action",
    "direct sell": "prohibited_action",
    "buy/sell instruction": "prohibited_action",
    "protected attribute": "prohibited_action",
    "protected_attribute": "prohibited_action",
}


def _decision(tool: dict[str, Any], status: str, reason: str) -> dict[str, Any]:
    return {
        "tool_name": tool["tool_name"],
        "status": status,
        "decision": status,
        "reason": reason,
        "side_effect_level": tool["side_effect_level"],
        "requires_approval": bool(tool["requires_approval"]),
    }


def _tool_text(tool: dict[str, Any], tool_input: dict[str, Any]) -> str:
    return " ".join([str(tool.get("tool_name", "")), str(tool.get("description", ""))]).lower().replace(".", " ")


def can_execute_tool(agent: str, tool: dict[str, Any], mode: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_tool_contract(tool)
    if mode == "dry-run":
        return _decision(normalized, "blocked", "dry_run_never_executes")

    runtime_adapter = normalized.get("runtime_adapter")
    if runtime_adapter in WEB_RUNTIME_ADAPTERS:
        allowed_callers = normalized.get("allowed_callers") or []
        if (
            normalized["tool_name"] != runtime_adapter
            or normalized["side_effect_level"] != "none"
            or normalized["requires_approval"] is True
            or normalized["audit_log_required"] is not True
            or not allowed_callers
            or agent not in allowed_callers
        ):
            return _decision(normalized, "blocked", "web_permission_denied")
        return _decision(normalized, "executed", "allowed")

    if normalized["runtime_adapter"] != "local_deterministic" and (
        "side_effect_level" not in tool or "requires_approval" not in tool
    ):
        return _decision(normalized, "blocked", "invalid_tool_contract")

    allowed_callers = normalized.get("allowed_callers") or []
    if allowed_callers and agent not in allowed_callers:
        return _decision(normalized, "blocked", "permission_denied")

    text = _tool_text(normalized, tool_input)
    for term, reason in PROHIBITED_ACTIONS.items():
        if term in text:
            return _decision(normalized, "blocked", reason)

    if normalized["side_effect_level"] in {"medium", "high"} and normalized["audit_log_required"] is False:
        return _decision(normalized, "blocked", "invalid_tool_contract")

    if runtime_adapter == "external_blocked":
        return _decision(normalized, "blocked", "external_tool_blocked")
    if runtime_adapter != "local_deterministic" or not normalized.get("adapter_name"):
        return _decision(normalized, "unsupported", "unsupported_tool")

    if normalized["requires_approval"] is True:
        return _decision(normalized, "pending_approval", "requires_approval")

    if normalized["side_effect_level"] in {"medium", "high"}:
        return _decision(normalized, "pending_approval", "side_effect_requires_approval")

    return _decision(normalized, "executed", "allowed")
'''


def _runtime_tool_executor_source() -> str:
    return r'''from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .runtime_audit import write_event
from .runtime_tool_policy import can_execute_tool
from .runtime_tool_registry import WEB_RUNTIME_ADAPTERS, get_adapter, normalize_tool_contract
from .runtime_tool_result import make_tool_result


def _duration_ms(start: datetime) -> int:
    return int((datetime.now(timezone.utc) - start).total_seconds() * 1000)


def _web_sources(output: dict[str, Any]) -> list[dict[str, Any]]:
    sources = output.get("sources")
    if isinstance(sources, list):
        return [source for source in sources if isinstance(source, dict) and source.get("url")]
    source = output.get("source")
    if isinstance(source, dict) and source.get("url"):
        return [source]
    return []


def execute_tool_decision(
    root: Path,
    *,
    agent: str,
    tool: dict[str, Any],
    tool_input: dict[str, Any],
    context: dict[str, Any] | None = None,
    mode: str = "run",
) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    normalized = normalize_tool_contract(tool)
    decision = can_execute_tool(agent, normalized, mode, tool_input)
    output: dict[str, Any] = {}
    status = decision["status"]
    reason = decision["reason"]

    if status == "executed":
        adapter = get_adapter(normalized)
        if adapter is None:
            status = "unsupported"
            reason = "unsupported_tool"
        else:
            try:
                output = adapter.execute(tool_input, {"agent": agent, "tool_name": normalized["tool_name"], "root": root, **(context or {})})
                if normalized["runtime_adapter"] in WEB_RUNTIME_ADAPTERS and not _web_sources(output):
                    status = "failed"
                    reason = "missing_sources"
            except Exception as exc:  # pragma: no cover - generated runtime defensive path
                status = "failed"
                message = str(exc)
                reason = "web_provider_unavailable" if "web_provider_unavailable" in message else f"adapter_failed: {message}"

    audit = write_event(
        root,
        "tool_decision",
        agent=agent,
        tool=normalized["tool_name"],
        status=status,
        details={
            "tool_name": normalized["tool_name"],
            "decision": status,
            "reason": reason,
            "agent": agent,
            "side_effect_level": normalized["side_effect_level"],
            "requires_approval": normalized["requires_approval"],
            "runtime_adapter": normalized["runtime_adapter"],
            "adapter_name": normalized.get("adapter_name", ""),
            "query": output.get("query") or tool_input.get("query") or tool_input.get("request") or "",
            "url": output.get("url") or tool_input.get("url") or "",
            "sources": _web_sources(output),
            "audit_required": normalized["audit_log_required"],
        },
    )
    return make_tool_result(
        tool_name=normalized["tool_name"],
        status=status,
        reason=reason,
        side_effect_level=normalized["side_effect_level"],
        requires_approval=normalized["requires_approval"],
        output=output,
        audit_event_id=str(audit.get("event_id", "")),
        duration_ms=_duration_ms(started),
    )
'''


def _runtime_engine_source() -> str:
    return _template_source("runtime_engine.py.tpl")


def _runtime_planner_source() -> str:
    return _template_source("runtime_planner.py.tpl")


def _test_manifest_contract_source() -> str:
    return r'''from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"manifest_version", "system_name", "agents", "tools", "workflows", "memory", "permissions", "guardrails", "test_cases"}


class ManifestContractTests(unittest.TestCase):
    def test_manifest_contract(self) -> None:
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(REQUIRED.issubset(manifest))
        for field in ("agents", "tools", "workflows", "memory", "guardrails", "test_cases"):
            self.assertIsInstance(manifest[field], list)
        self.assertIsInstance(manifest["permissions"], dict)


if __name__ == "__main__":
    unittest.main()
'''


def _test_permissions_source() -> str:
    return r'''from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PermissionTests(unittest.TestCase):
    def test_high_side_effect_tools_are_approval_gated(self) -> None:
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["permissions"].get("audit_log_required", True))
        for tool in manifest["tools"]:
            if tool.get("side_effect_level") == "high":
                self.assertTrue(tool.get("requires_approval"), tool)
                self.assertTrue(tool.get("audit_log_required"), tool)


if __name__ == "__main__":
    unittest.main()
'''


def _test_workflows_source() -> str:
    return r'''from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WorkflowTests(unittest.TestCase):
    def test_workflows_have_required_flow_fields(self) -> None:
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["workflows"])
        for state in manifest["workflows"]:
            self.assertIn("state_name", state)
            self.assertIn("next_states", state)
            self.assertIn("failure_paths", state)


if __name__ == "__main__":
    unittest.main()
'''


def _test_dry_run_source() -> str:
    return r'''from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DryRunTests(unittest.TestCase):
    def test_dry_run_outputs_json_without_state_side_effects(self) -> None:
        state_path = ROOT / "runtime_state.json"
        audit_path = ROOT / "audit" / "events.jsonl"
        before_state = state_path.read_text(encoding="utf-8") if state_path.exists() else None
        before_audit = audit_path.read_text(encoding="utf-8") if audit_path.exists() else None
        completed = subprocess.run(
            [sys.executable, str(ROOT / "run_agent.py"), "--dry-run", "--input", str(ROOT / "sample_input.json")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        output = json.loads(completed.stdout)
        self.assertEqual(output["mode"], "dry-run")
        self.assertEqual(output["status"], "ok")
        self.assertIn("available_tools", output)
        self.assertIn("blocked_tools", output)
        self.assertIn("pending_approvals", output)
        after_state = state_path.read_text(encoding="utf-8") if state_path.exists() else None
        after_audit = audit_path.read_text(encoding="utf-8") if audit_path.exists() else None
        self.assertEqual(before_state, after_state)
        self.assertEqual(before_audit, after_audit)

    def test_dry_run_does_not_expose_high_risk_tools_as_available(self) -> None:
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        completed = subprocess.run(
            [sys.executable, str(ROOT / "run_agent.py"), "--dry-run", "--input", str(ROOT / "sample_input.json")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        output = json.loads(completed.stdout)
        high_tools = {tool["tool_name"] for tool in manifest["tools"] if tool.get("side_effect_level") == "high"}
        self.assertTrue(high_tools.issubset(set(output["pending_approval_tools"])))
        self.assertTrue(high_tools.isdisjoint(set(output["tools_available"])))


if __name__ == "__main__":
    unittest.main()
'''


def _test_runtime_source() -> str:
    return r'''from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RuntimeTests(unittest.TestCase):
    def test_real_run_writes_state_and_audit(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "run_agent.py"), "--input", str(ROOT / "sample_input.json")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        output = json.loads(completed.stdout)
        self.assertEqual(output["mode"], "run")
        self.assertIn(output["status"], {"completed", "blocked"})
        self.assertIn("final_answer", output)
        self.assertEqual(output["planner_trace_path"], "planner_trace.json")
        self.assertTrue((ROOT / "planner_trace.json").exists())
        self.assertTrue((ROOT / "runtime_state.json").exists())
        self.assertTrue((ROOT / "audit" / "events.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
'''


def _write_scaffold_runtime(target: Path, manifest: dict[str, Any]) -> None:
    _write_text(target / "run_agent.py", _runner_source())
    runtime_dir = target / "runtime"
    _write_text(runtime_dir / "__init__.py", _runtime_init_source())
    _write_text(runtime_dir / "runtime_engine.py", _runtime_engine_source())
    _write_text(runtime_dir / "runtime_planner.py", _runtime_planner_source())
    _write_text(runtime_dir / "runtime_tools.py", _runtime_tools_source())
    _write_text(runtime_dir / "runtime_permissions.py", _runtime_permissions_source())
    _write_text(runtime_dir / "runtime_tool_registry.py", _runtime_tool_registry_source())
    _write_text(runtime_dir / "runtime_tool_executor.py", _runtime_tool_executor_source())
    _write_text(runtime_dir / "runtime_tool_result.py", _runtime_tool_result_source())
    _write_text(runtime_dir / "runtime_tool_policy.py", _runtime_tool_policy_source())
    _write_text(runtime_dir / "runtime_state.py", _runtime_state_source())
    _write_text(runtime_dir / "runtime_audit.py", _runtime_audit_source())
    _write_text(
        target / "README.md",
        "\n".join(
            [
                f"# {manifest.get('system_name', 'Agent Scaffold')}",
                "",
                "This is a generated CTCP agent scaffold from `manifest.json`.",
                "It supports a minimal planner runtime loop with a tool registry, policy layer, executor, and ToolResult schema. Deterministic local tools are available by default; web tools require explicit manifest declarations and policy approval.",
                "",
                "No real internet provider is implemented in this scaffold. Tests may enable the deterministic fixture provider with `CTCP_AGENT_WEB_PROVIDER=fixture`.",
                "",
                "## Dry Run",
                "",
                "`python run_agent.py --dry-run --input sample_input.json`",
                "",
                "Dry-run previews workflow, tools, guardrails, blocked tools, and pending approvals without writing runtime state or audit events.",
                "",
                "## Real Run",
                "",
                "`python run_agent.py --input sample_input.json`",
                "",
                "Real run uses the deterministic planner by default, writes `planner_trace.json` and `runtime_state.json`, appends `audit/events.jsonl`, blocks or queues risky tools, and records unsupported tools without crashing. Web-derived outputs must include sources/citations.",
            ]
        )
        + "\n",
    )
    _write_json(target / "sample_input.json", {"request": "runtime scaffold smoke"})
    tests_dir = target / "tests"
    _write_text(tests_dir / "test_manifest_contract.py", _test_manifest_contract_source())
    _write_text(tests_dir / "test_permissions.py", _test_permissions_source())
    _write_text(tests_dir / "test_workflows.py", _test_workflows_source())
    _write_text(tests_dir / "test_dry_run.py", _test_dry_run_source())
    _write_text(tests_dir / "test_runtime.py", _test_runtime_source())


def generate_agent_scaffold(manifest_path: Path, output_dir: Path, *, force: bool = False) -> dict[str, Any]:
    source = manifest_path.resolve()
    if not source.exists():
        raise ManifestConsumerError(f"manifest not found: {source}")
    if not source.is_file():
        raise ManifestConsumerError(f"manifest path must be a file: {source}")
    manifest = _read_json(source)
    validate_manifest(manifest)
    target = _prepare_output_dir(output_dir, force=force)
    _write_json(target / "manifest.json", manifest)
    counts = _write_definition_files(target, manifest)
    _write_scaffold_runtime(target, manifest)
    _write_json(
        target / SENTINEL,
        {
            "schema_version": "ctcp-agent-scaffold-sentinel-v1",
            "manifest_path": source.as_posix(),
            "system_name": manifest.get("system_name"),
            "runtime_mode": "minimal-local-deterministic",
        },
    )
    test_files = sorted(str(path.relative_to(target)).replace("\\", "/") for path in (target / "tests").glob("test_*.py"))
    return {
        "schema_version": "ctcp-agent-scaffold-generation-result-v2",
        "mode": "agent-scaffold",
        "status": "pass",
        "entrypoint": "scripts/ctcp_orchestrate.py agent-scaffold",
        "manifest_path": source.as_posix(),
        "output_dir": target.as_posix(),
        "system_name": manifest.get("system_name"),
        "agents_count": counts["agents"],
        "tools_count": counts["tools"],
        "workflows_count": counts["workflows"],
        "test_files": test_files,
        "dry_run_entrypoint": "run_agent.py --dry-run --input sample_input.json",
        "runtime_entrypoint": "run_agent.py --input sample_input.json",
        "runtime_files": [
            "runtime/runtime_engine.py",
            "runtime/runtime_planner.py",
            "runtime/runtime_tools.py",
            "runtime/runtime_permissions.py",
            "runtime/runtime_tool_registry.py",
            "runtime/runtime_tool_executor.py",
            "runtime/runtime_tool_result.py",
            "runtime/runtime_tool_policy.py",
            "runtime/runtime_state.py",
            "runtime/runtime_audit.py",
        ],
    }


def result_to_json(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)


def register_agent_scaffold_subcommand(subparsers: Any) -> None:
    parser = subparsers.add_parser("agent-scaffold", help="Generate a runnable local deterministic scaffold from an agent manifest")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--force", action="store_true", help="Replace an existing CTCP-generated scaffold directory")


def run_agent_scaffold_command(args: Any) -> int:
    try:
        result = generate_agent_scaffold(Path(args.manifest), Path(args.output_dir), force=bool(args.force))
    except Exception as exc:
        print(f"[ctcp_orchestrate][agent-scaffold][error] {exc}", file=sys.stderr)
        return 2
    print(result_to_json(result))
    return 0
