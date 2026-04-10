# Task - remove-legacy-gui-lane

## Queue Binding

- Queue Item: `ADHOC-20260407-remove-legacy-gui-lane`
- Layer/Priority: `L1 / P1`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: the user clarified that this project does not have its own GUI, but the repo still exposes a stale Qt GUI target and GUI-era docs that can be mistaken for a real startup path.
- Dependency check: `ADHOC-20260406-support-delivery-evidence-surface` = `done`.
- Scope boundary: remove the repo-shipped GUI build target and GUI-only source/resources, then align active docs/meta/verify to a headless-only surface without widening into unrelated frontend/support/product work.

## Task Truth Source

- task_purpose: remove the stale GUI lane so the repository only presents a headless executable/build path and no longer ships or advertises a dedicated GUI target.
- allowed_behavior_change:
  - `CMakeLists.txt`
  - `README.md`
  - `BUILD.md`
  - `artifacts/PLAN.md`
  - `scripts/verify_repo.ps1`
  - `scripts/verify_repo.sh`
  - `docs/00_CORE.md`
  - `docs/01_north_star.md`
  - `docs/03_quality_gates.md`
  - `docs/12_modules_index.md`
  - `docs/verify_contract.md`
  - `docs/adlc_pipeline.md`
  - `docs/00_overview.md`
  - `docs/01_architecture.md`
  - `docs/04_project_detection.md`
  - `docs/05_navigation.md`
  - `docs/06_graph_map.md`
  - `docs/07_layout_and_views.md`
  - `docs/10_workflow.md`
  - `docs/11_webengine_resources.md`
  - `docs/18_back_and_preview.md`
  - `docs/19_lod_rendering.md`
  - `docs/20_backend_bridge.md`
  - `meta/code_health/rules.json`
  - `meta/sddai_project.json`
  - `include/Bridge.h`
  - `include/DocPreviewer.h`
  - `include/FileIndexer.h`
  - `include/GraphBuilder.h`
  - `include/GraphTypes.h`
  - `include/GraphViewProjector.h`
  - `include/LayoutEngine.h`
  - `include/MainWindow.h`
  - `include/MetaStore.h`
  - `include/ProjectScanner.h`
  - `include/RunLoader.h`
  - `include/SchemaLoader.h`
  - `include/SpecExtractor.h`
  - `resources/app.qrc`
  - `resources/qt_style.qss`
  - `src/Bridge.cpp`
  - `src/DocPreviewer.cpp`
  - `src/FileIndexer.cpp`
  - `src/GraphBuilder.cpp`
  - `src/GraphViewProjector.cpp`
  - `src/LayoutEngine.cpp`
  - `src/MainWindow.cpp`
  - `src/MetaStore.cpp`
  - `src/ProjectScanner.cpp`
  - `src/RunLoader.cpp`
  - `src/SchemaLoader.cpp`
  - `src/SpecExtractor.cpp`
  - `src/main.cpp`
  - `src/preview_window.cpp`
  - `src/preview_window.h`
  - `src/sddai_bridge.cpp`
  - `src/sddai_bridge.h`
  - `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
  - `tests/test_workflow_checks.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `meta/tasks/archive/20260406-support-delivery-evidence-surface.md`
  - `meta/reports/archive/20260406-support-delivery-evidence-surface.md`
- forbidden_goal_shift:
  - do not introduce a replacement GUI or web UI path in this patch
  - do not refactor unrelated headless/runtime/support modules
  - do not turn this into a broad docs rewrite beyond GUI-lane removal and deprecation notes
- in_scope_modules:
  - build entrypoints and verify commands
  - GUI-only C++ source/resources
  - active docs/meta that currently advertise or depend on the GUI lane
  - focused workflow regression coverage for the new headless-only path
- out_of_scope_modules:
  - project generation mainline logic
  - frontend/support conversation behavior
  - generated projects and benchmark fixtures unless verify proves a direct dependency
- completion_evidence: the repo no longer defines a GUI build target, GUI-only code/resources are removed, active docs point only to headless startup/build paths, focused checks pass, and canonical verify closes.

## Analysis / Find

- Entrypoint analysis: the only active runnable binary path used by verify is `ctcp_headless`; the Qt GUI path is an optional leftover branch in `CMakeLists.txt` plus old docs and source files.
- Downstream consumer analysis: operators and agents should see one real startup/build path; stale GUI instructions create false manual-test and build expectations.
- Source of truth:
  - user clarification in this turn
  - `AGENTS.md`
  - `docs/00_CORE.md`
  - `docs/03_quality_gates.md`
  - `CMakeLists.txt`
  - `scripts/verify_repo.ps1`
  - `scripts/verify_repo.sh`
- Current break point / missing wiring:
  - `build\ctcp.exe` and `CTCP_ENABLE_GUI` still exist as a misleading startup lane
  - GUI-only Qt source/resources remain in repo even though the product surface is headless
  - active docs/build notes still advertise optional GUI behavior
- Repo-local search sufficient: `yes`

## Integration Check

- upstream: the user expects the repo startup/build story to be headless-only, and canonical verify already uses the headless path as the real runnable surface.
- current_module: CMake, verify scripts, active docs, and stale GUI-only code/resources must agree on one executable surface.
- downstream: manual startup, verify, and future maintenance should no longer surface or accidentally launch `ctcp.exe`.
- source_of_truth: `CMakeLists.txt`, `scripts/verify_repo.ps1`, `scripts/verify_repo.sh`, and the active routed docs.
- fallback: keep legacy GUI-era docs only as explicitly deprecated historical notes if hard deletion would leave duplicate authority or broken references.
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_workflow_checks.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`
- forbidden_bypass:
  - do not leave a dead `CTCP_ENABLE_GUI` option or `ctcp` GUI target behind
  - do not keep active docs suggesting a GUI build/start path still exists
  - do not fix this only by changing wording while leaving the executable GUI branch in place
- user_visible_effect: operators see one headless build/start path and no repo-provided GUI target.

## DoD Mapping

- [x] DoD-1: `CMakeLists.txt` and verify scripts expose only the headless build target; the stale GUI target/option is removed
- [x] DoD-2: GUI-only source/resources are removed, and active docs/meta no longer advertise a repo GUI path
- [x] DoD-3: focused checks and canonical `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` pass from the updated task/report state

## Acceptance

- [x] DoD written (this file complete)
- [x] Research logged (repo-local search only)
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1. Archive the previous active topic and bind a new ADHOC queue item for GUI removal.
2. Remove the GUI CMake branch, GUI-only source/resources, and GUI-specific verify arguments.
3. Align active docs/meta/tests to a headless-only repo surface, with deprecation notes on legacy GUI-era docs where needed.
4. Run focused workflow coverage and canonical verify.
5. Close the task with explicit first-failure evidence or final pass evidence.

## Check / Contrast / Fix Loop Evidence

- check-1: the repo still contains `CTCP_ENABLE_GUI`, a `ctcp` GUI binary target, and Qt source/resources even though verify and the actual runtime surface are headless.
- contrast-1: the user clarified there is no project GUI, so keeping a repo GUI lane creates a false startup/build path.
- fix-1: remove the GUI branch from build/verify and delete GUI-only code/resources.
- check-2: even after code deletion, stale docs/meta can still claim a GUI lane exists.
- contrast-2: active docs/meta must align to one headless-only surface.
- fix-2: rewrite the active routed docs/build notes and downgrade old GUI-era docs to explicit historical/deprecated status where retained.
- check-3: workflow/code-health checks may still point at deleted GUI entry files.
- contrast-3: task/report evidence and focused tests must describe the new headless-only path without dangling GUI entry references.
- fix-3: update task/report state, code-health entrypoint patterns, and the focused workflow regression fixture.

## Completion Criteria Evidence

- connected + accumulated + consumed:
- connected: CMake, verify scripts, and active docs all point to the same headless executable/build surface.
- accumulated: GUI-only code/resources and misleading GUI notes are removed or explicitly deprecated in one scoped patch.
- consumed: focused tests and canonical verify consume the new headless-only repo surface without referencing deleted GUI entrypoints.

## Notes / Decisions

- Default choices made: remove the executable GUI lane entirely and keep any retained GUI-era docs explicitly deprecated instead of silently authoritative.
- Alternatives considered: leaving the GUI target in place but hiding it in docs; rejected because that would preserve the wrong startup path the user already hit.
- Any contract exception reference:
  - None
- Issue memory decision: none; this is a direct repo-surface cleanup, not a recurring runtime defect class.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: yes` using `ctcp-workflow` for repo-standard execution and `ctcp-verify` for canonical closure.

## Results

- Files changed:
  - `CMakeLists.txt`
  - `README.md`
  - `BUILD.md`
  - `artifacts/PLAN.md`
  - `scripts/verify_repo.ps1`
  - `scripts/verify_repo.sh`
  - active headless/runtime docs under `docs/`
  - deprecated legacy GUI docs under `docs/`
  - `meta/code_health/rules.json`
  - `meta/sddai_project.json`
  - GUI-only files removed under `src/`, `include/`, and `resources/`
  - `tests/test_workflow_checks.py`
  - `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
  - task/report/queue/archive files under `meta/`
- Verification summary:
  - `python -m unittest discover -s tests -p "test_workflow_checks.py" -v` -> `0`
  - `python scripts/sync_doc_links.py --check` -> `0`
  - `python simlab/run.py --suite lite --json-out artifacts/gui_removal_simlab.json` -> `0`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `0`
- Queue status update suggestion (`todo/doing/done/blocked`): `done`
