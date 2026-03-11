# Problem Registry (Reusable Template + Examples)

Purpose:
- Capture recurring failure patterns as reusable institutional memory.
- Keep entries short, reproducible, and directly actionable.

When to add:
- Same class of failure appears >= 2 times.
- A failure required non-obvious debugging steps.
- A policy mismatch caused avoidable rework.

## Entry Template

- Symptom:
- Repro:
- Root cause:
- Fix:
- Prevention:
- Tags:

## Example 1

- Symptom:
  Agent/patch claims "verified" but no reproducible evidence artifacts exist.
- Repro:
  Run build/test manually without saving structured logs; output cannot be audited later.
- Root cause:
  Verification flow was fragmented and not tied to a hard gate entrypoint.
- Fix:
  Standardize on `scripts/verify_repo.ps1` / `scripts/verify_repo.sh`; record command and result in `meta/reports/LAST.md`.
- Prevention:
  Treat missing verify evidence as FAIL in review.
- Tags:
  verify, gate, evidence, reproducibility

## Example 2

- Symptom:
  Docs claim rules that scripts do not enforce (contract drift).
- Repro:
  Compare `docs/03_quality_gates.md` against `scripts/verify_repo.*`; documented gate differs from actual executed gate list.
- Root cause:
  Documentation changed independently from gate scripts.
- Fix:
  Update docs to script-aligned behavior or implement missing gate in scripts in the same patch.
- Prevention:
  Every gate change must include paired doc update and a verify run record.
- Tags:
  docs, contract, drift, verify

## Example 3

- Symptom:
  Customer-visible support replies suddenly expose internal file names, agent labels, or system fallback wording such as `verify_report.json`, `failure bundle`, or `internal agent`.
- Repro:
  Trigger report/bundle/dispatch/result/write-fail fallback branches in `tools/telegram_cs_bot.py` or provider/model fallback branches in `scripts/ctcp_support_bot.py`.
- Root cause:
  Some user-visible branches bypass the shared customer reply gate and send direct template/system text, while fallback code reverts to generic PM/system phrasing.
- Fix:
  Route every customer-visible notice through the same natural support reply builder, keep smalltalk/capability turns local when no run is active, and add regressions for the leaked branches and dataset expectations.
- Prevention:
  Treat any direct `tg.send(...)` customer notice containing internal labels/raw exceptions as a contract violation; cover new fallback branches with humanization tests before merge.
- Tags:
  support, frontend, leakage, wording, fallback

## Example 4

- Symptom:
  Telegram bot greeting works, but the first real project turn immediately fails with external API 401 and tells the user the model call is unavailable.
- Repro:
  Start the Telegram bot with `OPENAI_API_KEY=ollama` and no `OPENAI_BASE_URL`, then send a real project goal that creates a new run.
- Root cause:
  Greeting/smalltalk uses a local reply path, but new-run dispatch still defaults to `api_agent`; meanwhile `api_agent` treated any non-empty key as ready, so the placeholder `ollama` value slipped through until real execution hit OpenAI and failed.
- Fix:
  Align Telegram-created run dispatch configs away from `api_agent` when external API env is not truly ready, and treat `OPENAI_API_KEY=ollama` without `OPENAI_BASE_URL` as invalid for external API mode.
- Prevention:
  Validate provider readiness at run-creation time, not only after dispatch starts; add regression coverage for local greeting plus project-intake transition.
- Tags:
  telegram, provider, api, config, 401, local-first

## Example 5

- Symptom:
  Support-bot project turns regress to generic kickoff wording or leak `missing runtime_target`-style internal markers instead of reflecting the current detailed requirement.
- Repro:
  1. Bind a run and send a bare project-creation request such as `我想要创建一个项目`.
  2. Or send a detailed point-cloud requirement while the raw reply is only `收到，继续推进。missing runtime_target`.
- Root cause:
  New-run local ack and project-detail reply shaping over-trusted low-signal raw text; the frontend PM reply pipeline was bypassed even when the current requirement source was richer and the raw text still carried internal markers.
- Affected entrypoint:
  Telegram bound-run customer reply path (`tools/telegram_cs_bot.py::_handle_message` -> `_create_run` / `_send_customer_reply`).
- Affected modules:
  `tools/telegram_cs_bot.py`, `frontend/response_composer.py`
- Observed fallback behavior:
  The user sees a generic “做个项目” echo or `missing runtime_target` instead of a project kickoff / PM-style summary.
- Expected correct behavior:
  Bare project creation should ask for project goal, input, and expected result; detailed project turns should prefer the latest detailed requirement source and suppress internal markers.
- Fix:
  Tighten project kickoff fallback in `tools/telegram_cs_bot.py` and stop preserving low-signal/internal-marker raw project replies in `frontend/response_composer.py`.
- Fix attempt status:
  2026-03-11 scoped fix bound under `ADHOC-20260311-support-bot-humanization-verify-blocker`.
- Regression test status:
  Covered by `tests/test_support_bot_humanization.py` and `tests/test_frontend_rendering_boundary.py`.
- Prevention:
  Treat low-signal project replies as fallback candidates, not authoritative agent text; keep a direct frontend regression for internal-marker suppression in project-detail mode.
- Tags:
  support, frontend, reply-shaping, requirement-source, leakage
