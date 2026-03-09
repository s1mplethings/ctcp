import json
import re
import tempfile
import unittest
from pathlib import Path

from tools.stylebank import choose_variants
from tools.telegram_cs_bot import Bot, Config, build_user_reply_payload, default_support_session_state


LIST_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+")


def _make_config(base: Path) -> Config:
    return Config(
        token="fake",
        allowlist=None,
        repo_root=Path("d:/.c_projects/adc/ctcp").resolve(),
        state_db=base / "state.sqlite3",
        poll_seconds=1,
        tick_seconds=1,
        auto_advance=False,
        api_enabled=False,
        api_model="gpt-4.1-mini",
        api_timeout_sec=10,
        note_ack_path=False,
        progress_push_enabled=False,
    )


class SupportRouterAndStyleBankTests(unittest.TestCase):
    def test_stylebank_is_deterministic_and_turn_sensitive(self) -> None:
        a = choose_variants(chat_id=42, intent="local", turn_index=3, style_seed="seed-a", lang="zh")
        b = choose_variants(chat_id=42, intent="local", turn_index=3, style_seed="seed-a", lang="zh")
        c = choose_variants(chat_id=42, intent="local", turn_index=4, style_seed="seed-a", lang="zh")
        self.assertEqual(a, b)
        self.assertNotEqual(a.get("seed"), c.get("seed"))

    def test_router_escalates_patch_like_intent_to_api(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_router_api_") as td:
            base = Path(td)
            run_dir = base / "run_demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "RUN.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")
            bot = Bot(_make_config(base))
            try:
                bot._load_support_dispatch_config = lambda _run_dir: (  # type: ignore[method-assign]
                    {
                        "schema_version": "ctcp-dispatch-config-v1",
                        "mode": "manual_outbox",
                        "role_providers": {"support_lead_router": "mock_agent"},
                    },
                    "ok",
                )
                bot._execute_support_provider = lambda **kwargs: {  # type: ignore[method-assign]
                    "status": "exec_failed",
                    "reason": "router unavailable in test",
                }
                state = default_support_session_state()
                decision = bot._route_with_local_router(
                    chat_id=1001,
                    lang="zh",
                    run_dir=run_dir,
                    user_text="请直接改代码并给我 patch，然后跑 verify",
                    state=state,
                )
                self.assertEqual(str(decision.get("route")), "api")
            finally:
                bot.close()

    def test_router_keeps_simple_support_message_local(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_router_local_") as td:
            base = Path(td)
            run_dir = base / "run_demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "RUN.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")
            bot = Bot(_make_config(base))
            try:
                bot._load_support_dispatch_config = lambda _run_dir: (  # type: ignore[method-assign]
                    {
                        "schema_version": "ctcp-dispatch-config-v1",
                        "mode": "manual_outbox",
                        "role_providers": {"support_lead_router": "mock_agent"},
                    },
                    "ok",
                )
                bot._execute_support_provider = lambda **kwargs: {  # type: ignore[method-assign]
                    "status": "exec_failed",
                    "reason": "router unavailable in test",
                }
                state = default_support_session_state()
                decision = bot._route_with_local_router(
                    chat_id=1002,
                    lang="zh",
                    run_dir=run_dir,
                    user_text="你好，我想了解一下套餐价格",
                    state=state,
                )
                self.assertEqual(str(decision.get("route")), "local")
            finally:
                bot.close()

    def test_user_reply_payload_stays_clean_and_paragraphed(self) -> None:
        payload = build_user_reply_payload(
            reply_text=(
                "TRACE: guardrails_written\n"
                "- 先确认范围\n"
                "- 再处理代码\n"
                "1. 最后回传 artifacts/support_reply.json\n"
                "我现在先推进第一步。"
            ),
            next_question="",
            lang="zh",
            ops_status={},
            style_hint={"closer": "为了不耽误进度，", "style_seed": "seed-x", "seed": "abc"},
        )
        reply = str(payload.get("reply_text", ""))
        low = reply.lower()
        for token in ("trace", "outbox", "run.json", "artifacts/", "logs/", "diff --git"):
            self.assertNotIn(token, low)
        for phrase in ("收到，了解你想咨询的是", "方便的话再补充一些细节", "为了不耽误进度", "我记得你在推进"):
            self.assertNotIn(phrase, reply)
        self.assertIn("\n\n", reply)
        list_like_rows = [ln for ln in reply.splitlines() if LIST_RE.match(ln)]
        self.assertFalse(list_like_rows, msg=reply)
        question_count = reply.count("?") + reply.count("？")
        self.assertIn(question_count, {0, 1})

    def test_no_forced_default_assumption_when_question_is_empty(self) -> None:
        payload_a = build_user_reply_payload(
            reply_text="我来处理这件事。",
            next_question="",
            lang="zh",
            ops_status={},
            style_hint={"style_seed": "seed-a", "seed": "a"},
        )
        payload_b = build_user_reply_payload(
            reply_text="我来处理这件事。",
            next_question="",
            lang="zh",
            ops_status={},
            style_hint={"style_seed": "seed-b", "seed": "b"},
        )
        text_a = str(payload_a.get("reply_text", ""))
        text_b = str(payload_b.get("reply_text", ""))
        self.assertEqual(text_a, "我来处理这件事。")
        self.assertEqual(text_b, "我来处理这件事。")


if __name__ == "__main__":
    unittest.main()
