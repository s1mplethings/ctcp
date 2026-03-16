# Report Archive - 2026-03-16 - 全项目健康检查与阻塞问题审计

## Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `docs/25_project_plan.md`
- `PATCH_README.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`
- `.agents/skills/ctcp-failure-bundle/SKILL.md`
- `docs/30_artifact_contracts.md`

## Plan

1. Rebind queue/current/archive to a repo-health audit task.
2. Run workflow/contract/doc-index prechecks.
3. Execute default `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`.
4. Inspect the first failing SimLab evidence plus repo-state risks.
5. Record the blockers and the smallest follow-up repair path.

## Changes

- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260316-repo-health-audit.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260316-repo-health-audit.md`

## Verify

- `python scripts/workflow_checks.py` -> `0`
- `python scripts/contract_checks.py` -> `0`
- `python scripts/sync_doc_links.py --check` -> `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (final recheck after report sync) -> `1`
- first failure point:
  - gate: `lite scenario replay`
  - run_dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260316-130140`
  - summary: `passed=12`, `failed=2`
  - failed scenarios:
    - `S15_lite_fail_produces_bundle`: the captured fixer provider prompt omits `failure_bundle.zip`, so the scenario assertion at `simlab/scenarios/S15_lite_fail_produces_bundle.yaml` no longer matches runtime behavior
    - `S16_lite_fixer_loop_pass`: the second advance exits `0` but prints `blocked: repo dirty before apply`, leaving `artifacts/verify_report.json` at `"result": "FAIL"`
- failure chain detail:
  - `S15` prompt evidence: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_external_runs/20260316-124759/S15_lite_fail_produces_bundle/sandbox/20260316-124938-803680-orchestrate/outbox/AGENT_PROMPT_fixer_fix_patch.md`
  - `S16` dirty-state evidence: sandbox `git status --short` shows tracked drift at `meta/run_pointers/LAST_BUNDLE.txt`, and the run output is `blocked: repo dirty before apply (clean workspace and retry)`
- repo-state risk:
  - `git status --short` in the main worktree is already dirty and includes both modified tracked files and untracked archive/code files, so SimLab replay falls back to `Sandbox-Mode: copy`
- minimal fix strategy:
  - open a repair task scoped to SimLab S15/S16 only
  - for `S15`, decide whether the fixer request must always expose `failure_bundle.zip`; then align either the runtime prompt/request path or the scenario expectation in one patch
  - for `S16`, stop writing tracked repo pointers into the sandbox worktree before re-apply, or exempt managed pointer drift from `repo_dirty_before_apply` during fixer-loop retries

## Demo

- verify summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260316-124759/summary.json`
- final recheck summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260316-130140/summary.json`
- first failing trace: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260316-124759/S15_lite_fail_produces_bundle/TRACE.md`
- second failing trace: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260316-124759/S16_lite_fixer_loop_pass/TRACE.md`
- `S15` provider prompt: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_external_runs/20260316-124759/S15_lite_fail_produces_bundle/sandbox/20260316-124938-803680-orchestrate/outbox/AGENT_PROMPT_fixer_fix_patch.md`
- `S16` stale verify report: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260316-124759/S16_lite_fixer_loop_pass/sandbox/artifacts/_s16_verify_report.json`
- `S16` sandbox dirty file:
  - `meta/run_pointers/LAST_BUNDLE.txt`

## Questions

- None.
