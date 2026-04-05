# Demo Report - 20260403 Project Generation Mainline Closure

Archived because the active report topic moved to VN business-code generation on baseline `faeaedbd419aeb9de182c606cd7ce27eaa091e89`.

### Readlist

- `AGENTS.md`
- `meta/tasks/CURRENT.md`
- `docs/41_low_capability_project_generation.md`
- `docs/backend_interface_contract.md`
- `scripts/ctcp_dispatch.py`
- `scripts/project_generation_gate.py`
- `scripts/project_manifest_bridge.py`
- `tools/providers/api_agent.py`
- `tools/providers/project_generation_artifacts.py`
- `workflow_registry/wf_project_generation_manifest/recipe.yaml`
- `tests/manual_backend_interface_vn_project_runner.py`
- `tests/test_backend_interface_contract_apis.py`

### Plan

1. Route concrete project requests through `wf_project_generation_manifest`.
2. Add fixed generation stages and bridge-visible manifest artifacts.
3. Stop runner-side deliverable injection and rely on workflow output.

### Changes

- Routed project-generation requests into manifest workflow.
- Added `output_contract_freeze`, `source_generation`, `docs_generation`, `workflow_generation`, `artifact_manifest_build`, and `deliver` stage artifacts.
- Exposed `get_project_manifest` and stopped manual runner injection.

### Verify

- `python tests/manual_backend_interface_vn_project_runner.py` -> `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- first failure point: `PASS`
- minimal fix strategy: none for archived scope

### Questions

- None.

### Demo

- Archived handoff gap: project-generation still produced scaffold-first outputs, and librarian context was not a consumed source-generation input.
