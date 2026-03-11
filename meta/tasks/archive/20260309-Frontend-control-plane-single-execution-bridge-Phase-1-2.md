# Update 2026-03-09 - Frontend control plane + single execution bridge (Phase 1-2)

### Queue Binding
- Queue Item: `ADHOC-20260309-frontend-control-plane-single-bridge`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 在 CTCP 执行核心之上实现 text-first 的“类人项目经理”前端控制平面，并强制单桥执行接入。
- Scope: `frontend/*` 路由/提取/问答/脱敏流水线 + `tools/telegram_cs_bot.py` 与 `scripts/ctcp_front_bridge.py` 的执行桥接线路强化 + 对应测试。
- Out of scope: 真实语音流式 runtime、avatar/VTuber 呈现层、CTCP orchestrator 内核策略重写。

## Task Truth Source (single source for current task)

- task_purpose: 将客服/前端行为稳定为 text-first PM 控制平面，并把所有执行相关调用收敛到单一 CTCP bridge。
- allowed_behavior_change:
  - 强化 frontend conversation mode routing / requirement extraction / known-info gating / high-leverage question 选择。
  - 强化用户可见回复五阶段流水线（extract -> draft -> review -> sanitize -> final）。
  - 将 `tools/telegram_cs_bot.py` 的 new-run/status/advance/decision/upload/report 相关执行路径收敛到 `scripts/ctcp_front_bridge.py`。
  - 增补桥接与前端边界测试。
- forbidden_goal_shift:
  - 不得把工程执行逻辑迁入 frontend。
  - 不得引入并行 hidden execution path 绕开 bridge。
  - 不得扩展到实时语音/多模态完整实现。
- in_scope_modules:
  - `frontend/conversation_mode_router.py`
  - `frontend/project_manager_mode.py`
  - `frontend/response_composer.py`
  - `frontend/message_sanitizer.py`
  - `tools/telegram_cs_bot.py`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_front_api.py`
  - `tests/test_frontend_rendering_boundary.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_telegram_cs_bot_employee_style.py`
  - `meta/reports/LAST.md`
  - `meta/tasks/CURRENT.md`
- out_of_scope_modules:
  - `scripts/ctcp_orchestrate.py` 执行状态机语义
  - `src/` / `include/` C++ 执行核心
  - 实时音视频 transport 与中断处理运行时
- completion_evidence:
  - 前端边界测试通过（greeting/detail/dedupe/leakage/state consistency）
  - bridge 路径测试通过（create/status/advance/decision/upload）
  - triplet guard + canonical verify 结果已记录

## Analysis / Find (before plan)

- Entrypoint analysis:
  - 文本客服主入口：`tools/telegram_cs_bot.py`
  - 支持链路入口：`scripts/ctcp_support_bot.py`
  - bridge 入口：`scripts/ctcp_front_bridge.py`、`scripts/ctcp_front_api.py`
- Downstream consumer analysis:
  - 用户侧可见输出由 `frontend/response_composer.py` 最终闸门消费。
  - 执行状态与变更由 CTCP run artifacts（`RUN.json`/`verify_report.json`/`outbox`）和 bridge 事件消费。
- Source of truth:
  - 工程执行真源：CTCP run_dir artifacts + `scripts/verify_repo.ps1` 结果。
  - 前端会话决策真源：frontend pipeline state + support session state（仅会话，不可替代执行真源）。
- Current break point / missing wiring:
  - `tools/telegram_cs_bot.py` 当前含 `_run_orchestrate` 直接子进程调用与 target-path 直写，存在 bridge bypass 风险。
  - conversation mode / requirement / sanitizer 已有实现，但需与单桥执行路径做集成证明与回归覆盖。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: Telegram/customer 文本消息入口 `tools/telegram_cs_bot.py` 与 frontend render pipeline 调用点。
- current_module: `tools/telegram_cs_bot.py` bridge adapter + `frontend/response_composer.py` 多阶段控制平面。
- downstream: `scripts/ctcp_front_bridge.py`（ctcp_new_run/ctcp_get_status/ctcp_advance/ctcp_list_decisions_needed/ctcp_submit_decision/ctcp_upload_artifact/ctcp_get_last_report）-> CTCP run artifacts。
- source_of_truth: CTCP run_dir 状态与 `verify_report.json`；frontend 仅做可见层编排与脱敏。
- fallback: bridge 异常时仅给用户自然降级说明，不暴露内部错误细节；执行不由前端直连替代。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 前端直接写 run artifact target path 作为常规路径
  - 前端直接调用 `ctcp_orchestrate.py` 进行 new-run/advance/status 作为主路径
  - 用户可见回复中泄漏 provider/log/rc/internal prompt
- user_visible_effect:
  - 寒暄不再误触发项目规划
  - 详细需求可直接进入 PM 口径摘要与 1-2 个关键问题
  - 执行动作稳定走单桥，用户侧看到一致、自然、无内部泄漏的短文本回复

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: frontend text control plane routes greeting and smalltalk away from project planning while preserving PM-style project handling.
- [ ] DoD-2: frontend execution mutations and run-state queries go through scripts/ctcp_front_bridge.py bridge capabilities only.
- [ ] DoD-3: tests cover greeting isolation, detailed requirement understanding, duplicate-question prevention, leakage guard, single-bridge invocation path, and non-contradictory visible state.

## Acceptance (this update)

- [x] DoD written (this update section complete)
- [x] Research logged (if needed): `N/A (repo-local frontend/bridge refactor)`
- [x] Code changes allowed
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [ ] Demo report updated: `meta/reports/LAST.md`

## Plan

1) 先保持 doc/spec-first：绑定 queue + CURRENT 记录三重识别、task truth、integration check。
2) 收敛前端执行入口：在 `tools/telegram_cs_bot.py` 通过 `ctcp_front_bridge` 适配器替换 direct orchestrate/new-run/advance/status 及 decision/upload 路径。
3) 保持并补强 text-first PM 控制平面：router/extractor/known-info/question/sanitizer/final gate 行为维持一致并修复边界缺口。
4) 增补测试覆盖“单桥 enforcement + 前端可见行为稳定性”并执行本地 check/fix loop。
5) 运行 triplet guard 与 canonical verify，记录首个失败点和最小修复策略。
6) Completion criteria: prove `connected + accumulated + consumed`.

## Notes / Decisions

- Default choices made: 复用既有 frontend 模块，不新建并行执行逻辑；仅在 `telegram_cs_bot` 执行相关路径做 bridge 收敛。
- Alternatives considered: 全量重写 support bot 架构；已拒绝（超出 Phase 1-2 范围且回归风险高）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 如发现用户可见泄漏/路由误触发回归，按 triplet issue-memory contract 更新回归条目与状态。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this patch is repository-local integration wiring and does not introduce a stable reusable runtime workflow asset yet.

## Results (2026-03-09 - Frontend control plane + single bridge)

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `tools/telegram_cs_bot.py`
  - `tests/test_runtime_wiring_contract.py`

- DoD completion status:
  - [x] DoD-1: greeting/smalltalk 与项目路由隔离，PM 风格项目回复保持。
  - [x] DoD-2: frontend 执行相关路径改为 bridge（new-run/status/advance/list decisions/submit decision/upload/report）。
  - [x] DoD-3: 覆盖 greeting isolation / detailed requirement / dedupe / leakage / single-bridge / one-visible-state 的回归测试通过。

- Acceptance status:
  - [x] DoD written (this file complete)
  - [x] Research logged (if needed): `N/A (repo-local frontend/bridge refactor)`
  - [x] Code changes allowed
  - [x] Patch applies cleanly (`git diff` generated, no destructive operations used)
  - [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
  - [x] Demo report updated: `meta/reports/LAST.md`

- Verification summary:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` => `0` (15 passed)
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (20 passed)
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => `0` (22 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `1`
    - first failure gate: `lite scenario replay`
    - first failed scenario: `S16_lite_fixer_loop_pass`
    - failure detail: `step 6: expect_exit mismatch, rc=1, expect=0`
    - evidence:
      - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-225449/summary.json`
      - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-225449/S16_lite_fixer_loop_pass/TRACE.md`
      - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_external_runs/20260309-225449/S16_lite_fixer_loop_pass/sandbox/20260309-225622-687595-orchestrate/artifacts/verify_report.json`
    - minimal repair strategy:
      - 更新 `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` 对应的预期输出样本，使其匹配当前 frontend 文本口径（`B01-B06/U26` reply assertions）。
      - 保持修复范围仅限 simlab fixture 与对应断言，不扩展到运行时业务逻辑。

- Queue status update suggestion (`todo/doing/done/blocked`): `blocked` (blocked by pre-existing simlab S16 fixture drift on current baseline).

