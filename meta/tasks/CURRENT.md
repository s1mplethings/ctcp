# Task - live-api-only-all-roles-integration-tests

## Queue Binding
- Queue Item: `N/A (user-directed Live API-only pipeline integration hardening)`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json` (reference only)

## Context
- 目标是在现有 CTCP 架构下新增 Live API-only 测试模式，强制所有角色统一走 `api_agent`，验证角色契约衔接、路由正确性和故障鲁棒性。
- 需要补齐 API 调用证据链（`api_calls.jsonl` + `step_meta.jsonl`），防止 provider 被误判为 `n/a`。
- Live 测试必须默认跳过，只有显式启用且提供 API key 时才执行，保持 CI 离线友好。

## DoD Mapping (from execution_queue.json)
- [ ] DoD-1: 增加 `CTCP_FORCE_PROVIDER=api_agent` 强制路由与 fail-fast（live 模式下出现非 api_agent 立即失败并写 TRACE）。
- [ ] DoD-2: 新增 Live recipe，显式覆盖所有角色 provider 为 `api_agent`，并纳入 workflow registry。
- [ ] DoD-3: 新增 API 证据落盘：`api_calls.jsonl`（每次 `/v1/responses`）+ `step_meta.jsonl`（每步 gate/role/action/provider/inputs/outputs/rc/error）。
- [ ] DoD-4: 新增三组 Live API-only 测试（smoke/routing_matrix/robustness_faults），默认 skip，开启条件 `CTCP_LIVE_API=1` + API key。
- [ ] DoD-5: 补齐 plan-only 模板缺键最小回归测试，防止 `KeyError: 'agent'` 再发。
- [ ] DoD-6: 提供统一 Live 测试入口命令与简短运行说明文档。

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [x] Research logged (if needed): N/A (repo-local issue)
- [x] Code changes allowed
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes
- [ ] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Docs/Spec first: 更新任务单，确认必读约束与最小改动边界。
2) Implement: 强制 provider、证据日志、live recipe、API provider 细节修复。
3) Test: 新增/更新 live 测试与模板回归测试，补统一测试入口。
4) Verify: 运行针对性 `unittest` + `scripts/verify_repo.ps1`。
5) Record: 回填 `meta/reports/LAST.md`，输出统一 diff.patch。

## Notes / Decisions
- 不改 gate 状态机推进逻辑，不改 dispatcher 基础路由策略（仅增加 live 强制覆盖分支和可审计日志）。
- 不新增第三方依赖，维持 `unittest` + 现有脚本体系。
- Live 测试默认不联网执行；只有显式环境开关才触发真实 API。

## Results
- In progress.
