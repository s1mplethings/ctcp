# Root Expected Results Artifact

R201: The current root plan truthfully covers the mixed CTCP worktree for single-authority + frozen-kernel hardening.
Acceptance: `artifacts/PLAN.md`, `artifacts/REASONS.md`, `artifacts/EXPECTED_RESULTS.md`, and `contracts/module_freeze.json` describe the active task as root-authority / ownership-gate hardening while still acknowledging the already-dirty roots that remain in scope for `patch_check`.
Evidence: artifacts/PLAN.md, artifacts/REASONS.md, artifacts/EXPECTED_RESULTS.md, contracts/module_freeze.json
Related-Gates: plan_check, patch_check

R202: Prompt hierarchy hardening keeps compiled prompts below AGENTS/routed/task authority.
Acceptance: `docs/50_prompt_hierarchy_contract.md`, `docs/10_team_mode.md`, and `scripts/prompt_contract_check.py` define and enforce `AGENTS.md > routed contract + CURRENT.md > compiled PROMPT.md`, and `tests/test_prompt_contract_check.py` proves the hierarchy cannot invert.
Evidence: docs/50_prompt_hierarchy_contract.md, docs/10_team_mode.md, scripts/prompt_contract_check.py, tests/test_prompt_contract_check.py
Related-Gates: workflow_gate, prompt_contract_check

R203: Ownership/freeze gates and bridge-truth regressions are machine-enforced.
Acceptance: `contracts/module_freeze.json`, `scripts/module_protection_check.py`, `tests/test_module_protection_contract.py`, `tests/test_project_turn_mainline_contract.py`, and `tests/test_backend_interface_contract_apis.py` prove frozen-kernel elevation, bridge-only project turns, and backend snapshot truth boundaries.
Evidence: contracts/module_freeze.json, scripts/module_protection_check.py, tests/test_module_protection_contract.py, tests/test_project_turn_mainline_contract.py, tests/test_backend_interface_contract_apis.py
Related-Gates: workflow_gate, plan_check

R204: Canonical verify reaches an ownership-aware stable conclusion or records the first remaining downstream blocker.
Acceptance: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` advances through workflow, prompt hierarchy, ownership, and patch/code-health gates; if a later gate still fails, `meta/reports/LAST.md` records the new first failure and minimal fix.
Evidence: scripts/verify_repo.ps1, meta/reports/LAST.md, meta/reports/archive/20260417-mainline-freeze-ownership-hardening.md
Related-Gates: workflow_gate, prompt_contract_check, plan_check, patch_check, behavior_catalog_check
