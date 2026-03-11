# Update 2026-02-27 (V2P fixtures auto-acquire + cleanliness hardening)

### Readlist
- `AGENTS.md`
- `docs/00_CORE.md`
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/03_quality_gates.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`

### Plan
1) Doc-first: update task/report records for this run.
2) Add fixture helper (`discover_fixtures` + `ensure_fixture`) and wire into `cos-user-v2p` args/plan/report.
3) Harden scaffold/template hygiene and manifest exclusions.
4) Add generated-project clean utility script/test and CTCP unit tests.
5) Run targeted tests + full `scripts/verify_repo.ps1`, then record first failure + minimal fix.

### Changes
- Added fixture helper module:
  - `tools/v2p_fixtures.py`
    - `discover_fixtures(search_roots, max_depth=4)`
    - `ensure_fixture(mode, repo, run_dir, user_dialogue, fixture_path=..., runs_root=...)`
    - modes: `auto|synth|path`
    - auto root order:
      1. `V2P_FIXTURES_ROOT` (if set)
      2. `D:\v2p_fixtures` (Windows)
      3. `<repo>/fixtures`, `<repo>/tests/fixtures`
      4. `<runs_root>/fixtures_cache`
    - auto mode prompts:
      - multiple fixtures: choose index (`F1`)
      - none found: `Provide fixture path, or reply 'synth' to use generated synthetic fixture.` (`F2`)
    - synth path default: `<run_dir>/sandbox/fixture`
- Wired fixture flow into orchestrator:
  - `scripts/ctcp_orchestrate.py`
    - `cos-user-v2p` new args: `--fixture-mode`, `--fixture-path`
    - `USER_SIM_PLAN.md` now records fixture mode/source/path
    - always writes `artifacts/fixture_meta.json`
    - passes fixture path into testkit env (`V2P_FIXTURE_PATH`, `CTCP_V2P_FIXTURE_PATH`)
    - `v2p_report.json` now includes fixture metadata
- Updated testkit runner env wiring:
  - `tools/testkit_runner.py`
    - `run_testkit(..., fixture_path=...)` and fixture env export
- Template/scaffold cleanliness hardening:
  - `scripts/ctcp_orchestrate.py`
    - pointcloud template collector now excludes cache/runtime artifacts (`.pytest_cache`, `__pycache__`, `*.pyc`, `.DS_Store`, `Thumbs.db`, `.mypy_cache`, `.ruff_cache`, `out`, `fixture`, `runs`)
    - `meta/manifest.json` file list filtered with same exclusion rules
    - pointcloud required outputs now include `scripts/clean_project.py` and `tests/test_clean_project.py`
  - `templates/pointcloud_project/minimal/.gitignore`
    - added cache/runtime ignore entries (`.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `fixture`, etc.)
  - removed runtime artifacts from template tree (`.pytest_cache`, `__pycache__`)
- Generated project clean utility:
  - added `templates/pointcloud_project/minimal/scripts/clean_project.py`
    - deletes only within project root: `out/`, `fixture/`, `runs/`, plus recursive `__pycache__/`, `.pytest_cache/`
  - added `templates/pointcloud_project/minimal/tests/test_clean_project.py`
  - updated `templates/pointcloud_project/minimal/scripts/verify_repo.ps1` to run clean test too
  - updated `templates/pointcloud_project/minimal/README.md` clean command section
- Tests:
  - added `tests/test_v2p_fixture_discovery.py`
  - updated `tests/test_cos_user_v2p_runner.py`
    - uses `--fixture-mode synth`
    - asserts `artifacts/fixture_meta.json` exists and source is synth
  - updated `tests/test_scaffold_pointcloud_project.py`
    - asserts new clean files are generated
    - asserts manifest excludes cache/runtime paths
    - adds template hygiene check (no runtime artifacts under template tree)
- Behavior catalog:
  - added `docs/behaviors/B040-v2p-fixture-acquisition-cleanliness.md`
  - registered in `docs/behaviors/INDEX.md`
  - linked code marker in `tools/v2p_fixtures.py` (`BEHAVIOR_ID: B040`)
- Gate scope sync:
  - updated `artifacts/PLAN.md` `Scope-Allow` to include existing taskpack root `ctcp_v2p_fixture_clean_taskpack/` (minimal patch_check unblocking).

### Verify
- Static compile:
  - `python -m py_compile scripts/ctcp_orchestrate.py tools/testkit_runner.py tools/v2p_fixtures.py tests/test_v2p_fixture_discovery.py tests/test_cos_user_v2p_runner.py tests/test_scaffold_pointcloud_project.py` => exit 0
- Targeted tests:
  - `python -m unittest discover -s tests -p "test_v2p_fixture_discovery.py" -v` => exit 0
  - `python -m unittest discover -s tests -p "test_cos_user_v2p_runner.py" -v` => exit 0
  - `python -m unittest discover -s tests -p "test_scaffold_pointcloud_project.py" -v` => exit 0
- Generated project verify:
  - scaffold minimal project + run generated `scripts/verify_repo.ps1` => `3 passed`
- Full gate first failure #1:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit 1
  - first failed gate: `patch_check`
  - reason: out-of-scope existing taskpack files under `ctcp_v2p_fixture_clean_taskpack/`
  - minimal fix: add `ctcp_v2p_fixture_clean_taskpack/` to `artifacts/PLAN.md` `Scope-Allow`
- Full gate first failure #2 (after fix #1):
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit 1
  - first failed gate: `lite scenario replay` (S28)
  - reason: `cos-user-v2p` auto->synth fallback failed when repo lacks `scripts/make_synth_fixture.py`
  - minimal fix: `tools/v2p_fixtures.py` synth fallback now creates deterministic minimal fixture in run sandbox when script is absent
- Full gate final:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit 0
  - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260227-083025/summary.json` (`passed=14 failed=0`)
  - python unit tests: `Ran 73 tests, OK (skipped=3)`

### Questions
- None.

### Demo
- Report: `meta/reports/LAST.md`
- Task card: `meta/tasks/CURRENT.md`
- Full verify replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260227-083025/summary.json`
- Example scaffold run with updated template verify (3 tests): `C:/Users/sunom/AppData/Local/Temp/ctcp_pc_fixture_6910133437be4a6ab280a3f2b70eb4c9/runs/scaffold_pointcloud/20260227-082136-948030-scaffold-pointcloud-demo_fixture`

### Final Recheck (post-report update)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit 0
- lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260227-083443/summary.json` (`passed=14 failed=0`)
- python unit tests: `Ran 73 tests, OK (skipped=3)`
- recheck refresh: `scripts/verify_repo.ps1` rerun => exit 0; lite replay run=`C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260227-083812/summary.json`.

