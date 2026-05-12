from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tools.providers.project_generation_contracts import (
    load_generation_contract_context,
    write_generation_contract_artifacts,
)
from tools.providers.project_generation_model_budget import choose_model_tier


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


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json_dict(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _state_path(run_dir: Path) -> Path:
    return run_dir / "artifacts" / "source_generation_state.json"


def _partial_report_path(run_dir: Path) -> Path:
    return run_dir / "artifacts" / "source_generation_partial_report.json"


def _manifest_checkpoint_path(run_dir: Path) -> Path:
    return run_dir / "artifacts" / "source_generation_manifest.json"


def _batches_dir(run_dir: Path) -> Path:
    return run_dir / "artifacts" / "source_generation_batches"


def _batch_checkpoint_path(run_dir: Path, batch_index: int) -> Path:
    return _batches_dir(run_dir) / f"batch_{batch_index:03d}.json"


def _content_from_row(row: dict[str, Any]) -> str:
    if isinstance(row.get("content"), str):
        return str(row["content"])
    content_lines = row.get("content_lines")
    if isinstance(content_lines, list):
        lines = [str(line) for line in content_lines]
        return "\n".join(lines) + ("\n" if lines else "")
    return ""


def _materialize_incremental_file_rows(*, run_dir: Path, rows: list[dict[str, Any]]) -> list[str]:
    written: list[str] = []
    root = run_dir.resolve()
    for row in rows:
        rel = str(row.get("path", "")).strip().replace("\\", "/").lstrip("/")
        content = _content_from_row(row)
        if not rel or not content:
            continue
        target = (run_dir / rel).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            continue
        if target.exists():
            written.append(rel)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", errors="replace")
        written.append(rel)
    return written


def _refresh_generation_contracts(run_dir: Path) -> None:
    try:
        write_generation_contract_artifacts(run_dir, repair=False)
    except Exception:
        return


def _completed_batch_indexes(run_dir: Path) -> set[int]:
    completed: set[int] = set()
    for path in sorted(_batches_dir(run_dir).glob("batch_*.json")):
        doc = _read_json_dict(path)
        if str(doc.get("status", "")).strip().lower() != "completed":
            continue
        try:
            index = int(doc.get("batch_index", 0))
        except Exception:
            continue
        if index > 0:
            completed.add(index)
    return completed


def _completed_batch_docs(run_dir: Path, batches: list[list[str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    source_docs: list[dict[str, Any]] = []
    file_rows: list[dict[str, Any]] = []
    materialized: list[str] = []
    for batch_index, batch_paths in enumerate(batches, start=1):
        checkpoint = _read_json_dict(_batch_checkpoint_path(run_dir, batch_index))
        if str(checkpoint.get("status", "")).strip().lower() != "completed":
            continue
        provider_response = checkpoint.get("provider_response")
        if not isinstance(provider_response, dict):
            continue
        rows = _file_rows(provider_response, allowed_paths=set(batch_paths))
        source_docs.append(provider_response)
        file_rows.extend(rows)
        written = _materialize_incremental_file_rows(run_dir=run_dir, rows=rows)
        if written:
            _refresh_generation_contracts(run_dir)
        materialized.extend(written)
        checkpoint["materialized"] = True
        checkpoint["materialized_files"] = sorted(set(list(checkpoint.get("materialized_files", [])) + written))
        checkpoint["updated_at"] = _utc_now()
        _write_json(_batch_checkpoint_path(run_dir, batch_index), checkpoint)
    return file_rows, source_docs, sorted(set(materialized))


def _load_or_create_batch_plan(*, run_dir: Path, manifest_paths: list[str], safe_int_env: Callable[..., int]) -> tuple[int, list[list[str]]]:
    state = _read_json_dict(_state_path(run_dir))
    existing_batches = state.get("batches")
    if isinstance(existing_batches, list) and existing_batches:
        batches = [[str(item).strip() for item in row if str(item).strip()] for row in existing_batches if isinstance(row, list)]
        if batches:
            batch_size = int(state.get("batch_size", 0) or len(batches[0]))
            return max(batch_size, 1), batches
    batch_size = safe_int_env("CTCP_SOURCE_GENERATION_FILE_BATCH_SIZE", 3, minimum=1, maximum=12)
    batches = [manifest_paths[index : index + batch_size] for index in range(0, len(manifest_paths), batch_size)]
    return batch_size, batches


def _write_progress_state(
    *,
    run_dir: Path,
    batches: list[list[str]],
    batch_size: int,
    materialized_files: list[str],
    status: str,
) -> None:
    completed = sorted(_completed_batch_indexes(run_dir))
    total = len(batches)
    pending = [index for index in range(1, total + 1) if index not in set(completed)]
    generated_files: list[str] = []
    for index in completed:
        doc = _read_json_dict(_batch_checkpoint_path(run_dir, index))
        for row in doc.get("generated_files", []):
            value = str(row).strip().replace("\\", "/")
            if value:
                generated_files.append(value)
    materialized = sorted(set([str(row).strip().replace("\\", "/") for row in materialized_files if str(row).strip()]))
    state = {
        "schema_version": "ctcp-source-generation-state-v1",
        "phase": "source_generation",
        "batch_size": batch_size,
        "total_batches": total,
        "completed_batches": completed,
        "pending_batches": pending,
        "batches": batches,
        "generated_files": sorted(set(generated_files)),
        "materialized_files": materialized,
        "remaining_batches": len(pending),
        "status": status,
        "updated_at": _utc_now(),
    }
    _write_json(_state_path(run_dir), state)
    if completed:
        project_output_exists = (run_dir / "project_output").exists()
        partial = {
            "schema_version": "ctcp-source-generation-partial-report-v1",
            "status": "partial" if status != "completed" else "completed",
            "phase": "source_generation",
            "completed_batches": completed,
            "completed_batch_count": len(completed),
            "total_batches": total,
            "pending_batches": pending,
            "generated_files": sorted(set(generated_files)),
            "materialized_files": materialized,
            "project_output_exists": project_output_exists,
            "updated_at": state["updated_at"],
        }
        _write_json(_partial_report_path(run_dir), partial)


def _write_batch_checkpoint(
    *,
    run_dir: Path,
    batch_index: int,
    batch_paths: list[str],
    batch_doc: dict[str, Any],
    file_rows: list[dict[str, Any]],
    materialized_files: list[str],
) -> None:
    checkpoint = {
        "schema_version": "ctcp-source-generation-batch-v1",
        "batch_index": batch_index,
        "status": "completed",
        "requested_paths": list(batch_paths),
        "generated_files": [str(row.get("path", "")).strip().replace("\\", "/") for row in file_rows if str(row.get("path", "")).strip()],
        "provider_response": batch_doc,
        "timestamp": _utc_now(),
        "materialized": bool(materialized_files),
        "materialized_files": materialized_files,
    }
    _write_json(_batch_checkpoint_path(run_dir, batch_index), checkpoint)


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


def _model_budget_prompt_row(choice: dict[str, Any]) -> str:
    return json.dumps(
        {
            "stage": choice.get("stage", ""),
            "tier": choice.get("tier", ""),
            "reason": choice.get("reason", ""),
            "path": choice.get("path", ""),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _manifest_prompt(prompt_text: str) -> str:
    budget_choice = choose_model_tier(stage="file_manifest")
    return "\n".join(
        [
            prompt_text.rstrip(),
            "",
            "## Chunked Source Generation Phase: Manifest Only",
            "## Model Budget",
            _model_budget_prompt_row(budget_choice),
            "Return one JSON object only.",
            "Do not include file content in this phase.",
            'Use schema: {"schema_version":"ctcp-provider-source-manifest-v1","files":[{"path":"project_output/<project_id>/README.md","purpose":"startup docs"}],"source_map":{"api_content_applied":true}}',
            "List the concrete files you will author for the existing output contract.",
            "Also include an `interfaces` object keyed by Python file path. For each Python file list `defines`, `imports`, and `exports` symbol names.",
            "The interface contract is binding for later file-content batches: imported symbols must be defined or re-exported exactly as named.",
        ]
    )


def _batch_prompt(
    prompt_text: str,
    paths: list[str],
    batch_index: int,
    batch_count: int,
    interfaces: dict[str, Any] | None = None,
    model_budget_choice: dict[str, Any] | None = None,
    contract_context: str = "",
) -> str:
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
            "## Model Budget",
            _model_budget_prompt_row(model_budget_choice or choose_model_tier(stage="file_author")),
            "Return one JSON object only.",
            "Return content for exactly the requested paths below.",
            "Use schema_version `ctcp-provider-source-files-v1` and prefer `content_lines` arrays.",
            "Do not include Markdown fences or explanatory prose.",
            "This is a single-file authoring task by default. Keep custom code thin and use mature libraries from the manifest/interface plan instead of hand-rolling framework behavior.",
            "Honor this global Python interface contract exactly. If this batch writes an imported/exported symbol, the file content must define or re-export that exact name.",
            interface_text if interface_rows else "{}",
            "## Current Shared Generation Contracts",
            contract_context.strip() if contract_context.strip() else "{}",
            "Use these shared contracts as the single source of truth for service methods, routes, runtime entrypoint, and supported CLI args. Do not call methods, routes, or CLI flags that are absent from these snapshots unless this batch also defines them.",
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
    model_budget_choices = [choose_model_tier(stage="file_manifest")]
    if file_rows:
        manifest_doc["model_budget_choices"] = model_budget_choices
        materialized = _materialize_incremental_file_rows(run_dir=run_dir, rows=file_rows)
        if materialized:
            _refresh_generation_contracts(run_dir)
        _write_progress_state(run_dir=run_dir, batches=[manifest_paths], batch_size=max(len(manifest_paths), 1), materialized_files=materialized, status="completed")
        return file_rows, source_docs, None
    batch_size, batches = _load_or_create_batch_plan(run_dir=run_dir, manifest_paths=manifest_paths, safe_int_env=safe_int_env)
    persisted_rows, persisted_docs, materialized_files = _completed_batch_docs(run_dir, batches)
    file_rows.extend(persisted_rows)
    source_docs.extend(persisted_docs)
    _write_progress_state(run_dir=run_dir, batches=batches, batch_size=batch_size, materialized_files=materialized_files, status="running")
    completed = _completed_batch_indexes(run_dir)
    max_batches_this_run = safe_int_env("CTCP_SOURCE_GENERATION_MAX_BATCHES_PER_RUN", 0, minimum=0, maximum=1000)
    processed_this_run = 0
    for batch_index, batch_paths in enumerate(batches, start=1):
        if batch_index in completed:
            continue
        batch_choice = choose_model_tier(
            stage="file_author",
            file_task={"path": batch_paths[0]} if len(batch_paths) == 1 else {"path": ",".join(batch_paths)},
        )
        model_budget_choices.append(batch_choice)
        contract_context = load_generation_contract_context(run_dir)
        batch_prompt = _batch_prompt(prompt_text, batch_paths, batch_index, len(batches), interfaces, batch_choice, contract_context)
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
        batch_rows = _file_rows(batch_doc, allowed_paths=set(batch_paths))
        batch_materialized = _materialize_incremental_file_rows(run_dir=run_dir, rows=batch_rows)
        if batch_materialized:
            _refresh_generation_contracts(run_dir)
        _write_batch_checkpoint(
            run_dir=run_dir,
            batch_index=batch_index,
            batch_paths=batch_paths,
            batch_doc=batch_doc,
            file_rows=batch_rows,
            materialized_files=batch_materialized,
        )
        source_docs.append(batch_doc)
        file_rows.extend(batch_rows)
        materialized_files.extend(batch_materialized)
        completed.add(batch_index)
        processed_this_run += 1
        _write_progress_state(run_dir=run_dir, batches=batches, batch_size=batch_size, materialized_files=materialized_files, status="running")
        if max_batches_this_run and processed_this_run >= max_batches_this_run and len(completed) < len(batches):
            manifest_doc["model_budget_choices"] = model_budget_choices
            return file_rows, source_docs, {
                "status": "executed",
                "partial_source_generation": True,
                "target_path": target_rel,
                "prompt_path": prompt_path.relative_to(run_dir).as_posix(),
                "completed_batches": sorted(completed),
                "total_batches": len(batches),
                "remaining_batches": len(batches) - len(completed),
                "state_path": _state_path(run_dir).relative_to(run_dir).as_posix(),
                "partial_report_path": _partial_report_path(run_dir).relative_to(run_dir).as_posix(),
            }
    manifest_doc["model_budget_choices"] = model_budget_choices
    _write_progress_state(run_dir=run_dir, batches=batches, batch_size=batch_size, materialized_files=materialized_files, status="completed")
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
    model_budget_choices = []
    for doc in source_docs:
        choices = doc.get("model_budget_choices") if isinstance(doc.get("model_budget_choices"), list) else []
        model_budget_choices.extend(dict(row) for row in choices if isinstance(row, dict))
    if model_budget_choices:
        merged_doc["model_budget"] = {
            "schema_version": "ctcp-model-budget-v1",
            "stage_choices": model_budget_choices,
        }
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
    if model_budget_choices:
        result["model_budget"] = {
            "schema_version": "ctcp-model-budget-v1",
            "stage_choices": model_budget_choices,
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
    manifest_checkpoint = _read_json_dict(_manifest_checkpoint_path(run_dir))
    manifest_doc = manifest_checkpoint.get("provider_response") if isinstance(manifest_checkpoint.get("provider_response"), dict) else None
    retry_errors: list[dict[str, Any]] = []
    manifest_stdout = logs_dir / "agent.manifest.stdout"
    manifest_stderr = logs_dir / "agent.manifest.stderr"
    if manifest_doc is None:
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
        _write_json(
            _manifest_checkpoint_path(run_dir),
            {
                "schema_version": "ctcp-source-generation-manifest-checkpoint-v1",
                "status": "completed",
                "provider_response": manifest_doc,
                "manifest_paths": _manifest_paths(manifest_doc),
                "timestamp": _utc_now(),
            },
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
