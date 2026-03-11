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
