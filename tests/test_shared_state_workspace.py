from __future__ import annotations

import tempfile
import unittest

from bridge.state_store import SharedStateStore
from frontend.response_composer import render_frontend_output


class SharedStateWorkspaceTests(unittest.TestCase):
    def test_user_message_event_rebuilds_current_snapshot(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_shared_state_msg_") as td:
            store = SharedStateStore(workspace_root=td)
            store.append_event(
                task_id="task-msg",
                event_type="user_message",
                source="frontend",
                payload={"text": "请继续推进任务", "current_task_goal": "推进共享状态接线"},
            )
            current = store.rebuild_current("task-msg")
            self.assertEqual(str(current.get("latest_user_message", "")), "请继续推进任务")
            self.assertEqual(str(current.get("current_task_goal", "")), "推进共享状态接线")

    def test_authoritative_stage_change_collapses_visible_state_without_overwriting_stage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_shared_state_stage_") as td:
            store = SharedStateStore(workspace_root=td)
            store.append_event(
                task_id="task-stage",
                event_type="authoritative_stage_changed",
                source="runtime",
                payload={"authoritative_stage": "EXECUTING", "execution_status": "running"},
            )
            current = store.rebuild_current("task-stage")
            self.assertEqual(str(current.get("authoritative_stage", "")), "EXECUTING")
            self.assertEqual(str(current.get("visible_state", "")), "EXECUTING")

            store.append_event(
                task_id="task-stage",
                event_type="authoritative_stage_changed",
                source="runtime",
                payload={"authoritative_stage": "WAITING_DECISION", "execution_status": "blocked"},
            )
            current = store.rebuild_current("task-stage")
            self.assertEqual(str(current.get("authoritative_stage", "")), "WAITING_DECISION")
            self.assertEqual(str(current.get("visible_state", "")), "WAITING_FOR_DECISION")

    def test_waiting_blocked_done_visible_states_export_to_render(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_shared_state_visible_") as td:
            store = SharedStateStore(workspace_root=td)
            tid = "task-visible"

            store.append_event(
                task_id=tid,
                event_type="authoritative_stage_changed",
                source="runtime",
                payload={"authoritative_stage": "WAITING_DECISION", "execution_status": "blocked"},
            )
            store.append_event(
                task_id=tid,
                event_type="blocker_changed",
                source="runtime",
                payload={"current_blocker": "等待用户拍板", "blocking_question": "这轮先保速度还是质量？"},
            )
            current = store.rebuild_current(tid)
            render = store.refresh_render(tid, source="runtime", emit_event=False)
            self.assertEqual(str(current.get("visible_state", "")), "WAITING_FOR_DECISION")
            self.assertEqual(str(render.get("visible_state", "")), "WAITING_FOR_DECISION")

            store.append_event(
                task_id=tid,
                event_type="authoritative_stage_changed",
                source="runtime",
                payload={"authoritative_stage": "BLOCKED", "execution_status": "blocked"},
            )
            current = store.rebuild_current(tid)
            render = store.refresh_render(tid, source="runtime", emit_event=False)
            self.assertEqual(str(current.get("visible_state", "")), "BLOCKED_NEEDS_INPUT")
            self.assertEqual(str(render.get("visible_state", "")), "BLOCKED_NEEDS_INPUT")

            store.append_event(
                task_id=tid,
                event_type="authoritative_stage_changed",
                source="runtime",
                payload={"authoritative_stage": "DONE", "execution_status": "completed"},
            )
            store.append_event(
                task_id=tid,
                event_type="verification_result_recorded",
                source="runtime",
                payload={"verify_result": "PASS", "proof_refs": ["run_id=task-visible"]},
            )
            current = store.rebuild_current(tid)
            render = store.refresh_render(tid, source="runtime", emit_event=False)
            self.assertEqual(str(current.get("visible_state", "")), "DONE")
            self.assertEqual(str(render.get("visible_state", "")), "DONE")

    def test_refresh_render_can_emit_runtime_render_event(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_shared_state_render_event_") as td:
            store = SharedStateStore(workspace_root=td)
            tid = "task-render-event"
            store.append_event(
                task_id=tid,
                event_type="authoritative_stage_changed",
                source="runtime",
                payload={"authoritative_stage": "EXECUTING", "execution_status": "running"},
            )
            store.rebuild_current(tid)

            render = store.refresh_render(tid, source="runtime", emit_event=True)
            events = store.read_events(tid)

            self.assertEqual(str(render.get("visible_state", "")), "EXECUTING")
            self.assertTrue(any(str(row.get("type", "")) == "render_state_refreshed" for row in events))
            render_rows = [row for row in events if str(row.get("type", "")) == "render_state_refreshed"]
            self.assertEqual(str(render_rows[-1].get("payload", {}).get("visible_state", "")), "EXECUTING")
            self.assertTrue(bool(str(render_rows[-1].get("payload", {}).get("ui_badge", ""))))

    def test_response_composer_can_render_from_shared_state_binding(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_shared_state_render_") as td:
            store = SharedStateStore(workspace_root=td)
            tid = "task-reply"
            store.append_event(
                task_id=tid,
                event_type="authoritative_stage_changed",
                source="runtime",
                payload={"authoritative_stage": "EXECUTING", "execution_status": "running"},
            )
            store.append_event(
                task_id=tid,
                event_type="runtime_progress_recorded",
                source="runtime",
                payload={
                    "current_task_goal": "把 shared state 接到前端回复",
                    "last_confirmed_items": ["事件流已写入", "current 快照已重建"],
                    "current_blocker": "none",
                    "next_action": "继续接入 render adapter",
                    "proof_refs": ["run_id=task-reply"],
                    "conversation_mode": "STATUS_QUERY",
                },
            )
            current = store.rebuild_current(tid)
            render = store.refresh_render(tid, source="runtime", emit_event=False)

            result = render_frontend_output(
                raw_backend_state={},
                task_summary="",
                raw_reply_text="",
                raw_next_question="",
                notes={
                    "lang": "zh",
                    "recent_user_messages": ["现在做到什么程度了"],
                    "latest_user_message": "现在做到什么程度了",
                    "shared_state_current": current,
                    "shared_state_render": render,
                },
            )
            state = dict(result.pipeline_state or {})
            self.assertTrue(bool(dict(state.get("conversation_context", {})).get("shared_state_consumed", False)))
            self.assertIn("我这边已经完成", result.reply_text)
            self.assertIn("继续接入 render adapter", result.reply_text)

    def test_ui_and_support_shell_cannot_write_authoritative_events(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_shared_state_readonly_") as td:
            store = SharedStateStore(workspace_root=td)
            with self.assertRaises(PermissionError):
                store.append_event(
                    task_id="task-readonly",
                    event_type="authoritative_stage_changed",
                    source="support_shell",
                    payload={"authoritative_stage": "DONE"},
                )

    def test_done_state_requires_proof_refs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_shared_state_done_gate_") as td:
            store = SharedStateStore(workspace_root=td)
            tid = "task-proof-gate"
            store.append_event(
                task_id=tid,
                event_type="authoritative_stage_changed",
                source="runtime",
                payload={"authoritative_stage": "DONE", "execution_status": "completed"},
            )
            store.append_event(
                task_id=tid,
                event_type="verification_result_recorded",
                source="runtime",
                payload={"verify_result": "PASS", "proof_refs": []},
            )
            current = store.rebuild_current(tid)
            self.assertNotEqual(str(current.get("visible_state", "")), "DONE")

            store.append_event(
                task_id=tid,
                event_type="verification_result_recorded",
                source="runtime",
                payload={"verify_result": "PASS", "proof_refs": ["run_id=task-proof-gate"]},
            )
            current = store.rebuild_current(tid)
            self.assertEqual(str(current.get("visible_state", "")), "DONE")

    def test_event_log_replay_rebuilds_current_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_shared_state_replay_") as td:
            store = SharedStateStore(workspace_root=td)
            tid = "task-replay"
            store.append_event(
                task_id=tid,
                event_type="user_message",
                source="frontend",
                payload={"text": "开始执行", "current_task_goal": "验证 replay"},
            )
            store.append_event(
                task_id=tid,
                event_type="authoritative_stage_changed",
                source="runtime",
                payload={"authoritative_stage": "EXECUTING", "execution_status": "running"},
            )
            store.append_event(
                task_id=tid,
                event_type="next_action_set",
                source="runtime",
                payload={"next_action": "继续推进测试"},
            )

            rebuilt = store.rebuild_current(tid)
            replayed = store.replay(tid)
            self.assertEqual(str(rebuilt.get("task_id", "")), str(replayed.get("task_id", "")))
            self.assertEqual(str(rebuilt.get("authoritative_stage", "")), str(replayed.get("authoritative_stage", "")))
            self.assertEqual(str(rebuilt.get("next_action", "")), str(replayed.get("next_action", "")))


if __name__ == "__main__":
    unittest.main()
