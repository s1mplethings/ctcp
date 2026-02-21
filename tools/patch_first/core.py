#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import subprocess
from typing import Any

DEFAULT_ALLOW_ROOTS: tuple[str, ...] = (
    "src",
    "include",
    "web",
    "scripts",
    "tools",
    "docs",
    "specs",
    "meta",
    "contracts",
    "workflow_registry",
    "tests",
    "ai_context",
    "agents",
    "ai",
    "simlab",
    "ctcp",
    "resources",
    "executor",
    "third_party",
    "README.md",
    "BUILD.md",
    "PATCH_README.md",
    "TREE.md",
    "CMakeLists.txt",
    "AGENTS.md",
    "APPLY_OVERLAY.md",
    "LICENSE",
    "requirements-dev.txt",
)

DEFAULT_DENY_PREFIXES: tuple[str, ...] = (
    ".git/",
    "build/",
    "build_lite/",
    "build_verify/",
    "build_gui/",
    "dist/",
    "generated_projects/",
    "runs/",
    "artifacts/",
    "simlab/_runs",
    "meta/runs/",
    "tests/fixtures/adlc_forge_full_bundle/runs/",
)

DEFAULT_DENY_SUFFIXES: tuple[str, ...] = (
    ".lock",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".webp",
    ".ico",
    ".zip",
    ".7z",
    ".tar",
    ".gz",
    ".pdf",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".class",
    ".jar",
    ".pyc",
    ".pyo",
    ".o",
    ".obj",
    ".a",
    ".lib",
    ".db",
    ".sqlite",
    ".sqlite3",
)


class PatchValidationError(RuntimeError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        stage: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.details = details or {}


@dataclass(frozen=True)
class PatchPolicy:
    allow_roots: tuple[str, ...] = DEFAULT_ALLOW_ROOTS
    deny_prefixes: tuple[str, ...] = DEFAULT_DENY_PREFIXES
    deny_suffixes: tuple[str, ...] = DEFAULT_DENY_SUFFIXES
    max_files: int = 5
    max_added_lines: int = 400

    @staticmethod
    def _norm_entries(values: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
        if not values:
            return tuple()
        out: list[str] = []
        for raw in values:
            norm = _normalize_policy_path(str(raw))
            if norm:
                out.append(norm)
        return tuple(out)

    @staticmethod
    def _coerce_limit(value: Any, default: int) -> int:
        try:
            parsed = int(value)
        except Exception:
            return default
        return parsed if parsed > 0 else default

    @classmethod
    def from_mapping(cls, raw: Any) -> "PatchPolicy":
        if isinstance(raw, PatchPolicy):
            return raw
        if raw is None:
            return cls()
        if not isinstance(raw, dict):
            raise PatchValidationError(
                code="PATCH_POLICY_INVALID",
                stage="policy",
                message="patch policy must be an object",
            )
        return cls(
            allow_roots=cls._norm_entries(_as_list(raw.get("allow_roots"), list(DEFAULT_ALLOW_ROOTS))),
            deny_prefixes=cls._norm_entries(_as_list(raw.get("deny_prefixes"), list(DEFAULT_DENY_PREFIXES))),
            deny_suffixes=tuple(str(x).strip().lower() for x in _as_list(raw.get("deny_suffixes"), list(DEFAULT_DENY_SUFFIXES)) if str(x).strip()),
            max_files=cls._coerce_limit(raw.get("max_files", 5), 5),
            max_added_lines=cls._coerce_limit(raw.get("max_added_lines", 400), 400),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "allow_roots": list(self.allow_roots),
            "deny_prefixes": list(self.deny_prefixes),
            "deny_suffixes": list(self.deny_suffixes),
            "max_files": self.max_files,
            "max_added_lines": self.max_added_lines,
        }


@dataclass
class PatchApplyResult:
    ok: bool
    stage: str
    code: str
    message: str
    touched_files: list[str] = field(default_factory=list)
    added_lines: int = 0
    command: str = ""
    stdout: str = ""
    stderr: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "stage": self.stage,
            "code": self.code,
            "message": self.message,
            "touched_files": list(self.touched_files),
            "added_lines": int(self.added_lines),
            "command": self.command,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "details": dict(self.details),
        }


def _as_list(value: Any, default: list[str]) -> list[str]:
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        return [str(x) for x in value]
    return default


def _normalize_policy_path(value: str) -> str:
    text = (value or "").strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    text = text.strip("/")
    return text


def normalize_repo_relpath(p: str) -> str:
    text = (p or "").strip().replace("\\", "/")
    if text.startswith("a/") or text.startswith("b/"):
        text = text[2:]
    while text.startswith("./"):
        text = text[2:]
    if not text or text == ".":
        raise PatchValidationError(
            code="PATCH_PATH_INVALID",
            stage="path",
            message=f"invalid empty relative path: {p!r}",
        )
    if text.startswith("/") or text.startswith("\\"):
        raise PatchValidationError(
            code="PATCH_PATH_INVALID",
            stage="path",
            message=f"absolute path is not allowed: {p!r}",
        )
    if re.match(r"^[A-Za-z]:[\\/]", text):
        raise PatchValidationError(
            code="PATCH_PATH_INVALID",
            stage="path",
            message=f"drive-letter path is not allowed: {p!r}",
        )
    parts = [seg for seg in text.split("/") if seg not in {"", "."}]
    if any(seg == ".." for seg in parts):
        raise PatchValidationError(
            code="PATCH_PATH_INVALID",
            stage="path",
            message=f"path traversal is not allowed: {p!r}",
        )
    normalized = "/".join(parts)
    if not normalized:
        raise PatchValidationError(
            code="PATCH_PATH_INVALID",
            stage="path",
            message=f"invalid relative path: {p!r}",
        )
    return normalized


def parse_unified_diff(text: str) -> list[str]:
    raw = text or ""
    lines = raw.splitlines()
    non_empty = [ln for ln in lines if ln.strip()]
    if not non_empty:
        raise PatchValidationError(
            code="PATCH_PARSE_INVALID",
            stage="parse",
            message="patch is empty",
        )
    if not non_empty[0].startswith("diff --git "):
        raise PatchValidationError(
            code="PATCH_PARSE_INVALID",
            stage="parse",
            message="patch must start with 'diff --git'",
        )
    touched: list[str] = []
    seen: set[str] = set()
    for ln in lines:
        if not ln.startswith("diff --git "):
            continue
        m = re.match(r"^diff --git a/(.+) b/(.+)$", ln.strip())
        if not m:
            raise PatchValidationError(
                code="PATCH_PARSE_INVALID",
                stage="parse",
                message=f"invalid diff header: {ln.strip()}",
            )
        # A rename is still one touched target file; guard policy uses target path.
        path = normalize_repo_relpath(m.group(2))
        if path not in seen:
            seen.add(path)
            touched.append(path)
    if not touched:
        raise PatchValidationError(
            code="PATCH_PARSE_INVALID",
            stage="parse",
            message="no touched files found from diff headers",
        )
    return touched


def _count_added_lines(diff_text: str) -> int:
    added = 0
    for ln in (diff_text or "").splitlines():
        if ln.startswith("+++ "):
            continue
        if ln.startswith("+"):
            added += 1
    return added


def _contains_binary_payload(diff_text: str) -> bool:
    if "\x00" in diff_text:
        return True
    for ln in diff_text.splitlines():
        if ln.startswith("GIT binary patch"):
            return True
        if ln.startswith("Binary files "):
            return True
    return False


def _path_in_root(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def validate_diff_against_policy(
    diff_text: str,
    policy: PatchPolicy | dict[str, Any] | None,
    repo_root: Path | str,
) -> dict[str, Any]:
    del repo_root  # policy is repo-relative and does not depend on filesystem state.
    resolved_policy = PatchPolicy.from_mapping(policy)
    touched_files = parse_unified_diff(diff_text)

    if _contains_binary_payload(diff_text):
        raise PatchValidationError(
            code="PATCH_POLICY_DENY",
            stage="policy",
            message="binary patch payload is not allowed",
            details={"rule": "binary_payload"},
        )

    if len(touched_files) > resolved_policy.max_files:
        raise PatchValidationError(
            code="PATCH_POLICY_DENY",
            stage="policy",
            message=f"touched files exceed max_files ({len(touched_files)} > {resolved_policy.max_files})",
            details={
                "rule": "max_files",
                "limit": resolved_policy.max_files,
                "actual": len(touched_files),
            },
        )

    added_lines = _count_added_lines(diff_text)
    if added_lines > resolved_policy.max_added_lines:
        raise PatchValidationError(
            code="PATCH_POLICY_DENY",
            stage="policy",
            message=f"added lines exceed max_added_lines ({added_lines} > {resolved_policy.max_added_lines})",
            details={
                "rule": "max_added_lines",
                "limit": resolved_policy.max_added_lines,
                "actual": added_lines,
            },
        )

    for path in touched_files:
        if resolved_policy.allow_roots and not any(_path_in_root(path, root) for root in resolved_policy.allow_roots):
            raise PatchValidationError(
                code="PATCH_POLICY_DENY",
                stage="policy",
                message=f"path is outside allow_roots: {path}",
                details={"rule": "allow_roots", "path": path},
            )
        if any(_path_in_root(path, prefix) for prefix in resolved_policy.deny_prefixes):
            raise PatchValidationError(
                code="PATCH_POLICY_DENY",
                stage="policy",
                message=f"path matches deny_prefixes: {path}",
                details={"rule": "deny_prefixes", "path": path},
            )
        lower = path.lower()
        if any(lower.endswith(suffix) for suffix in resolved_policy.deny_suffixes):
            raise PatchValidationError(
                code="PATCH_POLICY_DENY",
                stage="policy",
                message=f"path matches deny_suffixes: {path}",
                details={"rule": "deny_suffixes", "path": path},
            )

    return {
        "touched_files": touched_files,
        "added_lines": added_lines,
        "policy": resolved_policy.to_dict(),
    }


def git_apply_check(repo_root: Path | str, diff_text: str) -> tuple[int, str, str]:
    root = Path(repo_root).resolve()
    if not root.exists():
        raise PatchValidationError(
            code="PATCH_ENV_INVALID",
            stage="env",
            message=f"repo_root does not exist: {root}",
        )
    proc = subprocess.run(
        ["git", "apply", "--check", "--whitespace=nowarn", "-"],
        cwd=str(root),
        input=diff_text,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def apply_patch(repo_root: Path | str, diff_text: str) -> tuple[int, str, str]:
    root = Path(repo_root).resolve()
    if not root.exists():
        raise PatchValidationError(
            code="PATCH_ENV_INVALID",
            stage="env",
            message=f"repo_root does not exist: {root}",
        )
    proc = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "-"],
        cwd=str(root),
        input=diff_text,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def apply_patch_safely(
    repo_root: Path | str,
    diff_text: str,
    policy: PatchPolicy | dict[str, Any] | None = None,
) -> PatchApplyResult:
    try:
        summary = validate_diff_against_policy(diff_text, policy, repo_root)
    except PatchValidationError as exc:
        return PatchApplyResult(
            ok=False,
            stage=exc.stage,
            code=exc.code,
            message=str(exc),
            details=exc.details,
        )

    touched_files = [str(x) for x in summary.get("touched_files", [])]
    added_lines = int(summary.get("added_lines", 0))

    try:
        rc_check, out_check, err_check = git_apply_check(repo_root, diff_text)
    except PatchValidationError as exc:
        return PatchApplyResult(
            ok=False,
            stage=exc.stage,
            code=exc.code,
            message=str(exc),
            touched_files=touched_files,
            added_lines=added_lines,
            details=exc.details,
        )
    except FileNotFoundError:
        return PatchApplyResult(
            ok=False,
            stage="git_check",
            code="PATCH_ENV_INVALID",
            message="git executable not found",
            touched_files=touched_files,
            added_lines=added_lines,
        )

    if rc_check != 0:
        return PatchApplyResult(
            ok=False,
            stage="git_check",
            code="PATCH_GIT_CHECK_FAIL",
            message="git apply --check failed",
            touched_files=touched_files,
            added_lines=added_lines,
            command="git apply --check --whitespace=nowarn -",
            stdout=out_check,
            stderr=err_check,
        )

    try:
        rc_apply, out_apply, err_apply = apply_patch(repo_root, diff_text)
    except PatchValidationError as exc:
        return PatchApplyResult(
            ok=False,
            stage=exc.stage,
            code=exc.code,
            message=str(exc),
            touched_files=touched_files,
            added_lines=added_lines,
            details=exc.details,
        )
    except FileNotFoundError:
        return PatchApplyResult(
            ok=False,
            stage="apply",
            code="PATCH_ENV_INVALID",
            message="git executable not found",
            touched_files=touched_files,
            added_lines=added_lines,
        )

    if rc_apply != 0:
        return PatchApplyResult(
            ok=False,
            stage="apply",
            code="PATCH_APPLY_FAIL",
            message="git apply failed",
            touched_files=touched_files,
            added_lines=added_lines,
            command="git apply --whitespace=nowarn -",
            stdout=out_apply,
            stderr=err_apply,
        )

    return PatchApplyResult(
        ok=True,
        stage="apply",
        code="PATCH_OK",
        message="patch applied",
        touched_files=touched_files,
        added_lines=added_lines,
        command="git apply --whitespace=nowarn -",
        stdout=out_apply,
        stderr=err_apply,
        details={"policy": summary.get("policy", {})},
    )

