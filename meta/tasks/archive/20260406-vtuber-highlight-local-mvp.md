# Task - vtuber-highlight-local-mvp

## Queue Binding

- Queue Item: `ADHOC-20260406-vtuber-highlight-local-mvp`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: the user asked for a real runnable local MVP project, not more generation-framework hardening.
- Dependency check: `ADHOC-20260406-generic-archetype-mainline-and-nonnarrative-e2e` = `done`.
- Scope boundary: land one concrete local project for VTuber replay highlight detection, plus the minimal repo evidence/tests needed to close it.

## Task Truth Source

- task_purpose: create a runnable local MVP that ingests local replay videos, detects high-energy VTuber reaction segments, scores/merges/export clips, and produces a viewable report with sample assets.
- allowed_behavior_change:
  - `generated_projects/vtuber_highlight_local_mvp/`
  - `tests/test_generated_vtuber_highlight_local_mvp.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `meta/tasks/archive/20260406-generic-archetype-mainline-and-nonnarrative-e2e.md`
  - `meta/reports/archive/20260406-generic-archetype-mainline-and-nonnarrative-e2e.md`
- forbidden_goal_shift:
  - do not turn this into another framework-only refactor
  - do not claim model-level scream/laughter understanding when the implementation is still heuristic audio analysis
  - do not ship only scripts without a coherent runnable project structure
- in_scope_modules:
  - local project source, config, assets, demo outputs, and one repo-level regression for that project
- out_of_scope_modules:
  - broad repo architecture rewrites
  - unrelated frontend/backend/support lanes
- completion_evidence: sample video path exists in repo, smoke/demo path runs from local file to clips/report, minimal tests pass, and canonical verify closes from the task state.

## Analysis / Find

- Entrypoint analysis: the runnable entry should be a local CLI under `generated_projects/vtuber_highlight_local_mvp/`.
- Downstream consumer analysis: the user needs direct project files, sample media, result images, and clear run commands rather than only repo-internal generation artifacts.
- Source of truth: the user request in this turn plus repo task/report closure rules.
- Current break point / missing wiring: no such local project exists yet.
- Repo-local search sufficient: `yes`

## Integration Check

- upstream: user requested a concrete local MVP with assets, clips, report, tests, and smoke validation.
- current_module: one generated local project plus one repo-level test.
- downstream: the repo should now contain a directly runnable example of the kind of MVP it claims to produce.
- source_of_truth: the task card, the project README/config/tests, and the smoke/demo evidence.
- fallback: if environment/model limits block stronger recognition, ship a rule-based detector with explicit extension points and honest limits.
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_generated_vtuber_highlight_local_mvp.py" -v`
  - `python generated_projects/vtuber_highlight_local_mvp/src/vtuber_highlight_mvp/cli.py --help`
  - `python generated_projects/vtuber_highlight_local_mvp/src/vtuber_highlight_mvp/cli.py analyze --input generated_projects/vtuber_highlight_local_mvp/demo_assets/sample_vtuber_replay.mp4 --output generated_projects/vtuber_highlight_local_mvp/output/smoke_run --export-clips`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`
- forbidden_bypass:
  - do not replace clip export with empty placeholders
  - do not count raw JSON only as “easy viewing”; a report or equivalent human-readable view is required
  - do not rely on unavailable external APIs or hosted models for the core smoke path
- user_visible_effect: the repo contains a directly runnable local VTuber highlight detector MVP project with sample media and demo outputs.

## DoD Mapping

- [x] DoD-1: A local runnable project exists under generated_projects with clear structure, README, dependency file, config, tests, sample assets, and one smoke path from local video to results
- [x] DoD-2: The project can analyze a local sample video, emit scored candidate segments with reasons, export at least one clip, and produce a human-viewable report
- [x] DoD-3: Repo evidence is updated and canonical `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` passes from the task closure state

## Acceptance

- [x] DoD written (this file complete)
- [x] Research logged (repo-local search only)
- [x] Code changes allowed
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1. Create the project skeleton under `generated_projects/vtuber_highlight_local_mvp/`.
2. Implement the local video/audio/highlight/report/export pipeline with a rule-based core and model-extension hooks.
3. Generate tiny sample video/assets/images and add project/internal plus repo-level tests.
4. Run project smoke/demo commands and collect concrete evidence.
5. Close through canonical verify and update report/queue state.

## Check / Contrast / Fix Loop Evidence

- check-1: the repo had no concrete local VTuber replay highlight project, only generation framework plumbing.
- contrast-1: this task requires a directly runnable local MVP with sample assets, clips, report output, and a smoke path.
- fix-1: added `generated_projects/vtuber_highlight_local_mvp/` with CLI, pipeline, config, tests, demo assets, and report/export flow.
- check-2: a local project would still be weak if it only dumped JSON and never produced reviewable output.
- contrast-2: the user explicitly asked for preview-friendly review, report visibility, and exported clips.
- fix-2: the pipeline now emits `HTML + JSON + CSV`, timeline image, preview frames, and optional ffmpeg clips.
- check-3: the first canonical verify attempt failed on workflow gate because the new task card missed two mandatory evidence sections.
- contrast-3: repo closure requires the same task/report discipline as implementation tasks.
- fix-3: added the mandatory check/contrast/fix and completion-criteria sections, then re-ran verify.

## Completion Criteria Evidence

- connected + accumulated + consumed:
- connected: the local MVP path is now connected from input video to extracted audio, scored candidates, report artifacts, and clip export.
- accumulated: demo assets, screenshots, config, tests, and CLI usage instructions are stored together inside one coherent project directory.
- consumed: smoke/demo/test runs consumed the sample replay video and produced three candidate highlight windows plus exported clips and reviewable report artifacts.

## Notes / Decisions

- Default choices made: use Python CLI + HTML report + ffmpeg-backed media pipeline to maximize local run reliability.
- Alternatives considered: a thin web UI; rejected for v1 because CLI + HTML report is simpler and more robust under the current environment.
- Any contract exception reference:
  - None
- Issue memory decision: none; this is a direct delivery task, not an isolated recurring runtime defect.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: yes` using `ctcp-workflow` and `ctcp-verify` for repo-standard closure discipline.

## Results

- Files changed:
  - `generated_projects/vtuber_highlight_local_mvp/README.md`
  - `generated_projects/vtuber_highlight_local_mvp/TESTING.md`
  - `generated_projects/vtuber_highlight_local_mvp/pyproject.toml`
  - `generated_projects/vtuber_highlight_local_mvp/requirements.txt`
  - `generated_projects/vtuber_highlight_local_mvp/config/default_config.json`
  - `generated_projects/vtuber_highlight_local_mvp/run_demo.py`
  - `generated_projects/vtuber_highlight_local_mvp/src/vtuber_highlight_mvp/`
  - `generated_projects/vtuber_highlight_local_mvp/tests/test_pipeline.py`
  - `generated_projects/vtuber_highlight_local_mvp/tools/generate_demo_assets.py`
  - `generated_projects/vtuber_highlight_local_mvp/tools/generate_demo_evidence.py`
  - `generated_projects/vtuber_highlight_local_mvp/demo_assets/sample_vtuber_replay.mp4`
  - `generated_projects/vtuber_highlight_local_mvp/demo_assets/sample_vtuber_replay.keywords.txt`
  - `generated_projects/vtuber_highlight_local_mvp/demo_assets/screenshots/`
  - `generated_projects/vtuber_highlight_local_mvp/demo_assets/demo_walkthrough.gif`
  - `tests/test_generated_vtuber_highlight_local_mvp.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `meta/tasks/archive/20260406-generic-archetype-mainline-and-nonnarrative-e2e.md`
  - `meta/reports/archive/20260406-generic-archetype-mainline-and-nonnarrative-e2e.md`
- Verification summary: project CLI help passed; project internal test passed; repo-level smoke test passed; manual demo run produced 3 highlight candidates and exported 3 clips; SimLab lite replay passed after the S16 fixer-loop fixture was rebased to the new README/CURRENT state; canonical `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` passed.
- Queue status update suggestion (`todo/doing/done/blocked`): `done`
