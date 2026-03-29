from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .event_append import build_event
from .render_adapter import build_render_state
from .snapshot_builder import rebuild_current_snapshot

ROOT = Path(__file__).resolve().parents[1]


def _default_workspace_root() -> Path:
    explicit = str(os.environ.get("CTCP_SHARED_STATE_ROOT", "")).strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    try:
        from tools.run_paths import get_repo_slug, get_runs_root

        return (get_runs_root() / get_repo_slug(ROOT) / "shared_state").resolve()
    except Exception:
        return (ROOT / "shared_state").resolve()


@dataclass(frozen=True)
class TaskPaths:
    task_id: str
    root: Path
    task_dir: Path
    events_path: Path
    current_path: Path
    render_path: Path
    locks_dir: Path


class SharedStateStore:
    def __init__(self, workspace_root: str | Path | None = None) -> None:
        base = Path(workspace_root).expanduser().resolve() if workspace_root else _default_workspace_root()
        self.workspace_root = base
        self.tasks_root = self.workspace_root / "tasks"
        self.tasks_root.mkdir(parents=True, exist_ok=True)

    def _task_paths(self, task_id: str) -> TaskPaths:
        tid = str(task_id or "").strip()
        if not tid:
            raise ValueError("task_id is required")
        task_dir = self.tasks_root / tid
        return TaskPaths(
            task_id=tid,
            root=self.workspace_root,
            task_dir=task_dir,
            events_path=task_dir / "events.jsonl",
            current_path=task_dir / "current.json",
            render_path=task_dir / "render.json",
            locks_dir=task_dir / "locks",
        )

    def ensure_task_layout(self, task_id: str) -> TaskPaths:
        paths = self._task_paths(task_id)
        paths.task_dir.mkdir(parents=True, exist_ok=True)
        paths.locks_dir.mkdir(parents=True, exist_ok=True)
        if not paths.events_path.exists():
            paths.events_path.touch()
        return paths

    def append_event(
        self,
        *,
        task_id: str,
        event_type: str,
        source: str,
        payload: Mapping[str, Any] | None = None,
        ts: str = "",
    ) -> dict[str, Any]:
        paths = self.ensure_task_layout(task_id)
        event = build_event(
            task_id=paths.task_id,
            event_type=event_type,
            source=source,
            payload=payload,
            ts=ts,
        )
        with paths.events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def read_events(self, task_id: str) -> list[dict[str, Any]]:
        paths = self.ensure_task_layout(task_id)
        out: list[dict[str, Any]] = []
        for raw in paths.events_path.read_text(encoding="utf-8", errors="replace").splitlines():
            row = str(raw or "").strip()
            if not row:
                continue
            try:
                doc = json.loads(row)
            except Exception:
                continue
            if isinstance(doc, dict):
                out.append(doc)
        return out

    def rebuild_current(self, task_id: str) -> dict[str, Any]:
        paths = self.ensure_task_layout(task_id)
        events = self.read_events(paths.task_id)
        current = rebuild_current_snapshot(task_id=paths.task_id, events=events)
        paths.current_path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return current

    def load_current(self, task_id: str) -> dict[str, Any]:
        paths = self.ensure_task_layout(task_id)
        if not paths.current_path.exists():
            return {}
        try:
            doc = json.loads(paths.current_path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return {}
        return doc if isinstance(doc, dict) else {}

    def refresh_render(self, task_id: str, *, source: str = "runtime", emit_event: bool = True) -> dict[str, Any]:
        paths = self.ensure_task_layout(task_id)
        current = self.load_current(paths.task_id)
        if not current:
            current = self.rebuild_current(paths.task_id)
        render = build_render_state(current)
        paths.render_path.write_text(json.dumps(render, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if emit_event:
            self.append_event(
                task_id=paths.task_id,
                event_type="render_state_refreshed",
                source=source,
                payload={"visible_state": str(render.get("visible_state", "")), "ui_badge": str(render.get("ui_badge", ""))},
            )
        return render

    def load_render(self, task_id: str) -> dict[str, Any]:
        paths = self.ensure_task_layout(task_id)
        if not paths.render_path.exists():
            return {}
        try:
            doc = json.loads(paths.render_path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return {}
        return doc if isinstance(doc, dict) else {}

    def append_and_refresh(
        self,
        *,
        task_id: str,
        event_type: str,
        source: str,
        payload: Mapping[str, Any] | None = None,
        ts: str = "",
    ) -> dict[str, Any]:
        self.append_event(task_id=task_id, event_type=event_type, source=source, payload=payload, ts=ts)
        current = self.rebuild_current(task_id)
        render = self.refresh_render(task_id, source="runtime", emit_event=True)
        return {"task_id": task_id, "current": current, "render": render}

    def replay(self, task_id: str) -> dict[str, Any]:
        return rebuild_current_snapshot(task_id=task_id, events=self.read_events(task_id))

