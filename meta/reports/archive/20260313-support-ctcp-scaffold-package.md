# Demo Report - Archive

## Topic

- Queue Item: `ADHOC-20260313-support-ctcp-scaffold-package`
- Date: 2026-03-13
- Topic: support 项目包升级为 CTCP 风格 scaffold 交付，而不是单文件占位目录
- Status: `blocked`

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `docs/00_CORE.md`
- `docs/01_north_star.md`
- `docs/04_execution_flow.md`
- `docs/03_quality_gates.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `docs/10_team_mode.md`
- `docs/40_reference_project.md`
- `scripts/patch_check.py`
- `tools/scaffold.py`
- `tests/test_scaffold_reference_project.py`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `agents/prompts/support_lead_reply.md`
- `scripts/ctcp_support_bot.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_runtime_wiring_contract.py`

### Plan
1. 把 support package 的 truth 改成“placeholder -> external CTCP scaffold -> zip”。
2. 修改 `scripts/ctcp_support_bot.py`，识别薄壳项目目录并 materialize scaffold project。
3. 把真实 package shape 注入 prompt/context，并同步 docs/prompt 契约。
4. 跑 support/runtime/scaffold 回归与 canonical verify。

### Changes
- `scripts/ctcp_support_bot.py`
  - added package-shape detection for CTCP project dirs vs. thin placeholder dirs
  - added support-side scaffold materialization artifact/logs
  - rewired zip delivery so thin placeholder dirs now materialize an external scaffold project before zipping
  - exposed `package_delivery_mode`, `project_name_hint`, and `package_structure_hint` to the support prompt/runtime context
- `agents/prompts/support_lead_reply.md`, `docs/10_team_mode.md`
  - locked the contract so scaffold packages must be described honestly as scaffold
- `tests/test_support_bot_humanization.py`, `tests/test_runtime_wiring_contract.py`
  - added regressions for scaffold package context and Telegram document delivery from placeholder-project sessions
- `ai_context/problem_registry.md`
  - recorded the placeholder-package overpromise defect
- `meta/backlog/execution_queue.json`, `meta/tasks/CURRENT.md`, `meta/tasks/archive/20260313-support-ctcp-scaffold-package.md`, `meta/reports/LAST.md`, `meta/reports/archive/20260313-support-ctcp-scaffold-package.md`
  - bound and reported the task

### Verify
- `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` => `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (24 passed)
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (15 passed)
- `python -m unittest discover -s tests -p "test_scaffold_reference_project.py" -v` => `0` (4 passed)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
- `python scripts/workflow_checks.py` => `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `1`
  - first failure point: `patch check (scope from PLAN)`
  - failure detail: `generated_projects/story_organizer/README.md` remains out-of-scope under the repo PLAN contract
  - minimal fix strategy: keep delivery artifacts on external scaffold exports and either remove/relocate the repo-local `generated_projects/` tree or open an explicit scope change before rerunning canonical verify

### Questions
- None.

### Demo
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `meta/tasks/archive/20260313-support-ctcp-scaffold-package.md`
- `meta/reports/archive/20260313-support-ctcp-scaffold-package.md`
- real support session `6092527664` resolves `package_delivery_mode=materialize_ctcp_scaffold`
- generated package: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\support_sessions\6092527664\artifacts\support_exports\story_organizer_ctcp_project.zip`
- zip head contains `README.md`, `docs/00_CORE.md`, `meta/tasks/CURRENT.md`, `scripts/verify_repo.ps1`, `workflow_registry/README.md`, `simlab/scenarios/S00_smoke.yaml`

### Integration Proof
- upstream: `scripts/ctcp_support_bot.py::process_message` and `scripts/ctcp_support_bot.py::run_telegram_mode`
- current_module: `scripts/ctcp_support_bot.py` plus support-lane contract docs/tests
- downstream: `build_support_prompt()` / `build_final_reply_doc()` -> `support_reply.json` -> `emit_public_delivery()` -> Telegram `sendDocument`
- source_of_truth: support session `support_session_state.json`, bound run `artifacts/patch_apply.json` / `artifacts/PLAN.md`, support session `support_scaffold_materialization.json`, support session `support_public_delivery.json`
- fallback: existing complete CTCP-like project dirs still zip directly; placeholder dirs first materialize an external scaffold; scaffold failure records an artifact and must not be described as a complete project package
- acceptance_test:
  - `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_scaffold_reference_project.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - prompt-only wording patch without runtime package-materialization changes
  - editing repo-local `generated_projects/` to fake a richer deliverable
  - continuing to zip placeholder dirs while describing them as complete projects
- user_visible_effect:
  - 用户现在收到的 剧情项目 zip 是 CTCP 风格多文档脚手架，而不是单 `main.py` 占位目录；客服也会按 scaffold 如实描述这个包的结构。
