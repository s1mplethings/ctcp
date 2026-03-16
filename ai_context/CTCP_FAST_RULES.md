# CTCP Fast Rules (Hard)

> Fast mirror only. Root agent entry is `AGENTS.md`.

<!-- TOC -->
| 区域 | 锚点 |
|------|------|
| 9 条硬规则 | [→](#hard-rules) |
| Concern→文件速查 | [→](#concern-file-map) |
| Agent 最小启动清单 | [→](#agent-minimal-startup) |
<!-- /TOC -->

## Hard Rules

1. DoD gate entrypoint is only `scripts/verify_repo.ps1` (Windows) or `scripts/verify_repo.sh` (Unix).
2. Final chat/console output must be patch-only unified diff; no report body in output.
3. Report body must be written to `meta/reports/LAST.md`.
4. Canonical verify artifact is `artifacts/verify_report.json` in external `run_dir` (`TRACE.md` + related artifacts).
5. `proof.json` is deprecated and non-authoritative; `verify_report.md` is optional human-readable material only.
6. Proceed by default; only ask when blocked by credentials/permissions, mutually exclusive decisions, or missing critical constraints.
7. The visible agent flow is defined in `AGENTS.md`; `docs/04_execution_flow.md` is the expanded reference. Do not redefine either locally.
8. Verification profiles (`doc-only`, `contract`, `code`) are supported via `--Profile`/`--profile` flag, `CTCP_VERIFY_PROFILE` env, or auto-detection. Default is `code`. See `docs/00_CORE.md` §9.1 and `docs/04_execution_flow.md` Step 9.
9. Cleanup follows archive-first policy for knowledge assets; hard delete only for generated/temp artifacts. See `docs/cleanup_policy.md`.

## Concern→File Map

> 一个 concern 只有一个权威文件。冲突时按此表分流。

| Concern | 权威文件 |
|---------|---------|
| Repo purpose | `docs/01_north_star.md` |
| Agent main contract | `AGENTS.md` |
| Expanded execution flow | `docs/04_execution_flow.md` |
| Current task scope | `meta/tasks/CURRENT.md` |
| Runtime truth | `docs/00_CORE.md` |
| AI system contract | `ai_context/00_AI_CONTRACT.md` |
| This fast-rules file | `ai_context/CTCP_FAST_RULES.md` |
| Verify gate scripts | `scripts/verify_repo.ps1` / `.sh` |
| Problem registry | `ai_context/problem_registry.md` |
| Decision log | `ai_context/decision_log.md` |

## Agent Minimal Startup

新任务只需读 3 类信息就能开始：

1. **`AGENTS.md`** — 根级 agent 主合同
2. **`meta/tasks/CURRENT.md`** — 当前任务范围
3. **任务相关文件** — 按 CURRENT.md `in_scope_modules` 定位

本文件只是速查，不替代根合同。
