# Demo Report - LAST

## Latest Report

- File: `meta/reports/LAST.md`
- Date: `2026-04-11`
- Topic: `public delivery wording, screenshot priority, hard sent checks, and final-ui evidence stopgap`

### Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `ai_context/problem_registry.md`
- `frontend/delivery_reply_actions.py`
- `frontend/progress_reply.py`
- `frontend/recovery_visibility.py`
- `frontend/support_reply_policy.py`
- `scripts/project_delivery_evidence_bridge.py`
- `scripts/ctcp_support_bot.py`
- `tools/providers/project_generation_source_helpers.py`
- `tests/test_frontend_rendering_boundary.py`
- `tests/test_project_generation_artifacts.py`
- `tests/test_screenshot_priority_selection.py`
- `tests/test_support_delivery_user_visible_contract.py`
- `tests/test_support_proactive_delivery.py`
- `tests/test_support_reply_policy_regression.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_telegram_http_client.py`
- `tests/test_support_to_production_path.py`

### Plan

1. Keep the active task bound to the public-delivery defect family and extend the stopgap to the generator-side `final-ui.png` naming plus support-bot sent checks.
2. Tighten `frontend/delivery_reply_actions.py` so screenshot ordering and delivery send success both use hard runtime evidence.
3. Rewrite `frontend/support_reply_policy.py` fallback delivery/progress language to stay user-readable and stop re-appending artifact filename lists.
4. Reorder screenshot selection in `scripts/project_delivery_evidence_bridge.py`, stabilize `final-ui.png` in `tools/providers/project_generation_source_helpers.py`, and prove both ordinary/proactive result paths through tests.
5. Run the requested regressions, canonical verify, and one fresh local delivery-proof run that writes `support_public_delivery.json`.

### Changes

- Updated [frontend/delivery_reply_actions.py](/d:/.c_projects/adc/ctcp/frontend/delivery_reply_actions.py):
  - normalized screenshot prioritization through `Path(...).name`
  - kept verify-pass Telegram action injection, but now counts prioritized screenshots
  - hardened `delivery_plan_failed(...)` so package delivery requires `document` and screenshot delivery requires `photo`
  - rewrote short/internal Telegram delivery text into a screenshot-first, zip-second summary that mentions `README`, startup entry, and run instructions
- Updated [frontend/support_reply_policy.py](/d:/.c_projects/adc/ctcp/frontend/support_reply_policy.py):
  - changed deliver-result fallback text to the requested user-facing screenshot-first package summary in both Chinese and English
  - changed Chinese progress fallback from process narration to result-oriented wording
  - stopped re-appending artifact filename lists on `deliver_result`
- Updated [frontend/progress_reply.py](/d:/.c_projects/adc/ctcp/frontend/progress_reply.py):
  - added a narrow humanization layer for `file_request.json` blocker/next-action wording on the status/progress lane
  - kept the existing progress-shell contract, but stopped exposing raw `waiting for file_request.json` and planner retry text to users
- Updated [frontend/recovery_visibility.py](/d:/.c_projects/adc/ctcp/frontend/recovery_visibility.py):
  - reused the same status humanization helper for `backend_blocked` / reply-truth wording
- Updated [scripts/project_delivery_evidence_bridge.py](/d:/.c_projects/adc/ctcp/scripts/project_delivery_evidence_bridge.py):
  - limited screenshot pickup to delivery-like image names and sorted them through the shared priority helper before slicing
- Updated [scripts/ctcp_support_bot.py](/d:/.c_projects/adc/ctcp/scripts/ctcp_support_bot.py):
  - grounded progress replies now humanize `file_request.json` blocker/next-step wording before emitting Telegram-visible status text
  - kept ordinary-result and proactive-result delivery failure checks on the same shared `delivery_plan_failed(...)` contract, so missing `photo` / `document` sent records now force requeue or failure notice instead of fake success
- Updated [tools/providers/project_generation_source_helpers.py](/d:/.c_projects/adc/ctcp/tools/providers/project_generation_source_helpers.py):
  - introduced `FINAL_UI_SCREENSHOT_NAME = "final-ui.png"` and used it for the generated visual-evidence artifact path
- Updated tests:
  - [tests/test_frontend_rendering_boundary.py](/d:/.c_projects/adc/ctcp/tests/test_frontend_rendering_boundary.py): updated backend-blocked rendering assertions to the new humanized `file_request.json` wording
  - [tests/test_screenshot_priority_selection.py](/d:/.c_projects/adc/ctcp/tests/test_screenshot_priority_selection.py): strengthened mixed-priority ordering and locked bridge preference to `final-ui.png`
  - [tests/test_support_delivery_user_visible_contract.py](/d:/.c_projects/adc/ctcp/tests/test_support_delivery_user_visible_contract.py): moved the wording assertion to the public fallback renderer and tightened the `document` + `photo` sent-file contract
  - [tests/test_support_proactive_delivery.py](/d:/.c_projects/adc/ctcp/tests/test_support_proactive_delivery.py): strengthened proactive/result push to require real `photo` + `document` sent records and prefer `final-ui.png` over `overview.png`
  - [tests/test_support_bot_humanization.py](/d:/.c_projects/adc/ctcp/tests/test_support_bot_humanization.py): kept grounded-status wording coverage aligned with the old shell plus the new blocker humanization
  - [tests/test_support_reply_policy_regression.py](/d:/.c_projects/adc/ctcp/tests/test_support_reply_policy_regression.py): updated the transcript dedupe check to assert durable `deliver_result` output instead of a forced raw artifact filename
  - [tests/test_telegram_http_client.py](/d:/.c_projects/adc/ctcp/tests/test_telegram_http_client.py): added curl-fallback regressions so Telegram API `ok=false` responses raise instead of being treated as success
- Updated [meta/tasks/CURRENT.md](/d:/.c_projects/adc/ctcp/meta/tasks/CURRENT.md) to narrow the bound tranche to this stopgap.
- Updated [ai_context/problem_registry.md](/d:/.c_projects/adc/ctcp/ai_context/problem_registry.md) Example 30 fix status with this follow-up.

### Verify

- first failure point:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` initially failed at `workflow gate (workflow checks)` because `meta/reports/LAST.md` had not yet been updated for this change set
  - minimal repair: write the current report and rerun canonical verify
- minimal fix strategy evidence:
  - keep the repair inside the user-visible delivery stopgap only: reply humanization, hard send-record checks, screenshot ordering, and the generator-side `final-ui.png` default
  - avoid reopening unrelated support-runtime or manifest plumbing while the current queue item is already bound to the same public-delivery defect family
- focused tests:
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` -> `OK` (`Ran 37 tests`)
  - `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v` -> `OK` (`Ran 13 tests`)
  - `python -m unittest discover -s tests -p "test_screenshot_priority_selection.py" -v` -> `OK` (`Ran 3 tests`)
  - `python -m unittest discover -s tests -p "test_support_delivery_user_visible_contract.py" -v` -> `OK` (`Ran 5 tests`)
  - `python -m unittest discover -s tests -p "test_support_proactive_delivery.py" -v` -> `OK` (`Ran 3 tests`)
  - `python -m unittest discover -s tests -p "test_support_reply_policy_regression.py" -v` -> `OK` (`Ran 11 tests`)
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `OK` (`Ran 58 tests`)
  - `python -m unittest discover -s tests -p "test_telegram_http_client.py" -v` -> `OK` (`Ran 4 tests`)
  - `python -m unittest discover -s tests -p "test_support_to_production_path.py" -v` -> `OK` (`Ran 15 tests`)
- triplet runtime wiring command evidence:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `OK` (`Ran 23 tests`)
- triplet issue memory command evidence:
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `OK` (`Ran 3 tests`)
- triplet skill consumption command evidence:
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `OK` (`Ran 3 tests`)
- delegated worker evidence:
  - worker scope: `tools/providers/project_generation_source_helpers.py`, `tests/test_screenshot_priority_selection.py`, `tests/test_support_delivery_user_visible_contract.py`, `tests/test_support_bot_humanization.py`
  - worker-reported commands all passed in its run, then the same touched tests were re-run successfully in the main workspace
- canonical verify:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `OK`
  - lite replay: `passed 14, failed 0` (`run_dir = C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260412-034034`)
  - python unit tests: `Ran 365 tests in 94.109s` -> `OK (skipped=3)`
  - post-closeout metadata check: `python scripts/workflow_checks.py` -> `OK`

### Questions

- None.

### Demo

- User-visible delivery reply now stays on the product lane:
  - screenshot first
  - zip second
  - no `Produced artifacts`, `Startup entry`, `stage`, `artifact`, `.json`, or hash leakage in the final wording path
- User-visible progress/status replies now keep the old progress shell but stop surfacing raw intake-internal blocker wording:
  - `waiting for file_request.json` is rendered as a humanized “需求整理这一步还没落下来...”
  - `retry planner intake synthesis and verify file_request.json lands` is rendered as a humanized “重试需求整理，并确认需求清单真正生成出来”
- Delivery success is now checked by actual send records:
  - package action requires a `document` entry in `support_public_delivery.json.sent`
  - screenshot action requires a `photo` entry in `support_public_delivery.json.sent`
- Screenshot evidence ordering now prefers product images over proof/debug images:
  - `final-ui.png` outranks `result.png`, `preview.png`, `overview.png`, and `debug.png`
  - bridge-side evidence selection uses the same priority helper as Telegram delivery planning
- Generator-side visual evidence now has a stable default filename:
  - `artifacts/screenshots/final-ui.png`
- Fresh local delivery-proof runtime evidence:
  - run: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/20260412-033834-delivery-proof`
  - `support_public_delivery.json.sent` contains two `photo` rows and one `document` row
  - first sent screenshot is `final-ui.png`
  - sent zip is `story_organizer.zip`
  - final user-visible reply stayed on the product lane: “项目已经整理好了…先看成品截图…再打开 zip 包…按 README 里的说明执行。”
