# Update 2026-02-26 (scaffold reference project generator)

### Goal
- Add `ctcp_orchestrate scaffold` to generate a deterministic CTCP reference project skeleton into a user-specified output directory.

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

### Plan
1) Spec/docs first: add scaffold behavior doc + user guide.
2) Implement scaffold core (`tools/scaffold.py`) and CLI wiring in `scripts/ctcp_orchestrate.py`.
3) Add profile templates under `templates/ctcp_ref/{minimal,standard,full}`.
4) Add scaffold unit test and run targeted tests.
5) Run `scripts/verify_repo.ps1`, repair first failing gate minimally, rerun to PASS.

### Changes
- Added scaffold engine:
  - `tools/scaffold.py`
- Added scaffold command entry:
  - `scripts/ctcp_orchestrate.py` (`scaffold` subcommand + run evidence generation)
- Added template packs:
  - `templates/ctcp_ref/minimal/*`
  - `templates/ctcp_ref/standard/*`
  - `templates/ctcp_ref/full/*`
- Added docs/behavior:
  - `docs/behaviors/B037-scaffold-reference-project.md`
  - `docs/behaviors/INDEX.md` (register B037)
  - `docs/40_reference_project.md`
  - `scripts/sync_doc_links.py` + `README.md` doc-index sync
- Added tests:
  - `tests/test_scaffold_reference_project.py`
- Minimal gate robustness fix discovered during verify loop:
  - `scripts/patch_check.py` decodes git quote-path for non-ASCII changed paths.

### Verify
- `python scripts/sync_doc_links.py` => exit `0`
- `python -m unittest discover -s tests -p "test_scaffold_reference_project.py"` => exit `0`
- `python -m unittest discover -s tests -p "test_workflow_checks.py"` => exit `0`
- `python -m unittest discover -s tests -p "test_orchestrate_review_gates.py"` => exit `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => first run exit `1`
  - first failure gate/check: `patch_check`
  - first failure message: `out-of-scope path (Scope-Allow): templates/ctcp_ref/full/.gitignore`
  - minimal repair: add `templates/` to `artifacts/PLAN.md` `Scope-Allow`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => rerun exit `0`
  - `[patch_check] ok (changed_files=75 max_files=200)`
  - `[behavior_catalog_check] ok (code_ids=34 index_ids=34 files=15)`
  - `[verify_repo] OK`

### Questions
- None.

### Demo
- Manual scaffold command:
  - `python scripts/ctcp_orchestrate.py scaffold --out C:\Users\sunom\AppData\Local\Temp\ctcp_scaffold_demo_20260226_191015\my_new_proj --name my_new_proj --profile minimal --runs-root C:\Users\sunom\AppData\Local\Temp\ctcp_scaffold_demo_20260226_191015\runs`
  - exit `0`
- Out dir:
  - `C:\Users\sunom\AppData\Local\Temp\ctcp_scaffold_demo_20260226_191015\my_new_proj`
- Generated files (`written_count=9`):
  - `.gitignore`, `README.md`, `docs/00_CORE.md`, `meta/tasks/CURRENT.md`, `meta/reports/LAST.md`, `scripts/verify_repo.ps1`, `scripts/verify_repo.sh`, `TREE.md`, `manifest.json`
- Run dir:
  - `C:\Users\sunom\AppData\Local\Temp\ctcp_scaffold_demo_20260226_191015\runs\ctcp\20260226-191015-855724-scaffold-my_new_proj`
- Artifacts:
  - `TRACE.md`
  - `artifacts/scaffold_plan.md`
  - `artifacts/scaffold_report.json`
  - `logs/scaffold_verify.stdout.txt`
  - `logs/scaffold_verify.stderr.txt`

