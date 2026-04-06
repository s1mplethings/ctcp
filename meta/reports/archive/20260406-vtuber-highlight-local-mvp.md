# Demo Report - LAST

## Latest Report

- File: `meta/reports/LAST.md`
- Date: `2026-04-06`
- Topic: `vtuber highlight local MVP project`

### Readlist

- `AGENTS.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `docs/25_project_plan.md`
- `artifacts/PLAN.md`
- `scripts/behavior_catalog_check.py`
- repo-local search for `generated_projects/`, smoke patterns, and project output expectations

### Plan

1. Bind a new ADHOC task for the concrete local MVP delivery.
2. Create a runnable project under `generated_projects/vtuber_highlight_local_mvp/`.
3. Implement the local replay analysis pipeline, sample assets, report view, clip export, and tests.
4. Run smoke/demo commands and canonical verify, then close with evidence.

### Changes

- Added a full local project under `generated_projects/vtuber_highlight_local_mvp/` with:
  - `README.md`, `TESTING.md`, `pyproject.toml`, `requirements.txt`, and default config
  - source modules for CLI, audio extraction, rule-based detection, keyword side signals, clip export, report generation, and pipeline orchestration
  - project-internal tests and one repo-level smoke regression
- Added `tools/generate_demo_assets.py` and generated:
  - `demo_assets/sample_vtuber_replay.mp4`
  - `demo_assets/sample_vtuber_replay.keywords.txt`
  - `demo_assets/screenshots/timeline_overview.png`
  - `demo_assets/screenshots/candidate_01_frame.png`
  - `demo_assets/screenshots/candidate_02_frame.png`
- Added `tools/generate_demo_evidence.py` to derive user-facing proof directly from `output/demo_run` artifacts and generated:
  - `demo_assets/screenshots/candidate_03_frame.png`
  - `demo_assets/screenshots/report_summary.png`
  - `demo_assets/screenshots/output_overview.png`
  - `demo_assets/demo_walkthrough.gif`
- The detector now emits scored candidate segments with reasons like `音量突增`, `峰值明显`, `高频尖锐反应`, and `关键词增强`.
- The runnable output path is `HTML + JSON + CSV + clips`, not just JSON dumps or isolated scripts.

### Verify

- `python generated_projects\vtuber_highlight_local_mvp\src\vtuber_highlight_mvp\cli.py --help` -> `0`
  - result: CLI entrypoint available
- `python -m unittest discover -s generated_projects\vtuber_highlight_local_mvp\tests -p "test_*.py" -v` -> `0`
  - result: project-internal minimal test passed
- `python -m unittest discover -s tests -p "test_generated_vtuber_highlight_local_mvp.py" -v` -> `0`
  - result: repo-level smoke regression passed, including clip export
- `python generated_projects\vtuber_highlight_local_mvp\run_demo.py` -> `0`
  - result: passed
  - generated candidates: `3`
  - exported clips: `3`
  - candidate windows:
    - `2.575s - 4.700s` score `88.25`
    - `6.700s - 8.950s` score `100.0`
    - `10.575s - 13.075s` score `86.70`
- `python generated_projects\vtuber_highlight_local_mvp\tools\generate_demo_evidence.py` -> `0`
  - result: passed
  - generated user-view artifacts: `6` screenshots + `1` gif
- first failure point: canonical verify initially failed at `workflow gate (workflow checks)`
  - reason: the newly rebound `CURRENT.md` and `LAST.md` were missing mandatory repo workflow evidence sections
- minimal fix strategy: add the required task/report evidence fields first, then rerun canonical verify before touching any implementation code
- secondary failure point during closure: `lite scenario replay`
  - reason: `S16_lite_fixer_loop_pass` still used a fixer patch fixture whose README/CURRENT context no longer matched the new active task/report state
- minimal fix strategy for the secondary failure: rebase `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` to the current README doc-index block and `# Task - vtuber-highlight-local-mvp`
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` via canonical verify
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0` via canonical verify
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0` via canonical verify
- `python simlab\run.py --suite lite` -> `0`
  - result: `14` scenarios passed, `0` failed
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `0`
  - result: pass
  - executed gates: `lite, workflow_gate, plan_check, patch_check, behavior_catalog_check, contract_checks, doc_index_check, code_health_check, triplet_guard, lite_replay, python_unit_tests`

### Questions

- None.

### Demo

- Goal delivered: one local runnable MVP that turns a replay video into highlight candidates, exported clips, and a reviewable HTML report.
- Detector mode: `rule_based_audio_plus_keywords`
- Viewing path:
  - run `python generated_projects/vtuber_highlight_local_mvp/run_demo.py`
  - open generated `output/demo_run/report.html`
- Fixed in-repo demo visuals:
  - `generated_projects/vtuber_highlight_local_mvp/demo_assets/screenshots/timeline_overview.png`
  - `generated_projects/vtuber_highlight_local_mvp/demo_assets/screenshots/candidate_01_frame.png`
  - `generated_projects/vtuber_highlight_local_mvp/demo_assets/screenshots/candidate_02_frame.png`
  - `generated_projects/vtuber_highlight_local_mvp/demo_assets/screenshots/candidate_03_frame.png`
  - `generated_projects/vtuber_highlight_local_mvp/demo_assets/screenshots/report_summary.png`
  - `generated_projects/vtuber_highlight_local_mvp/demo_assets/screenshots/output_overview.png`
  - `generated_projects/vtuber_highlight_local_mvp/demo_assets/demo_walkthrough.gif`
