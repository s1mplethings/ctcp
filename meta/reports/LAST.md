# Demo Report — LAST

## Goal
- Move default Team Mode / ADLC / SimLab run artifacts to external runs root, keep repo-internal files as pointers/path logic, and add clear ADLC-first multi-agent teamnet docs.

## Readlist
- `docs/00_CORE.md`
  - Conflict resolution source of truth; core remains ADLC + verifiable loop, GUI optional, find is local resolver mainline.
- `README.md`
  - Team Mode deliverables and quick-start contract must stay externally consistent.
- `AGENTS.md`
  - Execution order and allowed-question gate; output format and verify gate requirements.
- `ai_context/00_AI_CONTRACT.md`
  - Required report structure and run-bundle/question channel contract.
- `docs/10_team_mode.md`
  - Current team packet location contract needed migration.
- `BUILD.md`
  - Headless-first build constraints.
- `PATCH_README.md`
  - Unified diff delivery requirement.
- `TREE.md`
  - Existing doc/spec tree context.
- `docs/03_quality_gates.md`
  - `verify_repo` as mandatory gate.
- `ai_context/problem_registry.md`
  - Evidence-first verification precedent.
- `ai_context/decision_log.md`
  - No exemption required this run.
- `tools/ctcp_team.py`
  - Team Mode run packet creation logic.
- `scripts/adlc_run.py`
  - ADLC run output/history default paths.
- `simlab/run.py`
  - SimLab default runs root behavior.
- `.gitignore`
  - Repo hygiene for run artifacts and pointer temp files.
- `scripts/sync_doc_links.py`
  - README Doc Index curated list sync behavior.

## Plan
1) Docs/Spec
- Rewrite path policy to external `CTCP_RUNS_ROOT` + repo pointer model.
- Add path authority doc and ADLC-first agent teamnet doc.
2) Code
- Add unified run path resolver module.
- Switch Team Mode / ADLC / SimLab defaults to external run directories.
- Keep `verify_repo` replay behavior unchanged.
3) Verify
- Run `scripts/verify_repo.ps1`.
- Run Team Mode smoke and pointer checks.
4) Report
- Update LAST report and produce `artifacts/diff.patch`.

## Timeline / Trace pointer
- Run pointer file: `meta/run_pointers/LAST_RUN.txt`
- Run folder (external): `C:\Users\sunom\.ctcp\runs\ctcp\20260219-121343-smoke-goal`
- Trace file (external): `C:\Users\sunom\.ctcp\runs\ctcp\20260219-121343-smoke-goal\TRACE.md`

## Changes
- `meta/tasks/CURRENT.md`
  - Switched to current task topic and recorded default decisions.
- `docs/00_CORE.md`
  - Rewrote 2.1/2.2 to enforce external runs root and repo pointer-only internal policy.
- `README.md`
  - Updated Team Mode output section to `${CTCP_RUNS_ROOT}/ctcp/<run_id>` and `meta/run_pointers/LAST_RUN.txt`.
  - Doc Index now includes `docs/21_paths_and_locations.md` and `docs/22_agent_teamnet.md`.
- `docs/10_team_mode.md`
  - Updated run package location and pointer-based usage flow.
- `ai_context/00_AI_CONTRACT.md`
  - Updated run package and question-channel location to external run bundle + repo pointer.
- `AGENTS.md`
  - Updated allowed question and demo trace path wording for external run bundles.
- `meta/reports/TEMPLATE_LAST.md`
  - Updated timeline/questions template to pointer + external run paths.
- `meta/paths.json`
  - Added authoritative path logic metadata (`runs_root_env`, fallback, slug rule, run pattern, pointer dir).
- `docs/21_paths_and_locations.md`
  - Added authoritative repo-internal vs repo-external path rules and Windows/Linux env setup examples.
- `docs/22_agent_teamnet.md`
  - Added required two ASCII diagrams (teamnet mesh + ADLC mainline with artifacts and unique decision point).
- `meta/run_pointers/README.md`
  - Added pointer directory contract.
- `tools/run_paths.py`
  - Added unified path resolver (`get_repo_slug`, `get_runs_root`, `make_run_dir`, `default_simlab_runs_root`).
- `tools/ctcp_team.py`
  - Team runs now default to external run dir.
  - Writes `meta/run_pointers/LAST_RUN.txt`.
  - LAST report append entries now reference external absolute paths.
- `scripts/adlc_run.py`
  - Default run dir moved to external run root (`CTCP_RUNS_ROOT` fallback `~/.ctcp/runs`).
  - Writes `meta/run_pointers/LAST_RUN.txt`.
  - Run history moved from repo `meta/runs` to external repo-scope history file.
- `simlab/run.py`
  - Kept `--runs-root`; changed default to external `<runs_root>/<repo_slug>/simlab_runs`.
- `simlab/README.md`
  - Updated default output path documentation to external runs root.
- `scripts/sync_doc_links.py`
  - Added new docs to curated Doc Index.
- `tests/cases/08-team-start生成运行包.md`
  - Updated expected Team Mode output path and pointer behavior.
- `.gitignore`
  - Added run artifact/pointer-temp ignore rules for repo hygiene.
- `artifacts/diff.patch`
  - Wrote unified diff artifact for this patch theme.

## Verify
- `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1`
  - exit: `0`
  - key output:
    - `100% tests passed, 0 tests failed out of 2`
    - `[workflow_checks] ok`
    - `[contract_checks] ... ok`
    - `[sync_doc_links] ok`
    - `lite scenario replay ... "passed": 1, "failed": 0`
    - `[verify_repo] OK`
- `python tools/ctcp_team.py start "smoke goal"`
  - exit: `0`
  - key output:
    - created run: `C:\Users\sunom\.ctcp\runs\ctcp\20260219-121343-smoke-goal`
    - pointer: `meta/run_pointers/LAST_RUN.txt`
- smoke path checks:
  - `meta/run_pointers/LAST_RUN.txt` points to external absolute directory
  - external run dir contains: `PROMPT.md`, `TRACE.md`, `QUESTIONS.md`, `RUN.json`
- extra default check:
  - `python simlab/run.py --suite lite`
  - exit: `0`
  - key output:
    - run_dir under external root: `C:/Users/sunom/.ctcp/runs/ctcp/simlab_runs/...`

## Questions (only if blocking)
- None

## Next steps
- Optional: set explicit enterprise runs root before team runs:
  - Windows: `$env:CTCP_RUNS_ROOT = "D:\\ctcp-runs"`
  - Linux/macOS: `export CTCP_RUNS_ROOT=/data/ctcp-runs`

---

## Follow-up (CI job stabilization)

### Goal
- Address fast-fail CI jobs:
  - `gate-matrix / preflight-and-matrix`
  - `verify-evidence / verify (ubuntu-latest)`
  - `verify-evidence / verify (windows-latest)`

### Changes
- `tools/checks/gate_matrix_runner.py`
  - Hardened sandbox copy ignore logic:
    - removed fragile `.resolve()` on recursive artifact trees
    - added ignores for `simlab/_runs*`, `meta/runs/`, `artifacts/verify/`
  - Result: `python tools/checks/gate_matrix_runner.py` now completes successfully.
- `.github/workflows/verify.yml`
  - Removed external Qt install action (verify is headless, GUI optional).
  - Added explicit Linux build deps: `cmake`, `build-essential`, `ninja-build`, `xvfb`.

### Verify
- `python tools/checks/gate_matrix_runner.py`
  - exit: `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1`
  - exit: `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - exit: `0`
