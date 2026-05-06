from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROMPT_TEMPLATE_PATH = ROOT / "agents" / "prompts" / "support_lead_reply.md"
SUPPORT_INBOX_REL_PATH = Path("artifacts") / "support_inbox.jsonl"
SUPPORT_PROMPT_REL_PATH = Path("artifacts") / "support_prompt_input.md"
SUPPORT_REPLY_PROVIDER_REL_PATH = Path("artifacts") / "support_reply.provider.json"
SUPPORT_MODE_ROUTER_PROVIDER_REL_PATH = Path("artifacts") / "support_mode_router.provider.json"
SUPPORT_REPLY_REL_PATH = Path("artifacts") / "support_reply.json"
SUPPORT_SESSION_STATE_REL_PATH = Path("artifacts") / "support_session_state.json"
SUPPORT_PUBLIC_DELIVERY_REL_PATH = Path("artifacts") / "support_public_delivery.json"
SUPPORT_SCAFFOLD_MATERIALIZATION_REL_PATH = Path("artifacts") / "support_scaffold_materialization.json"
SUPPORT_EXPORTS_REL_DIR = Path("artifacts") / "support_exports"
DISPATCH_CONFIG_REL_PATH = Path("artifacts") / "dispatch_config.json"
SUPPORT_SCAFFOLD_STDOUT_REL_PATH = Path("logs") / "support_scaffold.stdout.log"
SUPPORT_SCAFFOLD_STDERR_REL_PATH = Path("logs") / "support_scaffold.stderr.log"
SUPPORT_T2P_STATE_MACHINE_REPORT_REL_PATH = Path("artifacts") / "support_t2p_state_machine_report.json"
SUPPORT_SCAFFOLD_PROFILE = "standard"
SUPPORT_SCAFFOLD_SOURCE_MODE = "live-reference"
CTCP_SCAFFOLD_STRUCTURE_HINT = [
    "README.md",
    "docs/",
    "meta/",
    "scripts/",
    "workflow_registry/",
    "simlab/",
]

KNOWN_PROVIDERS = {"manual_outbox", "ollama_agent", "api_agent", "codex_agent", "mock_agent", "local_exec"}
PRIMARY_SUPPORT_PROVIDER = "api_agent"
LOCAL_SUPPORT_REPLY_PROVIDERS = ("ollama_agent",)
SUPPORT_REPLY_PROVIDERS = (PRIMARY_SUPPORT_PROVIDER,) + LOCAL_SUPPORT_REPLY_PROVIDERS
DEFAULT_SUPPORT_OPENAI_MODEL = "gpt-4.1"
FORBIDDEN_REPLY_PATTERNS = (
    "trace.md",
    "trace:",
    "logs/",
    "logs\\",
    "stdout",
    "stderr",
    "outbox/",
    "outbox\\",
    "diff --git",
    "stack trace",
    "run_dir",
    "failure_bundle.zip",
)
_TASK_PROGRESS_STATUS_MARKERS_ZH = (
    "当前",
    "目前",
    "状态",
    "阶段",
    "进展",
    "卡点",
    "阻塞",
    "已完成",
)
_TASK_PROGRESS_STATUS_MARKERS_EN = (
    "current",
    "status",
    "phase",
    "progress",
    "blocked",
    "completed",
)
_TASK_PROGRESS_NEXT_ACTION_MARKERS_ZH = ("下一步", "接下来", "我会", "我先", "先把", "继续处理")
_TASK_PROGRESS_NEXT_ACTION_MARKERS_EN = ("next", "next step", "next action", "i will", "i'll", "start by")
_TASK_PROGRESS_LOW_INFO_ACKS_ZH = ("我在", "好的", "明白了", "收到", "稍等", "继续处理中")
_TASK_PROGRESS_LOW_INFO_ACKS_EN = ("got it", "okay", "understood", "on it", "processing")
_TASK_PROGRESS_TRANSITION_MARKERS_ZH = ("进入", "切换到", "从", "转到")
_TASK_PROGRESS_TRANSITION_MARKERS_EN = ("transition", "moved to", "state changed", "switched to")
_TASK_PROGRESS_REASON_MARKERS_ZH = ("原因", "因为", "触发")
_TASK_PROGRESS_REASON_MARKERS_EN = ("because", "reason", "triggered by", "due to")
_TASK_PROGRESS_OWNER_MARKERS_ZH = ("我会", "我先", "由我", "由你", "你只需要", "系统会")
_TASK_PROGRESS_OWNER_MARKERS_EN = ("i will", "i'll", "you need to", "system will", "owned by")
_TASK_PROGRESS_COMPLETION_CLAIMS_ZH = ("已完成", "已经完成", "可交付", "准备好了", "已经做好")
_TASK_PROGRESS_COMPLETION_CLAIMS_EN = ("completed", "done", "ready to deliver", "delivery ready")
_FINAL_READY_RUN_STATUSES = {"pass", "done", "completed", "success"}
_PROACTIVE_INTERNAL_GATE_LEAK_TOKENS = (
    "contract guardian",
    "cost controller",
    "chair/planner",
    "review_contract",
    "review_cost",
    "verdict=",
    "gate owner",
)
_TEST_SCREENSHOT_NAME_HINTS = ("test", "qa", "smoke", "acceptance", "validation", "replay")
_BACKEND_PLACEHOLDER_REPLY_MARKERS_ZH = (
    "没有可直接发送的正式回复",
    "正式回复链暂时不可用",
    "后端回复链暂时不可用",
    "低置信度兜底说明",
)
_BACKEND_PLACEHOLDER_REPLY_MARKERS_EN = (
    "no customer-ready reply",
    "formal reply path",
    "backend reply path is unavailable",
    "low-confidence fallback",
)

from scripts.ctcp_support_bot_text_patterns import *  # noqa: F403

__all__ = [name for name in globals() if (name.isupper() or name.startswith("_")) and not name.startswith("__")]
