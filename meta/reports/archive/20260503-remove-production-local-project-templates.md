# Demo Report - Remove Production Local Project Templates

## Latest Report

- File: `meta/reports/archive/20260503-remove-production-local-project-templates.md`
- Date: `2026-05-03`
- Topic: `Remove production local project templates`

### Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/tasks/CURRENT.md`
- `tools/providers/project_generation_source_stage.py`
- `tools/providers/project_generation_provenance.py`
- `tools/providers/project_generation_business_materializers.py`
- `tests/test_project_generation_provenance.py`
- `tests/test_project_generation_artifacts.py`
- `tests/test_plane_lite_benchmark_regression.py`
- `tests/test_project_generation_variant_content.py`
- `docs/03_quality_gates.md`
- `ai/MEMORY/ISSUE_MEMORY.md`

### Plan
1. Bind a Delivery Lane task for removing production local project-template materialization.
2. Add explicit provenance for disabled local templates.
3. Block production source generation before local deterministic materializers can write files.
4. Keep non-production benchmark/scaffold paths outside the production behavior change.
5. Update regressions, quality-gate docs, and issue memory.
6. Run targeted checks and canonical code-profile verify.

### Changes
- `tools/providers/project_generation_source_stage.py` no longer imports or calls `materialize_business_files()` on the production source-generation path.
- Production source generation now returns a blocked report with `production local project templates are disabled` before local business template files are produced.
- `tools/providers/project_generation_provenance.py` now records `disabled_local_templates`, `local_templates_disabled=true`, and a provider-source-required blocking reason.
- Project-generation regressions now assert that production runs do not create local template business files or variant sample files when provider-authored source is absent.
- `docs/03_quality_gates.md` and `ai/MEMORY/ISSUE_MEMORY.md` record the no-production-local-template rule and failure mode.

### Verify
- targeted command evidence:
  - `python -m py_compile tools\providers\project_generation_source_stage.py tools\providers\project_generation_provenance.py tests\test_plane_lite_benchmark_regression.py tests\test_project_generation_variant_content.py` passed.
  - `python tests\test_plane_lite_benchmark_regression.py -k test_high_quality_source_generation_writes_extended_coverage` passed (`1` test).
  - `$env:PYTHONPATH=(Get-Location).Path; python tests\test_project_generation_variant_content.py` passed (`1` test).
  - `python tests\test_project_generation_provenance.py` passed (`2` tests).
  - `$env:PYTHONPATH=(Get-Location).Path; python tests\test_project_generation_artifacts.py` passed (`36` tests).
  - `python scripts\module_protection_check.py` passed.
  - `python scripts\workflow_checks.py` passed.
  - `python scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` passed.
- first failure point evidence:
  - Initial canonical verify failed on two regressions that still expected production local-template outputs; fixed by updating those tests to require the new blocked/disabled behavior.
  - Post-report workflow check failed because `LAST.md` omitted mandatory triplet evidence sections; fixed by adding those command evidence entries.
- minimal fix strategy evidence:
  - Disable local business materialization at the production source-stage call site instead of only blocking final zip delivery.
  - Preserve benchmark/scaffold template assets because deleting them is a broader unrelated infrastructure change.
- triplet runtime wiring command evidence:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` ran during code-profile verify and passed.
- triplet issue memory command evidence:
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` ran during code-profile verify and passed.
- triplet skill consumption command evidence:
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` ran during code-profile verify and passed.
- canonical verify evidence:
  - command: `$env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`
  - result: passed, including lite ctest, workflow/protection/prompt/plan/patch/behavior/contract/doc/code-health/triplet/lane gates and `480` Python unit tests (`4` skipped).

### Questions
- None.

### Demo
- Production project generation with no provider-authored source now stops at source generation with `status=blocked`.
- The blocked report carries `file_materialization.strategy=disabled_local_templates` and `local_templates_disabled=true`.
- No `project_root/src` business files or variant `sample_data/example_project.json` files are emitted by the production local-template fallback.
- Direct API/provider-authored source evidence remains allowed and is still marked as provider/API content.

### Integration Proof
- upstream: `tools.providers.project_generation_artifacts.normalize_source_generation()` still calls the source-stage normalizer.
- current_module: `tools/providers/project_generation_source_stage.py` owns the production block before materialization; `project_generation_provenance.py` owns the disabled-local-template truth fields.
- downstream: project manifests and delivery logic consume the blocked source-generation report instead of receiving local template files.
- connected + accumulated + consumed:
  - connected: production source generation connects missing provider-authored source to an explicit blocked result.
  - accumulated: provenance accumulates disabled-local-template strategy and expected business-file count.
  - consumed: artifact regressions prove no local template business files are emitted and final delivery cannot proceed from that state.
