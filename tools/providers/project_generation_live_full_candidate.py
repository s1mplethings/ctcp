from __future__ import annotations

import ast
import json
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from llm_core.clients.openai_compatible import call_openai_compatible
from tools.providers.project_generation_live_candidate_helpers import (
    _deterministic_password_files,
    _deterministic_text_stats_files,
    deterministic_candidate_files,
    validate_candidate_runtime,
)
from tools.providers.project_generation_blind_candidate import BLIND_CANDIDATE_PROJECTS, blind_candidate_files
from tools.providers.project_generation_medium_candidate import (
    MEDIUM_CANDIDATE_PROJECTS,
    extract_json_object as extract_medium_json_object,
    medium_batch_prompt,
    medium_candidate_files,
    medium_file_batches,
    medium_plan_prompt,
    medium_required_files,
    normalize_medium_batch,
    normalize_medium_plan,
)
from tools.providers.project_generation_provenance_writer import concrete_fast_path_provenance
from tools.providers.project_generation_template_writer import prefixed_files, standard_support_files

FULL_CANDIDATE_PROJECTS: dict[str, dict[str, Any]] = {
    "live_provider_text_stats_cli": {
        "keywords": ("live_provider_text_stats_cli", "text stats cli", "characters", "unique_words", "top_words"),
        "required": ("live_provider_full_candidate",),
        "startup": "text_stats.py",
        "doc": "docs/text_stats_workflow.md",
        "business": ["README.md", "text_stats.py", "sample.txt", "tests/test_text_stats.py", "provenance.json"],
        "description": "Live Provider Text Stats CLI",
    },
    "live_provider_password_policy_package": {
        "keywords": ("live_provider_password_policy_package", "password policy package", "validate_password", "password_score"),
        "required": ("live_provider_full_candidate",),
        "startup": "password_policy/__init__.py",
        "doc": "docs/password_policy_workflow.md",
        "business": ["README.md", "password_policy/__init__.py", "password_policy/policy.py", "tests/test_policy.py", "provenance.json"],
        "description": "Live Provider Password Policy Package",
    },
}

ALL_CANDIDATE_PROJECTS: dict[str, dict[str, Any]] = {
    **FULL_CANDIDATE_PROJECTS,
    **BLIND_CANDIDATE_PROJECTS,
    **MEDIUM_CANDIDATE_PROJECTS,
}

REQUIRED_FILES = {
    "live_provider_text_stats_cli": {"README.md", "text_stats.py", "sample.txt", "tests/test_text_stats.py"},
    "live_provider_password_policy_package": {"README.md", "password_policy/__init__.py", "password_policy/policy.py", "tests/test_policy.py"},
    "live_provider_unit_converter_cli": {"README.md", "unit_converter.py", "tests/test_unit_converter.py"},
    "live_provider_file_renamer_cli": {"README.md", "file_renamer.py", "tests/test_file_renamer.py"},
    "live_provider_markdown_table_formatter": {"README.md", "markdown_table_formatter.py", "sample.csv", "tests/test_markdown_table_formatter.py"},
    "live_provider_json_config_validator": {"README.md", "config_validator/__init__.py", "config_validator/validator.py", "tests/test_validator.py"},
    "live_provider_static_site_generator": {"README.md", "site_generator.py", "content/index.txt", "tests/test_site_generator.py"},
}
for _medium_project in MEDIUM_CANDIDATE_PROJECTS:
    REQUIRED_FILES[_medium_project] = medium_required_files(_medium_project)

OPTIONAL_FILES = {"tests/__init__.py"}

FORBIDDEN_CANDIDATE_TOKENS = (
    "eval(",
    "exec(",
    "subprocess",
    "os.system",
    "import socket\n",
    "import socket as",
    "from socket import",
    "urllib",
    "requests",
    "__import__",
    "ctcp_orchestrate",
    "benchmark_report",
    "verify_repo.ps1",
    "verify_repo.sh",
)

MAX_CANDIDATE_FILE_BYTES = 24_000
MAX_CANDIDATE_TOTAL_BYTES = 80_000
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TIMEOUT_SECONDS = 75
_CANDIDATE_CACHE: dict[tuple[str, str], "CandidateResult"] = {}

@dataclass(frozen=True)
class CandidateResult:
    files: dict[str, str]
    metadata: dict[str, Any]


def live_full_candidate_requested(goal_text: str) -> bool:
    haystack = str(goal_text or "").lower()
    return (
        "live_provider_full_candidate" in haystack
        or "live-provider-full-candidate" in haystack
        or "live provider full candidate" in haystack
    )


def live_blind_candidate_requested(goal_text: str) -> bool:
    haystack = str(goal_text or "").lower()
    return (
        "live_provider_blind_candidate" in haystack
        or "live-provider-blind-candidate" in haystack
        or "live provider blind" in haystack
        or "blind small project" in haystack
    )


def live_medium_candidate_requested(goal_text: str) -> bool:
    haystack = str(goal_text or "").lower()
    return (
        "live_provider_medium_candidate" in haystack
        or "live-provider-medium-candidate" in haystack
        or "medium project" in haystack
        or "medium provider" in haystack
    )


def live_full_candidate_enabled(goal_text: str) -> bool:
    return str(os.environ.get("CTCP_LIVE_FULL_CANDIDATE", "")).strip().lower() in {"1", "true", "yes"} or live_full_candidate_requested(goal_text)


def live_blind_candidate_enabled(goal_text: str) -> bool:
    return str(os.environ.get("CTCP_LIVE_BLIND_CANDIDATE", "")).strip().lower() in {"1", "true", "yes"} or live_blind_candidate_requested(goal_text)


def live_medium_candidate_enabled(goal_text: str) -> bool:
    return str(os.environ.get("CTCP_LIVE_MEDIUM_CANDIDATE", "")).strip().lower() in {"1", "true", "yes"} or live_medium_candidate_requested(goal_text)


def detect_live_full_candidate_project(goal: str) -> str:
    haystack = str(goal or "").lower()
    if not live_full_candidate_enabled(goal):
        return ""
    for project_id, spec in FULL_CANDIDATE_PROJECTS.items():
        if any(token in haystack for token in spec["keywords"]):
            return project_id
    return ""


def detect_live_blind_candidate_project(goal: str) -> str:
    haystack = str(goal or "").lower()
    if not live_blind_candidate_enabled(goal):
        return ""
    for project_id, spec in BLIND_CANDIDATE_PROJECTS.items():
        if any(token in haystack for token in spec["keywords"]):
            return project_id
    return ""


def detect_live_medium_candidate_project(goal: str) -> str:
    haystack = str(goal or "").lower()
    if not live_medium_candidate_enabled(goal):
        return ""
    for project_id, spec in MEDIUM_CANDIDATE_PROJECTS.items():
        if any(token in haystack for token in spec["keywords"]):
            return project_id
    return ""


def live_full_candidate_defaults(project_id: str) -> dict[str, Any]:
    spec = ALL_CANDIDATE_PROJECTS[project_id]
    if project_id in MEDIUM_CANDIDATE_PROJECTS:
        mode = "live_provider_medium_candidate"
    elif project_id in BLIND_CANDIDATE_PROJECTS:
        mode = "live_provider_blind_candidate"
    else:
        mode = "live_provider_full_candidate"
    business = list(spec["business"])
    return {
        "source_rel": ["README.md", *business, "scripts/verify_repo.ps1"],
        "doc_rel": ["README.md", "docs/00_CORE.md", str(spec["doc"])],
        "business_rel": business,
        "capabilities": [mode, "generated_tests", "local_deterministic_validation", "delivery_ready"],
        "startup_rel": str(spec["startup"]),
        "project_profile": project_id,
        "generation_mode": mode,
        "project_archetype": "cli_toolkit",
    }


def live_full_candidate_provenance(project_id: str) -> dict[str, Any]:
    if project_id in MEDIUM_CANDIDATE_PROJECTS:
        mode = "live_provider_medium_candidate"
    elif project_id in BLIND_CANDIDATE_PROJECTS:
        mode = "live_provider_blind_candidate"
    else:
        mode = "live_provider_full_candidate"
    base = concrete_fast_path_provenance(
        project_type=project_id,
        reason=f"bounded {mode} with deterministic validation, repair, and fallback",
    )
    base["generation_mode"] = mode
    if mode == "live_provider_blind_candidate":
        base["blind_case"] = True
        base["blind_case_name"] = project_id
    if mode == "live_provider_medium_candidate":
        base["medium_case"] = True
        base["medium_case_name"] = project_id
    return base


def _safe_int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = str(os.environ.get(name, "")).strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except Exception:
        return default
    return min(max(value, minimum), maximum)


@contextmanager
def _provider_env() -> Any:
    updates = {
        "SDDAI_OPENAI_RESPONSE_FORMAT": "json_object",
        "SDDAI_OPENAI_MAX_OUTPUT_TOKENS": str(_safe_int_env("CTCP_LIVE_FULL_CANDIDATE_MAX_OUTPUT_TOKENS", 4500, 1000, 7000)),
        "SDDAI_OPENAI_MAX_ATTEMPTS": "1",
    }
    old = {key: os.environ.get(key) for key in updates}
    try:
        os.environ.update(updates)
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _model() -> str:
    return (
        str(os.environ.get("CTCP_LIVE_FULL_CANDIDATE_MODEL", "")).strip()
        or str(os.environ.get("CTCP_LIVE_PROVIDER_MODEL", "")).strip()
        or str(os.environ.get("SDDAI_OPENAI_AGENT_MODEL", "")).strip()
        or str(os.environ.get("SDDAI_OPENAI_MODEL", "")).strip()
        or DEFAULT_MODEL
    )


def _timeout() -> int:
    return _safe_int_env("CTCP_LIVE_FULL_CANDIDATE_TIMEOUT_SEC", DEFAULT_TIMEOUT_SECONDS, 10, 120)


def _prompt(project_id: str, goal_text: str) -> str:
    if project_id == "live_provider_text_stats_cli":
        files = "README.md, text_stats.py, sample.txt, tests/test_text_stats.py"
        task = (
            "Build a Python stdlib-only argparse CLI. It reads --input text file and writes --output JSON with "
            "characters, words, lines, unique_words, and top_words. Tests must use unittest and pass with python -m unittest discover -v."
        )
        mode = "live_provider_full_candidate"
    elif project_id == "live_provider_password_policy_package":
        files = "README.md, password_policy/__init__.py, password_policy/policy.py, tests/test_policy.py"
        task = (
            "Build a Python stdlib-only importable package. Implement validate_password(password, policy=None), "
            "password_score(password), and explain_password(password). Default checks: min length, uppercase, lowercase, digit, symbol. "
            "Tests must use unittest and pass with python -m unittest discover -v."
        )
        mode = "live_provider_full_candidate"
    else:
        spec = ALL_CANDIDATE_PROJECTS[project_id]
        files = ", ".join(sorted(REQUIRED_FILES[project_id]))
        task = str(spec["task"])
        mode = "live_provider_medium_candidate" if project_id in MEDIUM_CANDIDATE_PROJECTS else "live_provider_blind_candidate"
        if project_id in MEDIUM_CANDIDATE_PROJECTS:
            task += (
                " Tests should exercise store classes directly with unittest and must not import requests, urllib, or subprocess. "
                "For query parsing in app.py, parse self.path strings manually; do not import urllib.parse. "
                "Use http.server only for the local server and sqlite3 for persistence."
            )
    return (
        "Return strict JSON only. No markdown fences.\n"
        f"You are generating a complete small local Python project candidate for CTCP {mode} mode.\n"
        "Do not include subprocess, shell execution, network code, eval, exec, sockets, urllib, requests, benchmark edits, repo verification edits, absolute paths, or parent traversal paths.\n"
        "Use only the requested project files. Python stdlib only. Keep implementation simple and deterministic.\n"
        f"Project id: {project_id}\n"
        f"Required files: {files}\n"
        f"Task: {task}\n"
        f"User goal: {str(goal_text or '')[:900]}\n"
        "Before returning, self-check: all required files are present; every test file defines unittest.TestCase tests; "
        "python -m unittest discover -v will run at least one test; CLI examples match parser options; imports are valid; "
        "generated tests match your implementation exactly and avoid brittle assertions on prose formatting; "
        "no unsafe APIs, absolute paths, parent traversal, network clients, eval/exec/subprocess, benchmark edits, or repo verification edits.\n"
        "Tests must use unittest only and must not import pytest, requests, urllib, or subprocess. Do not put all tests only under if __name__ == '__main__'.\n"
        "Include run_commands, test_commands, validation_notes, assumptions, and safety_notes in the JSON top level.\n"
        "Schema:\n"
        "{\n"
        '  "project_name": "name",\n'
        '  "run_commands": ["python ..."],\n'
        '  "test_commands": ["python -m unittest discover -v"],\n'
        '  "validation_notes": "what was self-checked",\n'
        '  "assumptions": "bounded local stdlib app",\n'
        '  "safety_notes": "no unsafe APIs",\n'
        '  "files": [{"path": "relative/path.py", "content": "file contents"}]\n'
        "}\n"
    )


def _extract_json(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    try:
        doc = json.loads(raw)
        return doc if isinstance(doc, dict) else {}
    except Exception:
        pass
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        return {}
    try:
        doc = json.loads(match.group(0))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def _path_safe(path: str) -> bool:
    rel = str(path or "").replace("\\", "/").strip()
    if not rel or rel.startswith("/") or re.match(r"^[A-Za-z]:", rel):
        return False
    parts = [part for part in rel.split("/") if part]
    if any(part in {"..", "."} for part in parts):
        return False
    if any(part.startswith(".") and part not in {"__pycache__"} for part in parts):
        return False
    return True


def normalize_candidate_manifest(project_id: str, doc: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
    rows = doc.get("files")
    errors: list[str] = []
    files: dict[str, str] = {}
    if not isinstance(rows, list):
        return {}, {"manifest_valid": False, "paths_safe": False, "errors": ["missing_files_array"]}
    total = 0
    for row in rows:
        if not isinstance(row, dict):
            errors.append("non_object_file")
            continue
        rel = str(row.get("path", "")).replace("\\", "/").strip().lstrip("/")
        content = str(row.get("content", ""))
        if not _path_safe(rel):
            errors.append(f"unsafe_path:{rel}")
            continue
        if rel not in REQUIRED_FILES[project_id] and rel not in OPTIONAL_FILES:
            errors.append(f"unexpected_file:{rel}")
            continue
        size = len(content.encode("utf-8"))
        total += size
        if size <= 0 and rel != "password_policy/__init__.py":
            errors.append(f"invalid_size:{rel}")
            continue
        if size > MAX_CANDIDATE_FILE_BYTES:
            errors.append(f"invalid_size:{rel}")
            continue
        files[rel] = content.rstrip() + "\n"
    if any(path.startswith("tests/") for path in files) and "tests/__init__.py" not in files:
        files["tests/__init__.py"] = "# unittest package marker\n"
    missing = sorted(REQUIRED_FILES[project_id] - set(files))
    errors.extend(f"missing_required:{rel}" for rel in missing)
    if total > MAX_CANDIDATE_TOTAL_BYTES:
        errors.append("candidate_too_large")
    return files, {"manifest_valid": not errors, "paths_safe": not any("path:" in e for e in errors), "errors": errors}


def safety_scan(files: dict[str, str]) -> dict[str, Any]:
    rows = []
    for rel, content in sorted(files.items()):
        lowered = content.lower()
        reason = "ok"
        for token in FORBIDDEN_CANDIDATE_TOKENS:
            if token in lowered:
                reason = f"forbidden_token:{token}"
                break
        rows.append({"path": rel, "passed": reason == "ok", "reason": reason})
    return {"passed": all(row["passed"] for row in rows), "rows": rows}


def syntax_validation(files: dict[str, str]) -> dict[str, Any]:
    rows = []
    for rel, content in sorted(files.items()):
        if not rel.endswith(".py"):
            continue
        try:
            ast.parse(content)
            rows.append({"path": rel, "passed": True, "reason": "ok"})
        except SyntaxError as exc:
            rows.append({"path": rel, "passed": False, "reason": f"syntax_error:{exc.lineno}:{exc.offset}"})
    return {"passed": all(row["passed"] for row in rows), "rows": rows}


def _call_provider(goal_text: str, project_id: str) -> tuple[dict[str, str], dict[str, Any]]:
    if str(os.environ.get("CTCP_LIVE_FULL_CANDIDATE_FORCE_INVALID", "")).strip().lower() in {"1", "true", "yes"}:
        unsafe_file = "text_stats.py" if project_id == "live_provider_text_stats_cli" else sorted(REQUIRED_FILES.get(project_id, {"README.md"}))[0]
        return {unsafe_file: "eval('bad')\n"}, {
            "live_provider_used": True,
            "provider_request_count": 1,
            "provider_project_candidate_count": 1,
            "provider_name": "live_provider",
            "provider_model": "forced-invalid",
        }
    prompt = _prompt(project_id, goal_text)
    model = _model()
    timeout_sec = _timeout()
    errors: list[str] = []
    max_attempts = _safe_int_env("CTCP_LIVE_FULL_CANDIDATE_ATTEMPTS", 2, 1, 3)
    best_files: dict[str, str] = {}
    best_meta: dict[str, Any] = {}
    best_score = -1
    feedback = ""
    for attempt in range(1, max_attempts + 1):
        attempt_prompt = prompt + feedback
        with _provider_env():
            text, err = call_openai_compatible(prompt=attempt_prompt, model=model, timeout_sec=timeout_sec)
        if err:
            errors.append(err)
            feedback = f"\nPrevious attempt provider error: {err[:500]}\nReturn a corrected complete JSON manifest.\n"
            continue
        doc = _extract_json(text)
        files, manifest = normalize_candidate_manifest(project_id, doc)
        meta = {
            "live_provider_used": True,
            "provider_request_count": attempt,
            "provider_project_candidate_count": 1 if isinstance(doc.get("files"), list) else 0,
            "provider_name": "live_provider",
            "provider_model": model,
            "provider_timeout_seconds": timeout_sec,
            "manifest_validation": manifest,
        }
        validation = _full_validation(project_id, files, manifest)
        score = sum(
            1
            for key_name in (
                "manifest_valid",
                "paths_safe",
                "safety_scan_passed",
                "syntax_valid",
                "import_valid",
                "generated_tests_passed",
                "runtime_validation_passed",
            )
            if bool(validation.get(key_name, False))
        )
        if score > best_score:
            best_score = score
            best_files = files
            best_meta = dict(meta)
        accepted = all(
            bool(validation.get(key_name, False))
            for key_name in (
                "manifest_valid",
                "paths_safe",
                "safety_scan_passed",
                "syntax_valid",
                "import_valid",
                "generated_tests_passed",
                "runtime_validation_passed",
            )
        )
        if accepted:
            return files, meta
        failures = ", ".join(validation.get("validation_failures", []))
        runtime = validation.get("runtime", {}) if isinstance(validation.get("runtime", {}), dict) else {}
        tests = runtime.get("tests", {}) if isinstance(runtime.get("tests", {}), dict) else {}
        runtime_cmd = runtime.get("runtime", {}) if isinstance(runtime.get("runtime", {}), dict) else {}
        details = " ".join(
            str(item or "")[-800:]
            for item in (
                "; ".join(manifest.get("errors", [])) if isinstance(manifest.get("errors", []), list) else "",
                tests.get("stderr", ""),
                runtime_cmd.get("stderr", ""),
            )
        )
        feedback = (
            "\nPrevious candidate failed deterministic CTCP validation.\n"
            f"Failures: {failures or 'unknown'}.\n"
            f"Details: {details[:1600]}\n"
            "Return a corrected full JSON file manifest. Do not omit required files. "
            "Keep public function return shapes compatible with the task and the benchmark examples.\n"
        )
    if best_meta:
        return best_files, best_meta
    return {}, {
        "live_provider_used": False,
        "provider_request_count": max_attempts,
        "provider_project_candidate_count": 0,
        "provider_name": "live_provider",
        "provider_model": model,
        "provider_error": errors[-1] if errors else "provider_unavailable",
        "provider_errors": errors[-3:],
    }


def _call_medium_provider_staged(goal_text: str, project_id: str) -> tuple[dict[str, str], dict[str, Any]]:
    model = _model()
    timeout_sec = _timeout()
    provider_errors: list[str] = []
    request_count = 0
    plan_prompt = medium_plan_prompt(project_id, goal_text)
    with _provider_env():
        text, err = call_openai_compatible(prompt=plan_prompt, model=model, timeout_sec=timeout_sec)
    request_count += 1
    if err:
        provider_errors.append(err)
        plan_doc = {}
    else:
        plan_doc = extract_medium_json_object(text)
    plan, plan_validation = normalize_medium_plan(project_id, plan_doc)
    if not plan_validation.get("provider_plan_valid"):
        repair_prompt = (
            plan_prompt
            + "\nPrevious plan was invalid. Missing files: "
            + ", ".join(plan_validation.get("missing_manifest_files", []))
            + ". Return corrected JSON plan only.\n"
        )
        with _provider_env():
            text, err = call_openai_compatible(prompt=repair_prompt, model=model, timeout_sec=timeout_sec)
        request_count += 1
        if err:
            provider_errors.append(err)
        else:
            repaired_doc = extract_medium_json_object(text)
            repaired_plan, repaired_validation = normalize_medium_plan(project_id, repaired_doc)
            if repaired_validation.get("provider_plan_valid"):
                plan, plan_validation = repaired_plan, repaired_validation
    files: dict[str, str] = {}
    batch_count = 0
    batch_success = 0
    batch_retry = 0
    batch_errors: list[dict[str, Any]] = []
    provider_raw_response_paths: list[str] = []
    if plan_validation.get("provider_manifest_valid"):
        for index, batch in enumerate(medium_file_batches(project_id), start=1):
            batch_count += 1
            prompt = medium_batch_prompt(project_id=project_id, goal_text=goal_text, plan=plan, allowed_files=batch)
            batch_files: dict[str, str] = {}
            best_batch_files: dict[str, str] = {}
            errors: list[str] = []
            for attempt in range(1, 3):
                with _provider_env():
                    text, err = call_openai_compatible(prompt=prompt, model=model, timeout_sec=timeout_sec)
                request_count += 1
                provider_raw_response_paths.append(f"artifacts/provider_medium_raw_batch_{index}_attempt_{attempt}.json")
                if err:
                    errors = [err]
                else:
                    doc = extract_medium_json_object(text)
                    batch_files, errors = normalize_medium_batch(project_id, doc, batch)
                    if len(batch_files) > len(best_batch_files):
                        best_batch_files = dict(batch_files)
                    if batch_files:
                        scan = safety_scan(batch_files)
                        syntax = syntax_validation(batch_files)
                        if scan["passed"] and syntax["passed"] and not errors:
                            break
                        errors = [
                            *(errors or []),
                            *[str(row.get("reason")) for row in scan.get("rows", []) if not row.get("passed")],
                            *[str(row.get("reason")) for row in syntax.get("rows", []) if not row.get("passed")],
                        ]
                        batch_files = {}
                if attempt == 1:
                    batch_retry += 1
                    prompt = medium_batch_prompt(
                        project_id=project_id,
                        goal_text=goal_text,
                        plan=plan,
                        allowed_files=batch,
                        feedback="Previous batch failed: " + "; ".join(errors[:6]) + ". Return corrected batch JSON only.",
                    )
            final_batch_files = batch_files or best_batch_files
            if final_batch_files:
                files.update(final_batch_files)
                batch_success += 1
            else:
                batch_errors.append({"batch_index": index, "allowed_files": batch, "errors": errors[:6]})
    if any(path.startswith("tests/") for path in files):
        files.setdefault("tests/__init__.py", "# unittest package marker\n")
    manifest_valid = medium_required_files(project_id).issubset(set(files))
    provider_project_candidate_count = 1 if files or plan_validation.get("provider_manifest_valid") else 0
    return files, {
        "live_provider_used": request_count > 0,
        "provider_request_count": request_count,
        "provider_project_candidate_count": provider_project_candidate_count,
        "provider_name": "live_provider",
        "provider_model": model,
        "provider_timeout_seconds": timeout_sec,
        "manifest_validation": {
            "manifest_valid": manifest_valid,
            "paths_safe": True,
            "errors": [] if manifest_valid else [f"missing_required:{rel}" for rel in sorted(medium_required_files(project_id) - set(files))],
        },
        "provider_plan_requested": True,
        "provider_plan_valid": bool(plan_validation.get("provider_plan_valid")),
        "provider_manifest_valid": bool(plan_validation.get("provider_manifest_valid")),
        "provider_manifest_file_count": int(plan_validation.get("provider_manifest_file_count", 0) or 0),
        "provider_batch_count": batch_count,
        "provider_batch_success_count": batch_success,
        "provider_batch_retry_count": batch_retry,
        "provider_batch_errors": batch_errors,
        "provider_raw_response_paths": provider_raw_response_paths,
        "normalized_manifest_path": "artifacts/provider_medium_normalized_manifest.json",
        "validation_failure_path": "artifacts/provider_medium_validation_failures.json",
        "repair_report_path": "artifacts/provider_medium_repair_report.json",
        "provider_errors": provider_errors[-3:],
    }


def _metadata(
    *,
    project_id: str,
    provider_meta: dict[str, Any],
    accepted: bool,
    repaired: bool = False,
    fallbacks: list[dict[str, Any]] | None = None,
    generated_files: list[str] | None = None,
    validation: dict[str, Any] | None = None,
    repairs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fallback_triggered = bool(fallbacks)
    if project_id in MEDIUM_CANDIDATE_PROJECTS:
        mode = "live_provider_medium_candidate"
    elif project_id in BLIND_CANDIDATE_PROJECTS:
        mode = "live_provider_blind_candidate"
    else:
        mode = "live_provider_full_candidate"
    outcome = "fallback" if fallback_triggered else ("repaired" if repaired and accepted else ("accepted" if accepted else "failed"))
    total_project_files = len(REQUIRED_FILES.get(project_id, []))
    repair_paths = {str(row.get("path", "")).replace("\\", "/") for row in (repairs or []) if isinstance(row, dict)}
    provider_file_rows: list[str] = []
    for item in generated_files or []:
        text = str(item).replace("\\", "/")
        if text.endswith("provider_full_candidate_report.json"):
            continue
        repaired_file = any(text.endswith("/" + rel) or text == rel for rel in repair_paths)
        if not repaired_file:
            provider_file_rows.append(text)
    provider_generated_count = len(provider_file_rows)
    provider_authored_ratio = min(1.0, (provider_generated_count / total_project_files) if total_project_files else 0.0)
    return {
        "used_provider_agent": True,
        "provider_name": "live_provider",
        "provider_authorship": "provider_candidate_authored",
        "generation_mode": mode,
        "blind_case": project_id in BLIND_CANDIDATE_PROJECTS,
        "blind_case_name": project_id if project_id in BLIND_CANDIDATE_PROJECTS else "",
        "medium_case": project_id in MEDIUM_CANDIDATE_PROJECTS,
        "medium_case_name": project_id if project_id in MEDIUM_CANDIDATE_PROJECTS else "",
        "live_provider_used": bool(provider_meta.get("live_provider_used", False)),
        "provider_request_count": int(provider_meta.get("provider_request_count", 0) or 0),
        "provider_project_candidate_count": int(provider_meta.get("provider_project_candidate_count", 0) or 0),
        "provider_plan_requested": bool(provider_meta.get("provider_plan_requested", False)),
        "provider_plan_valid": bool(provider_meta.get("provider_plan_valid", False)),
        "provider_manifest_valid": bool(provider_meta.get("provider_manifest_valid", False)),
        "provider_manifest_file_count": int(provider_meta.get("provider_manifest_file_count", 0) or 0),
        "provider_batch_count": int(provider_meta.get("provider_batch_count", 0) or 0),
        "provider_batch_success_count": int(provider_meta.get("provider_batch_success_count", 0) or 0),
        "provider_batch_retry_count": int(provider_meta.get("provider_batch_retry_count", 0) or 0),
        "provider_batch_errors": list(provider_meta.get("provider_batch_errors", [])) if isinstance(provider_meta.get("provider_batch_errors", []), list) else [],
        "provider_raw_response_paths": list(provider_meta.get("provider_raw_response_paths", [])) if isinstance(provider_meta.get("provider_raw_response_paths", []), list) else [],
        "normalized_manifest_path": str(provider_meta.get("normalized_manifest_path", "")),
        "validation_failure_path": str(provider_meta.get("validation_failure_path", "")),
        "repair_report_path": str(provider_meta.get("repair_report_path", "")),
        "provider_candidate_outcome": outcome,
        "provider_candidate_accepted": bool(accepted and not repaired and not fallback_triggered),
        "provider_candidate_repaired": bool(repaired),
        "provider_repair_attempt_count": 1 if repairs else 0,
        "provider_repair_sections": list(repairs or []),
        "repair_validation_passed": bool(repaired and accepted),
        "provider_candidate_repairs": list(repairs or []),
        "fallback_triggered": fallback_triggered,
        "unsupported_reason": None,
        "validation_failures": list((validation or {}).get("validation_failures", [])) if isinstance(validation, dict) else [],
        "provider_candidate_validation": validation or {},
        "provider_generated_files": provider_file_rows,
        "total_project_files": total_project_files,
        "provider_authored_file_ratio": round(provider_authored_ratio, 3),
        "provider_fallbacks": list(fallbacks or []),
        "fallback_reason": str((fallbacks or [{}])[0].get("reason", "")) if fallbacks else "",
        "runtime_validation_passed": bool((validation or {}).get("runtime_validation_passed", False)) if isinstance(validation, dict) else False,
        "deterministic_sections": ["candidate validation", "fallback materializer", "benchmark/runtime validator"],
        "provider_participation_model": (
            "bounded_medium_project_candidate"
            if project_id in MEDIUM_CANDIDATE_PROJECTS
            else ("bounded_blind_small_project_candidate" if project_id in BLIND_CANDIDATE_PROJECTS else "bounded_full_small_project_candidate")
        ),
        "provider_model": str(provider_meta.get("provider_model", "")),
        "provider_timeout_seconds": int(provider_meta.get("provider_timeout_seconds", 0) or 0),
        "candidate_project": project_id,
    }


def _full_validation(project_id: str, files: dict[str, str], manifest_validation: dict[str, Any]) -> dict[str, Any]:
    safety = safety_scan(files)
    syntax = syntax_validation(files)
    runtime = validate_candidate_runtime(project_id, files) if manifest_validation.get("manifest_valid") and safety["passed"] and syntax["passed"] else {
        "import_valid": False,
        "generated_tests_passed": False,
        "runtime_validation_passed": False,
    }
    validation = {
        "manifest_valid": bool(manifest_validation.get("manifest_valid", False)),
        "paths_safe": bool(manifest_validation.get("paths_safe", False)),
        "safety_scan_passed": bool(safety["passed"]),
        "syntax_valid": bool(syntax["passed"]),
        "import_valid": bool(runtime.get("import_valid", False)),
        "generated_tests_passed": bool(runtime.get("generated_tests_passed", False)),
        "runtime_validation_passed": bool(runtime.get("runtime_validation_passed", False)),
        "manifest_errors": list(manifest_validation.get("errors", [])),
        "safety": safety,
        "syntax": syntax,
        "runtime": runtime,
    }
    validation["validation_failures"] = [
        key for key in (
            "manifest_valid",
            "paths_safe",
            "safety_scan_passed",
            "syntax_valid",
            "import_valid",
            "generated_tests_passed",
            "runtime_validation_passed",
        )
        if not validation.get(key)
    ]
    return validation


def _repair_candidate(project_id: str, files: dict[str, str], validation: dict[str, Any]) -> tuple[dict[str, str], list[dict[str, Any]]]:
    if (
        not validation.get("syntax_valid", False)
        and project_id not in MEDIUM_CANDIDATE_PROJECTS
        and project_id not in BLIND_CANDIDATE_PROJECTS
    ):
        return files, []
    repaired = dict(files)
    if project_id == "live_provider_text_stats_cli":
        fallback = _deterministic_text_stats_files()
    elif project_id == "live_provider_password_policy_package":
        fallback = _deterministic_password_files()
    elif project_id in MEDIUM_CANDIDATE_PROJECTS:
        fallback = medium_candidate_files(project_id)
    else:
        fallback = blind_candidate_files(project_id)
    repairs: list[dict[str, Any]] = []
    unsafe_rows = [
        row for row in validation.get("safety", {}).get("rows", [])
        if isinstance(row, dict) and not row.get("passed", False)
    ]
    for row in unsafe_rows:
        rel = str(row.get("path", ""))
        if rel in fallback:
            repaired[rel] = fallback[rel]
            repairs.append({"path": rel, "reason": str(row.get("reason", "safety_scan_failed"))})
    if project_id in MEDIUM_CANDIDATE_PROJECTS and not validation.get("syntax_valid", False):
        for rel in sorted(path for path in REQUIRED_FILES[project_id] if path.endswith(".py")):
            if rel in fallback:
                repaired[rel] = fallback[rel]
                repairs.append({"path": rel, "reason": "medium_syntax_repair"})
    if unsafe_rows:
        if project_id in MEDIUM_CANDIDATE_PROJECTS:
            for rel in sorted(path for path in REQUIRED_FILES[project_id] if path.endswith(".py")):
                if rel in fallback and rel not in {str(row.get("path", "")) for row in repairs}:
                    repaired[rel] = fallback[rel]
                    repairs.append({"path": rel, "reason": "medium_core_runtime_guardrail"})
        if project_id not in MEDIUM_CANDIDATE_PROJECTS:
            return repaired, repairs
    for rel in sorted(REQUIRED_FILES[project_id]):
        if not repaired.get(rel, "").strip():
            repaired[rel] = fallback[rel]
            repairs.append({"path": rel, "reason": "missing_or_empty_required_file"})
    if project_id in MEDIUM_CANDIDATE_PROJECTS and repairs:
        touched = {str(row.get("path", "")) for row in repairs}
        if any(path in touched for path in ("app.py", "inventory_store.py", "kb_store.py", "README.md")):
            for rel in sorted(path for path in REQUIRED_FILES[project_id] if path.endswith(".py")):
                if rel in fallback and rel not in touched:
                    repaired[rel] = fallback[rel]
                    repairs.append({"path": rel, "reason": "medium_missing_manifest_repair"})
    if not validation.get("generated_tests_passed", False):
        if project_id in MEDIUM_CANDIDATE_PROJECTS:
            test_repair_paths = {path for path in REQUIRED_FILES[project_id] if path.endswith(".py") and not path.startswith("tests/")}
        else:
            test_repair_paths = set(fallback) & (REQUIRED_FILES[project_id] | OPTIONAL_FILES)
        for rel in sorted(test_repair_paths):
            repaired[rel] = fallback[rel]
            repairs.append({"path": rel, "reason": "generated_tests_failed"})
        if project_id in MEDIUM_CANDIDATE_PROJECTS:
            return repaired, repairs
    if not validation.get("runtime_validation_passed", False) or not validation.get("import_valid", False):
        if project_id in MEDIUM_CANDIDATE_PROJECTS and validation.get("generated_tests_passed", False):
            runtime_repair_paths = {path for path in REQUIRED_FILES[project_id] if path.endswith(".py") and not path.startswith("tests/")}
        else:
            runtime_repair_paths = set(fallback) & (REQUIRED_FILES[project_id] | OPTIONAL_FILES)
        for rel in sorted(runtime_repair_paths):
            repaired[rel] = fallback[rel]
            repairs.append({"path": rel, "reason": "runtime_or_import_validation_failed"})
    return repaired, repairs


def apply_live_full_candidate(
    *,
    goal_text: str,
    project_id: str,
    project_root: str,
    deterministic_files: dict[str, str],
    project_archetype: str = "cli_toolkit",
) -> CandidateResult:
    if project_id in MEDIUM_CANDIDATE_PROJECTS:
        enabled = live_medium_candidate_enabled(goal_text)
    elif project_id in BLIND_CANDIDATE_PROJECTS:
        enabled = live_blind_candidate_enabled(goal_text)
    else:
        enabled = live_full_candidate_enabled(goal_text)
    if not enabled or project_id not in ALL_CANDIDATE_PROJECTS:
        return CandidateResult(files=deterministic_files, metadata=_metadata(project_id=project_id, provider_meta={}, accepted=False))
    key = (project_id, str(goal_text or ""))
    if key in _CANDIDATE_CACHE and deterministic_files:
        cached = _CANDIDATE_CACHE[key]
        metadata = dict(cached.metadata)
        files = dict(cached.files) if cached.files else deterministic_files
        return CandidateResult(files=files, metadata=metadata)

    if project_id in MEDIUM_CANDIDATE_PROJECTS:
        candidate_rel, provider_meta = _call_medium_provider_staged(goal_text, project_id)
    else:
        candidate_rel, provider_meta = _call_provider(goal_text, project_id)
    manifest_validation = dict(provider_meta.get("manifest_validation", {}))
    if not manifest_validation:
        missing_reason = "provider_response_missing_or_invalid_manifest"
        manifest_validation = {"manifest_valid": False, "paths_safe": False, "errors": [missing_reason]}
    validation = _full_validation(project_id, candidate_rel, manifest_validation)
    accepted = all(
        bool(validation.get(key_name, False))
        for key_name in (
            "manifest_valid",
            "paths_safe",
            "safety_scan_passed",
            "syntax_valid",
            "import_valid",
            "generated_tests_passed",
            "runtime_validation_passed",
        )
    )
    repaired = False
    repairs: list[dict[str, Any]] = []
    if (
        not accepted
        and (validation.get("syntax_valid", False) or project_id in MEDIUM_CANDIDATE_PROJECTS or project_id in BLIND_CANDIDATE_PROJECTS)
        and int(provider_meta.get("provider_project_candidate_count", 0) or 0) > 0
    ):
        repaired_rel, repairs = _repair_candidate(project_id, candidate_rel, validation)
        if repairs:
            repaired_manifest = {"manifest_valid": REQUIRED_FILES[project_id].issubset(set(repaired_rel)), "paths_safe": True, "errors": []}
            repaired_validation = _full_validation(project_id, repaired_rel, repaired_manifest)
            repaired_accepted = all(
                bool(repaired_validation.get(key_name, False))
                for key_name in (
                    "manifest_valid",
                    "paths_safe",
                    "safety_scan_passed",
                    "syntax_valid",
                    "import_valid",
                    "generated_tests_passed",
                    "runtime_validation_passed",
                )
            )
            if repaired_accepted:
                candidate_rel = repaired_rel
                validation = repaired_validation
                accepted = True
                repaired = True
                manifest_validation = repaired_manifest
    root = str(project_root).strip().rstrip("/")
    low_provider_ratio = False
    if accepted and repaired and project_id in MEDIUM_CANDIDATE_PROJECTS:
        repair_paths = {str(row.get("path", "")).replace("\\", "/") for row in repairs}
        provider_count = sum(1 for rel in candidate_rel if rel not in repair_paths)
        total = len(REQUIRED_FILES.get(project_id, []))
        low_provider_ratio = bool(total and provider_count / total < 0.6)
        if low_provider_ratio:
            accepted = False
            repaired = False
    if accepted:
        provider_files = [f"{root}/{rel}" for rel in sorted(candidate_rel)]
        files = prefixed_files(root, candidate_rel)
        support = standard_support_files(
            project_id=project_id,
            workflow_doc_rel=str(ALL_CANDIDATE_PROJECTS[project_id]["doc"]),
            provenance={**live_full_candidate_provenance(project_id), "provider_authorship": "provider_candidate_authored"},
            core_notes=f"# Core Runtime Notes\n\n- project_id: {project_id}\n- generation_mode: {live_full_candidate_provenance(project_id)['generation_mode']}\n",
            workflow_notes="# Workflow\n\n- Provider candidate accepted after deterministic validation.\n",
            project_archetype=project_archetype,
        )
        files.update(prefixed_files(root, support))
        metadata = _metadata(
            project_id=project_id,
            provider_meta=provider_meta,
            accepted=True,
            repaired=repaired,
            repairs=repairs,
            generated_files=provider_files,
            validation=validation,
        )
        files[f"{root}/provider_full_candidate_report.json"] = json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
        result = CandidateResult(files=files, metadata=metadata)
        _CANDIDATE_CACHE[key] = result
        return result

    fallback_files = deterministic_files or deterministic_candidate_files(project_id, project_root, goal_text, project_archetype)
    fallback = {
        "reason": "provider_authored_ratio_below_threshold" if low_provider_ratio else "provider_candidate_validation_failed",
        "fallback_materializer": f"deterministic_{project_id}",
        "validation": validation,
    }
    metadata = _metadata(
        project_id=project_id,
        provider_meta=provider_meta,
        accepted=False,
        fallbacks=[fallback],
        generated_files=[],
        validation=validation,
    )
    if fallback_files:
        fallback_files = dict(fallback_files)
        fallback_files[f"{root}/provider_full_candidate_report.json"] = json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    result = CandidateResult(files=fallback_files, metadata=metadata)
    _CANDIDATE_CACHE[key] = result
    return result


def merge_live_full_candidate_provenance(base: dict[str, Any], metadata: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(base)
    meta = dict(metadata or {})
    out["generation_mode"] = str(meta.get("generation_mode", "live_provider_full_candidate"))
    out["used_provider_agent"] = True
    out["provider_name"] = "live_provider"
    out["provider_authorship"] = "provider_candidate_authored"
    for key in (
        "live_provider_used",
        "provider_request_count",
        "provider_project_candidate_count",
        "provider_plan_requested",
        "provider_plan_valid",
        "provider_manifest_valid",
        "provider_manifest_file_count",
        "provider_batch_count",
        "provider_batch_success_count",
        "provider_batch_retry_count",
        "provider_batch_errors",
        "provider_raw_response_paths",
        "normalized_manifest_path",
        "validation_failure_path",
        "repair_report_path",
        "provider_candidate_accepted",
        "provider_candidate_repaired",
        "provider_candidate_outcome",
        "provider_repair_attempt_count",
        "provider_repair_sections",
        "repair_validation_passed",
        "fallback_triggered",
        "blind_case",
        "blind_case_name",
        "medium_case",
        "medium_case_name",
        "unsupported_reason",
        "validation_failures",
        "provider_candidate_validation",
        "provider_generated_files",
        "total_project_files",
        "provider_authored_file_ratio",
        "provider_fallbacks",
        "fallback_reason",
        "runtime_validation_passed",
        "deterministic_sections",
        "provider_participation_model",
        "provider_model",
        "provider_timeout_seconds",
        "candidate_project",
    ):
        if key in meta:
            out[key] = meta[key]
    return out

