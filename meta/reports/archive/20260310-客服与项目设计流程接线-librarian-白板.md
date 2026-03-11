# Update 2026-03-10 - 客服与项目设计流程接线（librarian + 白板）

### Readlist
- `docs/00_CORE.md`
- `docs/01_north_star.md`
- `docs/04_execution_flow.md`
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/03_quality_gates.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/tasks/CURRENT.md`
- `frontend/response_composer.py`
- `tools/telegram_cs_bot.py`
- `tools/local_librarian.py`
- `tests/test_telegram_cs_bot_employee_style.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_frontend_rendering_boundary.py`

### Plan
1) 在 support 通道增加 whiteboard 工件读写与 snapshot 能力。
2) 在 support turn 接入 librarian 检索，形成“提问->检索->白板记录->回问”闭环。
3) 将 whiteboard/librarian 摘要并入同一条主回复，不拆多条。
4) 删除旧会话或新目标 hard reset 时同步清理 whiteboard 工件。
5) 增补并执行回归测试，验证接线与清理行为。

### Changes
- `tools/telegram_cs_bot.py`
  - 新增 `support_whiteboard.json/.md` 常量与白板 state helper（load/save/default）。
  - 新增 `Bot._support_whiteboard_snapshot` 与 `Bot._support_librarian_whiteboard_exchange`。
  - 在 `_build_support_reply_prompt` 注入 `whiteboard_snapshot`。
  - 在 `_handle_support_turn` 将白板/检索摘要并入单条主回复，并在无问题时可补一个自然 follow-up。
  - 在 `_purge_old_session_records` 增加 whiteboard 工件清理。
  - 新增通用文本去重/白板意图识别/流程连接识别辅助函数。
- `tests/test_telegram_cs_bot_employee_style.py`
  - 新增 `test_support_turn_links_whiteboard_and_librarian_with_single_public_reply`。
  - 扩展 cleanup/new-goal 回归，校验 whiteboard 工件会被清理。
- `meta/tasks/CURRENT.md`
  - 追加本轮 task truth / integration check / verify evidence。
- `meta/reports/LAST.md`
  - 追加本轮 readlist/plan/changes/verify/demo 记录。

### Verify
- `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => `0` (29 passed)
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (20 passed)
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
- `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` => `0` (17 passed)
- `python -m py_compile tools/telegram_cs_bot.py tests/test_telegram_cs_bot_employee_style.py` => `0`

### Questions
- None.

### Demo
- 任务卡：`meta/tasks/CURRENT.md`（Update 2026-03-10 - 客服与项目设计流程接线）
- 回归用例：
  - `tests/test_telegram_cs_bot_employee_style.py::test_support_turn_links_whiteboard_and_librarian_with_single_public_reply`
  - `tests/test_telegram_cs_bot_employee_style.py::test_direct_cleanup_request_does_not_ask_archive_or_save`
  - `tests/test_telegram_cs_bot_employee_style.py::test_new_goal_hard_resets_old_state_and_enters_new_run`
- 运行期白板工件：
  - `${run_dir}/artifacts/support_whiteboard.json`
  - `${run_dir}/artifacts/support_whiteboard.md`

### Integration Proof
- upstream: Telegram message entrypoint `Bot._handle_message`.
- current_module: `Bot._handle_support_turn` + `Bot._support_librarian_whiteboard_exchange`.
- downstream: `_send_customer_reply`（用户可见单一回复）和 `_build_support_reply_prompt`（provider 读取 whiteboard snapshot）。
- source_of_truth: `artifacts/support_whiteboard.json` + `artifacts/support_session_state.json`.
- fallback: librarian 不可用/检索失败时降级为仅白板记录与自然客服回复，不阻断执行桥接主链路。
- acceptance_test:
  - `tests/test_telegram_cs_bot_employee_style.py` 新增白板接线回归。
  - `tests/test_support_bot_humanization.py` 清理/人性化回归。
  - `tests/test_runtime_wiring_contract.py` 单桥接线回归。
  - `tests/test_frontend_rendering_boundary.py` 前端回复边界回归。
- forbidden_bypass:
  - bypass `_send_customer_reply` 直接多条发送内部文本。
  - 未落盘白板工件仅靠 prompt 描述“已协同”。
  - 清理路径遗漏 whiteboard 残留旧状态。
- user_visible_effect: 用户在一条回复内可看到“已用 librarian 检索并记录白板”的自然表述，并继续收到最多一个关键问题。

