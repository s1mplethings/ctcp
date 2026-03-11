from __future__ import annotations

import re
from dataclasses import dataclass


_FORBIDDEN_TOKENS = (
    "api_agent",
    "mock_agent",
    "ollama_agent",
    "codex_agent",
    "manual_outbox",
    "local_exec",
    "traceback",
    "stack trace",
    "stderr",
    "stdout",
    "run_dir",
    "target-path",
    "prompt-path",
    "artifacts/",
    "outbox/",
    "logs/",
    "context.md",
    "constraints.md",
    "externals.md",
    "patch targets",
    "plan agent",
    "provider=",
    "provider:",
    "agent_request",
    "ctcp_orchestrate",
    # Chinese internal terms
    "\u5f85\u5904\u7406\u7684\u4e8b\u9879",  # 待处理的事项
    "\u9700\u8981\u7684\u4fe1\u606f",  # 需要的信息
    "\u7b49\u5f85\u5fc5\u8981\u8f93\u5165",  # 等待必要输入
    "\u5f53\u524d\u963b\u585e\u9879",  # 当前阻塞项
)

_RAW_PROMPT_PATTERNS = (
    re.compile(r"use\s+context\s*\+\s*constraints\s*\+\s*externals", re.IGNORECASE),
    re.compile(r"\bcontext\s*\+\s*constraints\s*\+\s*externals\b", re.IGNORECASE),
    re.compile(r"\bproduce a minimal plan\b", re.IGNORECASE),
)

_RC_PATTERN = re.compile(r"\b(?:command|agent|plan|patch|local[_ ]exec)[^\n]{0,80}\brc\s*=\s*\d+\b", re.IGNORECASE)
_FILE_PATH_PATTERN = re.compile(r"(?:[A-Za-z]:\\[^\s]+|/(?:home|users|tmp|var|opt)/[^\s]+)")
_INTERNAL_FIELD_PATTERN = re.compile(r"\b(?:exit[_ ]?code|return[_ ]?code|rc)\s*[:=]\s*\d+\b", re.IGNORECASE)
_INTERNAL_LABEL_PATTERN = re.compile(
    r"^(?:context|constraints|externals|patch targets|plan agent|target-path|prompt-path|provider)\s*[:=]",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SanitizedText:
    text: str
    redactions: int
    flagged_internal: bool


def _line_is_forbidden(raw_line: str) -> bool:
    line = str(raw_line or "").strip()
    if not line:
        return False
    low = line.lower()
    if any(token in low for token in _FORBIDDEN_TOKENS):
        return True
    if any(p.search(line) for p in _RAW_PROMPT_PATTERNS):
        return True
    if _RC_PATTERN.search(line):
        return True
    if _INTERNAL_FIELD_PATTERN.search(line):
        return True
    if _INTERNAL_LABEL_PATTERN.search(line):
        return True
    if _FILE_PATH_PATTERN.search(line):
        return True
    if line.startswith("[ctcp_orchestrate]"):
        return True
    return False


def sanitize_internal_text(text: str) -> SanitizedText:
    """
    Remove/neutralize backend-only content before it reaches user-visible chat.
    """

    rows = str(text or "").replace("\r\n", "\n").replace("\r", "\n").splitlines()
    kept: list[str] = []
    redactions = 0
    flagged_internal = False

    for row in rows:
        line = row.strip()
        if not line:
            if kept and kept[-1] != "":
                kept.append("")
            continue
        if _line_is_forbidden(line):
            redactions += 1
            flagged_internal = True
            continue
        cleaned = _FILE_PATH_PATTERN.sub("", line)
        cleaned = _RC_PATTERN.sub("", cleaned)
        cleaned = _INTERNAL_FIELD_PATTERN.sub("", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            redactions += 1
            flagged_internal = True
            continue
        kept.append(cleaned)

    while kept and kept[0] == "":
        kept.pop(0)
    while kept and kept[-1] == "":
        kept.pop()

    final_text = "\n".join(kept).strip()
    return SanitizedText(text=final_text, redactions=redactions, flagged_internal=flagged_internal)
