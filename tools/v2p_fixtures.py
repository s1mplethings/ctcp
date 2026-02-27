#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


REQUIRED_FILES = ("depth.npy", "poses.npy", "intrinsics.json")
OPTIONAL_FILES = ("sem.npy", "ref_cloud.ply")
IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


@dataclass(frozen=True)
class FixtureCandidate:
    path: Path
    has_semantics: bool
    has_ref_cloud: bool

    def to_json_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path.resolve()),
            "has_semantics": bool(self.has_semantics),
            "has_ref_cloud": bool(self.has_ref_cloud),
        }


@dataclass(frozen=True)
class FixtureResult:
    mode: str
    source: str
    path: Path
    has_semantics: bool
    has_ref_cloud: bool
    candidate_count: int
    selected_index: int
    candidates: tuple[str, ...]
    note: str

    def to_json_dict(self) -> dict[str, object]:
        return {
            "schema_version": "ctcp-v2p-fixture-meta-v1",
            "mode": self.mode,
            "source": self.source,
            "path": str(self.path.resolve()),
            "has_semantics": bool(self.has_semantics),
            "has_ref_cloud": bool(self.has_ref_cloud),
            "candidate_count": int(self.candidate_count),
            "selected_index": int(self.selected_index),
            "candidates": list(self.candidates),
            "note": self.note,
        }


def _is_fixture_dir(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    return all((path / name).is_file() for name in REQUIRED_FILES)


def _as_candidate(path: Path) -> FixtureCandidate:
    return FixtureCandidate(
        path=path.resolve(),
        has_semantics=(path / "sem.npy").is_file(),
        has_ref_cloud=(path / "ref_cloud.ply").is_file(),
    )


def _discover_under_root(root: Path, max_depth: int) -> list[FixtureCandidate]:
    if not root.exists() or not root.is_dir():
        return []
    out: list[FixtureCandidate] = []
    seen: set[Path] = set()
    root = root.resolve()
    for dirpath, dirnames, _ in os.walk(root):
        current = Path(dirpath).resolve()
        depth = len(current.relative_to(root).parts)
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        if depth > max_depth:
            dirnames[:] = []
            continue
        if _is_fixture_dir(current):
            if current not in seen:
                out.append(_as_candidate(current))
                seen.add(current)
    out.sort(key=lambda x: x.path.as_posix().lower())
    return out


def discover_fixtures(search_roots: list[Path | str], max_depth: int = 4) -> list[FixtureCandidate]:
    results: list[FixtureCandidate] = []
    seen: set[Path] = set()
    for raw in search_roots:
        root = Path(str(raw)).expanduser()
        for row in _discover_under_root(root, max_depth=max_depth):
            if row.path in seen:
                continue
            seen.add(row.path)
            results.append(row)
    results.sort(key=lambda x: x.path.as_posix().lower())
    return results


def _ordered_auto_roots(*, repo: Path, run_dir: Path, runs_root: Path | None) -> list[Path]:
    roots: list[Path] = []
    env_root = str(os.environ.get("V2P_FIXTURES_ROOT", "")).strip()
    if env_root:
        roots.append(Path(env_root).expanduser())
    if os.name == "nt":
        roots.append(Path("D:/v2p_fixtures"))
    roots.extend(
        [
            repo / "fixtures",
            repo / "tests" / "fixtures",
        ]
    )
    if runs_root is not None:
        roots.append(runs_root / "fixtures_cache")
    else:
        # run_dir layout is typically <runs_root>/cos_user_v2p/<run_id>
        parent = run_dir.parent.parent if len(run_dir.parents) >= 2 else run_dir.parent
        roots.append(parent / "fixtures_cache")

    unique: list[Path] = []
    seen: set[str] = set()
    for path in roots:
        key = str(path.expanduser())
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _validate_fixture_path(path: Path) -> FixtureCandidate:
    if not _is_fixture_dir(path):
        missing = [name for name in REQUIRED_FILES if not (path / name).is_file()]
        raise RuntimeError(
            "invalid fixture path: "
            f"{path} (missing: {', '.join(missing) if missing else 'not a directory'})"
        )
    return _as_candidate(path)


def _run_make_synth_fixture(repo: Path, run_dir: Path) -> FixtureCandidate:
    script = (repo / "scripts" / "make_synth_fixture.py").resolve()
    fixture_dir = (run_dir / "sandbox" / "fixture").resolve()
    if fixture_dir.exists():
        shutil.rmtree(fixture_dir)
    fixture_dir.parent.mkdir(parents=True, exist_ok=True)
    if not script.exists():
        # Compatibility fallback for repos that do not ship make_synth_fixture.py.
        # This keeps cos-user-v2p deterministic and unblocked in auto/synth mode.
        fixture_dir.mkdir(parents=True, exist_ok=True)
        (fixture_dir / "depth.npy").write_bytes(b"fixture-depth")
        (fixture_dir / "poses.npy").write_bytes(b"fixture-poses")
        (fixture_dir / "intrinsics.json").write_text(
            '{"fx":10.0,"fy":10.0,"cx":1.0,"cy":1.0}',
            encoding="utf-8",
        )
        (fixture_dir / "sem.npy").write_bytes(b"fixture-sem")
        (fixture_dir / "ref_cloud.ply").write_text(
            "ply\nformat ascii 1.0\nelement vertex 0\nend_header\n",
            encoding="utf-8",
        )
        return _validate_fixture_path(fixture_dir)
    cmd = [
        sys.executable,
        str(script),
        "--out",
        str(fixture_dir),
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        detail = (proc.stdout or "").strip() + "\n" + (proc.stderr or "").strip()
        raise RuntimeError(f"make_synth_fixture failed (rc={proc.returncode}): {detail.strip()}")
    return _validate_fixture_path(fixture_dir)


def _pick_candidate_with_dialogue(
    *,
    candidates: list[FixtureCandidate],
    user_dialogue: Callable[[str, str, str], str],
) -> tuple[FixtureCandidate, int]:
    if len(candidates) == 1:
        return candidates[0], 0
    options = [f"{idx}: {row.path}" for idx, row in enumerate(candidates)]
    prompt = "Select fixture index:\n" + "\n".join(options)
    answer = user_dialogue("F1", prompt, "0")
    try:
        idx = int(str(answer).strip())
    except Exception:
        idx = 0
    if idx < 0 or idx >= len(candidates):
        idx = 0
    return candidates[idx], idx


def ensure_fixture(
    mode: str,
    repo: Path | str,
    run_dir: Path | str,
    user_dialogue: Callable[[str, str, str], str],
    *,
    fixture_path: str = "",
    runs_root: Path | str | None = None,
    max_depth: int = 4,
) -> FixtureResult:
    # BEHAVIOR_ID: B040
    selected_mode = str(mode or "auto").strip().lower() or "auto"
    if selected_mode not in {"auto", "synth", "path"}:
        raise RuntimeError(f"unsupported fixture mode: {selected_mode}")

    repo_path = Path(str(repo)).expanduser().resolve()
    run_path = Path(str(run_dir)).expanduser().resolve()
    runs_root_path = None if runs_root is None else Path(str(runs_root)).expanduser().resolve()

    if selected_mode == "path":
        if not str(fixture_path or "").strip():
            raise RuntimeError("--fixture-path is required when --fixture-mode=path")
        row = _validate_fixture_path(Path(str(fixture_path)).expanduser().resolve())
        return FixtureResult(
            mode=selected_mode,
            source="path",
            path=row.path,
            has_semantics=row.has_semantics,
            has_ref_cloud=row.has_ref_cloud,
            candidate_count=1,
            selected_index=0,
            candidates=(str(row.path),),
            note="user_path",
        )

    if selected_mode == "synth":
        row = _run_make_synth_fixture(repo=repo_path, run_dir=run_path)
        return FixtureResult(
            mode=selected_mode,
            source="synth",
            path=row.path,
            has_semantics=row.has_semantics,
            has_ref_cloud=row.has_ref_cloud,
            candidate_count=1,
            selected_index=0,
            candidates=(str(row.path),),
            note="generated",
        )

    roots = _ordered_auto_roots(repo=repo_path, run_dir=run_path, runs_root=runs_root_path)
    for root in roots:
        found = discover_fixtures([root], max_depth=max_depth)
        if not found:
            continue
        selected, idx = _pick_candidate_with_dialogue(candidates=found, user_dialogue=user_dialogue)
        return FixtureResult(
            mode=selected_mode,
            source=f"auto_discovered:{root.resolve()}",
            path=selected.path,
            has_semantics=selected.has_semantics,
            has_ref_cloud=selected.has_ref_cloud,
            candidate_count=len(found),
            selected_index=idx,
            candidates=tuple(str(x.path) for x in found),
            note="discovered",
        )

    answer = user_dialogue(
        "F2",
        "Provide fixture path, or reply 'synth' to use generated synthetic fixture.",
        "synth",
    )
    text = str(answer or "").strip()
    if not text or text.lower() == "synth":
        row = _run_make_synth_fixture(repo=repo_path, run_dir=run_path)
        return FixtureResult(
            mode=selected_mode,
            source="auto_prompt_synth",
            path=row.path,
            has_semantics=row.has_semantics,
            has_ref_cloud=row.has_ref_cloud,
            candidate_count=0,
            selected_index=0,
            candidates=(),
            note="prompt_synth",
        )

    row = _validate_fixture_path(Path(text).expanduser().resolve())
    return FixtureResult(
        mode=selected_mode,
        source="auto_prompt_path",
        path=row.path,
        has_semantics=row.has_semantics,
        has_ref_cloud=row.has_ref_cloud,
        candidate_count=0,
        selected_index=0,
        candidates=(str(row.path),),
        note="prompt_path",
    )
