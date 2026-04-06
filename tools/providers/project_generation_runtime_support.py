from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from tools.providers.project_generation_decisions import (
    CLI_SHAPE,
    GUI_KEYWORDS,
    NARRATIVE_KEYWORDS,
    PRODUCTION_MODE,
    TOOL_KEYWORDS,
    WEB_KEYWORDS,
    contains_any as _contains_any,
)

ROOT = Path(__file__).resolve().parents[2]
ORCH_SCRIPT = ROOT / "scripts" / "ctcp_orchestrate.py"
POINTCLOUD_DIALOGUE_SCRIPT = ROOT / "tests" / "fixtures" / "dialogues" / "scaffold_pointcloud.jsonl"


def _collect_run_output_refs(run_dir: Path) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.resolve().relative_to(run_dir.resolve()).as_posix()
        if rel.startswith("outbox/"):
            continue
        refs.append({"rel_path": rel, "size_bytes": int(path.stat().st_size)})
    return refs


def _runs_root_for(run_dir: Path) -> Path:
    if run_dir.parent.name.lower() == "ctcp":
        return run_dir.parent.parent
    return run_dir.parent


def _extract_run_dir_from_stdout(text: str) -> str:
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if line.startswith("[ctcp_orchestrate] run_dir="):
            return line.split("=", 1)[1].strip()
    return ""


def _collect_project_files(run_dir: Path, project_root: str) -> list[str]:
    root = (run_dir / project_root).resolve()
    if not root.exists():
        return []
    rows: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rows.append(path.resolve().relative_to(run_dir.resolve()).as_posix())
    return rows


def _run_pointcloud_scaffold(*, run_dir: Path, goal: str, project_root: str, profile: str, project_slug: str) -> dict[str, Any]:
    out_dir = (run_dir / project_root).resolve()
    manifest = out_dir / "meta" / "manifest.json"
    if manifest.exists():
        return {
            "status": "pass",
            "result": "reused",
            "project_root": project_root,
            "out_dir": str(out_dir),
            "generated_files": _collect_project_files(run_dir, project_root),
            "scaffold_run_dir": "",
            "command": "",
            "rc": 0,
            "stdout_tail": "",
            "stderr_tail": "",
            "error": "",
        }

    out_dir.parent.mkdir(parents=True, exist_ok=True)
    bootstrap_profile = "standard" if profile not in {"minimal"} else "minimal"
    cmd = [
        sys.executable,
        str(ORCH_SCRIPT),
        "scaffold-pointcloud",
        "--out",
        str(out_dir),
        "--name",
        project_slug,
        "--profile",
        bootstrap_profile,
        "--source-mode",
        "template",
        "--force",
        "--runs-root",
        str(_runs_root_for(run_dir)),
        "--dialogue-script",
        str(POINTCLOUD_DIALOGUE_SCRIPT),
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stdout = str(proc.stdout or "")
    stderr = str(proc.stderr or "")
    generated = _collect_project_files(run_dir, project_root)
    scaffold_run_dir = _extract_run_dir_from_stdout(stdout)
    failed = int(proc.returncode) != 0 or not manifest.exists()
    return {
        "status": "blocked" if failed else "pass",
        "result": "failed" if failed else "generated",
        "project_root": project_root,
        "out_dir": str(out_dir),
        "generated_files": generated,
        "scaffold_run_dir": scaffold_run_dir,
        "command": " ".join(cmd),
        "rc": int(proc.returncode),
        "stdout_tail": "\n".join(stdout.splitlines()[-12:]),
        "stderr_tail": "\n".join(stderr.splitlines()[-12:]),
        "error": "" if not failed else "scaffold-pointcloud generation failed",
    }


def _load_context_pack(run_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = run_dir / "artifacts" / "context_pack.json"
    if not path.exists():
        return {}, []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}, []
    if not isinstance(doc, dict):
        return {}, []
    files: list[dict[str, Any]] = []
    for item in doc.get("files", []):
        if not isinstance(item, dict):
            continue
        path_value = str(item.get("path", "")).strip().replace("\\", "/")
        if not path_value:
            continue
        files.append(
            {
                "path": path_value,
                "why": str(item.get("why", "")).strip(),
                "content": str(item.get("content", "")),
            }
        )
    return doc, files


def _context_consumption(goal: str, context_files: list[dict[str, Any]], *, decision: dict[str, Any]) -> dict[str, Any]:
    used_paths: list[str] = []
    influence_summary: list[str] = []
    path_map = {str(item.get("path", "")).strip().replace("\\", "/"): item for item in context_files}
    for path in sorted(path_map):
        content = str(path_map[path].get("content", ""))
        if path == "docs/41_low_capability_project_generation.md":
            used_paths.append(path)
            influence_summary.append("docs/41_low_capability_project_generation.md reinforced production/benchmark split and layered gate semantics")
        elif path == "docs/backend_interface_contract.md":
            used_paths.append(path)
            influence_summary.append("docs/backend_interface_contract.md reinforced manifest and deliver bridge fields")
        elif path == "workflow_registry/wf_project_generation_manifest/recipe.yaml":
            used_paths.append(path)
            influence_summary.append("workflow recipe preserved fixed stage ordering for output_contract/source_generation/deliver")
        elif path == "scripts/project_generation_gate.py":
            used_paths.append(path)
            influence_summary.append("project_generation_gate rules influenced structural/behavioral/result gate reporting")
        elif path == "scripts/project_manifest_bridge.py":
            used_paths.append(path)
            influence_summary.append("project_manifest_bridge shaped bridge-readable manifest fields")
        elif path.startswith("artifacts/frontend_uploads/") and _contains_any(content, GUI_KEYWORDS + WEB_KEYWORDS + TOOL_KEYWORDS + NARRATIVE_KEYWORDS):
            used_paths.append(path)
            influence_summary.append(f"{path} contributed user-context signals to type/shape resolution")
    if "context:" in str(decision.get("shape_decision_source", "")):
        influence_summary.append(f"context influenced delivery_shape via {decision.get('shape_decision_source', '')}")
    return {
        "consumed_context_pack": bool(influence_summary),
        "consumed_context_files": _normalize_rel_list(used_paths),
        "context_influence_summary": influence_summary,
        "reference_style_applied": ["repo_script_layout", "workflow_manifest_stage_chain", "bridge_readable_manifest"] if influence_summary else [],
    }


def _normalize_rel_list(rows: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in rows:
        value = str(raw or "").strip().replace("\\", "/")
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _stage_report(
    *,
    stage: str,
    goal: str,
    project_root: str,
    required_files: list[str],
    generated_files: list[str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_required = _normalize_rel_list(required_files)
    normalized_generated = _normalize_rel_list(generated_files)
    missing = sorted(set(normalized_required) - set(normalized_generated))
    out: dict[str, Any] = {
        "schema_version": "ctcp-project-stage-report-v1",
        "stage": stage,
        "goal": goal,
        "project_root": project_root,
        "required_files": normalized_required,
        "generated_files": normalized_generated,
        "missing_files": missing,
        "status": "pass" if not missing else "blocked",
    }
    if isinstance(extra, dict):
        out.update(extra)
    return out
