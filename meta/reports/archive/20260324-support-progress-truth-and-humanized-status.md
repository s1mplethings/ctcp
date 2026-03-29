# Report - support-progress-truth-and-humanized-status

## Summary

- Topic: 客服进度真值修复与状态回复去机械化
- Date: 2026-03-24
- Queue Item: `ADHOC-20260324-support-progress-truth-and-humanized-status`
- Result: `done`

## Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `scripts/ctcp_support_bot.py`
- `scripts/ctcp_support_controller.py`
- `scripts/ctcp_dispatch.py`
- `frontend/response_composer.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_frontend_rendering_boundary.py`
- `tests/test_provider_selection.py`

## Plan

1. Bind ADHOC item and update CURRENT task truth.
2. Fix progress truthing for `running + gate.blocked` internal states.
3. Fix proactive dedupe drift by keeping controller status hash stable in support memory writes.
4. Adjust progress reply wording to reduce rigid repeated phrasing.
5. Add focused regressions for blocker truthing and dedupe stability.
6. Run focused tests and canonical verify.

## Changes

- `scripts/ctcp_support_bot.py`
  - `build_progress_binding` now treats internal `gate.state=blocked` as blocker even when `run_status=running`.
  - `remember_progress_notification` accepts `status_hash` override and preserves controller hash domain.
  - proactive emit path passes controller job `status_hash` into progress memory write.
- `frontend/response_composer.py`
  - progress status wording adjusted to be less template-rigid while keeping phase/blocker/next-action structure.
- `tests/test_support_bot_humanization.py`
  - added `test_build_final_reply_doc_status_query_handles_running_gate_blocked_as_real_blocker`.
  - added `test_support_controller_progress_dedupe_stays_stable_after_support_memory_write`.
- `tests/test_provider_selection.py`
  - added routing regression: analysis/guardrails remain in `plan_draft` family mapping.
- meta updates:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-progress-truth-and-humanized-status.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-progress-truth-and-humanized-status.md`

## Verify

- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0` (45 tests)
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` (21 tests)
- `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` -> `0` (30 tests)
- `python -m unittest discover -s tests -p "test_provider_selection.py" -v` -> `0` (10 tests)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0` (3 tests)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0` (3 tests)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> first run `1`
  - first failure point: workflow gate required `CURRENT.md` acceptance checkbox `- [x] Code changes allowed`.
  - minimal fix: add missing acceptance checklist row and include changed support controller path in current scope fields.
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> second run `1`
  - first failure point: lite replay `S17_lite_linear_mainline_resolver_only` expected `analysis.md` in `plan_draft` family mapping.
  - minimal fix: keep `analysis/guardrails` dispatch on existing `plan_draft` family and lock it with provider routing test.
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> final run `0`
  - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260324-171645` (`passed=14`, `failed=0`).

## Questions

- None.

## Demo

- 用户问“现在是什么情况”且 run 为 `running + gate.blocked` 时，不再出现“暂无阻塞”，会明确给出当前卡点与下一步处理。
- proactive 同状态轮询不会因为 hash 域漂移重复推送。
- 状态回复仍保持三要素（已完成/当前阶段/下一步），但句式不再固定机械复读。

## Integration Proof

- upstream: `ctcp_front_bridge.ctcp_get_support_context` (`run_status/gate/decisions`)
- current module: support progress binding + proactive memory write + frontend status composer
- downstream: Telegram proactive push dedupe behavior + STATUS_QUERY visible reply text
- source of truth: bridge run context only
- fallback: on verify failure, first failure point captured and minimal repair applied before final gate pass
