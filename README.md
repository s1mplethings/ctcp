# CTCP — Goal To MVP Project Generator

Human navigation map:

- Agent main contract: `AGENTS.md`
- Repo purpose: `docs/01_north_star.md`
- Expanded workflow reference: `docs/04_execution_flow.md`
- Current task purpose/scope: `meta/tasks/CURRENT.md`
- Runtime engineering truth: `docs/00_CORE.md`
- Frontend/backend separation boundary: `docs/42_frontend_backend_separation_contract.md`

This README is human-oriented quickstart and navigation. It does not act as the root agent contract.
CTCP focuses on structured execution, customized delivery, visible progress, and token-efficient reliability rather than brute-force giant-context generation.

---

## Product Promise

CTCP is not a brute-force coding agent.

CTCP is a structured goal-to-delivery generation system that turns vague user goals into customized runnable MVPs, visible progress evidence, and verifiable delivery packages.

Its mainline is:

`Goal -> Intent -> Spec -> Scaffold -> Core Feature -> Smoke Verify -> Demo Evidence -> Delivery Package`

CTCP does not optimize for giant-context code dumping or generic one-shot project generation.  
It optimizes for making projects **more structured, more customized, more visible during execution, and more reliable to deliver**.

### What CTCP is good at

- **Structured execution**  
  Work advances through explicit stages instead of freeform generation drift.

- **Customized runnable MVPs**  
  Output should match the user's actual goal, constraints, style, and delivery shape rather than a generic demo.

- **Visible progress**  
  Intermediate tests, screenshots, previews, smoke results, or other user-visible checkpoints should appear whenever the routed task supports them.

- **Token-efficient reliability**  
  CTCP prefers stage artifacts, bounded context, and verify-driven repair loops over repeatedly reloading the entire repo into context.

- **Verify-gated completion**  
  Completion means more than generating files. The result should be suitable for inspection, testing, demonstration, and user-facing delivery.

### What CTCP is not

- Not a generic bigger-context-is-better shell.
- Not a brute-force project generator that treats raw code volume as success.
- Not an artifact-first shell where verify, manifest, or evidence impersonate generated product value.
- Not a black-box run-until-done system when visible intermediate evidence can be shown.

### Supporting layer vs product value

Audit, verify, manifest, and evidence artifacts still matter. They remain essential support-layer components for:

- proving that the generation chain actually ran,
- exposing the first failure point,
- enabling minimal repair loops,
- and strengthening delivery trust.

But they are not the product by themselves.  
The product is the structured generation and delivery mainline that turns a vague goal into a runnable, testable, demoable, deliverable MVP.

---

## Quick Start

For agents:
- start from `AGENTS.md`
- bind the current task in `meta/tasks/CURRENT.md`

For operators or humans running the runtime pipeline:

运行入口（runtime orchestrator）：
```powershell
python scripts\ctcp_orchestrate.py new-run --goal "your-goal"
python scripts\ctcp_orchestrate.py advance --max-steps 8
```

显式隔离的 agent manifest 生成模式：
```powershell
python scripts\ctcp_orchestrate.py agent-manifest --input tests\agent_factory_benchmark\fixtures\input_devops_incident.json --output out\agent_manifest.json
```

独立入口仍可用：
```powershell
python scripts\generate_agent_manifest.py --input tests\agent_factory_benchmark\fixtures\input_devops_incident.json --output out\agent_manifest.json
```

`agent-manifest` 是显式 subcommand，不会作为默认 project generation 路径触发；普通项目生成仍使用 `new-run/status/advance` 主链。更多说明见 `docs/agent_manifest_mode.md`。

从 manifest 生成最小 runtime scaffold：
```powershell
python scripts\ctcp_orchestrate.py agent-scaffold --manifest out\agent_manifest.json --output-dir out\agent_project
python scripts\generate_agent_scaffold.py --manifest out\agent_manifest.json --output-dir out\agent_project
```

scaffold 是显式隔离的 minimal local deterministic runtime；它会保留权限、guardrails、workflow 和 tests，并提供安全 dry-run 与本地 real run：
```powershell
cd out\agent_project
python run_agent.py --dry-run --input sample_input.json
python run_agent.py --input sample_input.json
python -m unittest discover tests -v
```

dry-run 不执行 tools，也不写 `runtime_state.json`、`planner_trace.json` 或 `audit/events.jsonl`。real run 默认使用 bounded deterministic planner loop：planner 选择下一步 tool action，但权限仍只由 generated policy layer 决定。runtime 通过 generated tool registry、policy layer、executor 和 ToolResult schema 处理工具，只执行 exact allowed adapters，写 `planner_trace.json` 和 `runtime_state.json`，追加 `audit/events.jsonl`，high-risk tools blocked 或 pending，`requires_approval=true` tools 进入 pending approval，unknown/unsupported tools 不会当成功。

Planner 模式默认是：

```powershell
$env:CTCP_AGENT_PLANNER='deterministic'
```

`CTCP_AGENT_PLANNER=provider` 当前只是接口路径；未配置真实 provider 时会清楚失败为 `provider_planner_unavailable`，不会伪造成功，也不会调用外部 API。`final_answer` 会包含 `text`、`sources`、`pending_approvals`、`blocked_tools` 和 `executed_tools`。

Web access 是显式 manifest-only 能力，不会默认给所有 agent 开启。只有 manifest 声明 exact `web_search` / `fetch_url`，policy 确认 `side_effect_level=none`、`requires_approval=false`、`audit_log_required=true` 且 selected agent 在 `allowed_callers` 中时才会执行。当前只实现 deterministic fixture provider：

```powershell
$env:CTCP_AGENT_WEB_PROVIDER='fixture'
```

未配置 provider 时，web tools 返回 failed ToolResult（`web_provider_unavailable`）并写 audit；当前没有实现真实互联网 provider，也不接真实外部 API。Web-derived output 必须包含 `sources` / `source` citation metadata，audit 会记录 query 和 URL。

`agent-scaffold` 也是显式 subcommand，不会影响普通项目生成。更多说明见 `docs/agent_scaffold_mode.md`。

从需求到 manifest、scaffold、dry-run、scaffold tests 和 pipeline report 的完整显式管线：
```powershell
python scripts\ctcp_orchestrate.py agent-project --input tests\agent_factory_benchmark\fixtures\input_devops_incident.json --output-dir runs\agent_project_devops
```

`agent-project` 会生成 `manifest.json`、`scaffold/`、`pipeline_report.json` 和 `pipeline_report.md`。它不会默认触发普通项目生成；高风险 tools 在 runtime 中 blocked 或 pending approval，不会执行。每个 planner-selected tool decision 都写入 `tool_decision` audit event，并以 ToolResult 返回；planner trace 和 final answer 也会进入 runtime evidence。更多说明见 `docs/agent_project_pipeline.md`。

验收入口（Windows，作为支撑验证，不是生成本身）：
```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1
```

验收入口（Unix）：
```bash
bash scripts/verify_repo.sh
```

## Verify Contract (Canonical Names)

- DoD gate entrypoint 只有 `scripts/verify_repo.ps1` / `scripts/verify_repo.sh`。
- 运行级机器可读验收主产物是 `artifacts/verify_report.json`（位于外部 run_dir）。
- `proof.json` 不是当前硬规则验收产物，仅可作为兼容遗留项。
- `verify_report.md` 是可选的人类可读总结，不是权威 gate 判据。
- verify 负责回答“项目是否真的可运行、可交付、可追溯”，而不是替代 ProjectIntent 和 generation pipeline。

## Mainline Canonical Surface

- 唯一执行入口：`scripts/ctcp_orchestrate.py`
- 唯一产品主线 workflow id：`wf_project_generation_manifest`
- 唯一 freeze 真相面：`docs/architecture/contracts/default_mainline_freeze_contract.md` 与 `artifacts/mainline_freeze_manifest.json`
- 唯一责任账本面（run_dir）：`artifacts/run_responsibility_manifest.json`
- formal API-only：`CTCP_FORMAL_API_ONLY=1` 时，关键 API 阶段必须由 `api_agent` 执行；`librarian/context_pack` 为本地固定例外（`local_exec`）

---

## Mainline Outputs

主链输出分为两层：

- 产品主链：
  - `ProjectIntent`
  - `Project Spec`
  - runnable scaffold
  - core feature implementation
  - smoke-run evidence
  - delivery package
- 支撑层：
  - verify report
  - run artifacts
  - task/report pointers

## What Orchestrator Produces

- `meta/tasks/CURRENT.md`：任务单（首次缺失时自动从模板生成）
- `meta/reports/LAST.md`：演示报告（首次缺失时自动生成最小文件）
- `${CTCP_RUNS_ROOT:-~/.ctcp/runs}/ctcp/<run_id>/`：一次运行目录（artifacts/reviews/outbox/logs）
- `meta/run_pointers/LAST_RUN.txt`：仓库内指针，指向最新外部 run 包绝对路径
- `${run_dir}/artifacts/verify_report.json`：运行级机器可读验收报告（canonical）

## Concrete Project Generation Matrix

普通 concrete project generation 仍走 `new-run/status/advance`，并在 `analysis` 后进入 `source_generation` 写出 `project_output`。它不会使用 `agent-manifest`、`agent-scaffold` 或 `agent-project` 冒充普通项目。

当前 concrete matrix 覆盖：

- `todo_rest_api`：SQLite-backed `/todos` CRUD。
- `markdown_notes_api`：filesystem markdown note storage, list/search/update/delete。
- `simple_auth_api`：SQLite users/sessions, password hashing, login token, protected `/me`。
- `local_task_board_app`：small full-stack local app with static HTML/CSS/JS, `/api/tasks`, and SQLite-backed task persistence。
- `local_kanban_board_app`：full-stack local Kanban board with static frontend, boards/cards API, card move workflow, and SQLite persistence。
- `csv_expense_analyzer`：argparse CLI, CSV parsing, category/monthly totals, JSON report output。
- `log_analyzer_cli`：argparse CLI, INFO/WARN/ERROR counts, top error message extraction。
- `text_utils_package`：importable Python package with text utility functions and generated tests。
- `terminal_quiz_game`：terminal quiz CLI with JSON questions and deterministic `--test-mode` scoring。

矩阵、full-stack、non-web benchmark 会真实运行 generated tests；API/full-stack 会启动本地 HTTP server 并调用 endpoints，non-web 会运行 CLI/package/game validation。bounded fast paths 只在明确匹配的 concrete categories 中启用，通过 fast path registry 分派，并在 `artifacts/project_generation_provenance.json` 记录 `generation_mode`、`project_type`、`provider_authorship=not_claimed`、`local_materializer_used=true` 和 `repair_attempts`。普通 concrete benchmarks 还会写 `artifacts/generation_attribution.json`，明确 `used_agent_project=false`、`used_agent_scaffold=false`、`used_local_agent_runtime=false`，并暴露 local materializer / provider authorship evidence。

Provider-assisted generation 是一个显式 ordinary generation mode，不是默认 provider-authored generation。启用时仍走 `new-run/status/advance` 和 deterministic materializer，只允许 provider/local fixture 参与低风险 helper、docs、formatting 或 frontend enhancement 片段；片段必须通过大小、语法和安全 token 过滤，失败时回退到 deterministic output。Attribution 会记录 `generation_mode=provider_assisted`、`used_provider_agent=true`、`provider_authorship=provider_assisted`、`provider_assisted_sections`、`provider_generated_files`、`provider_fallbacks` 和 `provider_validation`。当前 benchmark provider 是本地 fixture/guardrail 模式，不代表完全 autonomous provider-authored generation。

`live_provider_assisted` 是更窄的 smoke path：真实 provider 只被调用来生成 bounded helper/docs/frontend-helper fragments，不能接管 server core、DB、validators、benchmark 或 orchestrator。Attribution 会额外记录 `live_provider_used`、`provider_request_count`、`provider_fragment_count`、`provider_generated_files` 和 fallback/validation evidence；runtime behavior 仍由 deterministic materializer 与 benchmark validators 验证。

`live_provider_full_candidate` 让真实 provider 返回完整小项目 candidate，但仍只支持 `live_provider_text_stats_cli` 和 `live_provider_password_policy_package` 这类小型非 server 项目。candidate 必须是 structured file manifest，CTCP 会验证路径、安全 token、syntax/import、generated tests 和 runtime behavior；有效 candidate 可接受，可修复 candidate 会记录 `provider_candidate_repaired=true`，非法 candidate 会 deterministic fallback。Attribution 会记录 `provider_project_candidate_count`、`provider_candidate_accepted`、`provider_candidate_validation`、`provider_generated_files` 和 `fallback_triggered`。

`live_provider_blind_candidate` 在同一 ordinary mainline 上测试以前没有专用 deterministic fast path 的小项目需求。Blind matrix 当前覆盖 unit converter CLI、file renamer dry-run CLI、markdown table formatter、JSON config validator package、static site generator。Live provider 仍必须返回 structured file manifest；CTCP 只允许 path-safe、stdlib-only、无 eval/exec/subprocess/network 的候选进入 validation，并用最多一次 bounded repair 分类为 `accepted|repaired|fallback|unsupported|failed`。Benchmark pass 要求 `failed_count=0` 且 `accepted_count + repaired_count >= 3`。

运行：

```powershell
python tests\concrete_project_matrix\run_matrix_benchmark.py
python tests\full_stack_app_benchmark\run_full_stack_benchmark.py
python tests\non_web_project_matrix\run_non_web_matrix.py
python tests\provider_assisted_benchmark\run_provider_assisted_benchmark.py
python tests\live_provider_benchmark\run_live_provider_benchmark.py
python tests\live_provider_full_candidate_benchmark\run_live_provider_full_candidate_benchmark.py
python tests\live_provider_blind_matrix\run_live_provider_blind_matrix.py
```

更多说明见 `docs/project_generation.md` 和 `docs/concrete_project_pipeline.md`。

---

## Build

默认 headless 构建：

```powershell
cmake -S . -B build_lite
cmake --build build_lite --config Release
```

当前仓库只保留 headless 可执行目标：`ctcp_headless`。更多见 `BUILD.md`。

---

## Project Scaffold Modes

`scaffold` 和 `scaffold-pointcloud` 支持双模式：

- `--source-mode template`（默认，保持现有模板行为）
- `--source-mode live-reference`（从当前 CTCP 仓库按白名单受控导出）

示例（pointcloud）：

```powershell
python scripts\ctcp_orchestrate.py scaffold-pointcloud --out D:\v2p_projects\demo_v2p --name demo_v2p --profile minimal --source-mode live-reference --runs-root D:\ctcp_runs
```

更多说明见 `docs/40_reference_project.md`，导出清单真源见 `meta/reference_export_manifest.yaml`。
低能力模型友好的完整项目生成硬约束见 `docs/41_low_capability_project_generation.md`。

---

## Doc Index

<!-- CTCP:DOC_INDEX:BEGIN -->
<!-- (auto-generated by scripts/sync_doc_links.py; curated list) -->

## Project Docs

- [AGENTS.md](AGENTS.md)
- [README.md](README.md)
- [BUILD.md](BUILD.md)
- [PATCH_README.md](PATCH_README.md)
- [docs/20_conventions.md](docs/20_conventions.md)
- [docs/PATCH_CONTRACT.md](docs/PATCH_CONTRACT.md)
- [TREE.md](TREE.md)
- [docs/00_CORE.md](docs/00_CORE.md)
- [docs/01_north_star.md](docs/01_north_star.md)
- [docs/00_overview.md](docs/00_overview.md)
- [docs/01_architecture.md](docs/01_architecture.md)
- [docs/02_workflow.md](docs/02_workflow.md)
- [docs/03_quality_gates.md](docs/03_quality_gates.md)
- [docs/04_execution_flow.md](docs/04_execution_flow.md)
- [docs/05_agent_mode_matrix.md](docs/05_agent_mode_matrix.md)
- [docs/25_project_plan.md](docs/25_project_plan.md)
- [docs/10_team_mode.md](docs/10_team_mode.md)
- [docs/21_paths_and_locations.md](docs/21_paths_and_locations.md)
- [docs/22_teamnet_adlc.md](docs/22_teamnet_adlc.md)
- [docs/22_agent_teamnet.md](docs/22_agent_teamnet.md)
- [docs/30_artifact_contracts.md](docs/30_artifact_contracts.md)
- [docs/40_reference_project.md](docs/40_reference_project.md)
- [docs/12_modules_index.md](docs/12_modules_index.md)
- [docs/13_contracts_index.md](docs/13_contracts_index.md)
- [docs/SELF_CHECK_SYSTEM.md](docs/SELF_CHECK_SYSTEM.md)
- [docs/cleanup_policy.md](docs/cleanup_policy.md)
- [ai_context/00_AI_CONTRACT.md](ai_context/00_AI_CONTRACT.md)
- [ai_context/CTCP_FAST_RULES.md](ai_context/CTCP_FAST_RULES.md)
- [ai_context/problem_registry.md](ai_context/problem_registry.md)
- [ai_context/decision_log.md](ai_context/decision_log.md)

<!-- CTCP:DOC_INDEX:END -->

---

## Notes

- 本仓库默认先澄清 `ProjectIntent`，再推进最小可运行实现。
- docs/spec/meta 仍然重要，但它们不能替代真实生成与可运行交付。
- “禁止代码”由 `scripts/workflow_checks.py` 强制执行（不满足直接 fail）。
