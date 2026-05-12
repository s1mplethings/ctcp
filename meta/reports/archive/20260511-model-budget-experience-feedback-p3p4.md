# Demo Report - Model budget and Librarian experience feedback P3/P4

## Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `docs/04_execution_flow.md`
- `docs/12_virtual_team_contract.md`
- `meta/tasks/CURRENT.md`
- source_generation, Librarian retrieval, chunked API, and focused test modules

## Plan
1. Bind the P3/P4 task and write Virtual Team artifacts.
2. Add contracts for model budget and experience feedback.
3. Implement deterministic helpers.
4. Integrate source_generation and chunked API evidence.
5. Add tests and run gates.

## Changes
- Added deterministic model budget tier selection and artifact writing.
- Added Librarian experience records and recipe candidates from source_generation reports.
- Source_generation reports now reference model budget and experience artifacts.
- Chunked source_generation now records model budget choices for manifest and file-author phases.
- Retrieval can select local experience records.

## Verify
- PASS: focused new tests returned 0, 6 tests OK.
- PASS: affected regressions returned 0, 9 tests OK.
- PASS: workflow/module/patch/code-health gates returned 0.
- PASS: canonical `verify_repo.ps1 -Profile code` with `CTCP_SKIP_LITE_REPLAY=1` returned 0; Python unit tests ran 550 tests with 4 skipped.
- triplet runtime wiring command evidence: `test_runtime_wiring_contract.py` passed inside canonical verify, 25 tests OK.
- triplet issue memory command evidence: `test_issue_memory_accumulation_contract.py` passed inside canonical verify, 3 tests OK.
- triplet skill consumption command evidence: `test_skill_consumption_contract.py` passed inside canonical verify, 3 tests OK.

## Questions
- None.

## Demo
- `artifacts/model_budget.json` records stage choices and escalation rules.
- `artifacts/librarian_experience_record.json` records source_generation pass/blocked lessons.
- `artifacts/librarian_recipe_candidate.json` provides a reusable recipe candidate.

## First Failure And Repair
- first failure point evidence: no gate failed after implementation.
- repair: no repair was required.
- minimal fix strategy: keep provider-specific model routing and persistent vector ingestion out of this patch.

## Skill Decision
- skill used: `ctcp-workflow`.
- skillized: no, because this is runtime functionality rather than a reusable workflow.
- persona_lab_impact: none.
