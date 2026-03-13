# Task Archive

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done`

## Active Task

- Queue Item: `ADHOC-20260313-support-ctcp-scaffold-package`
- Date: 2026-03-13
- Topic: support 项目包升级为 CTCP 风格 scaffold 交付，而不是单文件占位目录
- Status: `blocked`

## Context

- Why this item now?
  用户明确指出当前交付出去的 `vn_story_organizer` 只是 `main.py + README.md` 的薄壳，不是他要的“像 CTCP 一样有一套 MD 和项目结构”的项目。继续把 repo 内 `generated_projects/` 这种占位目录直接打包发给 Telegram，会导致客服对外承诺的项目形态和真实内容不一致。
- Dependency check:
  - `ADHOC-20260313-support-api-first-local-degrade`: `blocked`
  - `ADHOC-20260309-scaffold-live-reference-mode`: `done`
- Scope boundary:
  - 只调整 support package 交付链路、用户可见包结构描述、对应 docs/tests/meta evidence。
  - 复用现有 `scripts/ctcp_orchestrate.py scaffold --source-mode live-reference` 能力，不重写 scaffold 引擎。
  - 不修改 repo 内 `generated_projects/` 内容，不把本轮 scope 扩成新的 frontend/bridge/orchestrator 架构重构。

## Task Truth Source

- task_purpose:
  让 `scripts/ctcp_support_bot.py` 在用户要求项目 zip 时，如果绑定项目目录只是单文件/薄壳占位实现，就在 support session 外部真实生成一份 CTCP 风格 scaffold 项目再打包发送；同时让客服回复基于真实包结构描述，不再把薄壳项目说成完整实现。
- allowed_behavior_change:
  - 可更新 `scripts/ctcp_support_bot.py` 的 public delivery discovery、zip materialization、support prompt context、Telegram delivery runtime。
  - 可新增 support lane 的 scaffold package materialization artifact/log。
  - 可更新 `docs/10_team_mode.md` 与 `agents/prompts/support_lead_reply.md`，同步“项目包可能是 CTCP-style scaffold”这一真实交付契约。
  - 可更新 `tests/test_support_bot_humanization.py`、`tests/test_runtime_wiring_contract.py` 覆盖 scaffold package 交付和 truth-bound package 描述。
  - 可更新 `ai_context/problem_registry.md`、`meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/reports/LAST.md` 及对应 archive 文件记录证据。
- forbidden_goal_shift:
  - 不得继续把 repo 内 `generated_projects/` 目录作为 canonical customer package 来源。
  - 不得只改 prompt 话术而不改实际 zip 交付逻辑。
  - 不得编造“已经完成的完整项目功能”，如果当前只有 scaffold，就必须按 scaffold 如实描述。
- in_scope_modules:
  - `scripts/ctcp_support_bot.py`
  - `docs/10_team_mode.md`
  - `agents/prompts/support_lead_reply.md`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260313-support-ctcp-scaffold-package.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260313-support-ctcp-scaffold-package.md`
- out_of_scope_modules:
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_dispatch.py`
  - `scripts/ctcp_orchestrate.py`
  - repo 内 `generated_projects/`
  - 与本次 support scaffold package 交付无关的其他未提交工作树改动
- completion_evidence:
  - 用户要求项目 zip 且当前项目目录只是薄壳时，Telegram runtime 会生成并发送一份外部 `scaffold --source-mode live-reference` 项目包，而不是继续打 repo 内 placeholder。
  - 客服 prompt context 能拿到真实 package shape，并能按“CTCP-style scaffold”如实描述项目结构。
  - 没有真实 screenshot artifact 时，截图仍如实说没有；项目包逻辑不再依赖 repo 内 `generated_projects/` scope 放行。
  - targeted regressions、triplet guard、workflow gate、canonical verify 留下 `connected + accumulated + consumed` 证据。

## Analysis / Find

- Entrypoint analysis:
  - 用户入口仍是 `scripts/ctcp_support_bot.py::process_message`，Telegram 文件发送落点是 `run_telegram_mode()` -> `emit_public_delivery()`。
- Downstream consumer analysis:
  - `process_message()` -> `build_support_prompt()` / `build_final_reply_doc()` -> `support_reply.json`
  - `run_telegram_mode()` -> `emit_public_delivery()` -> `resolve_public_delivery_plan()` -> Telegram `sendDocument`
- Source of truth:
  - support session `support_session_state.json`
  - bound run `artifacts/patch_apply.json` / `artifacts/PLAN.md`
  - support session public delivery artifacts
  - existing scaffold run/report artifacts generated outside repo
- Current break point / missing wiring:
  - 当前 zip 交付逻辑只会“有目录就打包目录”，不会判断目录是不是完整 CTCP-style project。
  - prompt context 不知道当前可发包到底是完整 scaffold，还是 `main.py` 这类单文件占位壳子。
  - repo 内 `generated_projects/` 还在 current PLAN 的 `Scope-Deny` 里，继续围绕它交付会卡住 canonical verify。
- Repo-local search sufficient: `yes`

## Integration Check

- upstream:
  `scripts/ctcp_support_bot.py::process_message` and `scripts/ctcp_support_bot.py::run_telegram_mode`
- current_module:
  `scripts/ctcp_support_bot.py` plus support-lane contract docs/tests
- downstream:
  `build_support_prompt()` -> `build_final_reply_doc()` -> `emit_public_delivery()` -> Telegram `sendDocument`
- source_of_truth:
  support session state + bound run delivery evidence + support scaffold materialization artifact
- fallback:
  如果 scaffold materialization 失败，则用户可见回复不能冒充完整项目；runtime 只允许回落到已有真实 package，或明确说明当前没有可发送的完整项目包
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
  - prompt-only change that still zips placeholder directories
  - editing repo-local `generated_projects/` to fake a richer package
  - describing scaffold as feature-complete business logic implementation
- user_visible_effect:
  - 用户收到的项目 zip 会更接近 CTCP 这种多文档、多目录脚手架；如果当前只是 scaffold，客服也会按 scaffold 如实描述，不再说成“完整功能已经做完”。

## Plan

1. Docs/Spec:
   绑定 queue/CURRENT/LAST/archive，并明确 support package 的新 truth 是 CTCP-style scaffold delivery。
2. Code:
   在 `scripts/ctcp_support_bot.py` 里识别薄壳项目目录，并改为外部 materialize scaffold 后再 zip/send。
3. Verify:
   跑 support bot regressions、runtime wiring、reference scaffold tests、triplet guards、workflow gate、canonical verify。
4. Report:
   回填实际交付结果、首个失败点与最小修复策略。

## Notes / Decisions

- Default choices made:
  - scaffold package 默认复用现有 `scaffold --source-mode live-reference`，profile 取更接近 CTCP 结构的 `standard`。
- Alternatives considered:
  - 直接把 repo 内 `generated_projects/` 补成完整项目；拒绝，因为这会继续踩 `Scope-Deny`，而且不是稳定的交付链。
- Any contract exception reference:
  - None.
- Issue memory decision:
  - add one new support-lane contradiction entry because this is a user-visible repeated overpromise class.
- Skill decision:
  - skillized: no, because this is a repository-local support delivery correction over an existing scaffold workflow, not a new reusable workflow asset.

## Results

- Files changed:
  - `scripts/ctcp_support_bot.py`
  - `docs/10_team_mode.md`
  - `agents/prompts/support_lead_reply.md`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260313-support-ctcp-scaffold-package.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260313-support-ctcp-scaffold-package.md`
- Verification summary:
  - `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` => `0`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (24 passed)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (15 passed)
  - `python -m unittest discover -s tests -p "test_scaffold_reference_project.py" -v` => `0` (4 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `python scripts/workflow_checks.py` => `0`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `1`
    - first failure point: `patch check (scope from PLAN)`
    - failure detail: `generated_projects/vn_story_organizer/README.md` remains out-of-scope under the repo PLAN `Scope-Allow/Scope-Deny` contract
    - minimal fix strategy: keep customer delivery on external scaffold exports and either remove/relocate the repo-local `generated_projects/` tree or open an explicit scope change before rerunning canonical verify
- Real-session demo:
  - support session `6092527664` now resolves `package_delivery_mode=materialize_ctcp_scaffold`
  - generated package path: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\support_sessions\6092527664\artifacts\support_exports\vn_story_organizer_ctcp_project.zip`
  - zip head contains `README.md`, `docs/00_CORE.md`, `meta/tasks/CURRENT.md`, `scripts/verify_repo.ps1`, `workflow_registry/README.md`, `simlab/scenarios/S00_smoke.yaml`
