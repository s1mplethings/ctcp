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
from datetime import datetime, timezone
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


def load_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    missing = [field for field in REQUIRED_TOP_LEVEL_FIELDS if field not in manifest]
    if missing:
        raise SystemExit(f"manifest missing required fields: {', '.join(missing)}")
    return manifest


def dry_run(root: Path, input_path: Path) -> dict[str, Any]:
    manifest = load_manifest(root)
    agents = manifest.get("agents", [])
    workflows = manifest.get("workflows", [])
    tools = manifest.get("tools", [])
    permissions = manifest.get("permissions", {})
    guardrails = manifest.get("guardrails", [])
    selected_agent = agents[0].get("name") if agents else ""
    workflow_start = workflows[0].get("state_name") if workflows else ""
    pending_tools = [
        tool.get("tool_name")
        for tool in tools
        if tool.get("requires_approval") is True or tool.get("side_effect_level") == "high"
    ]
    low_risk_tools = [
        tool.get("tool_name")
        for tool in tools
        if tool.get("requires_approval") is not True and tool.get("side_effect_level") != "high"
    ]
    result = {
        "mode": "dry_run",
        "selected_agent": selected_agent,
        "workflow_start": workflow_start,
        "tools_available": low_risk_tools,
        "approval_required_actions": permissions.get("approval_required_for", []),
        "pending_approval_tools": pending_tools,
        "guardrails_active": guardrails,
        "audit_log_required": bool(permissions.get("audit_log_required", True)),
        "input_path": str(input_path),
        "status": "ok",
    }
    audit_event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "dry_run",
        "selected_agent": selected_agent,
        "workflow_start": workflow_start,
        "pending_approval_tools": pending_tools,
        "status": "ok",
    }
    audit_path = root / "audit" / "dry_run_audit.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit_event, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    result["audit_event"] = audit_event
    result["audit_log_path"] = str(audit_path.relative_to(root)).replace("\\", "/")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run a generated agent scaffold")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    if not args.dry_run:
        raise SystemExit("only --dry-run mode is supported by this scaffold")
    root = Path(__file__).resolve().parent
    result = dry_run(root, Path(args.input))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


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
    def test_dry_run_outputs_json_and_audit_log(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "run_agent.py"), "--dry-run", "--input", str(ROOT / "sample_input.json")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        output = json.loads(completed.stdout)
        self.assertEqual(output["mode"], "dry_run")
        self.assertEqual(output["status"], "ok")
        self.assertEqual(output["audit_log_path"], "audit/dry_run_audit.jsonl")
        self.assertTrue((ROOT / "audit" / "dry_run_audit.jsonl").exists())

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


def _write_scaffold_runtime(target: Path, manifest: dict[str, Any]) -> None:
    (target / "run_agent.py").write_text(_runner_source(), encoding="utf-8")
    (target / "README.md").write_text(
        "\n".join(
            [
                f"# {manifest.get('system_name', 'Agent Scaffold')}",
                "",
                "This is a generated CTCP agent scaffold from `manifest.json`.",
                "It is not a full LLM agent runtime. The runner only supports safe dry-run inspection.",
                "",
                "## Dry Run",
                "",
                "`python run_agent.py --dry-run --input sample_input.json`",
                "",
                "High-risk tools are never executed by the scaffold. They are reported as pending approval.",
                "Dry-run writes `audit/dry_run_audit.jsonl` in the scaffold root.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(target / "sample_input.json", {"request": "dry-run scaffold smoke"})
    tests_dir = target / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "test_manifest_contract.py").write_text(_test_manifest_contract_source(), encoding="utf-8")
    (tests_dir / "test_permissions.py").write_text(_test_permissions_source(), encoding="utf-8")
    (tests_dir / "test_workflows.py").write_text(_test_workflows_source(), encoding="utf-8")
    (tests_dir / "test_dry_run.py").write_text(_test_dry_run_source(), encoding="utf-8")


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
        },
    )
    test_files = sorted(str(path.relative_to(target)).replace("\\", "/") for path in (target / "tests").glob("test_*.py"))
    return {
        "schema_version": "ctcp-agent-scaffold-generation-result-v1",
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
    }


def result_to_json(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)


def register_agent_scaffold_subcommand(subparsers: Any) -> None:
    parser = subparsers.add_parser("agent-scaffold", help="Generate a runnable dry-run scaffold from an agent manifest")
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
