# Update 2026-02-26 (cos-user-v2p dialogue runner to fixed destination)

### Goal
- Add deterministic `ctcp_orchestrate.py cos-user-v2p` workflow with doc-first evidence, dialogue recording, external testkit execution, destination copy, verify hooks, and machine report.

### Readlist
- `AGENTS.md`
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
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`

### Plan
1) Wire `cos-user-v2p` CLI entry in `scripts/ctcp_orchestrate.py`.
2) Complete dialogue + verify + report path and taskpack-compatible script parsing.
3) Add fixtures, unit test, SimLab scenario, behavior registration.
4) Run full gate and repair first failing point only.

### Changes
- Core implementation:
  - `scripts/ctcp_orchestrate.py`
    - Added `cos-user-v2p` parser/dispatch wiring.
    - Added `cmd_cos_user_v2p` run flow and report generation.
    - Fixed dialogue script parsing to support `ask/answer + ref` JSONL.
    - Added repo verify command discovery for both repo root and `scripts/`.
    - Added top-level `dialogue_turns` in `v2p_report.json` and stricter pass condition.
  - `tools/testkit_runner.py` (new)
    - unzip + execute testkit outside repo
    - destination safety + `--force` overwrite control
    - output copy list enforcement and metric extraction
    - default `D:/v2p_tests` with CI-safe fallback when not explicit
- Fixtures/tests/scenario:
  - `tests/fixtures/dialogues/v2p_cos_user.jsonl` (new)
  - `tests/fixtures/testkits/stub_ok.zip` (new)
  - `tests/test_cos_user_v2p_runner.py` (new)
    - temp target repo + pre/post verify assertions
    - run-pointer restore guard to avoid cross-test pointer pollution
  - `simlab/scenarios/S28_cos_user_v2p_dialogue_to_D_drive.yaml` (new)
- Behavior/docs/contracts:
  - `docs/behaviors/B038-cos-user-v2p-dialogue-runner.md` (new)
  - `docs/behaviors/INDEX.md` (register B038)
  - `artifacts/PLAN.md` (Behaviors/Behavior-Refs + scope allow update)
  - `meta/tasks/CURRENT.md` updated for this task
- Additional minimal unblock for existing gate path:
  - Added missing scaffold template pack files under `templates/ctcp_ref/{minimal,standard,full}` so existing scaffold unit tests pass in lite replay contexts.

### Verify
- `python -m py_compile scripts/ctcp_orchestrate.py tools/testkit_runner.py` => exit `0`
- `python -m unittest discover -s tests -p "test_cos_user_v2p_runner.py"` => exit `0`
- `python scripts/workflow_checks.py` => exit `0`
- `python scripts/plan_check.py` => exit `0`
- `python scripts/patch_check.py` => first run exit `1`
  - first failure: out-of-scope `ctcp_cos_user_v2p_taskpack/...`
  - minimal fix: add `ctcp_cos_user_v2p_taskpack/` to `artifacts/PLAN.md` `Scope-Allow`
- `python scripts/patch_check.py` (rerun) => exit `0`
- `python scripts/behavior_catalog_check.py` => exit `0`
- `python simlab/run.py --suite lite` => first run exit `1`
  - first failure: `S16_lite_fixer_loop_pass`
  - first cause: run pointer overwritten by new unit test during nested verify
  - minimal fix: restore `meta/run_pointers/LAST_RUN.txt` in `tests/test_cos_user_v2p_runner.py`
- `python simlab/run.py --suite lite` (rerun) => exit `0`
  - run_dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260226-211053`
  - summary: `passed=14 failed=0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `0`
  - replay run_dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260226-211448`
  - summary: `passed=14 failed=0`
  - python unit tests: `Ran 68 tests, OK (skipped=3)`

### Acceptance Run (cos-user-v2p)
- Command:
  - `python scripts/ctcp_orchestrate.py cos-user-v2p --repo "C:\Users\sunom\AppData\Local\Temp\ctcp_cos_user_v2p_accept_20260226_211928\target_repo" --project v2p_lab_demo --testkit-zip tests/fixtures/testkits/stub_ok.zip --entry "python run_all.py" --dialogue-script tests/fixtures/dialogues/v2p_cos_user.jsonl --runs-root "C:\Users\sunom\AppData\Local\Temp\ctcp_cos_user_v2p_accept_20260226_211928\runs" --force`
- Exit code: `0`
- Out directory:
  - `D:/v2p_tests/v2p_lab_demo/20260226-211928-400858-cos-user-v2p-v2p_lab_demo/out`
- Generated output count:
  - copied outputs: `4`
  - key files: `scorecard.json`, `eval.json`, `cloud.ply`, `cloud_sem.ply`
- Run directory:
  - `C:\Users\sunom\AppData\Local\Temp\ctcp_cos_user_v2p_accept_20260226_211928\runs\cos_user_v2p\20260226-211928-400858-cos-user-v2p-v2p_lab_demo`
- Artifacts:
  - `TRACE.md`
  - `events.jsonl`
  - `artifacts/USER_SIM_PLAN.md`
  - `artifacts/dialogue.jsonl`
  - `artifacts/dialogue_transcript.md`
  - `artifacts/v2p_report.json`
  - `logs/verify_pre.log`
  - `logs/verify_post.log`
  - `logs/testkit_stdout.log`
  - `logs/testkit_stderr.log`

### Questions
- None.

### Demo
- Task: `meta/tasks/CURRENT.md`
- Report: `meta/reports/LAST.md`
- Acceptance run pointer: `meta/run_pointers/LAST_RUN.txt`
- Acceptance run dir:
  - `C:\Users\sunom\AppData\Local\Temp\ctcp_cos_user_v2p_accept_20260226_211928\runs\cos_user_v2p\20260226-211928-400858-cos-user-v2p-v2p_lab_demo`
- verify_repo replay summary:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260226-211448/summary.json`

### Final Recheck
- Added missing file: `templates/ctcp_ref/full/manifest.json`.
- Re-ran acceptance gate:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `0`
  - replay run_dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260226-212626`
  - summary: `passed=14 failed=0`

