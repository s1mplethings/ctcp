# Update 2026-02-26 (full pointcloud project + dialogue benchmark runner)

### Readlist
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`

### Plan
1) Docs/Spec: update `meta/tasks/CURRENT.md`, behavior docs, and behavior index.
2) Code: add `scaffold-pointcloud` command and harden `cos-user-v2p`/`testkit_runner` constraints.
3) Assets: add pointcloud templates, fixtures, tests, and SimLab scenario.
4) Verify: run targeted tests and `scripts/verify_repo.ps1`.
5) Report: write full evidence and demo pointers in `meta/reports/LAST.md`.

### Changes
- Added command: `scripts/ctcp_orchestrate.py scaffold-pointcloud` (`BEHAVIOR_ID: B039`)
  - doc-first `artifacts/SCAFFOLD_PLAN.md` before file generation.
  - safe `--force` cleanup (inside `--out` only; filesystem root blocked).
  - profile templates from `templates/pointcloud_project/{minimal,standard}` with token replacement (`{{PROJECT_NAME}}`, `{{UTC_ISO}}`).
  - generated `meta/manifest.json` with relative file list.
  - run evidence: `TRACE.md`, `events.jsonl`, `artifacts/dialogue.jsonl`, `artifacts/dialogue_transcript.md`, `artifacts/scaffold_pointcloud_report.json`.
- Updated `scripts/ctcp_orchestrate.py` `cos-user-v2p`
  - default verify command now prefers `scripts/verify_repo.ps1` (or shell equivalent) in tested repo.
  - enforces run_dir outside CTCP repo and outside tested repo.
  - report now includes `rc` object and top-level `metrics` and `paths.sandbox_dir`.
- Updated `tools/testkit_runner.py`
  - added forbidden-root sandbox guard to ensure testkit execution stays outside CTCP repo and tested repo.
  - returns sandbox path in result for auditable reporting.
- Added templates:
  - `templates/pointcloud_project/minimal/*`
  - `templates/pointcloud_project/standard/*`
- Added fixtures:
  - `tests/fixtures/dialogues/scaffold_pointcloud.jsonl`
  - `tests/fixtures/dialogues/v2p_cos_user.jsonl` (taskpack version)
  - `tests/fixtures/testkits/stub_ok.zip` (taskpack version)
- Added/updated tests:
  - `tests/test_scaffold_pointcloud_project.py`
  - `tests/test_cos_user_v2p_runner.py`
- Added scenario:
  - `simlab/scenarios/Syy_full_pointcloud_project_then_bench.yaml`
- Behavior docs:
  - added `docs/behaviors/B039-scaffold-pointcloud.md`
  - updated `docs/behaviors/B038-cos-user-v2p-dialogue-runner.md`
  - registered B039 in `docs/behaviors/INDEX.md`
- Updated task card:
  - `meta/tasks/CURRENT.md`

### Verify
- `python -m py_compile scripts/ctcp_orchestrate.py tools/testkit_runner.py tests/test_scaffold_pointcloud_project.py tests/test_cos_user_v2p_runner.py` => exit `0`
- `python -m unittest discover -s tests -p "test_scaffold_pointcloud_project.py" -v` => exit `0`
- `python -m unittest discover -s tests -p "test_cos_user_v2p_runner.py" -v` => exit `0`
- `python -m unittest discover -s tests -p "test_scaffold_reference_project.py" -v` => exit `0`
- Acceptance demo run (external temp roots) => both commands exit `0`
  - scaffold run_dir: `C:/Users/sunom/AppData/Local/Temp/ctcp_pointcloud_demo_20260226_222831/ctcp_runs/scaffold_pointcloud/20260226-222831-836580-scaffold-pointcloud-v2p_lab`
  - benchmark run_dir: `C:/Users/sunom/AppData/Local/Temp/ctcp_pointcloud_demo_20260226_222831/ctcp_runs/cos_user_v2p/20260226-222832-058628-cos-user-v2p-v2p_lab`
  - copied out_dir: `C:/Users/sunom/AppData/Local/Temp/ctcp_pointcloud_demo_20260226_222831/v2p_tests/v2p_lab/20260226-222832-058628-cos-user-v2p-v2p_lab/out`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => first run exit `1`
  - first failure gate/check: `workflow gate (workflow checks)`
  - first failure reason: code changes detected but `meta/reports/LAST.md` not updated.
  - minimal repair: update `meta/reports/LAST.md` in same patch.

### Questions
- None.

### Demo
- Report: `meta/reports/LAST.md`
- Task card: `meta/tasks/CURRENT.md`
- Run pointer: `meta/run_pointers/LAST_RUN.txt`
- External evidence roots:
  - `C:/Users/sunom/AppData/Local/Temp/ctcp_pointcloud_demo_20260226_222831/ctcp_runs/scaffold_pointcloud/20260226-222831-836580-scaffold-pointcloud-v2p_lab`
  - `C:/Users/sunom/AppData/Local/Temp/ctcp_pointcloud_demo_20260226_222831/ctcp_runs/cos_user_v2p/20260226-222832-058628-cos-user-v2p-v2p_lab`

### Final Recheck
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (second run) => exit `1`
  - first failure gate/check: `patch check (scope from PLAN)`
  - first failure reason: out-of-scope path `ctcp_pointcloud_full_project_taskpack/00_USE_THIS_PROMPT.md`
  - minimal repair: add `ctcp_pointcloud_full_project_taskpack/` to `artifacts/PLAN.md` `Scope-Allow`.
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (third run) => exit `1`
  - first failure gate/check: `lite scenario replay`
  - first failing scenario: `S16_lite_fixer_loop_pass` (`step 7 expect_exit mismatch`)
  - root cause: new scaffold test changed `meta/run_pointers/LAST_RUN.txt` and did not restore pointer inside verify-run unit tests.
  - minimal repair: restore pointer in `tests/test_scaffold_pointcloud_project.py` (same strategy as cos-user test).
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (final run) => exit `0`
  - replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260226-223903/summary.json` (`passed=14 failed=0`)
  - python unit tests: `Ran 69 tests, OK (skipped=3)`.

