# Demo Report - LAST

## Latest Report

- File: `meta/reports/LAST.md`
- Date: `2026-04-12`
- Topic: `real export-page screenshot priority over fallback evidence card`

### Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `meta/tasks/CURRENT.md`
- `tools/providers/project_generation_source_helpers.py`
- `tools/providers/project_generation_artifacts.py`
- `tests/test_project_generation_artifacts.py`
- `tests/test_screenshot_priority_selection.py`

### Plan

1. Replace the current evidence-card-only `final-ui.png` path with a real export-page screenshot path when GUI/web output can be rendered.
2. Keep the evidence card only as fallback and tag it with `visual_type=evidence_card`.
3. Propagate `visual_type` through source-generation and manifest artifacts.
4. Lock the contract with focused generation + screenshot-priority tests.
5. Produce one fresh local run proving `final-ui.png` is a real export-page capture.

### Changes

- Updated [tools/providers/project_generation_source_helpers.py](/d:/.c_projects/adc/ctcp/tools/providers/project_generation_source_helpers.py):
  - added a headless-browser capture path for GUI/web visual evidence
  - builds a real export preview HTML page from actual generated export files when no native HTML page already exists
  - writes `artifacts/screenshots/final-ui.png` from that real page capture first
  - falls back to the old synthetic card only if real page capture fails
  - emits `visual_type=real_export_page` or `visual_type=evidence_card`
- Updated [tools/providers/project_generation_artifacts.py](/d:/.c_projects/adc/ctcp/tools/providers/project_generation_artifacts.py):
  - propagates `visual_type` into source-generation and manifest-facing payloads
- Updated [tests/test_project_generation_artifacts.py](/d:/.c_projects/adc/ctcp/tests/test_project_generation_artifacts.py):
  - GUI and web generation now assert `visual_type=real_export_page`
  - added fallback regression for `visual_type=evidence_card`
- Updated [tests/test_screenshot_priority_selection.py](/d:/.c_projects/adc/ctcp/tests/test_screenshot_priority_selection.py):
  - added a regression showing Telegram screenshot delivery still prefers `final-ui.png` over `evidence-card.png`
- Updated [meta/tasks/CURRENT.md](/d:/.c_projects/adc/ctcp/meta/tasks/CURRENT.md) to narrow the active tranche to this generator-side visual-capture follow-up.

### Verify

- first failure point:
  - `python scripts/workflow_checks.py` failed first because this narrowed report rewrite initially omitted the mandatory workflow evidence fields that the repo gate expects.
- minimal fix strategy evidence:
  - keep the repair inside report metadata plus the generator-side visual capture files only
  - do not reopen delivery send logic or the reply wording shell while fixing this tranche
- focused tests:
  - `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v` -> `OK` (`Ran 14 tests`)
  - `python -m unittest discover -s tests -p "test_screenshot_priority_selection.py" -v` -> `OK` (`Ran 4 tests`)
- triplet runtime wiring command evidence:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `OK` (`Ran 23 tests`)
- triplet issue memory command evidence:
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `OK` (`Ran 3 tests`)
- triplet skill consumption command evidence:
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `OK` (`Ran 3 tests`)
- canonical verify:
  - `python scripts/workflow_checks.py` -> `OK`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `OK`
  - lite replay: `passed 14, failed 0` (`run_dir = C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260412-131013`)
  - python unit tests: `Ran 367 tests in 111.569s` -> `OK (skipped=3)`

### Questions

- None.

### Demo

- Real visual-evidence path now prefers a real export-page screenshot:
  - HTML preview page built from actual generated export files
  - headless browser capture writes `artifacts/screenshots/final-ui.png`
  - `visual_type=real_export_page`
- Fallback remains explicit:
  - only when browser/page capture fails
  - `visual_type=evidence_card`
- Fresh local proof run:
  - run: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/20260412-130847-real-ui-proof`
  - `visual_type=real_export_page`
  - `project_manifest.json` also records `visual_type=real_export_page`
  - `final-ui.source.html` is persisted under the run and does not contain `CTCP VISUAL EVIDENCE`
