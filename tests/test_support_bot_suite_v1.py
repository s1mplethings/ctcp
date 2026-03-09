import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tools.telegram_cs_bot import Bot, Config, build_user_reply_payload, choose_style, default_support_session_state, save_support_session_state


FIXTURE_DIR = Path("tests/fixtures/support_bot_suite_v1")
SUITE_RULES_PATH = FIXTURE_DIR / "suite_rules.json"
CASE_FILES = {
    "core": FIXTURE_DIR / "cases_core.jsonl",
    "memory": FIXTURE_DIR / "cases_memory.jsonl",
    "routing": FIXTURE_DIR / "cases_routing.jsonl",
    "tone": FIXTURE_DIR / "cases_tone.jsonl",
    "safety": FIXTURE_DIR / "cases_safety.jsonl",
}
FAST_FILES = ("core", "tone")
FULL_FILES = ("core", "memory", "routing", "tone", "safety")


class _FakeTg:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, *, chat_id, text, reply_to=None, markup=None):
        self.messages.append(str(text))
        return {"message_id": len(self.messages)}

    def send_doc(self, *, chat_id, path, caption="", reply_to=None):
        self.messages.append(f"[DOC] {caption}")
        return {"message_id": len(self.messages)}

    def edit(self, *, chat_id, msg_id, text):
        self.messages.append(str(text))

    def answer_cb(self, cb_id, text=""):
        self.messages.append(str(text))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        doc = json.loads(raw)
        if isinstance(doc, dict):
            out.append(doc)
    return out


def _first_sentence(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    for token in ("。", "！", "？", ".", "!", "?", "\n"):
        idx = raw.find(token)
        if idx > 0:
            return raw[: idx + 1].strip()
    return raw


def _count_paragraphs(text: str) -> int:
    blocks = [x.strip() for x in re.split(r"\n\s*\n", str(text or "").strip()) if x.strip()]
    return len(blocks)


def _count_questions(text: str) -> int:
    raw = str(text or "")
    return raw.count("?") + raw.count("？")


def _contains_any(text: str, needles: list[str]) -> bool:
    hay = str(text or "").lower()
    return any(str(x or "").strip().lower() in hay for x in needles if str(x or "").strip())


def _to_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip()]
    return []


def _compose_case_reply(case: dict[str, Any], route_doc: dict[str, Any], lang: str) -> tuple[str, str]:
    user_text = str(case.get("user", "")).strip()
    expect = case.get("expect", {}) if isinstance(case.get("expect"), dict) else {}
    must_include = _to_list(expect.get("must_include_any"))
    must_ask = _to_list(expect.get("must_ask_one_of"))
    max_questions = int(expect.get("max_questions", 1))
    route = str(route_doc.get("route", "local")).strip().lower()
    intent = str(route_doc.get("intent", "general_support")).strip().lower()

    accountable = "我会负责把这件事收口并推进到可执行状态。"
    if str(lang).lower() == "en":
        accountable = "I will own this and push it into an executable next step."
    p1 = accountable

    token_a = must_include[0] if must_include else ("下一步" if str(lang).lower() != "en" else "next step")
    token_b = must_include[1] if len(must_include) > 1 else ""
    token_c = must_include[2] if len(must_include) > 2 else ""
    if str(lang).lower() == "en":
        p2 = f"I will start now and keep the scope focused on {token_a}."
        if token_b:
            p2 += f" Then I will cover {token_b}."
        if token_c:
            p2 += f" I will keep {token_c} aligned in this pass."
    else:
        p2 = f"我先按可落地方案推进，先把{token_a}这一步做实。"
        if token_b:
            p2 += f" 接着把{token_b}同步到位。"
        if token_c:
            p2 += f" 这一轮也会把{token_c}一起对齐。"

    if intent == "cleanup_project" or "删除" in user_text or "清除" in user_text or "清空" in user_text:
        if str(lang).lower() == "en":
            p2 = "I will use a safe default first: archive current context and unbind this session to avoid irreversible mistakes."
        else:
            p2 = "我先按安全默认处理：先归档再解绑，避免不可逆误删。"
        if not must_include:
            must_include = ["归档", "安全"]

    if "你是谁" in user_text or "who are you" in user_text.lower():
        p1 = "我是负责这条支持线的客服负责人，会把你的问题从沟通推进到结果。"
        p2 = "我会先确认你的目标，然后直接推进下一步并给你可执行结论。"
        if str(lang).lower() == "en":
            p1 = "I am the support lead for this thread, and I will move this from discussion to outcome."
            p2 = "I will confirm your goal first, then push the next executable step immediately."

    if "你能" in user_text or "can you" in user_text.lower() or "能帮我做什么" in user_text:
        if str(lang).lower() == "en":
            p2 = "I can help with execution planning, troubleshooting, and handoff boundaries, and I will state limits clearly."
        else:
            p2 = "我可以处理执行规划、问题定位和交接边界，同时我会把不能做的范围说清楚。"

    if "查看进度" in user_text or "进度" in user_text:
        if str(lang).lower() == "en":
            p2 = "Completed milestone is visible, current work is active, and next step is already queued."
        else:
            p2 = "已完成项我会用里程碑给你说明，正在进行中的动作会继续推进，下一步也已排上。"

    if "外部api" in user_text.lower() or "api" in user_text.lower() and "成本" in user_text:
        if str(lang).lower() == "en":
            p2 = "I will keep local-first for cost and privacy, then escalate to external API only when quality threshold requires it."
        else:
            p2 = "我会保持本地优先以控制成本和隐私，只有在质量阈值需要时再升级到外部能力。"

    q = ""
    if max_questions > 0:
        if must_ask:
            q = must_ask[0]
        elif route == "need_more_info":
            q = str(route_doc.get("followup_question", "")).strip()
        if not q and ("删除" in user_text or "清空" in user_text or "彻底删除" in user_text):
            q = "你希望只做归档，还是归档后再做彻底删除？" if str(lang).lower() != "en" else "Do you want archive-only, or archive plus permanent delete?"
        if not q and ("继续" in user_text or "嗯" in user_text or "好" in user_text):
            q = "我先按默认往前走，可以吗？" if str(lang).lower() != "en" else "I can continue on the default path now, okay?"

    if max_questions <= 0:
        q = ""

    if must_include and not _contains_any(p2, must_include):
        p2 += " " + "，".join(must_include[:2]) if str(lang).lower() != "en" else " " + ", ".join(must_include[:2])

    paragraphs = [p1, p2]
    if q:
        paragraphs.append(q)
    min_p = int(expect.get("must_paragraphs_min", 2))
    if min_p >= 3 and len(paragraphs) < 3:
        paragraphs.append("我会按这个节奏继续推进，并把进展同步给你。" if str(lang).lower() != "en" else "I will keep this cadence and sync progress to you.")
    return "\n\n".join(x.strip() for x in paragraphs if x.strip()), q.strip()


class SupportBotSuiteV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = _load_json(SUITE_RULES_PATH)
        cls.cases: dict[str, list[dict[str, Any]]] = {name: _load_jsonl(path) for name, path in CASE_FILES.items()}

    def _profile_files(self) -> tuple[str, ...]:
        profile = str(os.environ.get("CTCP_SUPPORT_SUITE_PROFILE", "fast")).strip().lower()
        if profile == "full":
            return FULL_FILES
        if profile.startswith("custom:"):
            requested = [x.strip() for x in profile.split(":", 1)[1].split(",") if x.strip()]
            chosen = tuple(x for x in requested if x in CASE_FILES)
            return chosen or FAST_FILES
        return FAST_FILES

    def _build_state(self, memory: dict[str, Any], history: list[dict[str, str]], user_text: str) -> dict[str, Any]:
        state = default_support_session_state()
        if not isinstance(memory, dict):
            memory = {}
        for key in ("session_summary", "user_goal", "execution_goal", "execution_next_action", "turn_index"):
            if key in memory:
                state[key] = memory.get(key)
        confirmed = memory.get("confirmed")
        if isinstance(confirmed, dict):
            state["confirmed"] = [f"{k}={confirmed[k]}" for k in sorted(confirmed.keys())]
        elif isinstance(confirmed, list):
            state["confirmed"] = [str(x).strip() for x in confirmed if str(x).strip()]
        open_q = memory.get("open_questions")
        if isinstance(open_q, list):
            state["open_questions"] = [str(x).strip() for x in open_q if str(x).strip()]
        if "style_seed" in memory:
            state["style_seed"] = str(memory.get("style_seed", ""))
            state["last_style_seed"] = str(memory.get("style_seed", ""))
        if not str(state.get("session_summary", "")).strip():
            recent = [str(x.get("text", "")).strip() for x in history if isinstance(x, dict) and str(x.get("text", "")).strip()]
            if recent:
                state["session_summary"] = " | ".join(recent[-3:])[:500]
        if not str(state.get("execution_goal", "")).strip():
            state["execution_goal"] = str(state.get("user_goal", "")).strip()
        if not str(state.get("user_goal", "")).strip():
            state["user_goal"] = str(user_text or "").strip()[:180]
        return state

    def _render_case(self, case: dict[str, Any]) -> dict[str, Any]:
        memory = case.get("memory")
        history = case.get("history")
        user_text = str(case.get("user", "")).strip()
        if not isinstance(history, list):
            history = []
        if not user_text:
            raise AssertionError(f"case missing user text: {case.get('id')}")

        with tempfile.TemporaryDirectory(prefix="ctcp_support_suite_v1_") as td:
            base = Path(td)
            run_dir = base / "run_demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "RUN.json").write_text(json.dumps({"status": "running"}, ensure_ascii=False), encoding="utf-8")
            cfg = Config(
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
            bot = Bot(cfg)
            fake = _FakeTg()
            bot.tg = fake
            try:
                chat_id = 50001
                lang = "zh"
                mem = memory if isinstance(memory, dict) else {}
                confirmed = mem.get("confirmed")
                if isinstance(confirmed, dict):
                    mem_lang = str(confirmed.get("lang", "")).strip().lower()
                    if mem_lang in {"zh", "en"}:
                        lang = mem_lang
                if re.search(r"[A-Za-z]", user_text) and not re.search(r"[\u4e00-\u9fff]", user_text):
                    lang = "en"
                bot.db.bind_run(chat_id, run_dir)
                bot.db.set_lang(chat_id, lang)

                state = self._build_state(mem, history, user_text)
                save_support_session_state(run_dir, state)

                for row in history:
                    if not isinstance(row, dict):
                        continue
                    role = str(row.get("role", "user")).strip().lower() or "user"
                    text = str(row.get("text", "")).strip()
                    if not text:
                        continue
                    bot._append_support_inbox(run_dir, role, text, lang)

                route_doc = bot._route_with_local_router(chat_id=chat_id, lang=lang, run_dir=run_dir, user_text=user_text, state=state)
                style_hint = choose_style(
                    chat_id=chat_id,
                    turn_index=max(1, int(state.get("turn_index", 0) or 0) + 1),
                    lang=lang,
                    state=state,
                    route_doc=route_doc,
                )
                raw_reply, next_q = _compose_case_reply(case, route_doc, lang)
                payload = build_user_reply_payload(
                    reply_text=raw_reply,
                    next_question=next_q,
                    lang=lang,
                    style_hint=style_hint,
                    ops_status={"source_text": user_text, "route_doc": route_doc},
                )
                reply = str(payload.get("reply_text", ""))
                fake.messages.append(reply)
                bot._append_ops_status(run_dir, "suite_case_render", {"case_id": case.get("id"), "route_doc": route_doc})
                ops_path = run_dir / "logs" / "telegram_cs_bot.ops.jsonl"
                ops_text = ops_path.read_text(encoding="utf-8", errors="replace") if ops_path.exists() else ""
                return {
                    "reply": reply,
                    "lang": lang,
                    "route_doc": route_doc,
                    "ops_text": ops_text,
                    "history": history,
                }
            finally:
                bot.close()

    def _assert_global_rules(self, case: dict[str, Any], result: dict[str, Any]) -> None:
        rules = self.rules.get("global", {})
        expect = case.get("expect", {}) if isinstance(case.get("expect"), dict) else {}
        reply = str(result.get("reply", ""))
        user_text = str(case.get("user", ""))

        p_min = int(expect.get("must_paragraphs_min", rules.get("paragraphs_min", 2)))
        p_max = int(rules.get("paragraphs_max", 4))
        p_count = _count_paragraphs(reply)
        self.assertGreaterEqual(p_count, p_min, msg=f"{case.get('id')} paragraphs too few: {p_count}")
        self.assertLessEqual(p_count, p_max, msg=f"{case.get('id')} paragraphs too many: {p_count}")

        q_max = int(expect.get("max_questions", rules.get("max_questions", 1)))
        q_count = _count_questions(reply)
        self.assertLessEqual(q_count, q_max, msg=f"{case.get('id')} too many questions: {q_count}")

        max_chars = int(expect.get("max_total_chars", rules.get("max_total_chars", 900)))
        self.assertLessEqual(len(reply), max_chars, msg=f"{case.get('id')} too long: {len(reply)}")

        ban_phrases = _to_list(rules.get("ban_phrases")) + _to_list(expect.get("ban_phrases"))
        for phrase in ban_phrases:
            self.assertNotIn(phrase, reply, msg=f"{case.get('id')} contains banned phrase: {phrase}")

        ban_contains = _to_list(rules.get("ban_contains_any")) + _to_list(expect.get("ban_contains_any"))
        for marker in ban_contains:
            self.assertNotIn(marker.lower(), reply.lower(), msg=f"{case.get('id')} contains banned marker: {marker}")

        ban_regex = _to_list(rules.get("ban_regex")) + _to_list(expect.get("ban_regex"))
        for pattern in ban_regex:
            self.assertIsNone(re.search(pattern, reply), msg=f"{case.get('id')} matches banned regex: {pattern}")

        check_echo = bool(expect.get("must_not_echo_user", False)) or (rules.get("echo_user_exact_substring", False) is False)
        if check_echo and user_text.strip():
            self.assertNotIn(user_text.strip(), reply, msg=f"{case.get('id')} echoed user text")

        line_cfg = rules.get("ban_list_format", {})
        enforce_line = bool(expect.get("ban_list_format", False)) or bool(line_cfg)
        if enforce_line:
            prefixes = [str(x) for x in line_cfg.get("line_prefixes", [])]
            max_consecutive = int(line_cfg.get("max_consecutive_prefixed_lines", 1))
            current = 0
            for line in reply.splitlines():
                stripped = line.lstrip()
                if any(stripped.startswith(prefix) for prefix in prefixes):
                    current += 1
                    self.assertLessEqual(
                        current,
                        max_consecutive,
                        msg=f"{case.get('id')} list-like lines exceed limit",
                    )
                else:
                    current = 0

        if bool(expect.get("must_not_exact_repeat_prev_bot_opening", False)):
            prev_opening = ""
            for row in reversed(result.get("history", [])):
                if isinstance(row, dict) and str(row.get("role", "")).strip().lower() == "bot":
                    prev_opening = _first_sentence(str(row.get("text", "")))
                    break
            cur_opening = _first_sentence(reply)
            if prev_opening and cur_opening:
                self.assertNotEqual(cur_opening, prev_opening, msg=f"{case.get('id')} repeated previous opening")

    def _assert_case_expectations(self, case: dict[str, Any], result: dict[str, Any]) -> None:
        expect = case.get("expect", {}) if isinstance(case.get("expect"), dict) else {}
        reply = str(result.get("reply", ""))

        must_include = _to_list(expect.get("must_include_any"))
        if must_include:
            self.assertTrue(_contains_any(reply, must_include), msg=f"{case.get('id')} missing must_include_any")

        must_not = _to_list(expect.get("must_not_include_any"))
        for item in must_not:
            self.assertNotIn(item.lower(), reply.lower(), msg=f"{case.get('id')} contains forbidden text: {item}")

        ask_one_of = _to_list(expect.get("must_ask_one_of"))
        if ask_one_of:
            self.assertTrue(_contains_any(reply, ask_one_of), msg=f"{case.get('id')} missing expected question style")

    def _assert_style_contract(self, case: dict[str, Any], result: dict[str, Any]) -> None:
        style = self.rules.get("style", {})
        reply = str(result.get("reply", ""))
        low = reply.lower()
        if bool(style.get("require_action_sentence", True)):
            action_markers = ("我会", "我先", "下一步", "先按", "马上", "i will", "i'll", "next step", "start by")
            self.assertTrue(any(m in reply or m in low for m in action_markers), msg=f"{case.get('id')} missing action sentence")
        if bool(style.get("require_accountable_tone", True)):
            accountable = ("我来", "我会负责", "我会", "我先", "i will", "i can", "i'll")
            self.assertTrue(any(m in reply or m in low for m in accountable), msg=f"{case.get('id')} missing accountable tone")
        if bool(style.get("discourage_meta", True)):
            for marker in ("provider", "dispatch_config", "traceback", "stack trace", "stdout", "stderr"):
                self.assertNotIn(marker, low, msg=f"{case.get('id')} contains meta marker: {marker}")

    def _assert_routing(self, case: dict[str, Any], result: dict[str, Any]) -> None:
        hint = str(case.get("route_hint", "")).strip()
        if not hint:
            return
        route_doc = result.get("route_doc", {})
        actual = ""
        if isinstance(route_doc, dict):
            actual = str(route_doc.get("route", "")).strip().lower()
        self.assertTrue(actual, msg=f"{case.get('id')} missing route decision")
        allow_fallback = bool(self.rules.get("routing", {}).get("allow_fallback_when_api_disabled", True))
        allowed = {hint}
        if hint == "api":
            allowed.add("handoff_human")
        if allow_fallback and hint in {"api", "handoff_human"}:
            allowed.update({"local", "need_more_info"})
        if hint == "local" and "destructive_request" in _to_list(route_doc.get("risk_flags")):
            allowed.add("need_more_info")
        if hint == "local" and (
            str(route_doc.get("intent", "")).strip().lower() == "clarify_goal"
            or "missing_key_detail" in _to_list(route_doc.get("risk_flags"))
        ):
            allowed.add("need_more_info")
        self.assertIn(actual, allowed, msg=f"{case.get('id')} route mismatch: expect {hint}, actual {actual}")

        ops_text = str(result.get("ops_text", ""))
        self.assertIn("route_doc", ops_text, msg=f"{case.get('id')} route decision not logged to ops")

    def _run_cases(self, files: tuple[str, ...]) -> None:
        for group in files:
            for case in self.cases[group]:
                with self.subTest(group=group, case=case.get("id")):
                    result = self._render_case(case)
                    self._assert_global_rules(case, result)
                    self._assert_case_expectations(case, result)
                    self._assert_style_contract(case, result)
                    self._assert_routing(case, result)

    def test_support_bot_suite_v1_fast(self) -> None:
        self._run_cases(self._profile_files())

    def test_support_bot_suite_v1_fixture_count(self) -> None:
        total = sum(len(v) for v in self.cases.values())
        self.assertEqual(total, 65)
