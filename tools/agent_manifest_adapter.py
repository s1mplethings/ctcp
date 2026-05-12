from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from tools.agent_manifest_generator import generate_manifest_from_file, write_manifest


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


def generate_agent_manifest_artifact(input_path: Path, output_path: Path) -> dict[str, Any]:
    """Generate an agent manifest through the CTCP integration boundary."""
    source = input_path.resolve()
    target = output_path.resolve()
    if not source.exists():
        raise FileNotFoundError(f"agent manifest input not found: {source}")
    if not source.is_file():
        raise ValueError(f"agent manifest input must be a file: {source}")

    manifest = generate_manifest_from_file(source)
    missing = [field for field in REQUIRED_TOP_LEVEL_FIELDS if field not in manifest]
    if missing:
        raise ValueError(f"agent manifest generator returned missing fields: {', '.join(missing)}")
    write_manifest(target, manifest)
    return {
        "schema_version": "ctcp-agent-manifest-generation-result-v1",
        "mode": "agent-manifest",
        "status": "pass",
        "entrypoint": "scripts/ctcp_orchestrate.py agent-manifest",
        "input_path": source.as_posix(),
        "output_path": target.as_posix(),
        "manifest_version": manifest.get("manifest_version"),
        "system_name": manifest.get("system_name"),
        "agents_count": len(manifest.get("agents", [])),
        "tools_count": len(manifest.get("tools", [])),
        "workflows_count": len(manifest.get("workflows", [])),
    }


def result_to_json(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)


def register_agent_manifest_subcommand(subparsers: Any) -> None:
    parser = subparsers.add_parser("agent-manifest", help="Generate an agent manifest through the isolated mode")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)


def run_agent_manifest_command(args: Any) -> int:
    try:
        result = generate_agent_manifest_artifact(Path(args.input), Path(args.output))
    except Exception as exc:
        print(f"[ctcp_orchestrate][agent-manifest][error] {exc}", file=sys.stderr)
        return 2
    print(result_to_json(result))
    return 0
