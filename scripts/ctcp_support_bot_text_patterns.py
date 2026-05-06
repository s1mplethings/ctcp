from __future__ import annotations

import re

SMALLTALK_PATTERNS_ZH = (
    re.compile(r"^\s*(你好|您好|嗨|哈喽|在吗|早上好|下午好|晚上好|谢谢|辛苦了)\s*[!！。.\?？]*\s*$"),
)
SMALLTALK_PATTERNS_EN = (
    re.compile(r"^\s*(hi|hello|hey|thanks|thank you)\s*[!.\?]*\s*$", re.IGNORECASE),
)
GREETING_PATTERNS_ZH = (
    re.compile(r"^\s*(你好|您好|嗨|哈喽|在吗|早上好|下午好|晚上好)\s*[!！。.\?？]*\s*$"),
)
GREETING_PATTERNS_EN = (
    re.compile(r"^\s*(hi|hello|hey)\s*[!.\?]*\s*$", re.IGNORECASE),
)
LOW_SIGNAL_PROJECT_REPLY_PATTERNS = (
    re.compile(r"^\s*(没有|没|暂无|暂时没有)\s*([，,。.!！ ]*(你)?\s*先\s*(做着?|继续|推进|开始))?\s*[吧吗呀呢]?\s*$"),
    re.compile(r"^\s*((你)?\s*先\s*(做着?|继续|推进|开始)|继续|先继续|先推进|先这样|就这样|可以|好的|好|行|嗯+)\s*[，,。.!！ ]*(吧|呀|呢|吗)?\s*$"),
    re.compile(r"^\s*(no|not yet|none yet|go ahead|keep going|continue|start first|you start)\s*[!.,? ]*\s*$", re.IGNORECASE),
)
PROJECT_GOAL_HINTS_ZH = ("项目", "剧情", "故事", "设定", "分支", "脚本", "游戏", "叙事", "分镜", "角色", "世界观")
PROJECT_GOAL_HINTS_EN = (
    "project",
    "storyline",
    "story",
    "setting",
    "branch",
    "script",
    "game",
    "narrative design",
    "storyboard",
    "character",
    "worldbuilding",
)
IMPLEMENTATION_CONSTRAINT_HINTS_ZH = (
    "windows",
    "window开发",
    "qt",
    "qt6",
    "ui",
    "界面",
    "桌面",
    "平台",
    "框架",
    "技术栈",
    "c++",
    "python",
    "数据库",
    "前端",
    "后端",
)
IMPLEMENTATION_CONSTRAINT_HINTS_EN = (
    "windows",
    "qt",
    "qt6",
    "ui",
    "desktop",
    "platform",
    "framework",
    "tech stack",
    "c++",
    "python",
    "database",
    "frontend",
    "backend",
)
PROJECT_EXECUTION_FOLLOWUP_HINTS_ZH = (
    "先开始做",
    "先开始吧",
    "先做",
    "先做出",
    "做出第一版",
    "先出第一版",
    "先出一版",
    "开始做项目",
    "按这个做",
    "你先做",
    "你可以先开始",
    "后面我再补",
    "后面有了我再补",
    "我再调整",
    "后面再调整",
    "继续做",
    "继续推进",
)
PROJECT_EXECUTION_FOLLOWUP_HINTS_EN = (
    "go ahead and start",
    "start the project",
    "make a first draft",
    "make the first draft",
    "make a first version",
    "build the first version",
    "first version",
    "first draft",
    "first pass",
    "you can start first",
    "i'll adjust later",
    "i will adjust later",
    "keep building",
)
PROJECT_CREATE_INTENT_HINTS_ZH = (
    "创建项目",
    "创建一个项目",
    "帮我创建",
    "帮我做一个项目",
    "搭建项目",
    "生成项目",
    "做一个工具",
    "做个工具",
    "开发一个工具",
)
PROJECT_CREATE_INTENT_HINTS_EN = (
    "create a project",
    "build a project",
    "generate a project",
    "start the project",
    "make a tool",
    "build a tool",
)
TASK_BINDING_HINTS_ZH = (
    "绑定任务",
    "绑定一个新任务",
    "绑定新任务",
    "新任务",
    "启动这一任务",
    "启动这个任务",
)
TASK_BINDING_HINTS_EN = (
    "bind a new task",
    "bind this task",
    "start this task",
    "task binding",
)
DOMAIN_LIFT_HINTS_ZH = (
    "域提升",
    "完整产品域",
    "不要再只做",
    "不要只做",
    "覆盖门槛",
    "coverage gate",
    "user_acceptance_status",
    "internal_runtime_status",
)
DOMAIN_LIFT_HINTS_EN = (
    "domain lift",
    "domain-lift",
    "product-generation repair",
    "coverage gate",
    "user_acceptance_status",
    "internal_runtime_status",
)
GENERATION_RERUN_HINTS_ZH = (
    "重跑生成测试",
    "重跑测试",
    "重新生成",
    "粗目标",
    "不要细规格",
    "自己做产品定义并生成",
)
GENERATION_RERUN_HINTS_EN = (
    "rerun generation test",
    "rerun the generation test",
    "rerun",
    "rough goal",
    "product definition",
    "project generation",
)
EXECUTION_CLAIM_HINTS_ZH = (
    "我将处理此任务",
    "我将开始执行",
    "我会重跑相关测试",
    "我会先生成上下文包再继续",
    "我会启动这一任务",
    "我会绑定此任务",
    "开始处理此任务",
    "开始执行此任务",
    "我将开始处理",
)
EXECUTION_CLAIM_HINTS_EN = (
    "i will handle this task",
    "i will start executing",
    "i will rerun the test",
    "i will generate the context pack first",
    "i will start this task",
    "i will bind this task",
    "i'm starting this task",
)
NON_PROJECT_SUPPORT_REPLY_MODES = {"GREETING", "SMALLTALK", "CAPABILITY_QUERY", "PROJECT_INTAKE"}
SUPPORTED_CONVERSATION_MODES = {
    "GREETING",
    "SMALLTALK",
    "CAPABILITY_QUERY",
    "PROJECT_INTAKE",
    "PROJECT_DETAIL",
    "PROJECT_DECISION_REPLY",
    "STATUS_QUERY",
}
SUPPORT_ACTIVE_STAGES = (
    "INTAKE",
    "CLARIFY",
    "PLAN",
    "EXECUTE",
    "VERIFY",
    "RETRYING",
    "RECOVERY_NEEDED",
    "EXEC_FAILED",
    "BLOCKED_HARD",
    "WAIT_USER_DECISION",
    "FINALIZE",
    "DELIVER",
    "RECOVER",
    "DELIVERED",
)
SUPPORT_STAGE_EXIT_RULES: dict[str, str] = {
    "INTAKE": "goal_and_scope_bound",
    "CLARIFY": "blocking_detail_collected_or_default_applied",
    "PLAN": "minimal_execution_path_locked",
    "EXECUTE": "execution_step_change_or_verify_trigger",
    "VERIFY": "verification_result_recorded_or_blocker_identified",
    "RETRYING": "retry_attempt_recorded_or_gate_truth_changed",
    "RECOVERY_NEEDED": "explicit_recovery_action_bound",
    "EXEC_FAILED": "failed_execution_path_reconciled",
    "BLOCKED_HARD": "non_retryable_blocker_reconciled",
    "WAIT_USER_DECISION": "required_user_decision_received",
    "FINALIZE": "delivery_payload_ready",
    "DELIVER": "result_shared_with_user",
    "RECOVER": "first_failure_mitigated_or_escalated",
    "DELIVERED": "new_task_or_explicit_followup",
}
SUPPORT_MESSAGE_INTENTS = (
    "continue",
    "clarify",
    "constraint_update",
    "new_task",
    "small_talk",
    "status_check",
)
SUPPORT_HISTORY_RAW_TURN_LIMIT = 60
SUPPORT_HISTORY_PROMPT_RECENT_LIMIT = 8
MODE_ROUTER_HINTS_ZH = (
    "为什么",
    "为何",
    "为啥",
    "怎么会",
    "凭什么",
    "依据",
    "刚让你做",
)
MODE_ROUTER_HINTS_EN = (
    "why",
    "how come",
    "how is it that",
    "why did",
    "reason",
    "basis",
)
PROJECT_CONTEXT_LEAK_TOKENS_ZH = (
    "项目",
    "开发",
    "原型",
    "第一版",
    "设计",
    "实现",
    "功能模块",
    "需求",
    "方案",
    "架构",
    "部署",
    "框架",
    "代码",
)
PROJECT_CONTEXT_LEAK_TOKENS_EN = (
    "project",
    "prototype",
    "first version",
    "development",
    "implementation",
    "design",
    "feature module",
    "requirement",
    "architecture",
    "deployment",
    "framework",
    "codebase",
)
SUPPORT_AUTO_ADVANCE_INTERVAL_SEC = 20
SUPPORT_PROGRESS_PUSH_IDLE_INTERVAL_SEC = 6
SUPPORT_NOTIFICATION_COOLDOWN_SEC = 45
SUPPORT_OUTBOUND_REQUEUE_MAX_RETRIES = {
    "error": 3,
    "result": 2,
    "progress": 2,
    "decision": 3,
}
SUPPORT_OUTBOUND_DROP_COOLDOWN_SEC = 600
# 0 means "disable periodic no-change proactive progress push".
SUPPORT_EXECUTION_KEEPALIVE_INTERVAL_SEC = 0
PREVIOUS_OUTLINE_REQUEST_PATTERNS_ZH = (
    re.compile(r"之前.*大纲"),
    re.compile(r"(按|照).*(之前|原来).*(大纲|方案|项目)"),
    re.compile(r"(继续|接着|重做|重新做).*(之前|原来).*(项目|大纲|方案)"),
    re.compile(r"之前想要你做的项目"),
    re.compile(r"之前那个项目"),
)
PREVIOUS_OUTLINE_REQUEST_PATTERNS_EN = (
    re.compile(r"previous outline", re.IGNORECASE),
    re.compile(r"continue .*previous", re.IGNORECASE),
    re.compile(r"redo .*previous", re.IGNORECASE),
    re.compile(r"previous project", re.IGNORECASE),
)
PREVIOUS_PROJECT_STATUS_PATTERNS_ZH = (
    re.compile(r"(之前|原来).*(项目|方案|大纲).*(进度|状态|做到什么程度|做到哪|做到哪一步|做成什么样|做得怎么样|现在怎么样|现在什么情况)"),
    re.compile(r"(之前那个项目|之前的项目|原来的项目).*(做成什么样|做得怎么样|现在怎么样|进度|状态|做到哪|做到什么程度)"),
    re.compile(r"(还有|有没有|还在|还留着|能不能找到|找得到).*(之前|原来|上次).*(生成|做的)?.*(项目|方案|大纲)"),
    re.compile(r"(之前|原来|上次).*(生成|做的)?.*(项目|方案|大纲).*(还有|有没有|还在|还留着|能不能找到|找得到|在哪)"),
)
PREVIOUS_PROJECT_STATUS_PATTERNS_EN = (
    re.compile(
        r"\b(previous|earlier|old)\b.{0,24}\b(project|plan|outline)\b.{0,24}\b(status|progress|done|ready|finished|latest)\b",
        re.IGNORECASE,
    ),
)
CODE_REQUEST_HINTS_ZH = ("代码", "源码", "源代码", "完整代码", "示例代码", "代码片段", "贴代码", "写代码", "实现代码", "给我代码")
CODE_REQUEST_HINTS_EN = (
    "code",
    "source code",
    "show code",
    "write code",
    "code snippet",
    "implementation code",
    "full code",
)
SCREENSHOT_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv", ".avi"}
SUPPORT_PACKAGE_MIN_QUALITY_SCORE = 70
_PUBLIC_SCREENSHOT_BLOCKED_PATH_MARKERS = (
    "/artifacts/delivery_replay/",
    "/delivery_replay/",
    "/replay_artifacts/",
)
_PUBLIC_SCREENSHOT_BLOCKED_NAME_MARKERS = (
    "replayed_screenshot",
    "evidence-card",
    "ctcp_replay_pass",
    "ctcp-replay-pass",
    "run_project_gui",
)
_WHITEBOARD_DISPATCH_RESULT_RE = re.compile(
    r"^(?P<role>[^/\s]+)/(?P<action>[^\s]+)\s+via\s+(?P<provider>[^\s]+)\s+=>\s+(?P<status>[^\s]+)\s+\((?P<target>[^)]+)\)(?:;\s*(?P<reason>.*))?$"
)

__all__ = [name for name in globals() if (name.isupper() or name.startswith("_")) and not name.startswith("__")]
