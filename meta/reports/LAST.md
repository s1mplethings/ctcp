# Demo Report - LAST

## Latest Report

- File: `meta/reports/LAST.md`
- Date: `2026-04-10`
- Topic: `real visual evidence and public delivery for Telegram-bound project outputs`

### Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`
- `tools/providers/project_generation_source_helpers.py`
- `tools/providers/project_generation_artifacts.py`
- `scripts/project_generation_gate.py`
- `scripts/ctcp_support_bot.py`
- `tests/test_project_generation_artifacts.py`
- `tests/test_support_public_delivery_state.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_support_to_production_path.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_issue_memory_accumulation_contract.py`
- `tests/test_skill_consumption_contract.py`

### Plan

1. Add a real screenshot capture step for generated `gui_first` / `web_first` projects after runtime probes actually launch or export the output.
2. Propagate screenshot truth into `source_generation_report.json`, `project_manifest.json`, and `deliverable_index.json`.
3. Tighten source-generation + manifest gates so `placeholder_only` no longer counts as delivery-complete truth.
4. Make the Telegram delivery path prefer real screenshot/package actions over artifact-hint text once verify-pass truth exists.
5. Prove the result with focused tests, a real Telegram-lane outbound delivery, workflow checks, and canonical verify.

### Changes

- Updated [tools/providers/project_generation_source_helpers.py](/d:/.c_projects/adc/ctcp/tools/providers/project_generation_source_helpers.py):
  - added real visual evidence generation after successful GUI/web runtime probes
  - writes screenshot artifacts under generated project outputs at `artifacts/screenshots/overview.png`
  - changed GUI/web source-generation truth so `visual_evidence_status` must become `provided` with a real file, not `placeholder_only`
- Updated [tools/providers/project_generation_artifacts.py](/d:/.c_projects/adc/ctcp/tools/providers/project_generation_artifacts.py):
  - propagates `visual_evidence_status`, `visual_evidence_files`, and capture metadata into `source_generation_report.json`, `project_manifest.json`, and `deliverable_index.json`
  - re-collects generated file inventory after runtime probes so screenshot outputs are included in delivery truth
- Updated [scripts/project_generation_gate.py](/d:/.c_projects/adc/ctcp/scripts/project_generation_gate.py):
  - tightened GUI/web stage validation so `placeholder_only` no longer passes `source_generation` or manifest checks
  - validates that every declared screenshot file physically exists under the run output
- Updated [scripts/ctcp_support_bot.py](/d:/.c_projects/adc/ctcp/scripts/ctcp_support_bot.py):
  - auto-injects screenshot + package delivery actions for Telegram verify-pass result delivery
  - rewrites final delivery replies so they describe direct zip/screenshot sending instead of hash-only artifact hints
  - preserves `support_public_delivery.json` as the source of truth for what was actually sent
  - keeps direct CLI launch working by inserting the repo root into `sys.path` before importing frontend delivery helpers
  - fixed proactive/result outbound jobs so they call `emit_public_delivery()` after sending result text when delivery actions are present
  - treats a delivery action with no `sent` files or any delivery errors as a failed send that must be retried instead of a successful result push
- Updated [frontend/delivery_reply_actions.py](/d:/.c_projects/adc/ctcp/frontend/delivery_reply_actions.py):
  - added `delivery_plan_failed(...)` so Telegram paths can enforce the shared invariant: delivery actions require real `sent` files
- Updated [tests/test_project_generation_artifacts.py](/d:/.c_projects/adc/ctcp/tests/test_project_generation_artifacts.py):
  - added assertions that real PNG screenshots exist for GUI/web generation scenarios
- Updated [tests/test_support_bot_humanization.py](/d:/.c_projects/adc/ctcp/tests/test_support_bot_humanization.py):
  - added verify-pass delivery tests that require both screenshot and package actions plus non-hash final reply text
- Added [tests/test_support_proactive_delivery.py](/d:/.c_projects/adc/ctcp/tests/test_support_proactive_delivery.py):
  - proves proactive/result controller jobs send actual package and screenshot files instead of text-only result notifications
  - proves controller result jobs are requeued when delivery actions produce no `sent` files

### Verify

- first failure point evidence:
  - the real Telegram-bound run [20260409-215339-177800-orchestrate](C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/20260409-215339-177800-orchestrate) had already reached `verify PASS`, but delivery truth was still incomplete
  - pre-fix [project_manifest.json](C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/20260409-215339-177800-orchestrate/artifacts/project_manifest.json) declared:
    - `visual_evidence_required = true`
    - `screenshot_required = true`
    - `visual_evidence_status = "placeholder_only"`
  - pre-fix [support_public_delivery.json](C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/support_sessions/6092527664/artifacts/support_public_delivery.json) had no true delivery evidence:
    - `deliveries = []`
    - `sent = []`
- minimal fix strategy evidence:
  - generate a real screenshot artifact after successful GUI/web runtime probes
  - fail GUI/web source-generation or manifest truth when screenshots are still placeholder-only
  - synthesize final Telegram delivery actions from verify-pass truth and send the actual zip + screenshot files
- focused tests:
  - `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v` -> `OK`
  - `python -m unittest discover -s tests -p "test_support_public_delivery_state.py" -v` -> `OK`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `OK` including `test_controller_result_push_emits_public_delivery_files`
  - `python -m unittest discover -s tests -p "test_support_proactive_delivery.py" -v` -> `OK`
  - `python -m unittest discover -s tests -p "test_support_to_production_path.py" -v` -> `OK`
- triplet runtime wiring command evidence:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `OK`
- triplet issue memory command evidence:
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `OK`
- triplet skill consumption command evidence:
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `OK`
- workflow + canonical verify:
  - `python scripts/workflow_checks.py` -> `OK`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `OK`

### Questions

- None.

### Demo

- real Telegram-lane run and session:
  - run dir: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260409-215339-177800-orchestrate`
  - support session: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\support_sessions\6092527664`
- real screenshot evidence now exists:
  - [overview.png](C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/20260409-215339-177800-orchestrate/project_output/vn-mvp-ren-py-json/artifacts/screenshots/overview.png)
  - regenerated [source_generation_report.json](C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/20260409-215339-177800-orchestrate/artifacts/source_generation_report.json) now records:
    - `status = "pass"`
    - `visual_evidence_status = "provided"`
    - `visual_evidence_files = ["project_output/vn-mvp-ren-py-json/artifacts/screenshots/overview.png"]`
- real public delivery evidence now exists:
  - [support_public_delivery.json](C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/support_sessions/6092527664/artifacts/support_public_delivery.json) records both actual sends:
    - zip: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\support_sessions\6092527664\artifacts\support_exports\vn-mvp-ren-py-json.zip`
    - screenshot: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260409-215339-177800-orchestrate\project_output\vn-mvp-ren-py-json\artifacts\screenshots\overview.png`
  - `deliveries` and `sent` are both non-empty and list the same real files
- user-visible delivery effect:
  - Telegram final delivery is now allowed to send concrete zip/screenshot files instead of only hash or artifact-hint text
  - `placeholder_only` no longer counts as successful GUI/web delivery truth
  - refreshed [support_reply.json](C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/support_sessions/6092527664/artifacts/support_reply.json) now says:
    - `结果状态不变，`
    - `我现在直接把 zip 包和结果截图发到当前对话。`
  - live session `6092527664` was backfilled after finding the proactive/result push bug:
    - [support_public_delivery.json](C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/support_sessions/6092527664/artifacts/support_public_delivery.json) now has `sent` entries for both `photo` and `document`
    - active Telegram poller was restarted on the fixed code path
