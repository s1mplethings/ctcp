# Report Archive - 2026-03-16 - Markdown 流程拆清与逐条表达

## Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `docs/25_project_plan.md`
- `PATCH_README.md`
- `meta/tasks/TEMPLATE.md`
- `meta/reports/TEMPLATE_LAST.md`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`
- `.agents/skills/ctcp-failure-bundle/SKILL.md`

## Plan

1. Bind a docs-only markdown-flow-clarity task.
2. Add the markdown flow rule to the planning doc.
3. Rewrite task/report templates into one-item-per-line sections.
4. Rebind active `CURRENT.md` and `LAST.md` to the same clearer structure.
5. Run canonical verify and record the current first failure.

## Changes

- `docs/25_project_plan.md`
- `meta/tasks/TEMPLATE.md`
- `meta/reports/TEMPLATE_LAST.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260316-markdown-flow-clarity.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260316-markdown-flow-clarity.md`

## Verify

- `python scripts/workflow_checks.py` -> `0`
- `python scripts/contract_checks.py` -> `0`
- `python scripts/sync_doc_links.py --check` -> `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`
- first failure point:
  - gate: `lite scenario replay`
  - run_dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260316-132409`
  - summary: `passed=12`, `failed=2`
  - failed scenarios:
    - `S15_lite_fail_produces_bundle`: missing expected text `failure_bundle.zip`
    - `S16_lite_fixer_loop_pass`: missing expected text `"result": "PASS"`
- minimal fix strategy:
  - keep this task docs-only
  - open a separate repair task scoped only to the existing SimLab S15/S16 regressions
- triplet command references:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`

## Questions

- None.

## Demo

- project-plan rule: `docs/25_project_plan.md`
- task template: `meta/tasks/TEMPLATE.md`
- report template: `meta/reports/TEMPLATE_LAST.md`
- verify summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260316-132409/summary.json`
- first failing trace: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260316-132409/S15_lite_fail_produces_bundle/TRACE.md`
- second failing trace: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260316-132409/S16_lite_fixer_loop_pass/TRACE.md`
