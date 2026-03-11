# Update 2026-03-07 - 模拟用户对话生成类人测试集（Dialogue Sim V1）

### Readlist
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/tasks/CURRENT.md`
- `meta/tasks/TEMPLATE.md`
- `tools/telegram_cs_bot.py`
- `tests/test_support_bot_suite_v1.py`
- `tests/test_telegram_cs_bot_dataset_v1.py`

### Plan
1) 以“我来扮演用户”方式构建多轮对话场景，生成测试案例集。
2) 将案例集落盘到 fixture，并补充说明文档。
3) 新增数据驱动回放测试，逐轮喂给 bot 做基础类人卫生检查。
4) 执行新增测试 + 相关 Telegram/support 回归。
5) 运行 `scripts/verify_repo.ps1` 并记录首个失败点。

### Changes
- `tests/fixtures/telegram_human_dialogue_sim_v1/README.md`（新增）
  - 说明该数据集来自“模拟用户多轮对话”，用途是类人回复回放与基础卫生检查。
- `tests/fixtures/telegram_human_dialogue_sim_v1/cases.jsonl`（新增）
  - 新增 20 条 simulated dialogue cases（中英混合、不同 persona、2-3 轮用户输入）。
- `tests/test_telegram_human_dialogue_sim_v1.py`（新增）
  - `test_fixture_schema_and_coverage`：检查 schema、ID 唯一性、语言覆盖。
  - `test_dialogue_replay_human_hygiene`：逐轮回放并验证：
    - 回复非空；
    - 不含内部泄漏标记（`diff --git/trace.md/logs/outbox/artifacts/run_dir/stack trace`）；
    - 单条回复问句数不超过阈值。
- `meta/tasks/CURRENT.md`
  - 新增本次任务 update 与 DoD/Acceptance/Plan。
- `meta/reports/LAST.md`
  - 新增本节可审计报告。

### Verify
- `python -m unittest discover -s tests -p "test_telegram_human_dialogue_sim_v1.py" -v` => exit 0
  - result: 2 tests passed
- `python -m unittest discover -s tests -p "test_telegram_cs_bot_*.py" -v` => exit 0
  - result: 19 tests passed
- `python -m unittest discover -s tests -p "test_support_router_and_stylebank.py" -v` => exit 0
  - result: 5 tests passed
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit 1
  - first failure gate: `lite scenario replay`
  - replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-153355/summary.json`
  - summary: `passed=12 failed=2`
  - failed scenarios:
    - `S15_lite_fail_produces_bundle`: `missing expected text: failure_bundle.zip`
    - `S16_lite_fixer_loop_pass`: `expect_exit mismatch, rc=1, expect=0`
- Minimal repair strategy (first-failure focused):
  - S15: 同步 S15 断言与当前 fixer prompt 文案，确保包含 `failure_bundle.zip` 期望文本。
  - S16: 更新 `lite_fix_remove_bad_readme_link.patch` 使其适配当前 `README.md`。

### Questions
- None.

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- New fixture:
  - `tests/fixtures/telegram_human_dialogue_sim_v1/README.md`
  - `tests/fixtures/telegram_human_dialogue_sim_v1/cases.jsonl`
- New test:
  - `tests/test_telegram_human_dialogue_sim_v1.py`
- Verify replay summary:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-153355/summary.json`
- Verify failure bundles:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-153355/S15_lite_fail_produces_bundle/failure_bundle.zip`
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-153355/S16_lite_fixer_loop_pass/failure_bundle.zip`

