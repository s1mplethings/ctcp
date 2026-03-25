from __future__ import annotations

from typing import Any


class BridgeAdapter:
    """Thin adapter over existing bridge script to preserve runtime capability."""

    def __init__(self) -> None:
        from scripts import ctcp_front_bridge

        self._bridge = ctcp_front_bridge

    def new_run(self, *, goal: str, constraints: dict[str, Any], attachments: list[str]) -> dict[str, Any]:
        return self._bridge.ctcp_new_run(goal=goal, constraints=constraints, attachments=attachments)

    def advance(self, *, run_id: str, max_steps: int) -> dict[str, Any]:
        return self._bridge.ctcp_advance(run_id, max_steps=max_steps)

    def get_status(self, *, run_id: str) -> dict[str, Any]:
        return self._bridge.ctcp_get_status(run_id)

    def list_decisions(self, *, run_id: str) -> dict[str, Any]:
        return self._bridge.ctcp_list_decisions_needed(run_id)

    def submit_decision(self, *, run_id: str, decision: dict[str, Any]) -> dict[str, Any]:
        return self._bridge.ctcp_submit_decision(run_id, decision)

    def get_last_report(self, *, run_id: str) -> dict[str, Any]:
        return self._bridge.ctcp_get_last_report(run_id)


class JobRunner:
    def __init__(self, bridge: BridgeAdapter | None = None) -> None:
        self.bridge = bridge or BridgeAdapter()

    def create_run(self, *, goal: str, constraints: dict[str, Any], attachments: list[str]) -> dict[str, Any]:
        return self.bridge.new_run(goal=goal, constraints=constraints, attachments=attachments)

    def advance(self, *, run_id: str, max_steps: int) -> dict[str, Any]:
        return self.bridge.advance(run_id=run_id, max_steps=max_steps)

    def status(self, *, run_id: str) -> dict[str, Any]:
        return self.bridge.get_status(run_id=run_id)

    def decisions(self, *, run_id: str) -> dict[str, Any]:
        return self.bridge.list_decisions(run_id=run_id)

    def answer(self, *, run_id: str, decision: dict[str, Any]) -> dict[str, Any]:
        return self.bridge.submit_decision(run_id=run_id, decision=decision)

    def report(self, *, run_id: str) -> dict[str, Any]:
        return self.bridge.get_last_report(run_id=run_id)
