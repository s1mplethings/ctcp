# Demo Report - mainline-freeze-ownership-hardening

## Latest Report

- File: `meta/reports/archive/20260417-mainline-freeze-ownership-hardening.md`
- Date: `2026-04-17`
- Topic: `Harden single-authority prompt hierarchy, frozen kernels, and forced CTCP mainline ownership gates`

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `docs/04_execution_flow.md`
- `docs/10_team_mode.md`
- `docs/42_frontend_backend_separation_contract.md`
- `scripts/classify_change_profile.py`
- `scripts/verify_repo.ps1`
- `scripts/verify_repo.sh`
- existing verify / smoke / contract tests plus bridge/support runtime regressions under `tests/`

### Plan
1. Rebind queue/current/report artifacts to this governance-hardening topic and add explicit write-scope/elevation fields to the task-card template.
2. Land prompt hierarchy and module freeze contracts without introducing a second authority surface.
3. Extend classify/verify/workflow checks so ownership and protection participate in the acceptance gate.
4. Add regression tests proving project turns stay on the CTCP bridge mainline and frontend/support cannot invent execution truth.
5. Run focused tests plus canonical verify, then record the first blocking point and final rerun result.

### Changes
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/TEMPLATE.md`
- `meta/reports/LAST.md`
- `artifacts/PLAN.md`
- `artifacts/EXPECTED_RESULTS.md`
- `artifacts/REASONS.md`
- `AGENTS.md`
- `contracts/module_freeze.json`
- `docs/03_quality_gates.md`
- `docs/04_execution_flow.md`
- `docs/10_team_mode.md`
- `docs/42_frontend_backend_separation_contract.md`
- `docs/50_prompt_hierarchy_contract.md`
- `scripts/classify_change_profile.py`
- `scripts/ctcp_front_bridge_views.py`
- `scripts/module_protection_check.py`
- `scripts/prompt_contract_check.py`
- `scripts/verify_repo.ps1`
- `scripts/verify_repo.sh`
- `scripts/workflow_checks.py`
- `tests/test_backend_interface_contract_apis.py`
- `tests/test_module_protection_contract.py`
- `tests/test_project_turn_mainline_contract.py`
- `tests/test_prompt_contract_check.py`
- `tests/test_support_to_production_path.py`
- `tests/test_workflow_checks.py`
- `tools/module_protection.py`
- `meta/tasks/ARCHIVE_INDEX.md`
- `meta/tasks/archive/20260417-mainline-freeze-ownership-hardening.md`
- `meta/reports/archive/20260417-mainline-freeze-ownership-hardening.md`

### Verify
- first failure point: the penultimate canonical `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` run on `2026-04-17` failed at `python unit tests` because provider/env fail-fast contracts were masked by embedded API-key fallback behavior in `tools/providers/api_agent.py` and `llm_core/clients/openai_compatible.py`
- minimal fix strategy: remove the embedded API-key fallback, keep env/notes/CTCP credential resolution intact, and rerun the affected provider plus canonical suites
- canonical verify command:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `0`
- provider/env closeout:
  - `python -m unittest discover -s tests -p "test_openai_external_api_wrappers.py" -v` -> `3 tests OK`
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v` -> `12 tests OK`
  - `python -m unittest discover -s tests -p "test_openai_responses_client_resilience.py" -v` -> `5 tests OK`
  - `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v` -> `15 tests OK`
  - `python -m unittest discover -s tests -p "test_llm_core_openai_compatible.py" -v` -> `3 tests OK`
- prompt hierarchy contract check:
  - `python -m unittest discover -s tests -p "test_prompt_contract_check.py" -v` -> `5 tests OK`
- frozen-kernel ownership gate tests:
  - `python -m unittest discover -s tests -p "test_module_protection_contract.py" -v` -> `4 tests OK`
- project mainline bridge regression:
  - `python -m unittest discover -s tests -p "test_project_turn_mainline_contract.py" -v` -> `1 test OK`
- support-to-production lane regression:
  - `python -m unittest discover -s tests -p "test_support_to_production_path.py" -v` -> `15 tests OK`
- backend truth boundary regression:
  - `python -m unittest discover -s tests -p "test_backend_interface_contract_apis.py" -v` -> `6 tests OK`
- ownership gate command evidence:
  - `python scripts/module_protection_check.py` -> `ownership=frozen-kernel changed=49 ignored=235 ok`
- triplet runtime wiring command evidence:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `23 tests OK`
- triplet issue memory command evidence:
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `3 tests OK`
- triplet skill consumption command evidence:
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `3 tests OK`
- workflow gate rerun:
  - `python scripts/workflow_checks.py` -> `0`
- plan evidence gate:
  - `python scripts/plan_check.py --executed-gates lite,workflow_gate,prompt_contract_check,plan_check,patch_check,behavior_catalog_check --check-evidence` -> `0`
- workflow check fixture regression:
  - `python -m unittest discover -s tests -p "test_workflow_checks.py" -v` -> `2 tests OK`

### Questions
- None.

### Demo
- machine-readable freeze contract: `contracts/module_freeze.json`
- prompt hierarchy contract: `docs/50_prompt_hierarchy_contract.md`
- final proof point within scope:
  - `project turn must stay on CTCP mainline` -> `python -m unittest discover -s tests -p "test_project_turn_mainline_contract.py" -v` -> `1 test OK`
  - `frontend/support must not invent customer-facing truth` -> `python -m unittest discover -s tests -p "test_backend_interface_contract_apis.py" -v` -> `6 tests OK`
  - `frozen-kernel/ownership/elevation gate must fire` -> `python -m unittest discover -s tests -p "test_module_protection_contract.py" -v` -> `4 tests OK`
  - `final canonical acceptance` -> `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `0`
