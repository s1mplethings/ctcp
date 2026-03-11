# Update 2026-03-10 - 客服与项目设计流程接线（librarian + 白板）

### Queue Binding
- Queue Item: `ADHOC-20260310-support-project-whiteboard-librarian`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`（adhoc 追加）

### Context
- Goal: 把客服会话与项目设计流程接线，通过 librarian 检索与白板记录形成“提问-检索-回问-继续推进”的单轮闭环。
- Scope:
  - `tools/telegram_cs_bot.py` 增加 support whiteboard 状态工件与 librarian 接线。
  - 用户可见回复维持单条主回复，白板/检索摘要并入主回复，不拆多条。
  - 旧会话清理/新目标 hard reset 时同步清理 whiteboard 工件。
  - 增补最小回归测试覆盖白板接线与清理行为。
- Out of scope:
  - orchestrator 状态机语义变更
  - CTCP planner/chair/librarian 主流程协议重构
  - 新依赖引入

### Task Truth Source (single source for current task)

- task_purpose: 让客服通道能够和项目设计流程共享“白板 + librarian”检索上下文，并保持单一用户可见输出。
- allowed_behavior_change:
  - 新增 `artifacts/support_whiteboard.json` / `artifacts/support_whiteboard.md` 的会话级白板记录。
  - 在 support turn 中接入 `tools.local_librarian.search`（可选/容错），把检索结果写入白板并生成自然客服摘要。
  - 在 `_build_support_reply_prompt` 注入 whiteboard snapshot，供 reply provider 读取。
  - 扩展清理路径，删除旧会话时同时清掉 whiteboard 工件。
  - 测试覆盖白板接线与清理。
- forbidden_goal_shift:
  - 不得把 frontend/support 变成并行执行引擎，执行修改仍走 bridge。
  - 不得向用户泄露内部路径/工件名（analysis/outbox/run_dir 等）。
  - 不得恢复 archive-first 清理行为。
- in_scope_modules:
  - `tools/telegram_cs_bot.py`
  - `tests/test_telegram_cs_bot_employee_style.py`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - `scripts/ctcp_orchestrate.py`
  - `frontend/response_composer.py`（本轮无行为改动）
  - `src/` / `include/`
- completion_evidence:
  - support turn 可写入 whiteboard + librarian 检索条目。
  - 用户回复保持单条主回复并包含白板协作摘要。
  - cleanup/new-goal hard reset 后 whiteboard 工件被清理。
  - 相关单测通过。

### Analysis / Find (before plan)

- Entrypoint analysis:
  - 用户入口：`Bot._handle_message -> _handle_support_turn`。
- Downstream consumer analysis:
  - 用户可见输出：`_send_customer_reply` 单一公开闸门。
  - provider 输入：`_build_support_reply_prompt`。
- Source of truth:
  - 会话真源：`artifacts/support_session_state.json`
  - 白板真源：`artifacts/support_whiteboard.json`
- Current break point / missing wiring:
  - 原有链路缺少“客服 <-> 项目设计”共享白板与 librarian 互问互查。
  - 清理旧会话时未覆盖白板工件（新增后需同步清理）。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

### Integration Check (before implementation)

- upstream: Telegram text turn (`tools/telegram_cs_bot.py::_handle_message`).
- current_module: `Bot._support_librarian_whiteboard_exchange` + whiteboard load/save helpers.
- downstream: `_send_customer_reply`（用户侧）与 `_build_support_reply_prompt`（provider 侧 whiteboard snapshot）。
- source_of_truth: `artifacts/support_whiteboard.json`（白板）+ `artifacts/support_session_state.json`（会话）。
- fallback: `local_librarian` 不可用或检索异常时，仅记录白板提问并继续客服回复，不阻断主流程。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v`
- forbidden_bypass:
  - 直接多条 send 绕过 `_send_customer_reply` 主闸门。
  - 仅在 prompt 文本中宣称白板协同但不落盘工件。
  - 清理路径遗漏 whiteboard 导致旧状态残留。
- user_visible_effect:
  - 用户能在同一条回复中感知“已写入白板 + 已检索线索 + 下一步问题”。
  - 删除旧会话后旧白板记录不再污染新项目。

### DoD Mapping (from request)

- [x] DoD-1: support turn 增加 librarian + whiteboard 协同接线并落盘。
- [x] DoD-2: 用户可见输出保持单条主回复（白板摘要并入，不拆多条）。
- [x] DoD-3: reply provider prompt 可读取 whiteboard snapshot。
- [x] DoD-4: cleanup/new-goal reset 同步清理 whiteboard 工件。
- [x] DoD-5: 最小回归测试覆盖白板接线与清理行为。

### Acceptance (this update)

- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first task update included
- [x] Targeted tests pass
- [ ] `scripts/verify_repo.*` full pass（本轮仅执行 targeted test set）
- [x] `meta/reports/LAST.md` updated in same patch

### Plan

1) 在 `telegram_cs_bot` 增加 whiteboard state load/save 与 snapshot。
2) 在 support turn 加入 librarian 检索 + 白板写入 + 单条回复并入策略。
3) 在 provider prompt 注入 whiteboard snapshot。
4) 扩展 purge/reset 路径清理 whiteboard 工件。
5) 增补并执行回归测试，记录结果。

### Notes / Decisions

- Default choices made: 采用 repo-local `tools.local_librarian.search`；不引入新依赖。
- Alternatives considered: 新建独立 whiteboard service；拒绝（超出最小改动范围）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 本轮未观察新的用户可见泄漏/回归，暂不新增 issue_memory 条目。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this patch is repository-local integration wiring and not a stable reusable skill asset yet.

### Results (2026-03-10 - support/project whiteboard+librarian loop)

- Files changed:
  - `tools/telegram_cs_bot.py`
  - `tests/test_telegram_cs_bot_employee_style.py`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`

- Verification summary:
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => `0` (29 passed)
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (20 passed)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` => `0` (17 passed)
  - `python -m py_compile tools/telegram_cs_bot.py tests/test_telegram_cs_bot_employee_style.py` => `0`

- Queue status update suggestion (`todo/doing/done/blocked`): `done` (targeted wiring + regression coverage complete).

