from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.support_reply_policy import (
    default_reply_dedupe_memory,
    enforce_reply_policy,
    infer_reply_intent,
)


def _project_context(
    *,
    visible_state: str = "EXECUTING",
    progress_summary: str = "",
    decision_question: str = "",
    run_status: str = "running",
    error: bool = False,
    error_message: str = "",
    artifacts: list[str] | None = None,
    blocker: str = "",
    next_action: str = "",
) -> dict[str, object]:
    decision_cards = []
    if decision_question:
        decision_cards = [{"decision_id": "d-1", "question": decision_question, "status": "pending"}]
    out_artifacts = [{"path": item} for item in (artifacts or [])]
    return {
        "status": {"run_status": run_status, "verify_result": "", "gate": {"state": "open", "owner": "", "reason": ""}},
        "render_snapshot": {
            "visible_state": visible_state,
            "progress_summary": progress_summary,
            "decision_cards": decision_cards,
        },
        "runtime_state": {
            "run_status": run_status,
            "blocking_reason": blocker,
            "next_action": next_action,
            "error": {"has_error": error, "message": error_message or ("traceback details" if error else "")},
        },
        "current_snapshot": {
            "authoritative_stage": "WAIT_USER_DECISION" if visible_state == "WAITING_FOR_DECISION" else "EXECUTE",
            "current_blocker": blocker,
            "next_action": next_action,
        },
        "result_event": {"status": "done"} if visible_state == "DONE" else {},
        "artifact_manifest": {"artifacts": [{"path": item} for item in (artifacts or [])]} if artifacts else {},
        "output_artifacts": {"artifacts": out_artifacts} if artifacts else {"artifacts": []},
    }


class SupportReplyPolicyRegressionTests(unittest.TestCase):
    def test_natural_reply_policy_test(self) -> None:
        running_ctx = _project_context(visible_state="EXECUTING", progress_summary="正在整理需求拆分")
        decision_ctx = _project_context(visible_state="WAITING_FOR_DECISION", decision_question="先保速度还是先保质量？")
        done_ctx = _project_context(visible_state="DONE", artifacts=["artifacts/final_package.zip"])
        self.assertEqual(infer_reply_intent(conversation_mode="STATUS_QUERY", project_context=running_ctx), "progress_update")
        self.assertEqual(infer_reply_intent(conversation_mode="PROJECT_DETAIL", project_context=decision_ctx), "ask_decision")
        self.assertEqual(infer_reply_intent(conversation_mode="STATUS_QUERY", project_context=done_ctx), "deliver_result")

    def test_template_id_dedupe_test(self) -> None:
        mem = default_reply_dedupe_memory()
        ctx = _project_context(visible_state="EXECUTING", progress_summary="编排目录结构")
        first = enforce_reply_policy(
            reply_text="我这边正在继续处理",
            next_question="",
            conversation_mode="STATUS_QUERY",
            lang_hint="zh",
            project_context=ctx,
            provider_status="executed",
            reply_memory=mem,
            allow_suppress=False,
            source_kind="provider",
            provider_mode="fake",
        )
        second = enforce_reply_policy(
            reply_text="我先继续往下推进",
            next_question="",
            conversation_mode="STATUS_QUERY",
            lang_hint="zh",
            project_context=ctx,
            provider_status="executed",
            reply_memory=first["reply_memory"],
            allow_suppress=False,
            source_kind="provider",
            provider_mode="real",
        )
        self.assertEqual(str(first["template_id"]), str(second["template_id"]))
        self.assertIn(str(second["dedupe_action"]), {"downgrade", "suppress"})

    def test_semantic_progress_dedupe_test(self) -> None:
        mem = default_reply_dedupe_memory()
        ctx = _project_context(visible_state="EXECUTING", progress_summary="生成第一轮文档草案")
        first = enforce_reply_policy(
            reply_text="当前还在处理中，我继续跟进",
            next_question="",
            conversation_mode="STATUS_QUERY",
            lang_hint="zh",
            project_context=ctx,
            provider_status="executed",
            reply_memory=mem,
            allow_suppress=True,
            source_kind="proactive",
            provider_mode="stub",
        )
        second = enforce_reply_policy(
            reply_text="我这边正在继续处理",
            next_question="",
            conversation_mode="STATUS_QUERY",
            lang_hint="zh",
            project_context=ctx,
            provider_status="executed",
            reply_memory=first["reply_memory"],
            allow_suppress=True,
            source_kind="proactive",
            provider_mode="real",
        )
        self.assertIn(str(second.get("dedupe_action", "")), {"downgrade", "suppress"})
        self.assertTrue(bool(second.get("suppressed", False)))

    def test_per_intent_bucket_test(self) -> None:
        mem = default_reply_dedupe_memory()
        progress_ctx = _project_context(visible_state="EXECUTING", progress_summary="处理剧情分支")
        progress = enforce_reply_policy(
            reply_text="我在推进中",
            next_question="",
            conversation_mode="STATUS_QUERY",
            lang_hint="zh",
            project_context=progress_ctx,
            reply_memory=mem,
            provider_status="executed",
        )
        decision_ctx = _project_context(visible_state="WAITING_FOR_DECISION", decision_question="你要先看截图还是先拿 zip？")
        decision = enforce_reply_policy(
            reply_text="需要你确认",
            next_question="",
            conversation_mode="PROJECT_DETAIL",
            lang_hint="zh",
            project_context=decision_ctx,
            reply_memory=progress["reply_memory"],
            provider_status="executed",
        )
        self.assertEqual(str(progress["intent"]), "progress_update")
        self.assertEqual(str(decision["intent"]), "ask_decision")
        self.assertEqual(str(decision.get("dedupe_action", "send")), "send")

    def test_resend_downgrade_test(self) -> None:
        mem = default_reply_dedupe_memory()
        ctx = _project_context(visible_state="EXECUTING", progress_summary="整理项目结构")
        first = enforce_reply_policy(
            reply_text="我这边正在继续处理这一步，有变化会第一时间同步",
            next_question="",
            conversation_mode="STATUS_QUERY",
            lang_hint="zh",
            project_context=ctx,
            reply_memory=mem,
            provider_status="executed",
            allow_suppress=False,
        )
        second = enforce_reply_policy(
            reply_text="当前还在处理中，我继续往下推进",
            next_question="",
            conversation_mode="STATUS_QUERY",
            lang_hint="zh",
            project_context=ctx,
            reply_memory=first["reply_memory"],
            provider_status="executed",
            allow_suppress=False,
            previous_reply_text=str(first["reply_text"]),
        )
        self.assertEqual(str(second.get("dedupe_action", "")), "downgrade")
        self.assertNotEqual(str(first["reply_text"]), str(second["reply_text"]))
        self.assertIn("暂无", str(second["reply_text"]))

    def test_decision_question_not_over_deduped_test(self) -> None:
        mem = default_reply_dedupe_memory()
        ctx_a = _project_context(visible_state="WAITING_FOR_DECISION", decision_question="先保速度还是先保质量？")
        turn_a1 = enforce_reply_policy(
            reply_text="你看下",
            next_question="",
            conversation_mode="PROJECT_DETAIL",
            lang_hint="zh",
            project_context=ctx_a,
            reply_memory=mem,
            allow_suppress=True,
            source_kind="proactive",
            provider_status="executed",
        )
        turn_a2 = enforce_reply_policy(
            reply_text="需要你确认",
            next_question="",
            conversation_mode="PROJECT_DETAIL",
            lang_hint="zh",
            project_context=ctx_a,
            reply_memory=turn_a1["reply_memory"],
            allow_suppress=True,
            source_kind="proactive",
            provider_status="executed",
        )
        ctx_b = _project_context(visible_state="WAITING_FOR_DECISION", decision_question="先做世界观还是先写角色设定？")
        turn_b = enforce_reply_policy(
            reply_text="这一步请拍板",
            next_question="",
            conversation_mode="PROJECT_DETAIL",
            lang_hint="zh",
            project_context=ctx_b,
            reply_memory=turn_a2["reply_memory"],
            allow_suppress=True,
            source_kind="proactive",
            provider_status="executed",
        )
        self.assertTrue(bool(turn_a2.get("suppressed", False)))
        self.assertFalse(bool(turn_b.get("suppressed", False)))
        self.assertTrue(bool(str(turn_b.get("next_question", "")).strip()) or ("拍板" in str(turn_b["reply_text"])))

    def test_error_recovery_contextual_dedupe_test(self) -> None:
        mem = default_reply_dedupe_memory()
        err1 = _project_context(visible_state="ERROR", run_status="failed", error=True, error_message="network timeout")
        turn1 = enforce_reply_policy(
            reply_text="Traceback: network timeout",
            next_question="",
            conversation_mode="STATUS_QUERY",
            lang_hint="zh",
            project_context=err1,
            reply_memory=mem,
            allow_suppress=True,
            source_kind="proactive",
            provider_status="exec_failed",
        )
        turn1_repeat = enforce_reply_policy(
            reply_text="stderr: network timeout again",
            next_question="",
            conversation_mode="STATUS_QUERY",
            lang_hint="zh",
            project_context=err1,
            reply_memory=turn1["reply_memory"],
            allow_suppress=True,
            source_kind="proactive",
            provider_status="exec_failed",
        )
        err2 = _project_context(visible_state="ERROR", run_status="failed", error=True, error_message="permission denied")
        turn2 = enforce_reply_policy(
            reply_text="exception: permission denied",
            next_question="",
            conversation_mode="STATUS_QUERY",
            lang_hint="zh",
            project_context=err2,
            reply_memory=turn1_repeat["reply_memory"],
            allow_suppress=True,
            source_kind="proactive",
            provider_status="exec_failed",
        )
        self.assertIn(str(turn1_repeat.get("dedupe_action", "")), {"downgrade", "suppress"})
        self.assertFalse(bool(turn2.get("suppressed", False)))

    def test_transcript_near_duplicate_regression_test(self) -> None:
        mem = default_reply_dedupe_memory()
        t1 = enforce_reply_policy(
            reply_text="我这边正在继续处理",
            next_question="",
            conversation_mode="STATUS_QUERY",
            lang_hint="zh",
            project_context=_project_context(visible_state="EXECUTING", progress_summary="解析输入素材"),
            provider_status="executed",
            reply_memory=mem,
            allow_suppress=False,
        )
        t2 = enforce_reply_policy(
            reply_text="当前还在处理中，我继续往下推进",
            next_question="",
            conversation_mode="STATUS_QUERY",
            lang_hint="zh",
            project_context=_project_context(visible_state="EXECUTING", progress_summary="解析输入素材"),
            provider_status="executed",
            reply_memory=t1["reply_memory"],
            allow_suppress=False,
            previous_reply_text=str(t1["reply_text"]),
        )
        t3 = enforce_reply_policy(
            reply_text="请确认",
            next_question="",
            conversation_mode="PROJECT_DETAIL",
            lang_hint="zh",
            project_context=_project_context(visible_state="WAITING_FOR_DECISION", decision_question="先做主线还是先做UI？"),
            provider_status="executed",
            reply_memory=t2["reply_memory"],
            allow_suppress=False,
        )
        t4 = enforce_reply_policy(
            reply_text="完成了",
            next_question="",
            conversation_mode="STATUS_QUERY",
            lang_hint="zh",
            project_context=_project_context(visible_state="DONE", run_status="completed", artifacts=["artifacts/result.zip"]),
            provider_status="executed",
            reply_memory=t3["reply_memory"],
            allow_suppress=False,
        )
        self.assertIn(str(t2.get("dedupe_action", "")), {"downgrade", "suppress"})
        self.assertTrue(bool(str(t3.get("next_question", "")).strip()) or ("拍板" in str(t3["reply_text"])))
        self.assertIn("result.zip", str(t4["reply_text"]))

    def test_provider_mode_consistency_with_dedupe_test(self) -> None:
        mem = default_reply_dedupe_memory()
        ctx = _project_context(visible_state="EXECUTING", progress_summary="同步当前执行进度")
        docs = []
        for text, mode in (
            ("我这边正在继续处理", "fake"),
            ("当前还在处理中，我继续推进", "stub"),
            ("Quick progress sync: still working on this step.", "real"),
        ):
            out = enforce_reply_policy(
                reply_text=text,
                next_question="",
                conversation_mode="STATUS_QUERY",
                lang_hint="zh",
                project_context=ctx,
                provider_status="executed",
                provider_mode=mode,
                source_kind="provider",
                reply_memory=mem,
                allow_suppress=False,
            )
            mem = out["reply_memory"]
            docs.append(out)
        self.assertTrue(all(str(item["intent"]) == "progress_update" for item in docs))
        self.assertEqual(str(docs[0].get("dedupe_action", "")), "send")
        self.assertIn(str(docs[1].get("dedupe_action", "")), {"downgrade", "suppress"})
        self.assertIn(str(docs[2].get("dedupe_action", "")), {"downgrade", "suppress"})


if __name__ == "__main__":
    unittest.main()
