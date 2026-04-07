# Demo Report - LAST

## Latest Report

- File: `meta/reports/LAST.md`
- Date: `2026-04-07`
- Topic: `remove legacy gui lane`

### Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `CMakeLists.txt`
- `README.md`
- `BUILD.md`
- `scripts/verify_repo.ps1`
- `scripts/verify_repo.sh`
- repo-local search for `CTCP_ENABLE_GUI`, `ctcp.exe`, `src/main.cpp`, `app.qrc`, and GUI-only docs

### Plan

1. Archive the previous support/frontend evidence topic and bind a new GUI-removal task.
2. Remove the GUI build branch and GUI-only source/resources.
3. Align active docs/meta/tests to a headless-only repo surface.
4. Run focused checks and canonical verify.
5. Close with explicit pass/fail evidence and the minimal repair path if needed.

### Changes

- Removed the GUI branch from `CMakeLists.txt` so the repo now builds only `ctcp_headless`.
- Removed GUI-only Qt source, headers, and resource files under `src/`, `include/`, and `resources/`.
- Updated active build/verify docs and scripts to a headless-only build surface.
- Marked legacy GUI-era docs as deprecated historical material so they no longer read as active authority.
- Updated code-health metadata, the neutral project marker, and the focused workflow regression to match the headless-only repo surface.
- Rebases `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` to the new `# Task - remove-legacy-gui-lane` header so `S16_lite_fixer_loop_pass` still converges after the task-topic change.

### Verify

- `python -m unittest discover -s tests -p "test_workflow_checks.py" -v` -> `0`
  - result: focused workflow gate regression still passes after the headless-only entrypoint change
- `python scripts/sync_doc_links.py --check` -> `0`
  - result: README doc index remains synchronized after the doc updates
- first failure point: `workflow gate (workflow checks)` during canonical `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`
  - reason: `meta/reports/LAST.md` was missing the mandatory first-failure/minimal-fix strings and the explicit triplet command evidence lines
- minimal fix strategy: record the first failure evidence here, add the three explicit triplet command lines, and rerun canonical verify before touching runtime code again
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
- second failure point: `lite scenario replay` during canonical `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`
  - reason: `S16_lite_fixer_loop_pass` still used a fixer patch fixture that expected the old `# Task - support-delivery-evidence-surface` header, so the second-pass patch no longer applied cleanly in the replay sandbox
- minimal fix strategy: rebase `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` to the current task header, rerun lite replay, then rerun canonical verify
- `python simlab/run.py --suite lite --json-out artifacts/gui_removal_simlab.json` -> `0`
  - result: `14` scenarios passed, `0` failed
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `0`
  - result: canonical verify passed with executed gates `lite, workflow_gate, plan_check, patch_check, behavior_catalog_check, contract_checks, doc_index_check, code_health_check, triplet_guard, lite_replay, python_unit_tests`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` (post-close rerun after CURRENT/LAST/queue finalization) -> `0`
  - result: final closure state still passes the canonical gate after the task/report/queue updates

### Questions

- None.

### Demo

- Goal: the repo should expose only a headless executable/build path and should no longer ship or advertise a dedicated GUI target.
- Startup/build surface now points only to `ctcp_headless`; the stale `ctcp` GUI target and its Qt source/resources are gone.
- Legacy GUI docs remain only as deprecated historical notes, so operators no longer get a false repo GUI startup path.
