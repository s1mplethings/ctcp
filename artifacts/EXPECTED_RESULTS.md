R001: PLAN contract remains parseable and signed
Acceptance: scripts/plan_check.py passes required header checks and ID resolution.
Evidence: artifacts/PLAN.md,scripts/plan_check.py,tools/checks/plan_contract.py
Related-Gates: plan_check

R002: Patch scope is enforced from PLAN scope fields
Acceptance: scripts/patch_check.py rejects changed paths outside Scope-Allow or inside Scope-Deny.
Evidence: artifacts/PLAN.md,scripts/patch_check.py
Related-Gates: patch_check

R003: Behavior catalog covers code markers bidirectionally
Acceptance: scripts/behavior_catalog_check.py validates code markers, index entries, and page sections.
Evidence: docs/behaviors/INDEX.md,scripts/behavior_catalog_check.py
Related-Gates: behavior_catalog_check

R004: verify_repo executes all PLAN-declared gates
Acceptance: scripts/plan_check.py --executed-gates confirms every PLAN gate name is recorded.
Evidence: scripts/verify_repo.ps1,scripts/verify_repo.sh
Related-Gates: lite,workflow_gate,plan_check,patch_check,behavior_catalog_check,contract_checks,doc_index_check,lite_replay,python_unit_tests

R005: Audit evidence paths are present and stable
Acceptance: scripts/plan_check.py --check-evidence confirms every EXPECTED_RESULTS Evidence path exists.
Evidence: artifacts/EXPECTED_RESULTS.md,artifacts/REASONS.md,meta/reports/LAST.md
Related-Gates: plan_check
