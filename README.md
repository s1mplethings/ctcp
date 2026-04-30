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
- formal API-only：`CTCP_FORMAL_API_ONLY=1` 时，所有关键阶段（含 `librarian/context_pack`）必须由 `api_agent` 执行

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
