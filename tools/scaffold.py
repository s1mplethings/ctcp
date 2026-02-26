#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

PROFILE_CHOICES = ("minimal", "standard", "full")
TEMPLATE_MANIFEST_SCHEMA = "ctcp-scaffold-template-manifest-v1"
OUTPUT_MANIFEST_SCHEMA = "ctcp-scaffold-manifest-v1"
TOKEN_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


class ScaffoldError(RuntimeError):
    """Raised when scaffold validation or IO rules fail."""


def _norm_relpath(raw: str) -> str:
    value = str(raw or "").strip().replace("\\", "/")
    if not value:
        raise ScaffoldError("empty relative path in manifest")
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise ScaffoldError(f"absolute path is not allowed: {raw}")
    parts = [p for p in value.split("/") if p not in ("", ".")]
    if not parts:
        raise ScaffoldError(f"invalid relative path: {raw}")
    if any(p == ".." for p in parts):
        raise ScaffoldError(f"path traversal is not allowed: {raw}")
    return "/".join(parts)


def _as_rel_path(rel: str) -> Path:
    return Path(*rel.split("/"))


def _is_within(root: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def _must_be_within(root: Path, target: Path) -> None:
    if not _is_within(root, target):
        raise ScaffoldError(f"path escapes output directory: {target}")


def load_profile_manifest(template_root: Path, profile: str) -> dict[str, object]:
    selected = (profile or "").strip().lower()
    if selected not in PROFILE_CHOICES:
        raise ScaffoldError(f"unsupported profile: {profile}")

    profile_root = template_root / selected
    manifest_path = profile_root / "manifest.json"
    if not manifest_path.exists():
        raise ScaffoldError(f"missing template manifest: {manifest_path}")

    try:
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ScaffoldError(f"invalid template manifest json: {exc}") from exc

    if str(doc.get("schema_version", "")) != TEMPLATE_MANIFEST_SCHEMA:
        raise ScaffoldError(
            f"template manifest schema must be {TEMPLATE_MANIFEST_SCHEMA}: {manifest_path}"
        )
    if str(doc.get("profile", "")).strip().lower() != selected:
        raise ScaffoldError(f"template manifest profile mismatch: {manifest_path}")

    rows = doc.get("files")
    if not isinstance(rows, list) or not rows:
        raise ScaffoldError(f"template manifest files must be a non-empty array: {manifest_path}")

    files: list[str] = []
    seen: set[str] = set()
    for raw in rows:
        rel = _norm_relpath(str(raw))
        if rel in seen:
            continue
        src = profile_root / _as_rel_path(rel)
        if not src.exists() or not src.is_file():
            raise ScaffoldError(f"template file listed in manifest does not exist: {src}")
        files.append(rel)
        seen.add(rel)

    return {
        "profile": selected,
        "profile_root": profile_root,
        "manifest_path": manifest_path,
        "files": files,
    }


def build_scaffold_plan(*, out_dir: Path, project_name: str, profile_doc: dict[str, object]) -> dict[str, object]:
    files = list(profile_doc.get("files", []))
    return {
        "profile": str(profile_doc.get("profile", "")),
        "out_dir": str(out_dir.resolve()),
        "project_name": project_name,
        "template_manifest": str(Path(str(profile_doc.get("manifest_path", ""))).resolve()),
        "files": files,
        "file_count": len(files),
    }


def _render_tokens(text: str, tokens: dict[str, str]) -> str:
    def _replace(match: re.Match[str]) -> str:
        key = str(match.group(1) or "").strip()
        return str(tokens.get(key, match.group(0)))

    return TOKEN_RE.sub(_replace, text)


def _write_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _render_or_copy(src: Path, dst: Path, tokens: dict[str, str]) -> None:
    raw = src.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        _write_parent(dst)
        dst.write_bytes(raw)
        return
    rendered = _render_tokens(text, tokens)
    _write_parent(dst)
    dst.write_text(rendered, encoding="utf-8")


def _load_existing_generated_files(out_dir: Path) -> list[str]:
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.exists():
        return []
    try:
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if str(doc.get("schema_version", "")) != OUTPUT_MANIFEST_SCHEMA:
        return []
    rows = doc.get("files")
    if not isinstance(rows, list):
        return []
    files: list[str] = []
    for raw in rows:
        try:
            files.append(_norm_relpath(str(raw)))
        except ScaffoldError:
            continue
    return files


def _remove_generated_files(out_dir: Path, candidates: list[str]) -> list[str]:
    removed: list[str] = []
    for rel in sorted(set(candidates)):
        target = out_dir / _as_rel_path(rel)
        _must_be_within(out_dir, target)
        if target.is_symlink() or target.is_file():
            target.unlink()
            removed.append(rel)
    # prune empty dirs bottom-up
    for node in sorted(out_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if node.is_dir():
            try:
                node.rmdir()
            except OSError:
                pass
    return removed


def _remaining_files(out_dir: Path) -> list[str]:
    remain: list[str] = []
    for node in out_dir.rglob("*"):
        if node.is_file() or node.is_symlink():
            remain.append(node.relative_to(out_dir).as_posix())
    return sorted(remain)


def prepare_output_dir(out_dir: Path, *, force: bool, planned_files: list[str]) -> dict[str, object]:
    if out_dir.exists() and not out_dir.is_dir():
        raise ScaffoldError(f"--out exists but is not a directory: {out_dir}")

    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)
        return {"removed_files": [], "mode": "created"}

    if not force:
        raise ScaffoldError(f"--out already exists (use --force to regenerate): {out_dir}")

    known = _load_existing_generated_files(out_dir)
    candidates = list(known) if known else list(planned_files)
    candidates.extend(["manifest.json", "TREE.md"])
    removed = _remove_generated_files(out_dir, candidates)

    remain = _remaining_files(out_dir)
    if remain:
        preview = ", ".join(remain[:8])
        raise ScaffoldError(
            "--force refuses to delete unknown files in --out. "
            f"remaining files: {preview}"
        )

    return {"removed_files": removed, "mode": "forced"}


def write_tree_file(out_dir: Path, files: list[str]) -> str:
    rel = "TREE.md"
    target = out_dir / rel
    _must_be_within(out_dir, target)
    lines = [
        "# TREE",
        "",
        "Generated by CTCP scaffold.",
        "",
        "Files:",
    ]
    for row in sorted(files):
        lines.append(f"- {row}")
    lines.append("")
    target.write_text("\n".join(lines), encoding="utf-8")
    return rel


def write_output_manifest(
    out_dir: Path,
    *,
    profile: str,
    project_name: str,
    utc_iso: str,
    files: list[str],
    source_manifest: str,
) -> str:
    rel = "manifest.json"
    target = out_dir / rel
    _must_be_within(out_dir, target)
    doc = {
        "schema_version": OUTPUT_MANIFEST_SCHEMA,
        "generated_by": "ctcp_orchestrate scaffold",
        "profile": profile,
        "project_name": project_name,
        "generated_at_utc": utc_iso,
        "source_template_manifest": source_manifest,
        "files": sorted(files),
        "file_count": len(files),
    }
    target.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rel


def validate_scaffold_output(out_dir: Path) -> dict[str, object]:
    required_paths = ["README.md", "docs", "meta", "scripts", "manifest.json"]
    missing: list[str] = []
    for rel in required_paths:
        if not (out_dir / _as_rel_path(rel)).exists():
            missing.append(rel)

    manifest_ok = True
    manifest_missing: list[str] = []
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.exists():
        manifest_ok = False
    else:
        try:
            doc = json.loads(manifest_path.read_text(encoding="utf-8"))
            rows = doc.get("files")
            if not isinstance(rows, list):
                manifest_ok = False
            else:
                for raw in rows:
                    rel = _norm_relpath(str(raw))
                    path = out_dir / _as_rel_path(rel)
                    if not path.exists():
                        manifest_missing.append(rel)
                if manifest_missing:
                    manifest_ok = False
        except Exception:
            manifest_ok = False

    return {
        "ok": (not missing) and manifest_ok,
        "missing_required": missing,
        "manifest_ok": manifest_ok,
        "manifest_missing": manifest_missing,
    }


def scaffold_project(
    *,
    template_root: Path,
    out_dir: Path,
    project_name: str,
    profile: str,
    force: bool,
    tokens: dict[str, str],
) -> dict[str, object]:
    t0 = time.time()
    profile_doc = load_profile_manifest(template_root, profile)
    plan = build_scaffold_plan(out_dir=out_dir, project_name=project_name, profile_doc=profile_doc)
    prepared = prepare_output_dir(out_dir, force=force, planned_files=list(plan["files"]))

    profile_root = Path(str(profile_doc["profile_root"]))
    written_files: list[str] = []
    for rel in list(plan["files"]):
        src = profile_root / _as_rel_path(rel)
        dst = out_dir / _as_rel_path(rel)
        _must_be_within(out_dir, dst)
        _render_or_copy(src, dst, tokens)
        written_files.append(rel)

    tree_rel = write_tree_file(out_dir, written_files)
    written_files.append(tree_rel)
    manifest_rel = write_output_manifest(
        out_dir,
        profile=str(plan["profile"]),
        project_name=project_name,
        utc_iso=str(tokens.get("UTC_ISO", "")),
        files=written_files,
        source_manifest=Path(str(profile_doc["manifest_path"])).resolve().as_posix(),
    )
    written_files.append(manifest_rel)

    validation = validate_scaffold_output(out_dir)
    if not bool(validation.get("ok", False)):
        raise ScaffoldError(
            "scaffold validation failed: "
            f"missing_required={validation.get('missing_required', [])}, "
            f"manifest_missing={validation.get('manifest_missing', [])}"
        )

    elapsed_ms = int((time.time() - t0) * 1000)
    return {
        "plan": plan,
        "prepared": prepared,
        "written_files": sorted(written_files),
        "written_count": len(written_files),
        "validation": validation,
        "elapsed_ms": elapsed_ms,
    }

