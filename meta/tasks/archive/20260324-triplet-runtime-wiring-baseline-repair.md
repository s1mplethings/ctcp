# Task - triplet-runtime-wiring-baseline-repair

## Queue Binding

- Queue Item: `ADHOC-20260324-triplet-runtime-wiring-baseline-repair`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 用户确认继续后，需修复 canonical verify 当前首个 triplet runtime wiring 失败链。
- Dependency check: `ADHOC-20260324-api-connectivity-project-wiring-check` = `blocked` (API validated; verify still blocked by runtime wiring baseline defects).
- Scope boundary: 仅修复 triplet 首失败链路与必要回归，不做功能扩展。

## Task Truth Source (single source for current task)

- task_purpose: 消除 triplet runtime wiring 的既有崩溃/锁释放/回退文案问题，恢复可验证基线。
- allowed_behavior_change: 可更新 `frontend/response_composer.py`、`scripts/ctcp_support_bot.py`、`tests/test_runtime_wiring_contract.py`、`meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/tasks/archive/20260324-triplet-runtime-wiring-baseline-repair.md`、`meta/reports/LAST.md`、`meta/reports/archive/20260324-triplet-runtime-wiring-baseline-repair.md`。
- forbidden_goal_shift: 不引入新对话策略；不重构 provider 架构；不跳过 canonical verify。
- in_scope_modules:
  - `frontend/response_composer.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_runtime_wiring_contract.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-triplet-runtime-wiring-baseline-repair.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-triplet-runtime-wiring-baseline-repair.md`
- out_of_scope_modules:
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_front_bridge.py`
  - `docs/`
  - `src/`
  - `include/`
- completion_evidence: triplet 首失败链中的 IndexError / StringIO / lock cleanup / API fallback wording 均有修复证据并进入 verify 结果。

## Analysis / Find (before plan)

- Entrypoint analysis: `render_frontend_output()` -> `compose_user_reply()` 触发 hint-bank IndexError；`run_stdin_mode()` 对 StringIO 误用 `.buffer`；`run_telegram_mode()` 仅 atexit 解锁导致临时目录清理锁文件失败；API failover 文案由 `prepend_failover_notice()` 注入但当前 notice 为空。
- Downstream consumer analysis: runtime wiring triplet 与 support 用户可见回复直接依赖上述链路。
- Source of truth: `tests/test_runtime_wiring_contract.py` 与 `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`。
- Current break point / missing wiring: triplet runtime wiring contract 首失败并阻断后续 issue-memory/skill-consumption triplet 阶段。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: frontend/support runtime entrypoints (`render_frontend_output`, `run_stdin_mode`, `run_telegram_mode`, support provider failover).
- current_module: reply composition fallback + stdin UTF-8 wrapper + telegram poll lock lifecycle + failover notice.
- downstream: runtime wiring triplet tests and canonical verify.
- source_of_truth: test exit codes + verify first failure point.
- fallback: 若仍失败，记录新首失败点并给最小修复路径。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不通过改测试绕过真实运行时缺陷
  - 不跳过 triplet 命令证据记录
  - 不跳过 canonical verify
- user_visible_effect: API 失败降级回复明确告知 API 路径不可用并继续本地兜底；运行时不再因上述基础缺陷崩溃。

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: frontend reply composition no longer crashes when hint banks are empty and runtime wiring tests cover the path
- [ ] DoD-2: support stdin mode handles StringIO-like stdin safely, Telegram poll lock is released on loop exit, and API failover reply visibly states API-path fallback
- [ ] DoD-3: canonical verify runs with first failure recorded or passes after scoped runtime wiring repairs

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local runtime/code scan only)
- [x] Code changes allowed (`Scoped runtime wiring baseline repair`)
- [ ] Patch applies cleanly
- [ ] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [ ] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Bind queue item + task card.
2) Add safe fallback defaults in `compose_user_reply` to prevent empty-bank indexing.
3) Harden `run_stdin_mode` for StringIO-like stdin without `.buffer`.
4) Ensure Telegram poll lock is released via `finally` on loop exit.
5) Restore explicit API failover user-visible notice when degraded to local provider.
6) Run focused runtime/support tests.
7) Run canonical verify and record first failure + minimal fix.

## Check / Contrast / Fix Loop Evidence

- check / contrast / fix loop:
  - check-1: triplet logs show `IndexError` in `compose_user_reply` on empty hint banks.
  - contrast-1: expectation is no crash even when hint bank is empty.
  - fix-1: switch to safe defaults instead of `bank[key][0]` direct indexing.
  - check-2: `run_stdin_mode` fails on `_io.StringIO` because `.buffer` absent.
  - contrast-2: stdin mode should work under test harness and real stdin.
  - fix-2: only wrap with `TextIOWrapper` when `buffer` exists; otherwise keep original stream.
  - check-3: proactive telegram test leaves lock file handle open until process exit.
  - contrast-3: lock should release when polling loop exits, not only at atexit.
  - fix-3: add `try/finally` release around telegram loop.
  - check-4: API failover reply lacks explicit API fallback phrase.
  - contrast-4: failover reply must clearly mention API path unavailable + local continuation.
  - fix-4: restore failover notice text generation (zh/en).

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: fixes apply at actual runtime entrypoints used by triplet tests.
  - accumulated: provider degradation metadata (`degraded_from/degraded_kind`) drives failover notice emission.
  - consumed: final support reply text and runtime tests consume repaired paths.

## Notes / Decisions

- Default choices made: 仅补基础防护和生命周期处理，不改变主行为策略。
- Alternatives considered: 回滚“空 hint bank”改动；不采纳（会重新引入既有崩溃）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): none.
- Issue memory decision: 这是已登记既有问题链路，沿现有问题记忆推进修复，不新增重复条目。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is a bounded runtime baseline repair.
- persona_lab_impact: none.

## Results

- Files changed:
  - `frontend/response_composer.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_runtime_wiring_contract.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-triplet-runtime-wiring-baseline-repair.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-triplet-runtime-wiring-baseline-repair.md`
- Verification summary: pending
- Queue status update suggestion (`todo/doing/done/blocked`): doing
