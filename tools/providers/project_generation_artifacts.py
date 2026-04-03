from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ORCH_SCRIPT = ROOT / "scripts" / "ctcp_orchestrate.py"
POINTCLOUD_DIALOGUE_SCRIPT = ROOT / "tests" / "fixtures" / "dialogues" / "scaffold_pointcloud.jsonl"


def _slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9_-]+", "-", (text or "").strip().lower())
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "goal"


def _project_slug(goal: str) -> str:
    raw = _slug(goal)
    return raw[:48] or "project"


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


def normalize_patch_payload(raw_text: str) -> tuple[str, str]:
    text = str(raw_text or "")
    if not text.strip():
        return "", "patch output is empty"

    fenced_blocks = re.findall(r"```(?:diff|patch)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    if fenced_blocks:
        for block in fenced_blocks:
            if "diff --git " in block:
                text = block
                break

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    start_idx = -1
    for idx, line in enumerate(lines):
        if line.startswith("diff --git "):
            start_idx = idx
            break
    if start_idx < 0:
        return "", "patch output must contain diff --git header"

    normalized_lines = [line for line in lines[start_idx:] if line.strip()]
    if not normalized_lines:
        return "", "patch output has no non-empty diff lines"
    if not normalized_lines[0].startswith("diff --git "):
        return "", "patch output must start with diff --git"
    return "\n".join(normalized_lines).rstrip() + "\n", ""


def _prefixed(project_root: str, rels: list[str]) -> list[str]:
    root = str(project_root or "").strip().replace("\\", "/").strip("/")
    return [f"{root}/{rel}".replace("//", "/") for rel in rels]


def _default_project_file_lists(goal: str) -> dict[str, Any]:
    project_id = _project_slug(goal)
    project_root = f"project_output/{project_id}"
    source_rel = [
        "pyproject.toml",
        "scripts/run_v2p.py",
        "scripts/eval_v2p.py",
        "scripts/make_synth_fixture.py",
        "scripts/clean_project.py",
    ]
    doc_rel = [
        "README.md",
        "docs/00_CORE.md",
    ]
    workflow_rel = [
        "meta/tasks/CURRENT.md",
        "meta/reports/LAST.md",
        "meta/manifest.json",
        "scripts/verify_repo.ps1",
    ]
    source_files = _prefixed(project_root, source_rel)
    doc_files = _prefixed(project_root, doc_rel)
    workflow_files = _prefixed(project_root, workflow_rel)
    target_files = sorted(set(source_files + doc_files + workflow_files))
    acceptance_files = [
        f"{project_root}/README.md",
        f"{project_root}/scripts/run_v2p.py",
        f"{project_root}/meta/manifest.json",
    ]
    return {
        "project_id": project_id,
        "project_root": project_root,
        "project_profile": "minimal",
        "target_files": target_files,
        "source_files": source_files,
        "doc_files": doc_files,
        "workflow_files": workflow_files,
        "acceptance_files": acceptance_files,
    }


def normalize_output_contract_freeze(doc: dict[str, Any] | None, *, goal: str) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    goal_text = str(src.get("goal", "")).strip() or goal.strip()
    defaults = _default_project_file_lists(goal_text)
    project_root = str(src.get("project_root", "")).strip().replace("\\", "/") or str(defaults["project_root"])
    project_id = str(src.get("project_id", "")).strip() or str(defaults["project_id"])
    project_profile = str(src.get("project_profile", "")).strip().lower() or str(defaults["project_profile"])

    target_files = src.get("target_files") if isinstance(src.get("target_files"), list) else defaults["target_files"]
    source_files = src.get("source_files") if isinstance(src.get("source_files"), list) else defaults["source_files"]
    doc_files = src.get("doc_files") if isinstance(src.get("doc_files"), list) else defaults["doc_files"]
    workflow_files = src.get("workflow_files") if isinstance(src.get("workflow_files"), list) else defaults["workflow_files"]
    acceptance_files = src.get("acceptance_files") if isinstance(src.get("acceptance_files"), list) else defaults["acceptance_files"]

    normalized_target = sorted(set(_normalize_rel_list([str(x) for x in target_files])))
    return {
        "schema_version": "ctcp-project-output-contract-v1",
        "stage": "output_contract_freeze",
        "goal": goal_text,
        "project_id": project_id,
        "project_root": project_root,
        "project_profile": project_profile,
        "target_files": normalized_target,
        "source_files": _normalize_rel_list([str(x) for x in source_files]),
        "doc_files": _normalize_rel_list([str(x) for x in doc_files]),
        "workflow_files": _normalize_rel_list([str(x) for x in workflow_files]),
        "generated_files": [],
        "missing_files": list(normalized_target),
        "acceptance_files": _normalize_rel_list([str(x) for x in acceptance_files]),
        "reference_project_mode": {"enabled": False, "mode": "structure_workflow_docs"},
        "reference_style_applied": [],
    }


def _load_output_contract_lists(run_dir: Path, *, goal: str = "") -> dict[str, Any]:
    path = run_dir / "artifacts" / "output_contract_freeze.json"
    defaults = _default_project_file_lists(goal or run_dir.name)
    if not path.exists():
        return defaults
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return defaults
    if not isinstance(doc, dict):
        return defaults
    out = dict(defaults)
    root_value = str(doc.get("project_root", "")).strip().replace("\\", "/")
    if root_value:
        out["project_root"] = root_value
    project_id = str(doc.get("project_id", "")).strip()
    if project_id:
        out["project_id"] = project_id
    profile = str(doc.get("project_profile", "")).strip().lower()
    if profile:
        out["project_profile"] = profile
    for key in ("target_files", "source_files", "doc_files", "workflow_files", "acceptance_files"):
        value = doc.get(key)
        if isinstance(value, list):
            cleaned = _normalize_rel_list([str(x) for x in value])
            if cleaned:
                out[key] = cleaned
    return out


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
        if not path.is_file():
            continue
        rows.append(path.resolve().relative_to(run_dir.resolve()).as_posix())
    return rows


def _run_pointcloud_scaffold(*, run_dir: Path, goal: str, project_root: str, profile: str) -> dict[str, Any]:
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
    project_name = _project_slug(goal or run_dir.name)
    cmd = [
        sys.executable,
        str(ORCH_SCRIPT),
        "scaffold-pointcloud",
        "--out",
        str(out_dir),
        "--name",
        project_name,
        "--profile",
        profile if profile in {"minimal", "standard"} else "minimal",
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
        "error": "" if not failed else ("scaffold-pointcloud generation failed"),
    }


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


def normalize_source_generation(doc: dict[str, Any] | None, *, goal: str, run_dir: Path) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    goal_text = str(src.get("goal", "")).strip() or goal.strip()
    lists = _load_output_contract_lists(run_dir, goal=goal_text)
    project_root = str(lists.get("project_root", "")).strip() or f"project_output/{_project_slug(goal_text)}"
    profile = str(lists.get("project_profile", "minimal")).strip().lower() or "minimal"
    scaffold = _run_pointcloud_scaffold(run_dir=run_dir, goal=goal_text, project_root=project_root, profile=profile)
    report = _stage_report(
        stage="source_generation",
        goal=goal_text,
        project_root=project_root,
        required_files=list(lists.get("source_files", [])),
        generated_files=list(scaffold.get("generated_files", [])),
        extra={
            "project_id": str(lists.get("project_id", "")),
            "entrypoint": f"{project_root}/scripts/run_v2p.py",
            "startup_readme": f"{project_root}/README.md",
            "scaffold": scaffold,
        },
    )
    if str(scaffold.get("status", "")).strip().lower() != "pass":
        report["status"] = "blocked"
    return report


def normalize_docs_generation(doc: dict[str, Any] | None, *, goal: str, run_dir: Path) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    goal_text = str(src.get("goal", "")).strip() or goal.strip()
    lists = _load_output_contract_lists(run_dir, goal=goal_text)
    project_root = str(lists.get("project_root", "")).strip() or f"project_output/{_project_slug(goal_text)}"
    generated = _collect_project_files(run_dir, project_root)
    return _stage_report(
        stage="docs_generation",
        goal=goal_text,
        project_root=project_root,
        required_files=list(lists.get("doc_files", [])),
        generated_files=generated,
        extra={"project_id": str(lists.get("project_id", ""))},
    )


def normalize_workflow_generation(doc: dict[str, Any] | None, *, goal: str, run_dir: Path) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    goal_text = str(src.get("goal", "")).strip() or goal.strip()
    lists = _load_output_contract_lists(run_dir, goal=goal_text)
    project_root = str(lists.get("project_root", "")).strip() or f"project_output/{_project_slug(goal_text)}"
    generated = _collect_project_files(run_dir, project_root)
    return _stage_report(
        stage="workflow_generation",
        goal=goal_text,
        project_root=project_root,
        required_files=list(lists.get("workflow_files", [])),
        generated_files=generated,
        extra={"project_id": str(lists.get("project_id", ""))},
    )


def normalize_project_manifest(doc: dict[str, Any] | None, *, goal: str, run_dir: Path) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    goal_text = str(src.get("goal", "")).strip() or goal.strip()
    lists = _load_output_contract_lists(run_dir, goal=goal_text)
    output_refs = _collect_run_output_refs(run_dir)
    generated_files = (
        _normalize_rel_list([str(x) for x in src.get("generated_files", [])])
        if isinstance(src.get("generated_files"), list)
        else sorted({str(x.get("rel_path", "")).strip() for x in output_refs if str(x.get("rel_path", "")).strip()})
    )
    target_files = list(lists.get("target_files", []))
    missing_files = (
        _normalize_rel_list([str(x) for x in src.get("missing_files", [])])
        if isinstance(src.get("missing_files"), list)
        else sorted(set(target_files) - set(generated_files))
    )
    run_id = run_dir.name
    project_root = str(lists.get("project_root", "")).strip()
    source_files = list(lists.get("source_files", []))
    doc_files = list(lists.get("doc_files", []))
    workflow_files = list(lists.get("workflow_files", []))
    startup_entrypoint = next((p for p in source_files if p.endswith("/scripts/run_v2p.py")), source_files[0] if source_files else "")
    startup_readme = next((p for p in doc_files if p.endswith("/README.md")), doc_files[0] if doc_files else "")
    source_stage_doc: dict[str, Any] = {}
    source_stage_path = run_dir / "artifacts" / "source_generation_report.json"
    if source_stage_path.exists():
        try:
            raw = json.loads(source_stage_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                source_stage_doc = raw
        except Exception:
            source_stage_doc = {}

    return {
        "schema_version": "ctcp-project-manifest-v1",
        "stage": "artifact_manifest_build",
        "goal": goal_text,
        "run_id": str(src.get("run_id", "")).strip() or run_id,
        "project_id": str(src.get("project_id", "")).strip() or str(lists.get("project_id", "")).strip() or _slug(goal_text or run_id),
        "project_root": project_root,
        "source_files": source_files,
        "doc_files": doc_files,
        "workflow_files": workflow_files,
        "generated_files": generated_files,
        "missing_files": missing_files,
        "acceptance_files": list(lists.get("acceptance_files", [])),
        "startup_entrypoint": startup_entrypoint,
        "startup_readme": startup_readme,
        "scaffold_run_dir": str(source_stage_doc.get("scaffold", {}).get("scaffold_run_dir", "")).strip(),
        "reference_project_mode": {"enabled": False, "mode": "structure_workflow_docs"},
        "reference_style_applied": [],
        "artifacts": output_refs,
    }


def normalize_deliverable_index(doc: dict[str, Any] | None, *, goal: str, run_dir: Path) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    manifest_path = run_dir / "artifacts" / "project_manifest.json"
    manifest_doc: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                manifest_doc = raw
        except Exception:
            manifest_doc = {}
    deliverables: list[str] = []
    artifacts = manifest_doc.get("artifacts")
    if isinstance(artifacts, list):
        for row in artifacts:
            if not isinstance(row, dict):
                continue
            rel = str(row.get("rel_path", "")).strip()
            if rel:
                deliverables.append(rel)
    if not deliverables and manifest_path.exists():
        deliverables.append("artifacts/project_manifest.json")
    return {
        "schema_version": "ctcp-deliverable-index-v1",
        "stage": "deliver",
        "goal": str(src.get("goal", "")).strip() or goal.strip(),
        "run_id": str(src.get("run_id", "")).strip() or run_dir.name,
        "project_id": str(src.get("project_id", "")).strip() or str(manifest_doc.get("project_id", "")).strip() or _slug(goal or run_dir.name),
        "project_manifest_path": "artifacts/project_manifest.json",
        "project_root": str(manifest_doc.get("project_root", "")).strip(),
        "startup_entrypoint": str(manifest_doc.get("startup_entrypoint", "")).strip(),
        "startup_readme": str(manifest_doc.get("startup_readme", "")).strip(),
        "deliverables": sorted(set(deliverables)),
        "delivery_note": str(src.get("delivery_note", "")).strip() or "deliver artifacts are indexed for bridge consumption and verify handoff",
    }
