from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Callable


def _env_flag_enabled(name: str, default: bool) -> bool:
    raw = str(os.environ.get(name, "")).strip().lower()
    if not raw:
        return default
    return raw not in {"0", "false", "no", "off"}


def _is_source_generation_request(request: dict[str, Any]) -> bool:
    return (
        str(request.get("role", "")).strip().lower() == "chair"
        and str(request.get("action", "")).strip().lower() == "source_generation"
        and str(request.get("target_path", "")).strip().lower().endswith("artifacts/source_generation_report.json")
    )


def should_chunk_source_generation(*, run_dir: Path, request: dict[str, Any]) -> bool:
    if not _is_source_generation_request(request):
        return False
    if not _env_flag_enabled("CTCP_CHUNKED_SOURCE_GENERATION", True):
        return False
    return (run_dir / "artifacts" / "output_contract_freeze.json").exists()


def _append_retry_event(
    *,
    logs_dir: Path,
    run_dir: Path,
    request: dict[str, Any],
    phase: str,
    attempt: int,
    next_attempt: int,
    max_attempts: int,
    reason: str,
    delay_sec: float,
    stdout_log: Path,
    stderr_log: Path,
) -> None:
    path = logs_dir / "agent_retry.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "event": "agent_retry_scheduled",
        "role": str(request.get("role", "")),
        "action": str(request.get("action", "")),
        "phase": phase,
        "attempt": attempt,
        "next_attempt": next_attempt,
        "max_attempts": max_attempts,
        "reason": reason,
        "delay_sec": delay_sec,
        "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
        "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _run_text_with_retry(
    *,
    cmd: str,
    repo_root: Path,
    run_dir: Path,
    logs_dir: Path,
    request: dict[str, Any],
    phase: str,
    prompt_text: str,
    api_call_env: dict[str, str],
    run_command: Callable[..., subprocess.CompletedProcess[str]],
    write_text: Callable[[Path, str], None],
    agent_retry_policy: Callable[[dict[str, Any]], tuple[int, float]],
    is_transient_transport_error: Callable[..., bool],
) -> tuple[subprocess.CompletedProcess[str], list[dict[str, Any]], Path, Path]:
    max_attempts, base_delay = agent_retry_policy(request)
    retry_errors: list[dict[str, Any]] = []
    phase_stdout = logs_dir / f"{phase}.stdout"
    phase_stderr = logs_dir / f"{phase}.stderr"
    proc: subprocess.CompletedProcess[str] | None = None
    for attempt in range(1, max_attempts + 1):
        proc = run_command(cmd, cwd=repo_root, stdin_text=prompt_text, extra_env=api_call_env)
        attempt_stdout = logs_dir / f"{phase}.attempt_{attempt:02d}.stdout"
        attempt_stderr = logs_dir / f"{phase}.attempt_{attempt:02d}.stderr"
        write_text(attempt_stdout, proc.stdout)
        write_text(attempt_stderr, proc.stderr)
        write_text(phase_stdout, proc.stdout)
        write_text(phase_stderr, proc.stderr)
        if proc.returncode == 0 and str(proc.stdout or "").strip():
            return proc, retry_errors, phase_stdout, phase_stderr
        transient = is_transient_transport_error(proc.stdout, proc.stderr)
        if attempt >= max_attempts or not transient:
            break
        reason = "transient_transport_error"
        if proc.returncode == 0 and not str(proc.stdout or "").strip():
            reason = "transient_transport_error_after_empty_payload"
        delay = min(120.0, base_delay * (2 ** (attempt - 1)))
        retry_errors.append(
            {
                "attempt": attempt,
                "phase": phase,
                "rc": proc.returncode,
                "reason": reason,
                "stderr_tail": str(proc.stderr or "")[-1000:],
            }
        )
        _append_retry_event(
            logs_dir=logs_dir,
            run_dir=run_dir,
            request=request,
            phase=phase,
            attempt=attempt,
            next_attempt=attempt + 1,
            max_attempts=max_attempts,
            reason=reason,
            delay_sec=delay,
            stdout_log=attempt_stdout,
            stderr_log=attempt_stderr,
        )
        if delay > 0:
            time.sleep(delay)
    if proc is None:
        proc = subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="agent command was not executed")
        write_text(phase_stdout, proc.stdout)
        write_text(phase_stderr, proc.stderr)
    return proc, retry_errors, phase_stdout, phase_stderr


def _extract_json_dict(text: str) -> dict[str, Any] | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        doc = json.loads(raw)
        return doc if isinstance(doc, dict) else None
    except Exception:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        doc = json.loads(raw[start : end + 1])
    except Exception:
        return None
    return doc if isinstance(doc, dict) else None


def _manifest_paths(doc: dict[str, Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    candidates: list[Any] = []
    for key in ("files", "paths", "file_manifest", "source_files", "target_files"):
        value = doc.get(key)
        if isinstance(value, list):
            candidates.extend(value)
    manifest = doc.get("manifest")
    if isinstance(manifest, dict):
        for key in ("files", "paths", "source_files", "target_files"):
            value = manifest.get(key)
            if isinstance(value, list):
                candidates.extend(value)
    for item in candidates:
        path = str(item.get("path", "") if isinstance(item, dict) else item).strip().replace("\\", "/").lstrip("/")
        if path and path not in seen:
            seen.add(path)
            out.append(path)
    return out


def _interface_contract(doc: dict[str, Any]) -> dict[str, Any]:
    value = doc.get("interfaces")
    if isinstance(value, dict):
        return value
    value = doc.get("interface_contract")
    if isinstance(value, dict):
        return value
    manifest = doc.get("manifest")
    if isinstance(manifest, dict):
        value = manifest.get("interfaces")
        if isinstance(value, dict):
            return value
        value = manifest.get("interface_contract")
        if isinstance(value, dict):
            return value
    return {}


def _file_rows(doc: dict[str, Any], *, allowed_paths: set[str] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    candidates: list[Any] = []
    for key in ("files", "provider_source_files", "generated_files", "project_files"):
        value = doc.get(key)
        if isinstance(value, list):
            candidates.extend(value)
        elif isinstance(value, dict):
            candidates.extend({"path": k, "content": v} for k, v in value.items())
    bundle = doc.get("source_bundle")
    if isinstance(bundle, dict):
        value = bundle.get("files")
        if isinstance(value, list):
            candidates.extend(value)
        elif isinstance(value, dict):
            candidates.extend({"path": k, "content": v} for k, v in value.items())
    for item in candidates:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).strip().replace("\\", "/").lstrip("/")
        if not path or (allowed_paths is not None and path not in allowed_paths):
            continue
        row: dict[str, Any] = {"path": path}
        if isinstance(item.get("content_lines"), list):
            row["content_lines"] = [str(line) for line in item["content_lines"]]
        elif isinstance(item.get("content"), str):
            row["content"] = item["content"]
        else:
            continue
        rows.append(row)
    return rows


def _manifest_prompt(prompt_text: str) -> str:
    return "\n".join(
        [
            prompt_text.rstrip(),
            "",
            "## Chunked Source Generation Phase: Manifest Only",
            "Return one JSON object only.",
            "Do not include file content in this phase.",
            'Use schema: {"schema_version":"ctcp-provider-source-manifest-v1","files":[{"path":"project_output/<project_id>/README.md","purpose":"startup docs"}],"source_map":{"api_content_applied":true}}',
            "List the concrete files you will author for the existing output contract.",
            "Also include an `interfaces` object keyed by Python file path. For each Python file list `defines`, `imports`, and `exports` symbol names.",
            "The interface contract is binding for later file-content batches: imported symbols must be defined or re-exported exactly as named.",
        ]
    )


def _batch_prompt(prompt_text: str, paths: list[str], batch_index: int, batch_count: int, interfaces: dict[str, Any] | None = None) -> str:
    path_lines = "\n".join(f"- {path}" for path in paths)
    interface_rows = interfaces if isinstance(interfaces, dict) else {}
    interface_text = json.dumps(interface_rows, ensure_ascii=False, indent=2)
    if len(interface_text) > 12000:
        focused = {path: interface_rows.get(path) for path in paths if path in interface_rows}
        interface_text = json.dumps(focused, ensure_ascii=False, indent=2)
    return "\n".join(
        [
            prompt_text.rstrip(),
            "",
            f"## Chunked Source Generation Phase: File Content Batch {batch_index}/{batch_count}",
            "Return one JSON object only.",
            "Return content for exactly the requested paths below.",
            "Use schema_version `ctcp-provider-source-files-v1` and prefer `content_lines` arrays.",
            "Do not include Markdown fences or explanatory prose.",
            "Honor this global Python interface contract exactly. If this batch writes an imported/exported symbol, the file content must define or re-export that exact name.",
            interface_text if interface_rows else "{}",
            "Requested paths:",
            path_lines,
        ]
    )


def _merge_source_maps(docs: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "api_content_applied": True,
        "api_content_source_ref": "API:api_agent/source_generation/chunked",
    }
    for doc in docs:
        source_map = doc.get("source_map") if isinstance(doc.get("source_map"), dict) else {}
        for key, value in source_map.items():
            if key not in merged:
                merged[key] = value
    return merged


def _collect_file_rows_from_batches(
    *,
    cmd: str,
    repo_root: Path,
    run_dir: Path,
    logs_dir: Path,
    prompt_text: str,
    api_call_env: dict[str, str],
    hooks: Any,
    request: dict[str, Any],
    target_path: Path,
    target_rel: str,
    prompt_path: Path,
    manifest_doc: dict[str, Any],
    retry_errors: list[dict[str, Any]],
    fallback_target_result: Callable[..., dict[str, Any]],
    run_command: Callable[..., subprocess.CompletedProcess[str]],
    write_text: Callable[[Path, str], None],
    agent_retry_policy: Callable[[dict[str, Any]], tuple[int, float]],
    is_transient_transport_error: Callable[..., bool],
    safe_int_env: Callable[..., int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None]:
    source_docs = [manifest_doc]
    file_rows = _file_rows(manifest_doc)
    manifest_paths = _manifest_paths(manifest_doc)
    interfaces = _interface_contract(manifest_doc)
    if file_rows:
        return file_rows, source_docs, None
    batch_size = safe_int_env("CTCP_SOURCE_GENERATION_FILE_BATCH_SIZE", 3, minimum=1, maximum=12)
    batches = [manifest_paths[index : index + batch_size] for index in range(0, len(manifest_paths), batch_size)]
    for batch_index, batch_paths in enumerate(batches, start=1):
        batch_prompt = _batch_prompt(prompt_text, batch_paths, batch_index, len(batches), interfaces)
        batch_prompt_path = prompt_path.with_name(prompt_path.stem + f"_batch_{batch_index:02d}.md")
        write_text(batch_prompt_path, batch_prompt)
        batch_proc, batch_retry_errors, _stdout, _stderr = _run_text_with_retry(
            cmd=cmd,
            repo_root=repo_root,
            run_dir=run_dir,
            logs_dir=logs_dir,
            request=request,
            phase=f"agent.batch_{batch_index:02d}",
            prompt_text=batch_prompt,
            api_call_env=api_call_env,
            run_command=run_command,
            write_text=write_text,
            agent_retry_policy=agent_retry_policy,
            is_transient_transport_error=is_transient_transport_error,
        )
        retry_errors.extend(batch_retry_errors)
        if batch_proc.returncode != 0:
            result = fallback_target_result(
                hooks=hooks,
                repo_root=repo_root,
                run_dir=run_dir,
                request=request,
                target_path=target_path,
                target_rel=target_rel,
                prompt_path=batch_prompt_path,
                logs_dir=logs_dir,
                phase=f"agent.batch_{batch_index:02d}",
                reason=f"chunked source file batch command failed rc={batch_proc.returncode}",
            )
            if retry_errors:
                result["api_retry_errors"] = retry_errors
                result["api_retry_log"] = (logs_dir / "agent_retry.jsonl").relative_to(run_dir).as_posix()
            return [], source_docs, result
        batch_doc = _extract_json_dict(batch_proc.stdout)
        if batch_doc is None:
            return [], source_docs, fallback_target_result(
                hooks=hooks,
                repo_root=repo_root,
                run_dir=run_dir,
                request=request,
                target_path=target_path,
                target_rel=target_rel,
                prompt_path=batch_prompt_path,
                logs_dir=logs_dir,
                phase=f"agent.batch_{batch_index:02d}",
                reason="chunked source file batch output is not valid JSON object",
            )
        source_docs.append(batch_doc)
        file_rows.extend(_file_rows(batch_doc, allowed_paths=set(batch_paths)))
    return file_rows, source_docs, None


def _write_merged_target(
    *,
    hooks: Any,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    target_path: Path,
    target_rel: str,
    prompt_path: Path,
    manifest_prompt_path: Path,
    logs_dir: Path,
    manifest_stdout: Path,
    manifest_stderr: Path,
    file_rows: list[dict[str, Any]],
    source_docs: list[dict[str, Any]],
    manifest_paths: list[str],
    retry_errors: list[dict[str, Any]],
    fallback_target_result: Callable[..., dict[str, Any]],
    write_text: Callable[[Path, str], None],
) -> dict[str, Any]:
    merged_doc = {
        "schema_version": "ctcp-provider-source-files-v1",
        "files": file_rows,
        "source_map": _merge_source_maps(source_docs),
        "chunked_source_generation": {
            "enabled": True,
            "manifest_file_count": len(manifest_paths),
            "materialized_file_count": len(file_rows),
        },
    }
    interfaces = _interface_contract(source_docs[0]) if source_docs else {}
    if interfaces:
        merged_doc["interfaces"] = interfaces
    target_payload, norm_err = hooks.normalize_target_payload(
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
        raw_text=json.dumps(merged_doc, ensure_ascii=False),
    )
    if norm_err:
        result = fallback_target_result(
            hooks=hooks,
            repo_root=repo_root,
            run_dir=run_dir,
            request=request,
            target_path=target_path,
            target_rel=target_rel,
            prompt_path=manifest_prompt_path,
            logs_dir=logs_dir,
            phase="agent.manifest",
            reason=norm_err,
        )
        if retry_errors:
            result["api_retry_errors"] = retry_errors
            result["api_retry_log"] = (logs_dir / "agent_retry.jsonl").relative_to(run_dir).as_posix()
        return result
    write_text(target_path, target_payload)
    result = {
        "status": "executed",
        "target_path": target_rel,
        "prompt_path": prompt_path.relative_to(run_dir).as_posix(),
        "chunked_source_generation": True,
        "manifest_prompt_path": manifest_prompt_path.relative_to(run_dir).as_posix(),
        "manifest_stdout_log": manifest_stdout.relative_to(run_dir).as_posix(),
        "manifest_stderr_log": manifest_stderr.relative_to(run_dir).as_posix(),
        "materialized_file_count": len(file_rows),
    }
    if retry_errors:
        result["api_retry_errors"] = retry_errors
        result["api_retry_log"] = (logs_dir / "agent_retry.jsonl").relative_to(run_dir).as_posix()
    return result


def run_chunked_source_generation_phase(
    *,
    template: str,
    placeholders: dict[str, str],
    repo_root: Path,
    run_dir: Path,
    logs_dir: Path,
    prompt_text: str,
    api_call_env: dict[str, str],
    hooks: Any,
    request: dict[str, Any],
    target_path: Path,
    target_rel: str,
    prompt_path: Path,
    format_cmd_template: Callable[[str, dict[str, str]], tuple[str, str]],
    failure_result: Callable[..., dict[str, Any]],
    fallback_target_result: Callable[..., dict[str, Any]],
    run_command: Callable[..., subprocess.CompletedProcess[str]],
    write_text: Callable[[Path, str], None],
    agent_retry_policy: Callable[[dict[str, Any]], tuple[int, float]],
    is_transient_transport_error: Callable[..., bool],
    safe_int_env: Callable[..., int],
) -> dict[str, Any]:
    cmd, fmt_err = format_cmd_template(template, placeholders)
    if fmt_err:
        review = hooks.record_failure_review(run_dir, fmt_err)
        return failure_result(run_dir=run_dir, review_path=review, reason=fmt_err)
    manifest_prompt = _manifest_prompt(prompt_text)
    manifest_prompt_path = prompt_path.with_name(prompt_path.stem + "_manifest.md")
    write_text(manifest_prompt_path, manifest_prompt)
    manifest_proc, retry_errors, manifest_stdout, manifest_stderr = _run_text_with_retry(
        cmd=cmd,
        repo_root=repo_root,
        run_dir=run_dir,
        logs_dir=logs_dir,
        request=request,
        phase="agent.manifest",
        prompt_text=manifest_prompt,
        api_call_env=api_call_env,
        run_command=run_command,
        write_text=write_text,
        agent_retry_policy=agent_retry_policy,
        is_transient_transport_error=is_transient_transport_error,
    )
    if manifest_proc.returncode != 0:
        result = fallback_target_result(
            hooks=hooks,
            repo_root=repo_root,
            run_dir=run_dir,
            request=request,
            target_path=target_path,
            target_rel=target_rel,
            prompt_path=manifest_prompt_path,
            logs_dir=logs_dir,
            phase="agent.manifest",
            reason=f"chunked source manifest command failed rc={manifest_proc.returncode}",
        )
        if retry_errors:
            result["api_retry_errors"] = retry_errors
            result["api_retry_log"] = (logs_dir / "agent_retry.jsonl").relative_to(run_dir).as_posix()
        return result
    manifest_doc = _extract_json_dict(manifest_proc.stdout)
    if manifest_doc is None:
        return fallback_target_result(
            hooks=hooks,
            repo_root=repo_root,
            run_dir=run_dir,
            request=request,
            target_path=target_path,
            target_rel=target_rel,
            prompt_path=manifest_prompt_path,
            logs_dir=logs_dir,
            phase="agent.manifest",
            reason="chunked source manifest output is not valid JSON object",
        )
    file_rows, source_docs, failure = _collect_file_rows_from_batches(
        cmd=cmd,
        repo_root=repo_root,
        run_dir=run_dir,
        logs_dir=logs_dir,
        prompt_text=prompt_text,
        api_call_env=api_call_env,
        hooks=hooks,
        request=request,
        target_path=target_path,
        target_rel=target_rel,
        prompt_path=prompt_path,
        manifest_doc=manifest_doc,
        retry_errors=retry_errors,
        fallback_target_result=fallback_target_result,
        run_command=run_command,
        write_text=write_text,
        agent_retry_policy=agent_retry_policy,
        is_transient_transport_error=is_transient_transport_error,
        safe_int_env=safe_int_env,
    )
    if failure:
        return failure
    return _write_merged_target(
        hooks=hooks,
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
        target_path=target_path,
        target_rel=target_rel,
        prompt_path=prompt_path,
        manifest_prompt_path=manifest_prompt_path,
        logs_dir=logs_dir,
        manifest_stdout=manifest_stdout,
        manifest_stderr=manifest_stderr,
        file_rows=file_rows,
        source_docs=source_docs,
        manifest_paths=_manifest_paths(manifest_doc),
        retry_errors=retry_errors,
        fallback_target_result=fallback_target_result,
        write_text=write_text,
    )


__all__ = ["run_chunked_source_generation_phase", "should_chunk_source_generation"]
