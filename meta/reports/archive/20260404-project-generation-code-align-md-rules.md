# Demo Report - LAST

## Latest Report

- File: `meta/reports/LAST.md`
- Date: `2026-04-04`
- Topic: `Project-generation code alignment to the separated production/benchmark MD on faeaedbd419aeb9de182c606cd7ce27eaa091e89`

### Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `docs/41_low_capability_project_generation.md`
- `meta/tasks/CURRENT.md`
- `tools/providers/project_generation_artifacts.py`
- `tools/providers/project_generation_business_templates.py`
- `tools/providers/api_agent.py`
- `scripts/project_generation_gate.py`
- `scripts/project_manifest_bridge.py`
- `tests/test_project_generation_artifacts.py`
- `tests/test_backend_interface_contract_apis.py`
- `tests/manual_backend_interface_narrative_project_runner.py`
- `meta/backlog/execution_queue.json`

### Plan

1. Bind a new code-alignment task and archive the contract-only topic.
2. Add explicit production/benchmark mode plus project-type/delivery-shape decision wiring to the project-generation provider path.
3. Isolate fixed narrative sample behavior to benchmark mode and remove it from production defaults.
4. Upgrade manifest/gate artifacts with effective context influence and structural/behavioral/result gate evidence.
5. Update unit/manual regression coverage and run canonical verify.

### Changes

- `meta/backlog/execution_queue.json`
  - archived the docs-only task and bound `ADHOC-20260404-project-generation-code-align-md-rules`.
- `meta/tasks/ARCHIVE_INDEX.md`
  - added the contract-only task archive row.
- `meta/tasks/CURRENT.md`
  - rebound the active topic to runtime code alignment.
- `meta/tasks/archive/20260404-project-generation-contract-mode-separation.md`
  - captured the handoff from docs-only clarification to runtime alignment.
- `meta/reports/archive/20260404-project-generation-contract-mode-separation.md`
  - archived the contract-only report topic.
- `meta/reports/LAST.md`
  - opened the runtime-alignment report topic.
- `tools/providers/project_generation_artifacts.py`
  - added one unified project-generation decision path for `execution_mode + project_type + delivery_shape`.
  - made request-derived mode/type fields authoritative in `output_contract_freeze` so benchmark cases cannot be silently rewritten as production.
  - surfaced `context_influence_summary`, `decision_nodes`, `flow_nodes`, `gate_layers`, and `behavioral_checks` into stage and manifest artifacts.
- `tools/providers/project_generation_business_templates.py`
  - moved fixed narrative sample content behind benchmark mode only.
  - added a goal-driven production narrative template so production narrative requests no longer emit fixed benchmark characters/chapters/export content.
  - added shape-aware launcher generation for CLI/GUI/web/tool-library delivery contracts.
- `tools/providers/api_agent.py`
  - passed `run_dir` into `normalize_output_contract_freeze` so runtime constraints participate in the contract decision.
- `scripts/project_generation_gate.py`
  - upgraded validation to explicit structural/behavioral/result checks.
  - enforced mode/shape fields, effective context influence, and benchmark-vs-production separation.
  - fixed behavioral probe `rc=0` handling so passing probes do not fail the gate.
- `scripts/project_manifest_bridge.py`
  - exposed new manifest fields for mode, delivery shape, context influence, gate layers, and decision-node metadata.
- `tests/test_project_generation_artifacts.py`
  - added coverage for production-vs-benchmark split, tool-library shape selection, real context influence reporting, and layered source-generation evidence.
- `tests/test_backend_interface_contract_apis.py`
  - extended bridge manifest assertions for the new mode/type/shape/context/gate fields.
- `tests/manual_backend_interface_narrative_project_runner.py`
  - made the fixed narrative runner benchmark-explicit and updated its checks to require benchmark mode fields and non-fake context/gate evidence.

### Verify

- `python -m unittest tests/test_project_generation_artifacts.py -v` -> `1`
  - first failure point: repo test invocation style was wrong for a non-package `tests/` directory
  - minimal fix strategy: run the file directly with `PYTHONPATH=.` or use `discover`
- `$env:PYTHONPATH='.'; python tests/test_project_generation_artifacts.py` -> `0`
- `python tests/test_backend_interface_contract_apis.py` -> `0`
- `python tests/test_api_agent_templates.py` -> `0`
- `python tests/manual_backend_interface_narrative_project_runner.py` -> `1`
  - first failure point: benchmark request still resolved to production because `execution_mode` precedence favored agent output over `frontend_request.constraints`
  - minimal fix strategy: make request-derived mode/type fields authoritative in `decide_project_generation` and `normalize_output_contract_freeze`
- `python tests/manual_backend_interface_narrative_project_runner.py` -> `1`
  - follow-up failure: `behavioral_checks.startup_probe.rc=0` was being coerced to `1` inside `project_generation_gate`
  - minimal fix strategy: parse probe rc explicitly instead of using truthy fallback
- `python tests/manual_backend_interface_narrative_project_runner.py` -> `0`
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0`
- `python scripts/workflow_checks.py` -> `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`
  - first failure point: `LAST.md` was missing mandatory workflow evidence strings for workflow checks
  - minimal fix strategy: record first-failure/minimal-fix evidence and include the three triplet command lines in `LAST.md`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`
  - follow-up failure: `tools/providers/project_generation_artifacts.py` exceeded the code-health max-function guard
  - minimal fix strategy: extract helper functions and keep the project-generation mainline behavior unchanged
- `python simlab/run.py --suite lite` -> `1`
  - first failure point: `S16_lite_fixer_loop_pass` failed because `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` no longer matched the current repo headers/doc-index recovery path
  - minimal fix strategy: refresh that fix patch fixture so it restores the README doc-index line and still applies against current `meta/tasks/CURRENT.md`
- `python simlab/run.py --suite lite` -> `0` (`passed=14`, `failed=0`)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`

### Questions

- None.

### Demo

- production requests now go through a unified mode/type/shape decision and no longer inherit the fixed narrative benchmark sample by default.
- benchmark narrative regression still runs through the mainline, but only after explicit benchmark mode selection from the request constraints.
- `context_pack` is only reported as consumed when it leaves a traceable influence summary in generation and manifest artifacts.
- gate/runtime artifacts now expose structural, behavioral, and result completion separately instead of only blocking scaffold-only output.

