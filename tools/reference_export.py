#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

DEFAULT_EXPORT_MANIFEST = "meta/reference_export_manifest.yaml"
EXPORT_MANIFEST_SCHEMA = "ctcp-reference-export-manifest-v1"
TOKEN_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


class ReferenceExportError(RuntimeError):
    """Raised when live-reference manifest or export rules are invalid."""


def norm_relpath(raw: str) -> str:
    value = str(raw or "").strip().replace("\\", "/")
    if not value:
        raise ReferenceExportError("empty relative path")
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise ReferenceExportError(f"absolute path is not allowed: {raw}")
    parts = [part for part in value.split("/") if part not in ("", ".")]
    if not parts:
        raise ReferenceExportError(f"invalid relative path: {raw}")
    if any(part == ".." for part in parts):
        raise ReferenceExportError(f"path traversal is not allowed: {raw}")
    return "/".join(parts)


def as_rel_path(rel: str) -> Path:
    return Path(*rel.split("/"))


def is_within(root: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def must_be_within(root: Path, target: Path) -> None:
    if not is_within(root, target):
        raise ReferenceExportError(f"path escapes root: {target}")


def _load_yaml_module() -> Any:
    try:
        import yaml  # type: ignore

        return yaml
    except Exception:
        return None


def _parse_manifest_text(raw: str) -> dict[str, Any]:
    yaml_mod = _load_yaml_module()
    errors: list[str] = []

    if yaml_mod is not None:
        try:
            doc = yaml_mod.safe_load(raw)
            if isinstance(doc, dict):
                return doc
            errors.append("yaml root must be an object")
        except Exception as exc:
            errors.append(f"yaml parse error: {exc}")

    try:
        doc_json = json.loads(raw)
    except Exception as exc:
        details = "; ".join(errors) if errors else "yaml parser unavailable"
        raise ReferenceExportError(f"manifest parse failed: {details}; json parse error: {exc}") from exc

    if not isinstance(doc_json, dict):
        raise ReferenceExportError("manifest root must be an object")
    return doc_json


def _normalize_patterns(raw: Any) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ReferenceExportError("exclude patterns must be an array")
    patterns: list[str] = []
    for item in raw:
        text = str(item or "").strip().replace("\\", "/")
        if not text:
            continue
        patterns.append(text)
    return patterns


def _entry_pair(raw: Any) -> tuple[str, str]:
    if isinstance(raw, str):
        rel = norm_relpath(raw)
        return rel, rel
    if isinstance(raw, dict):
        source = norm_relpath(str(raw.get("source", "")))
        target_raw = str(raw.get("target", source))
        target = norm_relpath(target_raw)
        return source, target
    raise ReferenceExportError(f"invalid export entry type: {type(raw)!r}")


def _matches_any(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatchcase(normalized, pattern) for pattern in patterns)


def _expand_entry(
    *,
    repo_root: Path,
    source_rel: str,
    target_rel: str,
    exclude_patterns: list[str],
) -> tuple[list[dict[str, str]], list[str]]:
    src_root = (repo_root / as_rel_path(source_rel)).resolve()
    must_be_within(repo_root, src_root)
    if not src_root.exists():
        raise ReferenceExportError(f"export source does not exist: {source_rel}")

    rows: list[tuple[str, str]] = []
    if src_root.is_file():
        rows.append((source_rel, target_rel))
    elif src_root.is_dir():
        for node in sorted(src_root.rglob("*")):
            if not node.is_file():
                continue
            rel_child = node.relative_to(src_root).as_posix()
            src_rel = norm_relpath(f"{source_rel}/{rel_child}")
            dst_rel = norm_relpath(f"{target_rel}/{rel_child}")
            rows.append((src_rel, dst_rel))
    else:
        raise ReferenceExportError(f"export source must be file or directory: {source_rel}")

    included: list[dict[str, str]] = []
    excluded_targets: list[str] = []
    for src_rel, dst_rel in rows:
        if _matches_any(src_rel, exclude_patterns) or _matches_any(dst_rel, exclude_patterns):
            excluded_targets.append(dst_rel)
            continue
        included.append({"source_rel": src_rel, "target_rel": dst_rel})
    return included, excluded_targets


def load_export_manifest(repo_root: Path, manifest_rel: str = DEFAULT_EXPORT_MANIFEST) -> dict[str, Any]:
    manifest_norm = norm_relpath(manifest_rel)
    manifest_path = (repo_root / as_rel_path(manifest_norm)).resolve()
    must_be_within(repo_root, manifest_path)
    if not manifest_path.exists() or not manifest_path.is_file():
        raise ReferenceExportError(f"reference export manifest not found: {manifest_path}")

    raw = manifest_path.read_text(encoding="utf-8")
    doc = _parse_manifest_text(raw)
    schema_version = str(doc.get("schema_version", ""))
    if schema_version != EXPORT_MANIFEST_SCHEMA:
        raise ReferenceExportError(
            f"manifest schema_version must be {EXPORT_MANIFEST_SCHEMA}: {manifest_path}"
        )

    targets = doc.get("targets")
    if not isinstance(targets, dict) or not targets:
        raise ReferenceExportError("manifest targets must be a non-empty object")

    doc["_manifest_path"] = manifest_path.resolve().as_posix()
    doc["_manifest_rel"] = manifest_norm
    return doc


def _collect_entries(
    *,
    repo_root: Path,
    raw_entries: Any,
    exclude_patterns: list[str],
    target_tag: str,
) -> tuple[list[dict[str, str]], list[str]]:
    if raw_entries is None:
        return [], []
    if not isinstance(raw_entries, list):
        raise ReferenceExportError(f"{target_tag} must be an array")

    expanded: list[dict[str, str]] = []
    excluded: list[str] = []
    for idx, item in enumerate(raw_entries):
        source_rel, target_rel = _entry_pair(item)
        rows, skipped = _expand_entry(
            repo_root=repo_root,
            source_rel=source_rel,
            target_rel=target_rel,
            exclude_patterns=exclude_patterns,
        )
        if not rows and not skipped:
            raise ReferenceExportError(f"{target_tag}[{idx}] produced no files")
        expanded.extend(rows)
        excluded.extend(skipped)

    return expanded, excluded


def resolve_export_plan(
    *,
    repo_root: Path,
    manifest_doc: dict[str, Any],
    target: str,
    profile: str,
) -> dict[str, Any]:
    target_name = str(target or "").strip()
    profile_name = str(profile or "").strip().lower()
    targets = manifest_doc.get("targets")
    if not isinstance(targets, dict):
        raise ReferenceExportError("manifest targets is invalid")

    target_doc = targets.get(target_name)
    if not isinstance(target_doc, dict):
        raise ReferenceExportError(f"manifest target not found: {target_name}")

    profiles_doc = target_doc.get("profiles")
    if not isinstance(profiles_doc, dict):
        raise ReferenceExportError(f"target profiles missing: {target_name}")

    profile_doc = profiles_doc.get(profile_name)
    if not isinstance(profile_doc, dict):
        raise ReferenceExportError(f"profile not found for target={target_name}: {profile_name}")

    exclude_patterns = []
    exclude_patterns.extend(_normalize_patterns(manifest_doc.get("default_exclude")))
    exclude_patterns.extend(_normalize_patterns(target_doc.get("exclude")))
    exclude_patterns.extend(_normalize_patterns(profile_doc.get("exclude")))

    inherit_copy, excluded_copy = _collect_entries(
        repo_root=repo_root,
        raw_entries=profile_doc.get("inherit_copy"),
        exclude_patterns=exclude_patterns,
        target_tag="inherit_copy",
    )
    inherit_transform, excluded_transform = _collect_entries(
        repo_root=repo_root,
        raw_entries=profile_doc.get("inherit_transform"),
        exclude_patterns=exclude_patterns,
        target_tag="inherit_transform",
    )

    seen_targets: dict[str, str] = {}
    for row in inherit_copy:
        target_rel = row["target_rel"]
        if target_rel in seen_targets:
            raise ReferenceExportError(
                f"duplicate target path in export plan: {target_rel} (from {seen_targets[target_rel]} and inherit_copy)"
            )
        seen_targets[target_rel] = "inherit_copy"

    for row in inherit_transform:
        target_rel = row["target_rel"]
        if target_rel in seen_targets:
            raise ReferenceExportError(
                f"target path overlaps between inherit_copy/inherit_transform: {target_rel}"
            )
        seen_targets[target_rel] = "inherit_transform"

    raw_generate = profile_doc.get("generate", [])
    if raw_generate is None:
        raw_generate = []
    if not isinstance(raw_generate, list):
        raise ReferenceExportError("generate must be an array")
    generate = [norm_relpath(str(item)) for item in raw_generate]

    raw_required = profile_doc.get("required_outputs", [])
    if raw_required is None:
        raw_required = []
    if not isinstance(raw_required, list):
        raise ReferenceExportError("required_outputs must be an array")
    required_outputs = [norm_relpath(str(item)) for item in raw_required]

    excluded = sorted(set(excluded_copy + excluded_transform))
    planned_files = sorted({row["target_rel"] for row in inherit_copy + inherit_transform} | set(generate))

    return {
        "target": target_name,
        "profile": profile_name,
        "manifest_path": str(manifest_doc.get("_manifest_path", "")),
        "manifest_rel": str(manifest_doc.get("_manifest_rel", "")),
        "exclude_patterns": exclude_patterns,
        "inherit_copy": inherit_copy,
        "inherit_transform": inherit_transform,
        "generate": generate,
        "required_outputs": required_outputs,
        "excluded": excluded,
        "planned_files": planned_files,
    }


def _render_tokens(text: str, tokens: dict[str, str]) -> str:
    def _replace(match: re.Match[str]) -> str:
        key = str(match.group(1) or "").strip()
        return str(tokens.get(key, match.group(0)))

    return TOKEN_RE.sub(_replace, text)


def apply_export_plan(
    *,
    repo_root: Path,
    out_dir: Path,
    plan: dict[str, Any],
    tokens: dict[str, str],
) -> dict[str, Any]:
    written_files: list[str] = []
    inherited_copy: list[str] = []
    inherited_transform: list[str] = []

    for row in plan.get("inherit_copy", []):
        source_rel = str(row.get("source_rel", ""))
        target_rel = str(row.get("target_rel", ""))
        src = (repo_root / as_rel_path(source_rel)).resolve()
        dst = (out_dir / as_rel_path(target_rel)).resolve()
        must_be_within(repo_root, src)
        must_be_within(out_dir, dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        written_files.append(target_rel)
        inherited_copy.append(target_rel)

    for row in plan.get("inherit_transform", []):
        source_rel = str(row.get("source_rel", ""))
        target_rel = str(row.get("target_rel", ""))
        src = (repo_root / as_rel_path(source_rel)).resolve()
        dst = (out_dir / as_rel_path(target_rel)).resolve()
        must_be_within(repo_root, src)
        must_be_within(out_dir, dst)
        raw = src.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            rendered_bytes = raw
        else:
            rendered_bytes = _render_tokens(text, tokens).encode("utf-8")
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(rendered_bytes)
        written_files.append(target_rel)
        inherited_transform.append(target_rel)

    unique_written = sorted(set(written_files))
    return {
        "written_files": unique_written,
        "inherited_copy": sorted(set(inherited_copy)),
        "inherited_transform": sorted(set(inherited_transform)),
        "excluded": sorted(set(str(x) for x in plan.get("excluded", []))),
        "required_outputs": [str(x) for x in plan.get("required_outputs", [])],
        "generate": [str(x) for x in plan.get("generate", [])],
    }


def validate_required_outputs(out_dir: Path, required_outputs: list[str]) -> list[str]:
    missing: list[str] = []
    for rel in required_outputs:
        rel_norm = norm_relpath(rel)
        target = (out_dir / as_rel_path(rel_norm)).resolve()
        if not target.exists():
            missing.append(rel_norm)
    return sorted(set(missing))


def current_source_commit(repo_root: Path) -> str:
    if str(os.environ.get("CTCP_DISABLE_GIT_SOURCE", "")).strip() == "1":
        return "unknown"

    proc = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if int(proc.returncode) != 0:
        return "unknown"
    sha = str(proc.stdout or "").strip()
    if not re.fullmatch(r"[0-9a-fA-F]{7,64}", sha):
        return "unknown"
    return sha.lower()


def _load_manifest_files(path: Path) -> list[str]:
    if not path.exists() or not path.is_file():
        return []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = doc.get("files")
    if not isinstance(rows, list):
        return []

    files: list[str] = []
    for raw in rows:
        try:
            files.append(norm_relpath(str(raw)))
        except ReferenceExportError:
            continue
    return sorted(set(files))


def _remaining_files(out_dir: Path) -> list[str]:
    remain: list[str] = []
    for node in out_dir.rglob("*"):
        if node.is_file() or node.is_symlink():
            remain.append(node.relative_to(out_dir).as_posix())
    return sorted(remain)


def _remove_candidates(out_dir: Path, candidates: list[str]) -> list[str]:
    removed: list[str] = []
    for rel in sorted(set(candidates)):
        target = (out_dir / as_rel_path(rel)).resolve()
        must_be_within(out_dir, target)
        if target.is_symlink() or target.is_file():
            target.unlink()
            removed.append(rel)

    for node in sorted(out_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if node.is_dir():
            try:
                node.rmdir()
            except OSError:
                pass
    return removed


def prepare_output_dir_manifest_guarded(
    *,
    out_dir: Path,
    force: bool,
    planned_files: list[str],
    manifest_candidates: list[str],
) -> dict[str, Any]:
    if out_dir.exists() and not out_dir.is_dir():
        raise ReferenceExportError(f"--out exists but is not a directory: {out_dir}")

    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)
        return {"mode": "created", "removed_files": []}

    if not force:
        raise ReferenceExportError(f"--out already exists (use --force to regenerate): {out_dir}")

    known: list[str] = []
    for rel in manifest_candidates:
        rel_norm = norm_relpath(rel)
        manifest_path = (out_dir / as_rel_path(rel_norm)).resolve()
        must_be_within(out_dir, manifest_path)
        known = _load_manifest_files(manifest_path)
        if known:
            break

    remain_before = _remaining_files(out_dir)
    if remain_before and not known:
        raise ReferenceExportError(
            "--force requires an existing generated manifest in --out; "
            "refusing to delete unmanaged files"
        )

    candidates = sorted(set(known + [norm_relpath(x) for x in planned_files]))
    removed = _remove_candidates(out_dir, candidates)

    remain = _remaining_files(out_dir)
    if remain:
        preview = ", ".join(remain[:8])
        raise ReferenceExportError(
            "--force refuses to delete unknown files in --out. "
            f"remaining files: {preview}"
        )

    return {"mode": "forced", "removed_files": removed}
