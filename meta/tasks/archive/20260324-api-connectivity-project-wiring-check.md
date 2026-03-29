# Task - api-connectivity-project-wiring-check

## Queue Binding

- Queue Item: `ADHOC-20260324-api-connectivity-project-wiring-check`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 用户反馈 API 连接不稳定，要求先验证 API，再验证是否可在项目链路里实际使用。
- Dependency check: `ADHOC-20260324-support-package-final-stage-gate` = `blocked` (existing runtime wiring failures remain outside this test-only scope).
- Scope boundary: 仅做 API 连通性与项目内接线可用性验证，不做功能重构。

## Task Truth Source (single source for current task)

- task_purpose: 给出 API 直连结果与项目内调用结果，明确当前可用/不可用状态。
- allowed_behavior_change: 可更新 `meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/tasks/archive/20260324-api-connectivity-project-wiring-check.md`、`meta/reports/LAST.md`、`meta/reports/archive/20260324-api-connectivity-project-wiring-check.md`。
- forbidden_goal_shift: 不扩展为 provider 重构；不改 support 主流程；不跳过 canonical verify。
- in_scope_modules:
  - `scripts/externals/openai_responses_client.py` (read/test only)
  - `scripts/ctcp_support_bot.py` (runtime exercise only)
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-api-connectivity-project-wiring-check.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-api-connectivity-project-wiring-check.md`
- out_of_scope_modules:
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_front_bridge.py`
  - `frontend/`
  - `src/`
  - `include/`
- completion_evidence: API 直连探测结果 + support bot 项目轮次实际调用结果 + canonical verify 首失败证据。

## Analysis / Find (before plan)

- Entrypoint analysis: API 直连入口在 `scripts/externals/openai_responses_client.py`，项目调用入口在 `scripts/ctcp_support_bot.py --stdin --provider api_agent`。
- Downstream consumer analysis: support 项目轮次需要输出 `support_reply.json.reply_text` 且 provider path 可执行。
- Source of truth: 命令返回码、stdout/stderr、support session run artifacts。
- Current break point / missing wiring: 用户报告“api 连接不好”，需先确认是外部连通性问题还是项目接线问题。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: user message -> `ctcp_support_bot.process_message()` -> provider execution.
- current_module: external API client probe + support runtime invocation.
- downstream: `support_reply.json` customer-facing reply output.
- source_of_truth: command evidence + support session artifacts in external run_dir.
- fallback: 若 API 不可用，记录首失败点和最小修复方向，不做越界改造。
- acceptance_test:
  - `python -c "from scripts.externals.openai_responses_client import call_openai_responses; text, err = call_openai_responses(prompt='Reply with API_OK only.', model='gpt-4.1-mini', timeout_sec=60); print('OK' if text else 'ERR'); print((text or err)[:200])"`
  - `echo 现在先做一个项目内API接线测试 | python scripts/ctcp_support_bot.py --stdin --chat-id api-connectivity-check --provider api_agent`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不用 mock 替代真实 API 探测
  - 不仅跑单测，必须跑一次项目入口 runtime 调用
  - 不省略 canonical verify
- user_visible_effect: 给出“API 是否可连”和“项目里是否可用”的直接结论。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: execute an external API reachability probe through the repository OpenAI-compatible client and capture success/failure evidence
- [x] DoD-2: execute a real support-bot project turn with provider api_agent and confirm the response path is usable in project runtime
- [x] DoD-3: run canonical verify and record first failure point with minimal next fix strategy

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local runtime/code scan only)
- [x] Code changes allowed (`Docs/meta-only task; no code dirs touched`)
- [x] Patch applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Bind queue item + task card.
2) Run API direct connectivity probe through repository client.
3) Run support bot stdin project turn with `--provider api_agent`.
4) Capture run artifact evidence for provider path and reply output.
5) Run canonical verify and record first failure point/minimal fix.
6) Update report and queue status.

## Check / Contrast / Fix Loop Evidence

- check / contrast / fix loop:
  - check-1: API 直连探测返回 `API_OK`，证明外部 OpenAI-compatible 通道可用。
  - contrast-1: 用户反馈“API 连接不好”，但直连结果为可用，怀疑问题更可能在项目接线路径或间歇性网络。
  - fix-1: 增加项目入口实测（support bot stdin + api_agent）确认运行时真实调用链路。
  - check-2: support 运行产物显示 `provider=api_agent` 且 `provider_status=executed`。
  - contrast-2: 若仅看 stdout 文案不能证明链路，必须读取 `support_reply.json` 与 `support_session_state.json`。
  - fix-2: 记录 artifact 证据并进入 canonical verify。

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: `ctcp_support_bot --stdin --provider api_agent` 成功触发 provider 执行。
  - accumulated: support session state 记录 `provider_runtime_buffer.last_provider=api_agent`。
  - consumed: 用户可见 `support_reply.json.reply_text` 已由该 provider path 产出。

## Notes / Decisions

- Default choices made: 优先用仓库已有 API client 与 support runtime，避免额外脚本偏差。
- Alternatives considered: 仅调用 curl 测 API；不采纳（不能证明项目接线可用）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): none.
- Issue memory decision: 仅测试验证，不新增 failure memory 条目。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is a one-off validation task.

## Results

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-api-connectivity-project-wiring-check.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-api-connectivity-project-wiring-check.md`
- Verification summary:
  - `python -c "from scripts.externals.openai_responses_client import call_openai_responses; ..."` -> `0` (`RESULT=OK`, response `API_OK`)
  - `echo 现在先做一个项目内API接线测试 | python scripts/ctcp_support_bot.py --stdin --chat-id api-connectivity-check --provider api_agent` -> `0` (runtime reply produced)
  - support session evidence: `support_reply.json.provider=api_agent`, `support_reply.json.provider_status=executed`, `support_session_state.provider_runtime_buffer.last_provider=api_agent`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (run-1) -> `1` (first failure: `workflow gate`, `CURRENT.md` missing mandatory evidence sections)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (run-2, after task-card fix) -> `1` (first failure: `triplet runtime wiring contract`)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (run-3) -> `1` (first failure: `workflow gate`, `LAST.md` missing triplet command evidence; fixed)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (run-4) -> `1` (first failure: `triplet runtime wiring contract`)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (run-5, final) -> `1` (first failure: `triplet runtime wiring contract`)
  - triplet first failure detail: preexisting `frontend/response_composer.py` hint-bank `IndexError`, `run_stdin_mode` StringIO `.buffer` compatibility, Telegram poll lock cleanup `PermissionError`, and fallback mojibake assertion mismatch
  - minimal fix strategy: 在独立修复任务处理上述 runtime wiring 既有问题后重跑 canonical verify
- Queue status update suggestion (`todo/doing/done/blocked`): blocked
