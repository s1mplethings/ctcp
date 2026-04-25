from __future__ import annotations

import zipfile
from pathlib import Path


_FINAL_BUNDLE_EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
_FINAL_BUNDLE_EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
_FINAL_BUNDLE_EXCLUDED_FILENAMES = {"run.json", "events.jsonl", "trace.md", "verify_report.json", "failure_bundle.zip"}


def _should_exclude_from_final_bundle(rel_item: Path) -> bool:
    normalized = rel_item.as_posix().lower()
    parts = {part.lower() for part in rel_item.parts}
    if parts & _FINAL_BUNDLE_EXCLUDED_PARTS:
        return True
    if rel_item.suffix.lower() in _FINAL_BUNDLE_EXCLUDED_SUFFIXES:
        return True
    if rel_item.name.lower() in _FINAL_BUNDLE_EXCLUDED_FILENAMES:
        return True
    if normalized.startswith("artifacts/") and not normalized.startswith("artifacts/screenshots/"):
        return True
    if normalized.startswith("reviews/") or normalized.startswith("workflow_reports/"):
        return True
    if normalized.startswith("process/") or normalized.startswith("run/"):
        return True
    return False


def zip_directory(source_dir: Path, archive_path: Path, *, excluded_root: Path | None = None) -> Path:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    final_bundle = archive_path.name.lower() == "final_project_bundle.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(source_dir.rglob("*")):
            if not item.is_file() or item.resolve() == archive_path.resolve():
                continue
            try:
                rel_item = item.relative_to(source_dir)
            except ValueError:
                continue
            if excluded_root is not None and rel_item.parts[: len(excluded_root.parts)] == excluded_root.parts:
                continue
            if final_bundle and _should_exclude_from_final_bundle(rel_item):
                continue
            zf.write(item, (Path(source_dir.name) / rel_item).as_posix())
    return archive_path


def package_bundle_role(path: Path) -> str:
    name = path.name.lower()
    if name == "final_project_bundle.zip":
        return "final_project_bundle"
    if name == "process_bundle.zip":
        return "process_bundle"
    return "generic_bundle"


def choose_public_package(existing_packages: list[Path]) -> Path | None:
    ordered = sorted(
        (path for path in existing_packages if path.exists()),
        key=lambda item: (
            0 if package_bundle_role(item) == "final_project_bundle" else (2 if package_bundle_role(item) == "process_bundle" else 1),
            -item.stat().st_mtime,
        ),
    )
    return ordered[0] if ordered else None


def parse_scaffold_run_dir(text: str) -> str:
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if "run_dir=" in line:
            return line.split("run_dir=", 1)[1].strip()
    return ""
