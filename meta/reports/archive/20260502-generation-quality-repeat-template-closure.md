# Demo Report - Generation Quality Repeat/Template Closure

## Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/tasks/CURRENT.md`
- `frontend/support_reply_policy.py`
- `scripts/ctcp_support_bot.py`
- `tools/providers/project_generation_provenance.py`
- `tools/providers/project_generation_artifacts.py`
- `tests/test_support_reply_policy_regression.py`
- `tests/test_project_generation_provenance.py`
- `docs/03_quality_gates.md`
- `ai/MEMORY/ISSUE_MEMORY.md`

## Plan
1. Bind a Delivery Lane closure task for repeated/long replies and template-like final delivery.
2. Add focused reply and provenance regressions.
3. Add compact/dedupe, provenance completion, and final package gates.
4. Run targeted tests, canonical verify, and restart Telegram bot.

## Changes
- Support replies now compact oversized non-error text and suppress duplicate proactive delivery.
- Support bot clears text/question when policy returns `suppressed=true`.
- Source provenance now emits `source_customization_completion`.
- Deliverable index does not build `final_project_bundle.zip` when production source is local materializer-only.
- Quality gate docs and issue memory now record the delivery-completion requirement.

## Verify
- `python tests/test_support_reply_policy_regression.py` passed (`14` tests).
- `python tests/test_project_generation_provenance.py` passed (`2` tests).
- `$env:PYTHONPATH=(Get-Location).Path; python tests/test_project_generation_artifacts.py` passed (`36` tests).
- `$env:PYTHONPATH=(Get-Location).Path; python tests/test_support_session_recovery_regression.py -k test_build_grounded_status_reply_doc_surfaces_invalid_source_generation_report_blocker` passed (`1` test).
- `python -m py_compile scripts/ctcp_support_bot.py frontend\support_reply_policy.py tools\providers\project_generation_source_stage.py tools\providers\project_generation_provenance.py tools\providers\project_generation_artifacts.py` passed.
- `python scripts\workflow_checks.py` passed.
- `python scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` passed.
- `$env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` passed with `480` Python unit tests (`4` skipped).

## Questions
- None.

## Demo
- Duplicate proactive delivery now returns `suppressed=true`, `dedupe_action=suppress`, and empty `reply_text`.
- Materializer-only production source now leaves `final_package_path` empty and records a blocking reason.
- API-content provenance marks files as `mixed_api_content` and allows final delivery.
- Telegram bot restarted as PID pair `20400` / `34512`.

## Integration Proof
- connected: source-map API-content evidence connects into source-generation provenance; policy suppression connects to Telegram-bound reply construction.
- accumulated: manifest accumulates `source_customization_completion`; reply memory accumulates delivery context signatures.
- consumed: deliverable index blocks final zip on failed completion, and support bot consumes suppression by clearing sendable text.
