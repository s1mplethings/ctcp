#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import reference_export
from tools.run_paths import get_repo_slug, get_runs_root

try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"[ctcp_persona_lab] PyYAML is required: {exc}") from exc

PERSONA_LAB_DIR = ROOT / "persona_lab"
CASES_DIR = PERSONA_LAB_DIR / "cases"
RUBRICS_DIR = PERSONA_LAB_DIR / "rubrics"
VERSION_FILE = ROOT / "VERSION"

RUN_MANIFEST_SCHEMA = "ctcp-persona-lab-run-v1"
TRANSCRIPT_SCHEMA = "ctcp-persona-lab-transcript-v1"
SCORE_SCHEMA = "ctcp-persona-lab-score-v1"

GREETINGS = (
    "你好",
    "您好",
    "你好呀",
    "很高兴为您服务",
    "收到",
    "抱歉",
    "为了更好地帮助您",
    "hello",
    "hi",
    "hey",
    "我在",
    "好的",
    "明白了",
    "稍等",
)
TEMPLATE_SUPPORT_PHRASES = (
    "为了更好地帮助您",
    "请问还有什么可以帮您",
    "收到，我先帮你整理一下",
    "很高兴为您服务",
    "我会尽快处理",
    "感谢您的反馈",
    "thanks for reaching out",
    "happy to help",
    "glad to assist",
    "please let me know",
    "i'm here to help",
    "我在",
    "好的",
    "明白了",
    "稍等",
)
JUDGMENT_MARKERS = (
    "问题是",
    "当前问题",
    "现在的问题",
    "核心问题",
    "判断是",
    "当前判断",
    "结论是",
    "结论:",
    "判断:",
    "风险是",
    "缺口是",
    "已足够明确",
    "任务已经明确",
    "不需要再澄清",
    "the problem is",
    "the issue is",
    "my judgment",
    "judgment:",
    "the task is clear",
    "the task is already clear",
    "current problem:",
    "problem:",
)
ACTION_MARKERS = (
    "下一步",
    "我先",
    "先做",
    "先列",
    "接下来",
    "下一步我",
    "先把",
    "现在先",
    "next action",
    "next step",
    "i will",
    "i'll",
    "start by",
    "first step",
    "next move",
)
BLOCKER_MARKERS = (
    "阻塞",
    "缺口",
    "缺少",
    "还缺",
    "需要你补",
    "需要补充",
    "需要一个",
    "需要提供",
    "blocker",
    "missing",
    "need one detail",
    "one missing input",
    "without",
)
RECEPTIONIST_MARKERS = (
    "抱歉",
    "不好意思",
    "感谢您的反馈",
    "为您",
    "我来帮你",
    "很高兴为您服务",
    "请问",
    "please let me know",
    "happy to help",
    "glad to assist",
    "i'm here to help",
    "thanks for reaching out",
)
STATUS_MARKERS = (
    "当前",
    "现在",
    "阶段",
    "状态",
    "进展",
    "判断",
    "结论",
    "问题是",
    "已完成",
    "当前阻塞",
    "卡在",
    "running",
    "blocked",
    "completed",
    "done",
)
LOW_INFO_ACKS = (
    "我在",
    "好的",
    "明白了",
    "稍等",
    "收到",
    "继续处理中",
    "got it",
    "okay",
    "understood",
)
TRANSITION_MARKERS = (
    "进入",
    "从",
    "切到",
    "切换到",
    "transition",
    "moved to",
    "state changed",
)
REASON_MARKERS = (
    "原因",
    "因为",
    "触发",
    "based on",
    "due to",
)
OWNER_MARKERS = (
    "我会",
    "我先",
    "接下来我",
    "你确认",
    "你只需要",
    "由我",
    "由你",
    "系统会",
    "我们会",
)
COMPLETION_CLAIM_MARKERS = (
    "已完成",
    "已经完成",
    "准备好了",
    "可交付",
    "完成了",
    "done",
    "ready to deliver",
    "delivery ready",
)
TRUTH_EVIDENCE_MARKERS = (
    "验证",
    "verify",
    "pass",
    "status",
    "gate",
    "run",
    "证据",
    "依据",
    "artifact",
)


class PersonaLabError(RuntimeError):
    pass


def now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_lab_run_id() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f-persona-lab")


def is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def ensure_external_run_dir(run_dir: Path) -> None:
    if is_within(run_dir, ROOT):
        raise PersonaLabError(f"persona-lab run_dir must be outside repo root: {run_dir}")


def resolve_run_dir(run_id: str = "", raw_run_dir: str = "") -> tuple[str, Path]:
    if str(raw_run_dir or "").strip():
        run_dir = Path(raw_run_dir).expanduser().resolve()
        ensure_external_run_dir(run_dir)
        return run_dir.name, run_dir
    lab_run_id = str(run_id or "").strip() or default_lab_run_id()
    run_dir = (get_runs_root() / get_repo_slug(ROOT) / "persona_lab" / lab_run_id).resolve()
    ensure_external_run_dir(run_dir)
    return lab_run_id, run_dir


def read_version() -> str:
    if not VERSION_FILE.exists():
        raise PersonaLabError(f"missing VERSION file: {VERSION_FILE}")
    value = VERSION_FILE.read_text(encoding="utf-8").lstrip("\ufeff").strip()
    if not value:
        raise PersonaLabError("VERSION file is empty")
    return value


def load_yaml_doc(path: Path) -> dict[str, Any]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise PersonaLabError(f"YAML root must be an object: {path}")
    return doc


def load_case_docs(case_ids: list[str] | None = None) -> dict[str, dict[str, Any]]:
    wanted = set(case_ids or [])
    docs: dict[str, dict[str, Any]] = {}
    for path in sorted(CASES_DIR.glob("*.yaml")):
        doc = load_yaml_doc(path)
        case_id = str(doc.get("case_id", "")).strip()
        if not case_id:
            raise PersonaLabError(f"case_id missing: {path}")
        if wanted and case_id not in wanted:
            continue
        docs[case_id] = doc
    if wanted:
        missing = sorted(wanted - set(docs))
        if missing:
            raise PersonaLabError(f"unknown persona-lab case ids: {', '.join(missing)}")
    return docs


def load_rubric_docs() -> dict[str, dict[str, Any]]:
    docs: dict[str, dict[str, Any]] = {}
    for path in sorted(RUBRICS_DIR.glob("*.yaml")):
        doc = load_yaml_doc(path)
        rubric_id = str(doc.get("rubric_id", "")).strip()
        if rubric_id:
            docs[rubric_id] = doc
    required = {"response_style_lint", "task_progress_score", "bilingual_consistency"}
    if not required.issubset(docs):
        raise PersonaLabError("persona-lab rubrics are incomplete")
    return docs


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, doc: dict[str, Any]) -> None:
    write_text(path, json.dumps(doc, ensure_ascii=False, indent=2) + "\n")


def normalize_text(text: str) -> str:
    cleaned = str(text or "").replace("：", ":").replace("，", ",")
    return re.sub(r"\s+", " ", cleaned.strip()).lower()


def first_sentence(text: str) -> str:
    stripped = str(text or "").strip()
    if not stripped:
        return ""
    parts = re.split(r"(?<=[。！？!?])|\n+", stripped, maxsplit=1)
    return str(parts[0] if parts else stripped).strip()


def contains_any(text: str, phrases: tuple[str, ...] | list[str]) -> bool:
    low = normalize_text(text)
    return any(normalize_text(item) in low for item in phrases if str(item or "").strip())


def starts_with_any(text: str, phrases: tuple[str, ...] | list[str]) -> bool:
    low = normalize_text(text)
    return any(low.startswith(normalize_text(item)) for item in phrases if str(item or "").strip())


def count_questions(text: str) -> int:
    return str(text or "").count("?") + str(text or "").count("？")


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", str(text or "")))


def contains_ascii_word(text: str) -> bool:
    return bool(re.search(r"[A-Za-z]{2,}", str(text or "")))


def is_bilingual_case(case_doc: dict[str, Any]) -> bool:
    mode = str(case_doc.get("language_mode", "")).strip().lower()
    if mode == "mixed":
        return True
    texts = [str(item.get("text", "")) for item in case_doc.get("user_script", []) if isinstance(item, dict)]
    joined = " ".join(texts)
    return contains_cjk(joined) and contains_ascii_word(joined)


def find_marker_position(text: str, markers: tuple[str, ...] | list[str]) -> int | None:
    low = normalize_text(text)
    positions = [low.find(normalize_text(item)) for item in markers if low.find(normalize_text(item)) >= 0]
    return min(positions) if positions else None


def explicit_judgment_pass(text: str) -> bool:
    judgment_pos = find_marker_position(text, JUDGMENT_MARKERS)
    if judgment_pos is None:
        return False
    action_pos = find_marker_position(text, ACTION_MARKERS)
    return action_pos is None or judgment_pos <= action_pos


def next_action_pass(text: str) -> bool:
    return find_marker_position(text, ACTION_MARKERS) is not None


def status_anchor_pass(text: str) -> bool:
    return contains_any(text, STATUS_MARKERS)


def goal_echo_pass(reply_text: str, user_task: str) -> bool:
    reply = normalize_text(reply_text)
    task = normalize_text(user_task)
    if not reply or not task:
        return True
    if reply == task:
        return False
    if task and reply.startswith(task[: min(len(task), 28)]):
        return False
    if task in reply and not explicit_judgment_pass(reply_text) and not next_action_pass(reply_text):
        return False
    return difflib.SequenceMatcher(a=task, b=reply).ratio() < 0.72 or next_action_pass(reply_text)


def unnecessary_question_pass(text: str) -> bool:
    qcount = count_questions(text)
    if qcount == 0:
        return True
    if qcount > 1:
        return False
    return contains_any(text, BLOCKER_MARKERS) and explicit_judgment_pass(text)


def task_advancement_pass(text: str) -> bool:
    return explicit_judgment_pass(text) or next_action_pass(text) or contains_any(text, ("已完成", "当前进展", "deliver", "result is"))


def _is_low_information_ack(text: str) -> bool:
    low = normalize_text(text)
    if not low:
        return True
    if not contains_any(text, LOW_INFO_ACKS):
        return False
    if next_action_pass(text) or status_anchor_pass(text):
        return False
    return len(low) <= 48


def no_redundant_progress_pass(at: list[dict[str, Any]]) -> bool:
    if not at:
        return False
    if any(_is_low_information_ack(str(turn.get("text", ""))) for turn in at):
        return False
    first_sentences = [normalize_text(first_sentence(str(turn.get("text", "")))) for turn in at]
    for idx in range(1, len(first_sentences)):
        if first_sentences[idx] and first_sentences[idx] == first_sentences[idx - 1]:
            return False
    return True


def transition_response_complete_pass(text: str) -> bool:
    if not contains_any(text, TRANSITION_MARKERS):
        return True
    return status_anchor_pass(text) and contains_any(text, REASON_MARKERS) and next_action_pass(text) and contains_any(text, OWNER_MARKERS)


def truth_grounded_completion_pass(text: str) -> bool:
    if not contains_any(text, COMPLETION_CLAIM_MARKERS):
        return True
    return contains_any(text, TRUTH_EVIDENCE_MARKERS)


def receptionist_fallback_pass(text: str) -> bool:
    if contains_any(text, RECEPTIONIST_MARKERS):
        return False
    low = normalize_text(text)
    return low.count("抱歉") < 2 and low.count("sorry") < 2


def template_english_fallback_pass(text: str) -> bool:
    return not contains_any(text, TEMPLATE_SUPPORT_PHRASES)


def context_reset_pass(assistant_turns: list[dict[str, Any]]) -> bool:
    return all(not starts_with_any(first_sentence(str(turn.get("text", ""))), GREETINGS) for turn in assistant_turns[1:])


def collect_fixture_map(args: argparse.Namespace) -> dict[str, list[str]]:
    fixtures: dict[str, list[str]] = {}
    if str(args.fixture_file or "").strip():
        doc = json.loads(Path(str(args.fixture_file)).expanduser().resolve().read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise PersonaLabError("fixture file root must be an object")
        for case_id, raw in doc.items():
            replies = raw.get("assistant_replies") if isinstance(raw, dict) else raw
            if not isinstance(replies, list) or not all(isinstance(item, str) for item in replies):
                raise PersonaLabError(f"fixture assistant_replies must be a string array: {case_id}")
            fixtures[str(case_id)] = [str(item) for item in replies]
    if args.case and args.assistant_reply and len(args.case) == 1:
        fixtures[str(args.case[0])] = [str(item) for item in args.assistant_reply]
    if not fixtures:
        raise PersonaLabError("no fixture replies supplied")
    return fixtures


def build_transcript(case_doc: dict[str, Any], assistant_replies: list[str], session_id: str) -> dict[str, Any]:
    script = case_doc.get("user_script") or []
    if not isinstance(script, list):
        raise PersonaLabError(f"user_script must be a list: {case_doc.get('case_id')}")
    turns: list[dict[str, Any]] = []
    turn_index = 1
    limited_replies = list(assistant_replies[: max(0, int(case_doc.get("turn_limit", len(assistant_replies) or 1)))])
    for idx, item in enumerate(script):
        if not isinstance(item, dict):
            raise PersonaLabError(f"user_script item must be an object: {case_doc.get('case_id')}")
        turns.append({"turn_index": turn_index, "role": "user", "text": str(item.get("text", ""))})
        turn_index += 1
        if idx < len(limited_replies):
            turns.append({"turn_index": turn_index, "role": "assistant", "text": str(limited_replies[idx])})
            turn_index += 1
    for text in limited_replies[len(script) :]:
        turns.append({"turn_index": turn_index, "role": "assistant", "text": str(text)})
        turn_index += 1
    return {
        "schema_version": TRANSCRIPT_SCHEMA,
        "case_id": str(case_doc.get("case_id", "")),
        "session_id": session_id,
        "assistant_persona": str(case_doc.get("assistant_persona", "")),
        "user_persona": str(case_doc.get("user_persona", "")),
        "language_mode": str(case_doc.get("language_mode", "")),
        "turn_limit": int(case_doc.get("turn_limit", len(limited_replies) or 1)),
        "turns": turns,
    }


def assistant_turns(transcript_doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [turn for turn in transcript_doc.get("turns", []) if str(turn.get("role", "")) == "assistant"]


def response_lint_results(
    case_doc: dict[str, Any],
    transcript_doc: dict[str, Any],
    lint_rubric: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    at = assistant_turns(transcript_doc)
    first_turn = at[0] if at else {"turn_index": 0, "text": ""}
    first_text = str(first_turn.get("text", ""))
    all_text = "\n".join(str(turn.get("text", "")) for turn in at)
    first_idx = int(first_turn.get("turn_index", 0))
    banned = tuple(str(item) for item in lint_rubric["checks"][1]["fail_if"]["contains_any"])
    bilingual_needed = is_bilingual_case(case_doc)
    return {
        "first_sentence_direct": {"passed": bool(first_text) and not starts_with_any(first_sentence(first_text), GREETINGS), "turn_index": first_idx, "evidence": first_sentence(first_text)},
        "banned_phrase": {"passed": not contains_any(all_text, banned), "turn_index": first_idx, "evidence": all_text},
        "explicit_judgment": {"passed": explicit_judgment_pass(first_text), "turn_index": first_idx, "evidence": first_text},
        "next_action_present": {"passed": next_action_pass(first_text), "turn_index": first_idx, "evidence": first_text},
        "status_anchor_present": {"passed": status_anchor_pass(first_text), "turn_index": first_idx, "evidence": first_text},
        "no_goal_echo": {"passed": goal_echo_pass(first_text, str(case_doc.get("initial_task", ""))), "turn_index": first_idx, "evidence": first_text},
        "no_unnecessary_question": {"passed": unnecessary_question_pass(first_text), "turn_index": first_idx, "evidence": first_text},
        "task_advancement": {"passed": task_advancement_pass(first_text), "turn_index": first_idx, "evidence": first_text},
        "no_receptionist_fallback": {"passed": all(receptionist_fallback_pass(str(turn.get("text", ""))) for turn in at), "turn_index": first_idx, "evidence": all_text},
        "bilingual_stability": {"passed": True if not bilingual_needed else explicit_judgment_pass(first_text) and next_action_pass(first_text) and template_english_fallback_pass(all_text), "turn_index": first_idx, "evidence": all_text},
        "no_redundant_progress": {"passed": no_redundant_progress_pass(at), "turn_index": first_idx, "evidence": all_text},
        "transition_response_complete": {"passed": transition_response_complete_pass(first_text), "turn_index": first_idx, "evidence": first_text},
        "truth_grounded_completion": {"passed": truth_grounded_completion_pass(first_text), "turn_index": first_idx, "evidence": first_text},
        "no_context_reset": {"passed": context_reset_pass(at), "turn_index": int(at[1]["turn_index"]) if len(at) > 1 else first_idx, "evidence": "\n".join(first_sentence(str(turn.get("text", ""))) for turn in at[1:]) if len(at) > 1 else ""},
    }


def bilingual_results(case_doc: dict[str, Any], transcript_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    at = assistant_turns(transcript_doc)
    first_turn = at[0] if at else {"turn_index": 0, "text": ""}
    first_text = str(first_turn.get("text", ""))
    all_text = "\n".join(str(turn.get("text", "")) for turn in at)
    first_idx = int(first_turn.get("turn_index", 0))
    if not is_bilingual_case(case_doc):
        return {key: {"passed": True, "turn_index": first_idx, "evidence": ""} for key in ("no_language_shift_reset", "task_progress_stable", "canonical_terms_stable", "no_template_english_fallback")}
    return {
        "no_language_shift_reset": {"passed": not starts_with_any(first_sentence(first_text), GREETINGS) and context_reset_pass(at), "turn_index": first_idx, "evidence": first_sentence(first_text)},
        "task_progress_stable": {"passed": explicit_judgment_pass(first_text) and next_action_pass(first_text), "turn_index": first_idx, "evidence": first_text},
        "canonical_terms_stable": {"passed": True, "turn_index": first_idx, "evidence": ""},
        "no_template_english_fallback": {"passed": template_english_fallback_pass(all_text), "turn_index": first_idx, "evidence": all_text},
    }


def fill_fail_statement(template: str, case_id: str, turn_index: int, total_score: int = 0) -> str:
    return str(template or "").replace("{case_id}", case_id).replace("{turn_index}", str(turn_index)).replace("{total_score}", str(total_score))


def build_check_results(
    case_doc: dict[str, Any],
    rubrics: dict[str, dict[str, Any]],
    transcript_doc: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lint_rubric = rubrics["response_style_lint"]
    bilingual_rubric = rubrics["bilingual_consistency"]
    lint_results = response_lint_results(case_doc, transcript_doc, lint_rubric)
    bilingual_eval = bilingual_results(case_doc, transcript_doc)
    check_results: list[dict[str, Any]] = []
    fail_entries: list[dict[str, Any]] = []
    for check in lint_rubric.get("checks", []):
        check_id = str(check.get("id", ""))
        result = lint_results[check_id]
        passed = bool(result["passed"])
        check_results.append({"rubric_id": "response_style_lint", "check_id": check_id, "kind": str(check.get("kind", "required")), "passed": passed, "turn_index": int(result["turn_index"]), "evidence": str(result["evidence"])})
        if not passed:
            fail_entries.append({"id": f"response_style_lint.{check_id}", "rule_id": check_id, "rubric_id": "response_style_lint", "turn_index": int(result["turn_index"]), "statement": str(lint_rubric["fail_reason_templates"].get(check_id, "")), "why": f"{check_id} violates task-progress dialogue because it weakens judgment-first execution.", "repair": f"Repair {check_id} by keeping the reply judgment-first and concrete on the next action.", "kind": str(check.get("kind", "required"))})
    for check in bilingual_rubric.get("checks", []):
        check_id = str(check.get("id", ""))
        result = bilingual_eval[check_id]
        passed = bool(result["passed"])
        check_results.append({"rubric_id": "bilingual_consistency", "check_id": check_id, "kind": "required", "passed": passed, "turn_index": int(result["turn_index"]), "evidence": str(result["evidence"])})
        if not passed:
            fail_entries.append({"id": f"bilingual_consistency.{check_id}", "rule_id": check_id, "rubric_id": "bilingual_consistency", "turn_index": int(result["turn_index"]), "statement": str(bilingual_rubric["fail_reason_templates"].get(check_id, "")), "why": f"{check_id} violates bilingual style stability under Persona Test Lab.", "repair": f"Repair {check_id} by preserving the same judgment-first task structure across language shifts.", "kind": "required"})
    return check_results, fail_entries


def score_dimensions(
    case_doc: dict[str, Any],
    rubrics: dict[str, dict[str, Any]],
    transcript_doc: dict[str, Any],
    check_results: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], int]:
    score_rubric = rubrics["task_progress_score"]
    by_check = {f"{item['rubric_id']}.{item['check_id']}": item for item in check_results}
    first_idx = int((assistant_turns(transcript_doc) or [{"turn_index": 0}])[0]["turn_index"])
    bilingual_needed = is_bilingual_case(case_doc)
    dim_pass = {
        "task_entry_directness": bool(by_check["response_style_lint.first_sentence_direct"]["passed"]),
        "explicit_judgment": bool(by_check["response_style_lint.explicit_judgment"]["passed"]),
        "next_action_clarity": bool(by_check["response_style_lint.next_action_present"]["passed"]),
        "question_discipline": bool(by_check["response_style_lint.no_unnecessary_question"]["passed"]),
        "non_repetition": bool(by_check["response_style_lint.no_goal_echo"]["passed"]),
        "task_advancement": bool(by_check["response_style_lint.task_advancement"]["passed"]),
        "pressure_stability": bool(by_check["response_style_lint.no_receptionist_fallback"]["passed"]),
        "bilingual_consistency": True if not bilingual_needed else bool(by_check["response_style_lint.bilingual_stability"]["passed"]) and bool(by_check["bilingual_consistency.no_language_shift_reset"]["passed"]) and bool(by_check["bilingual_consistency.no_template_english_fallback"]["passed"]),
        "context_cleanliness": bool(by_check["response_style_lint.no_context_reset"]["passed"]),
    }
    total_score = 0
    dimension_scores: dict[str, dict[str, Any]] = {}
    dimension_failures: list[dict[str, Any]] = []
    for dim in score_rubric.get("dimensions", []):
        dim_id = str(dim.get("id", ""))
        weight = int(dim.get("weight", 0))
        passed = bool(dim_pass.get(dim_id, False))
        score = weight if passed else 0
        total_score += score
        dimension_scores[dim_id] = {"score": score, "weight": weight, "pass_min": int(dim.get("pass_score", 0)), "passed": passed}
        if not passed:
            dimension_failures.append({"id": f"task_progress_score.{dim_id}", "rule_id": dim_id, "rubric_id": "task_progress_score", "turn_index": first_idx, "statement": str(score_rubric["fail_reason_templates"].get(dim_id, "")), "why": f"{dim_id} is below the task-progress scoring requirement.", "repair": f"Repair {dim_id} until it reaches the rubric pass threshold.", "kind": "dimension"})
    return dimension_scores, dimension_failures, total_score


def finalize_fail_reasons(
    *,
    case_doc: dict[str, Any],
    rubrics: dict[str, dict[str, Any]],
    lint_failures: list[dict[str, Any]],
    dimension_failures: list[dict[str, Any]],
    total_score: int,
) -> list[dict[str, Any]]:
    case_id = str(case_doc.get("case_id", ""))
    score_rubric = rubrics["task_progress_score"]
    finalized: list[dict[str, Any]] = []
    for item in lint_failures + dimension_failures:
        turn_index = int(item.get("turn_index", 0))
        finalized.append(
            {
                "id": str(item.get("id", "")),
                "rule_id": str(item.get("rule_id", "")),
                "rubric_id": str(item.get("rubric_id", "")),
                "turn_index": turn_index,
                "statement": fill_fail_statement(str(item.get("statement", "")), case_id, turn_index, total_score),
                "why": str(item.get("why", "")),
                "repair": str(item.get("repair", "")),
                "kind": str(item.get("kind", "")),
            }
        )
    if total_score < int(score_rubric["pass_thresholds"]["total_min"]):
        finalized.append(
            {
                "id": "task_progress_score.total_below_threshold",
                "rule_id": "total_below_threshold",
                "rubric_id": "task_progress_score",
                "turn_index": 0,
                "statement": fill_fail_statement(str(score_rubric["fail_reason_templates"].get("total_below_threshold", "")), case_id, 0, total_score),
                "why": "The total style score is below the rubric threshold.",
                "repair": "Raise failed dimensions until the total score reaches the contract minimum.",
                "kind": "dimension",
            }
        )
    unique: dict[str, dict[str, Any]] = {}
    for item in finalized:
        unique[str(item["id"])] = item
    return list(unique.values())


def evaluate_case(
    *,
    case_doc: dict[str, Any],
    rubrics: dict[str, dict[str, Any]],
    assistant_replies: list[str],
    source_version: str,
    source_commit: str,
    session_id: str,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    transcript_doc = build_transcript(case_doc, assistant_replies, session_id)
    check_results, lint_failures = build_check_results(case_doc, rubrics, transcript_doc)
    dimension_scores, dimension_failures, total_score = score_dimensions(case_doc, rubrics, transcript_doc, check_results)
    fail_reason_entries = finalize_fail_reasons(case_doc=case_doc, rubrics=rubrics, lint_failures=lint_failures, dimension_failures=dimension_failures, total_score=total_score)
    fail_fast_hits = [item for item in check_results if item["rubric_id"] == "response_style_lint" and item["kind"] == "fail_fast" and not item["passed"]]
    required_failures = [item for item in check_results if item["kind"] == "required" and not item["passed"]]
    must_pass_failures = []
    for check_ref in case_doc.get("must_pass_checks", []):
        ref = str(check_ref)
        matched = next((item for item in check_results if f"{item['rubric_id']}.{item['check_id']}" == ref), None)
        if matched is not None:
            if not matched["passed"]:
                must_pass_failures.append(ref)
            continue
        if ref.startswith("task_progress_score."):
            dim_id = ref.split(".", 1)[1]
            if not bool(dimension_scores.get(dim_id, {}).get("passed", False)):
                must_pass_failures.append(ref)
    thresholds = dict(rubrics["task_progress_score"]["pass_thresholds"].get("required_dimension_mins", {}))
    threshold_failures = [dim_id for dim_id, threshold in thresholds.items() if int(dimension_scores.get(dim_id, {}).get("score", 0)) < int(threshold)]
    verdict = "pass"
    stop_reason = "fixture_replies_consumed"
    if fail_fast_hits:
        verdict = "fail"
        stop_reason = "fail_fast_lint_hit"
    elif required_failures or must_pass_failures or threshold_failures or total_score < int(rubrics["task_progress_score"]["pass_thresholds"]["total_min"]):
        verdict = "fail"
        stop_reason = "scoring_or_required_check_failure"
    transcript_doc["stop_reason"] = stop_reason
    transcript_doc["source_version"] = source_version
    transcript_doc["source_commit"] = source_commit
    score_doc = {
        "schema_version": SCORE_SCHEMA,
        "case_id": str(case_doc.get("case_id", "")),
        "judge_rubrics": sorted(rubrics.keys()),
        "check_results": check_results,
        "dimension_scores": dimension_scores,
        "total_score": total_score,
        "verdict": verdict,
        "fail_reason_ids": [str(item["id"]) for item in fail_reason_entries],
        "must_pass_failures": must_pass_failures,
        "threshold_failures": threshold_failures,
        "source_version": source_version,
        "source_commit": source_commit,
    }
    return transcript_doc, score_doc, fail_reason_entries


def render_transcript_md(case_doc: dict[str, Any], transcript_doc: dict[str, Any]) -> str:
    lines = [f"# Transcript - {case_doc['case_id']}", "", f"- Session-ID: `{transcript_doc['session_id']}`", f"- Assistant-Persona: `{transcript_doc['assistant_persona']}`", f"- User-Persona: `{transcript_doc['user_persona']}`", f"- Stop-Reason: `{transcript_doc['stop_reason']}`", ""]
    for turn in transcript_doc.get("turns", []):
        lines.extend([f"## Turn {turn['turn_index']} - {turn['role']}", "", str(turn.get("text", "")).strip(), ""])
    return "\n".join(lines).rstrip() + "\n"


def render_fail_reasons_md(case_doc: dict[str, Any], fail_reason_entries: list[dict[str, Any]]) -> str:
    lines = [f"# Fail Reasons - {case_doc['case_id']}", ""]
    if not fail_reason_entries:
        return "# Fail Reasons - %s\n\n- None.\n" % case_doc["case_id"]
    for item in fail_reason_entries:
        lines.extend([f"## {item['id']}", "", f"- Rule: `{item['rule_id']}`", f"- Turn: `{item['turn_index']}`", f"- Statement: {item['statement']}", f"- Why: {item['why']}", f"- Minimum Repair: {item['repair']}", ""])
    return "\n".join(lines)


def render_case_summary_md(case_doc: dict[str, Any], transcript_doc: dict[str, Any], score_doc: dict[str, Any], fail_reason_entries: list[dict[str, Any]]) -> str:
    next_focus = f"`{fail_reason_entries[0]['rule_id']}`" if fail_reason_entries else "keep the same task-progress structure when the production adapter is added"
    return "\n".join(
        [
            f"# Case Summary - {case_doc['case_id']}",
            "",
            f"- Purpose: {case_doc['purpose']}",
            f"- Verdict: `{score_doc['verdict']}`",
            f"- Session-ID: `{transcript_doc['session_id']}`",
            f"- Total-Score: `{score_doc['total_score']}`",
            f"- Stop-Reason: `{transcript_doc['stop_reason']}`",
            f"- Expected-Traits: {', '.join(str(item) for item in case_doc.get('expected_response_traits', []))}",
            f"- Next-Regression-Focus: {next_focus}",
            "",
        ]
    )


def render_run_summary_md(manifest_doc: dict[str, Any]) -> str:
    lines = [f"# Persona Test Lab Run - {manifest_doc['lab_run_id']}", "", f"- Source-Version: `{manifest_doc['source_version']}`", f"- Source-Commit: `{manifest_doc['source_commit']}`", f"- Session-Policy: `{manifest_doc['session_policy']}`", f"- Executed-Cases: `{len(manifest_doc['case_ids'])}`", f"- Pass-Count: `{manifest_doc['pass_count']}`", f"- Fail-Count: `{manifest_doc['fail_count']}`", f"- First-Failing-Case: `{manifest_doc['first_failing_case'] or 'none'}`", f"- Score-Distribution: min={manifest_doc['score_distribution']['min']}, avg={manifest_doc['score_distribution']['avg']}, max={manifest_doc['score_distribution']['max']}", "", "## Cases", ""]
    for row in manifest_doc.get("cases", []):
        lines.append(f"- `{row['case_id']}` -> `{row['verdict']}` score=`{row['total_score']}` session=`{row['session_id']}` path=`cases/{row['case_id']}`")
    if manifest_doc.get("key_fail_reasons"):
        lines.extend(["", "## Key Fail Reasons", ""])
        for item in manifest_doc["key_fail_reasons"]:
            lines.append(f"- `{item['case_id']}`: {item['statement']}")
    lines.append("")
    return "\n".join(lines)


def run_fixture_suite(
    *,
    case_fixtures: dict[str, list[str]],
    case_ids: list[str] | None = None,
    run_id: str = "",
    raw_run_dir: str = "",
) -> tuple[Path, dict[str, Any]]:
    requested = case_ids[:] if case_ids else sorted(case_fixtures)
    if not requested:
        raise PersonaLabError("no persona-lab cases requested")
    case_docs = load_case_docs(requested)
    rubrics = load_rubric_docs()
    source_version = read_version()
    source_commit = reference_export.current_source_commit(ROOT)
    lab_run_id, run_dir = resolve_run_dir(run_id, raw_run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    started_at = now_utc_iso()
    case_rows: list[dict[str, Any]] = []
    session_ids: list[str] = []
    key_fail_reasons: list[dict[str, Any]] = []
    for case_id in requested:
        replies = list(case_fixtures.get(case_id) or [])
        if not replies:
            raise PersonaLabError(f"missing fixture assistant replies for case: {case_id}")
        case_doc = case_docs[case_id]
        session_id = f"{case_id}-{uuid.uuid4().hex[:12]}"
        session_ids.append(session_id)
        transcript_doc, score_doc, fail_reason_entries = evaluate_case(case_doc=case_doc, rubrics=rubrics, assistant_replies=replies, source_version=source_version, source_commit=source_commit, session_id=session_id)
        case_dir = run_dir / "cases" / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        write_text(case_dir / "transcript.md", render_transcript_md(case_doc, transcript_doc))
        write_json(case_dir / "transcript.json", transcript_doc)
        write_json(case_dir / "score.json", score_doc)
        write_text(case_dir / "fail_reasons.md", render_fail_reasons_md(case_doc, fail_reason_entries))
        write_text(case_dir / "summary.md", render_case_summary_md(case_doc, transcript_doc, score_doc, fail_reason_entries))
        case_rows.append({"case_id": case_id, "session_id": session_id, "verdict": str(score_doc["verdict"]), "total_score": int(score_doc["total_score"]), "path": f"cases/{case_id}", "fail_reason_ids": list(score_doc["fail_reason_ids"])})
        if fail_reason_entries:
            key_fail_reasons.append({"case_id": case_id, "statement": fail_reason_entries[0]["statement"]})
    scores = [int(item["total_score"]) for item in case_rows]
    manifest_doc = {
        "schema_version": RUN_MANIFEST_SCHEMA,
        "lab_run_id": lab_run_id,
        "repo_slug": get_repo_slug(ROOT),
        "source_version": source_version,
        "source_commit": source_commit,
        "session_policy": "fresh_session_per_case",
        "production_persona": str(case_docs[requested[0]].get("assistant_persona", "")),
        "judge_rubrics": sorted(rubrics.keys()),
        "case_ids": requested,
        "cases": case_rows,
        "started_at": started_at,
        "completed_at": now_utc_iso(),
        "pass_count": sum(1 for item in case_rows if item["verdict"] == "pass"),
        "fail_count": sum(1 for item in case_rows if item["verdict"] == "fail"),
        "first_failing_case": next((item["case_id"] for item in case_rows if item["verdict"] == "fail"), ""),
        "score_distribution": {"min": min(scores) if scores else 0, "avg": round(sum(scores) / len(scores), 2) if scores else 0, "max": max(scores) if scores else 0},
        "fresh_session_evidence": {"unique_session_ids": len(set(session_ids)) == len(session_ids), "session_ids": session_ids},
        "fixture_mode": "assistant_replies",
        "key_fail_reasons": key_fail_reasons,
    }
    write_json(run_dir / "manifest.json", manifest_doc)
    write_text(run_dir / "summary.md", render_run_summary_md(manifest_doc))
    return run_dir, manifest_doc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Persona Test Lab fixture cases and score them.")
    parser.add_argument("--fixture-file", default="", help="JSON file mapping case_id -> assistant_replies[]")
    parser.add_argument("--case", action="append", help="Persona-lab case id to run; can repeat")
    parser.add_argument("--assistant-reply", action="append", default=[], help="Assistant fixture reply for a single-case run; can repeat")
    parser.add_argument("--run-id", default="", help="Override lab run id")
    parser.add_argument("--run-dir", default="", help="Explicit external output directory")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    fixtures = collect_fixture_map(args)
    case_ids = [str(item) for item in args.case] if args.case else sorted(fixtures)
    run_dir, manifest_doc = run_fixture_suite(case_fixtures=fixtures, case_ids=case_ids, run_id=str(args.run_id or ""), raw_run_dir=str(args.run_dir or ""))
    print(json.dumps({"run_dir": str(run_dir), "manifest": manifest_doc}, ensure_ascii=False, indent=2))
    return 0 if int(manifest_doc["fail_count"]) == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PersonaLabError as exc:
        raise SystemExit(f"[ctcp_persona_lab] {exc}") from exc
