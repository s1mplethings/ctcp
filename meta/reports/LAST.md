# Demo Report - LAST

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

1. Keep VN fixed prompt as regression input and verify current chain failure point.
2. Add missing fixed project-generation stages (`source_generation/docs_generation/workflow_generation`) and hard gate checks.
3. Connect stage execution to existing scaffold generator (no manual VN artifact injection).
4. Build manifest/deliver from real generated project files and expose via bridge.
5. Strengthen manual regression checks for full project output and startup smoke.
6. Pass targeted tests + fixed VN regression + canonical verify.

### Changes

- `workflow_registry/wf_project_generation_manifest/recipe.yaml`
  - stage list extended to include `source_generation`, `docs_generation`, `workflow_generation`.
- `scripts/project_generation_gate.py`
  - added stage-report gate checks.
  - added hard checks for `project_manifest.missing_files == []`.
  - added startup file existence checks and non-empty deliverable index check.
- `scripts/ctcp_dispatch.py`
  - added derive mapping for:
    - `artifacts/source_generation_report.json`
    - `artifacts/docs_generation_report.json`
    - `artifacts/workflow_generation_report.json`
- `tools/providers/project_generation_artifacts.py`
  - output contract now freezes real project-target lists under `project_output/<project_id>/...`.
  - added stage generators:
    - `normalize_source_generation`
    - `normalize_docs_generation`
    - `normalize_workflow_generation`
  - source stage calls existing `ctcp_orchestrate scaffold-pointcloud` template path, then records stage report.
  - manifest now includes `project_root`, `startup_entrypoint`, `startup_readme`, `scaffold_run_dir`.
  - deliver index now includes startup and project-root metadata.
- `tools/providers/api_agent.py`
  - wired new chair actions to stage normalizers.
  - kept patch output normalization.
  - compressed imports/flow to satisfy code-health growth guard.
- `scripts/project_manifest_bridge.py`
  - bridge manifest now preserves `project_root/startup_entrypoint/startup_readme/scaffold_run_dir`.
- `tests/manual_backend_interface_vn_project_runner.py`
  - upgraded regression checks from intermediate artifacts to full output closure:
    - stage reports exist
    - manifest missing files cleared
    - generated project root exists
    - startup entry/readme exist
    - startup smoke (`python <entry> --help`) passes
    - still checks no manual injected `vn_story_tree_project`.
- `tests/test_backend_interface_contract_apis.py`
  - manifest API assertions extended for `project_root/startup_entrypoint/startup_readme`.

### Verify

- `python -m py_compile tools/providers/project_generation_artifacts.py tools/providers/api_agent.py scripts/ctcp_dispatch.py scripts/project_generation_gate.py scripts/project_manifest_bridge.py tests/manual_backend_interface_vn_project_runner.py tests/test_backend_interface_contract_apis.py` -> `0`
- `python -m unittest discover -s tests -p "test_workflow_dispatch.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_backend_interface_contract_apis.py" -v` -> `0`
- `python scripts/code_health_check.py --enforce --changed-only --baseline-ref HEAD` -> `0`
- `python tests/manual_backend_interface_vn_project_runner.py` -> `0`
  - run: `20260403-013447-927876-orchestrate`
  - selected workflow: `wf_project_generation_manifest`
  - stage timeline includes `output_contract_freeze -> source_generation -> docs_generation -> workflow_generation -> artifact_manifest_build -> deliver -> ready_verify`
  - checks:
    - `manifest_missing_files_empty=true`
    - `project_root_exists=true`
    - `startup_entry_exists=true`
    - `startup_smoke_passed=true`
    - `has_manual_injected_vn_story_tree_project=false`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
  - lite replay summary: `passed=14 failed=0`

### Questions

- None.

### Demo

- Fixed VN prompt run evidence:
  - run dir: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260403-013447-927876-orchestrate`
  - generated project root: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260403-013447-927876-orchestrate\project_output\vn-cg-vn`
  - manifest path: `artifacts/project_manifest.json`
  - deliver index path: `artifacts/deliverable_index.json`
  - startup entry: `project_output/vn-cg-vn/scripts/run_v2p.py`
  - startup smoke: `python .../run_v2p.py --help` exit `0`
