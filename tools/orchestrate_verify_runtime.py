from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _read_json_doc(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _selected_workflow_id_from_find_result(path: Path) -> str:
    doc = _read_json_doc(path)
    return str(doc.get("selected_workflow_id", "")).strip()


def _is_project_generation_workflow(selected_workflow_id: str) -> bool:
    text = str(selected_workflow_id or "").strip().lower()
    return text == "wf_project_generation_manifest" or "project_generation" in text or "project-generation" in text


def verify_cmd() -> list[str]:
    if os.name == "nt":
        return ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts" / "verify_repo.ps1")]
    return ["bash", str(ROOT / "scripts" / "verify_repo.sh")]


def verify_cmd_for_repo(repo_path: Path) -> tuple[list[str], str]:
    candidates = [
        (repo_path / "scripts" / "verify_repo.ps1", "scripts/verify_repo.ps1"),
        (repo_path / "scripts" / "verify_repo.sh", "scripts/verify_repo.sh"),
        (repo_path / "verify_repo.ps1", "verify_repo.ps1"),
        (repo_path / "verify_repo.sh", "verify_repo.sh"),
    ]
    ps1_candidates = [(p, rel) for p, rel in candidates if p.suffix.lower() == ".ps1" and p.exists()]
    sh_candidates = [(p, rel) for p, rel in candidates if p.suffix.lower() == ".sh" and p.exists()]
    if os.name == "nt":
        if ps1_candidates:
            p, rel = ps1_candidates[0]
            return (["powershell", "-ExecutionPolicy", "Bypass", "-File", str(p.resolve())], rel)
        if sh_candidates:
            p, rel = sh_candidates[0]
            return (["bash", str(p.resolve())], rel)
    else:
        if sh_candidates:
            p, rel = sh_candidates[0]
            return (["bash", str(p.resolve())], rel)
        if ps1_candidates:
            p, rel = ps1_candidates[0]
            return (["powershell", "-ExecutionPolicy", "Bypass", "-File", str(p.resolve())], rel)
    return ([], "")


def scaffold_verify_cmd(out_dir: Path) -> tuple[list[str], str]:
    ps1 = out_dir / "scripts" / "verify_repo.ps1"
    sh = out_dir / "scripts" / "verify_repo.sh"
    if os.name == "nt" and ps1.exists():
        return (["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps1.resolve())], "scripts/verify_repo.ps1")
    if os.name != "nt" and sh.exists():
        return (["bash", str(sh.resolve())], "scripts/verify_repo.sh")
    return ([], "")


def resolve_repo_verify_cmd(repo_path: Path) -> tuple[str, str]:
    cmd, rel = verify_cmd_for_repo(repo_path)
    if cmd:
        if os.name == "nt" and rel == "scripts/verify_repo.ps1":
            return ("powershell -ExecutionPolicy Bypass -File scripts\\verify_repo.ps1", rel)
        if os.name != "nt" and rel == "scripts/verify_repo.sh":
            return ("bash scripts/verify_repo.sh", rel)
        return (" ".join(cmd), rel)
    return "", ""


def _resolve_project_generation_verify_target(run_dir: Path) -> tuple[list[str], Path, str, str]:
    artifacts = run_dir / "artifacts"
    project_root = ""
    for source in (
        artifacts / "project_manifest.json",
        artifacts / "output_contract_freeze.json",
        artifacts / "deliverable_index.json",
    ):
        doc = _read_json_doc(source)
        value = str(doc.get("project_root", "")).strip()
        if value:
            project_root = value
            break
    if not project_root:
        return ([], ROOT, "", "project_generation_verify_target_missing_project_root")
    project_dir = (run_dir / Path(project_root)).resolve()
    if not _is_within(project_dir, run_dir):
        return ([], ROOT, "", f"project_generation_verify_target_outside_run_dir:{project_root}")
    if not project_dir.exists() or not project_dir.is_dir():
        return ([], ROOT, "", f"project_generation_verify_target_missing_dir:{project_root}")
    cmd, entry = verify_cmd_for_repo(project_dir)
    if not cmd:
        return ([], project_dir, "", f"project_generation_verify_target_missing_verify_repo:{project_root}")
    return (cmd, project_dir, entry, "")


def resolve_run_verify_invocation(run_dir: Path, run_doc: dict[str, Any] | None = None) -> tuple[list[str], Path, str, str]:
    del run_doc
    selected_workflow_id = _selected_workflow_id_from_find_result(run_dir / "artifacts" / "find_result.json")
    if _is_project_generation_workflow(selected_workflow_id):
        cmd, cwd, entry, note = _resolve_project_generation_verify_target(run_dir)
        if cmd:
            return (cmd, cwd, entry, note)
    return (verify_cmd(), ROOT, "scripts/verify_repo.ps1" if os.name == "nt" else "scripts/verify_repo.sh", "")


def missing_verify_target_report(*, iteration: int, max_iterations: int, note: str = "") -> dict[str, Any]:
    message = note or "verify target missing"
    paths = {
        "trace": "TRACE.md",
        "verify_report": "artifacts/verify_report.json",
        "bundle": "failure_bundle.zip",
    }
    return {
        "result": "FAIL",
        "gate": "lite",
        "iteration": iteration,
        "max_iterations": max_iterations,
        "patch_sha256": "",
        "commands": [],
        "failures": [{"kind": "verify", "id": "verify_target_missing", "message": message}],
        "paths": paths,
        "artifacts": dict(paths),
    }


def write_verify_report(
    run_dir: Path,
    *,
    rc: int,
    iteration: int,
    max_iterations: int,
    cmd: list[str],
    verify_cwd: Path,
    verify_entry: str,
    out_log: Path,
    err_log: Path,
    patch_sha: str,
    failures: list[dict[str, Any]],
) -> dict[str, Any]:
    paths = {
        "trace": "TRACE.md",
        "verify_report": "artifacts/verify_report.json",
        "bundle": "failure_bundle.zip" if rc != 0 else "",
        "stdout_log": out_log.relative_to(run_dir).as_posix(),
        "stderr_log": err_log.relative_to(run_dir).as_posix(),
    }
    if (run_dir / "artifacts" / "PLAN.md").exists():
        paths["plan"] = "artifacts/PLAN.md"
    if (run_dir / "artifacts" / "diff.patch").exists():
        paths["patch"] = "artifacts/diff.patch"
    report = {
        "result": "PASS" if rc == 0 else "FAIL",
        "gate": "lite",
        "iteration": iteration,
        "max_iterations": max_iterations,
        "patch_sha256": patch_sha,
        "commands": [
            {
                "cmd": " ".join(cmd),
                "exit_code": rc,
                "cwd": str(verify_cwd),
                "verify_entry": verify_entry,
                "stdout_log": out_log.relative_to(run_dir).as_posix(),
                "stderr_log": err_log.relative_to(run_dir).as_posix(),
            }
        ],
        "failures": failures,
        "paths": paths,
        "artifacts": dict(paths),
    }
    target = run_dir / "artifacts" / "verify_report.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
