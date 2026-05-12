from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _list_len(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def format_source_generation_progress(run_dir: Path) -> str | None:
    progress_path = run_dir / "artifacts" / "source_generation_state.json"
    final_report = run_dir / "artifacts" / "source_generation_report.json"
    if final_report.exists() or not progress_path.exists():
        return None
    try:
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(progress, dict) or str(progress.get("phase", "")) != "source_generation":
        return None
    return (
        "[ctcp_orchestrate] source_generation_progress="
        f"completed_batches={_list_len(progress.get('completed_batches'))}/"
        f"{int(progress.get('total_batches', 0) or 0)}, "
        f"generated_files={_list_len(progress.get('generated_files'))}, "
        f"materialized_files={_list_len(progress.get('materialized_files'))}, "
        f"remaining_batches={_list_len(progress.get('pending_batches'))}, "
        f"status={progress.get('status', '')}"
    )
