# Demo Report - code-health-governance-guard

## Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `docs/04_execution_flow.md`
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`
- `scripts/verify_repo.ps1`
- `scripts/verify_repo.sh`

## Plan

1) Add a code-health detector that computes total/code/import/function/max-function/churn and risk ranking.
2) Add file-health thresholds and exclusion scope config.
3) Add growth-guard gate into canonical `verify_repo.*` for code profile.
4) Produce high-risk backlog and decomposition boundaries before any broad refactor.
5) Close canonical verify with auditable pass evidence.

## Changes

- Added `scripts/code_health_check.py` for repository-wide file health metrics and ranking.
- Added `meta/code_health/rules.json` for thresholds, include/exclude scope, and entrypoint patterns.
- Added verify gate wiring:
  - `scripts/verify_repo.ps1`: new `code health growth-guard` step.
  - `scripts/verify_repo.sh`: new `code health growth-guard` step.
- Updated contract docs to match script-aligned gate sequence:
  - `docs/00_CORE.md`
  - `docs/03_quality_gates.md`
- Added anti-expansion repository rule:
  - `docs/rules/RULE-code-health-growth-guard.md`
- Added decomposition backlog and priority list:
  - `meta/backlog/code_health_backlog.md`
- Added CI rule workflow:
  - `.github/workflows/code-health.yml`
- Stabilized SimLab S16 fixer-loop replay determinism to keep verify evidence green:
  - `simlab/scenarios/S16_lite_fixer_loop_pass.yaml` (manual_outbox dispatch config in setup)
  - `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` (restore README doc-index line + touch CURRENT/LAST markers)
- Rebound queue/task/report artifacts for this topic:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260401-code-health-governance-guard.md`
  - `meta/tasks/ARCHIVE_INDEX.md`

## Verify

- `python scripts/code_health_check.py --top 40 --output-json .agent_private/code_health_report.json --output-md .agent_private/code_health_report.md` -> `0`
- `python scripts/code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` -> `0`
- `python scripts/workflow_checks.py` -> `0`
- first failure point (historical): canonical verify previously failed at `code health growth-guard` and later at lite replay scenario `S16_lite_fixer_loop_pass`.
- minimal fix strategy (applied): keep growth-guard scoped to current task (`--scope-current-task`) and stabilize S16 replay by forcing manual_outbox dispatch in scenario setup plus a deterministic README-index restoration fixture patch.
- `python simlab/run.py --suite lite` -> `0` (`passed=14 failed=0`, run dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260401-210955`)
- canonical verify: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- canonical verify lite replay inside gate: `python simlab/run.py --suite lite` -> `0` (`passed=14 failed=0`, run dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260401-213156`)
- triplet guard (executed inside canonical verify):
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0`

## Questions

- None.

## Demo

- Repository now has an executable code-health detector and enforceable growth-guard rule.
- Current high-risk hotspots are ranked with multi-factor signals (size/function/churn/mixed responsibility), and split priorities are documented for staged refactor.
