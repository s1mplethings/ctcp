#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any


class TestkitRunnerError(RuntimeError):
    """Raised when testkit run contract is violated."""


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def _norm_relpath(raw: str) -> str:
    value = str(raw or "").strip().replace("\\", "/")
    if not value:
        raise TestkitRunnerError("empty copy path")
    if value.startswith("/") or (len(value) >= 2 and value[1] == ":"):
        raise TestkitRunnerError(f"absolute copy path is not allowed: {raw}")
    parts = [p for p in value.split("/") if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts):
        raise TestkitRunnerError(f"invalid copy path: {raw}")
    return "/".join(parts)


def parse_copy_csv(raw: str) -> list[str]:
    rows = [x.strip() for x in str(raw or "").split(",")]
    out: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if not row:
            continue
        rel = _norm_relpath(row)
        if rel in seen:
            continue
        out.append(rel)
        seen.add(rel)
    if not out:
        raise TestkitRunnerError("copy list is empty")
    return out


def resolve_out_root(raw: str, *, explicit: bool, default_path: str = "D:/v2p_tests") -> tuple[Path, str]:
    source = str(raw or "").strip() or default_path
    note = ""
    path = Path(source).expanduser()
    # CI-safe fallback when using default D: destination in non-Windows or missing D: drive.
    if not explicit:
        drive = str(path.drive or "").strip()
        if os.name != "nt":
            path = Path(tempfile.gettempdir()) / "v2p_tests"
            note = "fallback_temp_non_windows"
        elif drive.upper() == "D:":
            if not Path("D:/").exists():
                path = Path(tempfile.gettempdir()) / "v2p_tests"
                note = "fallback_temp_missing_d_drive"
    return path.resolve(), note


def ensure_destination(
    *,
    out_root: Path,
    project: str,
    run_id: str,
    force: bool,
) -> tuple[Path, Path]:
    project_name = str(project or "").strip()
    if not project_name:
        raise TestkitRunnerError("project name is empty")
    run_root = (out_root / project_name / run_id).resolve()
    out_dir = (run_root / "out").resolve()
    if not _is_within(run_root, out_root) or not _is_within(out_dir, out_root):
        raise TestkitRunnerError(f"destination escaped out-root: out_root={out_root} run_root={run_root}")
    if run_root.exists():
        if not force:
            raise TestkitRunnerError(f"destination run folder exists (use --force): {run_root}")
        shutil.rmtree(run_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    return run_root, out_dir


def unzip_testkit(zip_path: Path, target_dir: Path) -> None:
    if not zip_path.exists() or not zip_path.is_file():
        raise TestkitRunnerError(f"testkit zip not found: {zip_path}")
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)
    except Exception as exc:
        raise TestkitRunnerError(f"failed to unzip testkit: {exc}") from exc


def run_entry(
    *,
    entry_cmd: str,
    cwd: Path,
    env_extra: dict[str, str] | None = None,
) -> dict[str, Any]:
    merged_env = os.environ.copy()
    if env_extra:
        for k, v in env_extra.items():
            merged_env[str(k)] = str(v)
    t0 = time.time()
    proc = subprocess.run(
        str(entry_cmd),
        cwd=str(cwd),
        env=merged_env,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed_sec = time.time() - t0
    return {
        "rc": int(proc.returncode),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "runtime_sec": elapsed_sec,
    }


def copy_outputs(
    *,
    work_dir: Path,
    copy_list: list[str],
    out_dir: Path,
) -> dict[str, Any]:
    copied: list[dict[str, Any]] = []
    missing: list[str] = []
    for rel in copy_list:
        src = (work_dir / Path(*rel.split("/"))).resolve()
        dst = (out_dir / Path(*rel.split("/"))).resolve()
        if not _is_within(dst, out_dir):
            raise TestkitRunnerError(f"copy destination escaped out dir: {rel}")
        row = {
            "rel": rel,
            "src": src.as_posix(),
            "dst": dst.as_posix(),
            "exists": bool(src.exists()),
        }
        if src.exists() and src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            row["copied"] = True
        else:
            row["copied"] = False
            missing.append(rel)
        copied.append(row)
    return {"copied": copied, "missing": missing}


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _get_first_number(doc: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        value = doc.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    metrics = doc.get("metrics")
    if isinstance(metrics, dict):
        for key in keys:
            value = metrics.get(key)
            if isinstance(value, (int, float)):
                return float(value)
    return None


def extract_metrics(out_dir: Path) -> dict[str, Any]:
    scorecard = _load_json_if_exists(out_dir / "out" / "scorecard.json")
    eval_doc = _load_json_if_exists(out_dir / "out" / "eval.json")
    metrics: dict[str, Any] = {
        "scorecard_exists": bool(scorecard is not None),
        "eval_exists": bool(eval_doc is not None),
    }
    if scorecard is not None:
        metrics["fps"] = _get_first_number(scorecard, ["fps", "fps_mean", "fps_avg"])
        metrics["points_down"] = _get_first_number(scorecard, ["points_down", "points", "points_count"])
    if eval_doc is not None:
        metrics["voxel_fscore"] = _get_first_number(eval_doc, ["voxel_fscore", "fscore", "voxel_f1"])
    return metrics


def run_testkit(
    *,
    run_dir: Path,
    testkit_zip: Path,
    entry_cmd: str,
    copy_csv: str,
    out_root: Path,
    project: str,
    run_id: str,
    force: bool,
    semantics_enabled: bool,
    fixture_path: Path,
    forbidden_roots: list[Path] | None = None,
) -> dict[str, Any]:
    copy_list = parse_copy_csv(copy_csv)
    run_root, out_dir = ensure_destination(out_root=out_root, project=project, run_id=run_id, force=force)
    sandbox_dir = (run_dir / "sandbox" / "testkit").resolve()
    for forbidden in forbidden_roots or []:
        if _is_within(sandbox_dir, forbidden):
            raise TestkitRunnerError(
                f"testkit sandbox must be outside forbidden root: sandbox={sandbox_dir} forbidden={forbidden}"
            )
    unzip_testkit(testkit_zip, sandbox_dir)
    exec_result = run_entry(
        entry_cmd=entry_cmd,
        cwd=sandbox_dir,
        env_extra={
            "CTCP_SEMANTICS_ENABLED": "1" if semantics_enabled else "0",
            "V2P_SEMANTICS": "1" if semantics_enabled else "0",
            "CTCP_V2P_FIXTURE_PATH": str(fixture_path.resolve()),
            "V2P_FIXTURE_PATH": str(fixture_path.resolve()),
        },
    )
    copy_result = copy_outputs(work_dir=sandbox_dir, copy_list=copy_list, out_dir=run_root)
    metrics = extract_metrics(run_root)
    return {
        "run_root": run_root.as_posix(),
        "out_dir": out_dir.as_posix(),
        "sandbox_dir": sandbox_dir.as_posix(),
        "copy_list": copy_list,
        "testkit_rc": int(exec_result["rc"]),
        "runtime_sec": float(exec_result["runtime_sec"]),
        "stdout": str(exec_result["stdout"]),
        "stderr": str(exec_result["stderr"]),
        "copied": list(copy_result["copied"]),
        "missing_outputs": list(copy_result["missing"]),
        "metrics": metrics,
    }
