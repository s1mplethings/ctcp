# Agent Factory Benchmark Report

## Project Discovery
- project type: Python CTCP goal-to-MVP project generator with CMake headless support
- runtime: Python 3; optional CMake headless build; no package.json/pyproject project script file at repo root
- entrypoints: scripts/ctcp_orchestrate.py new-run/status/advance, scripts/resolve_workflow.py --goal --out, tools.providers.project_generation_artifacts.normalize_output_contract_freeze, tools.providers.project_generation_artifacts.normalize_source_generation, tools.providers.project_generation_artifacts.normalize_workflow_generation, tools.providers.project_generation_artifacts.normalize_project_manifest
- previous_entrypoint: scripts/resolve_workflow.py
- new_entrypoint: scripts/generate_agent_manifest.py
- reason: resolve_workflow outputs CTCP project workflow docs, not agent manifest
- agent manifest generation entrypoint: scripts/generate_agent_manifest.py --input <fixture.json> --output <output.json>
- test command: .venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1
- runtime status: can run
- dependency files: requirements-dev.txt, CMakeLists.txt
- schema files: contracts/__init__.py, contracts/agent_manifest.schema.json, contracts/enums.py, contracts/file_manifest.schema.json, contracts/file_task.schema.json, contracts/librarian_context_pack.schema.json, contracts/librarian_experience_record.schema.json, contracts/library_usage_verification.schema.json, contracts/model_budget.schema.json, contracts/module_freeze.json, contracts/project_capability_bundles.json, contracts/project_domain_matrix.json, contracts/project_library_plan.schema.json, contracts/retrieval_trace.schema.json, contracts/validation.py, contracts/version.py

```json
{
  "project_type": "Python CTCP goal-to-MVP project generator with CMake headless support",
  "runtime": "Python 3; optional CMake headless build; no package.json/pyproject project script file at repo root",
  "entrypoints_found": [
    "scripts/ctcp_orchestrate.py new-run/status/advance",
    "scripts/resolve_workflow.py --goal --out",
    "tools.providers.project_generation_artifacts.normalize_output_contract_freeze",
    "tools.providers.project_generation_artifacts.normalize_source_generation",
    "tools.providers.project_generation_artifacts.normalize_workflow_generation",
    "tools.providers.project_generation_artifacts.normalize_project_manifest"
  ],
  "previous_entrypoint": "scripts/resolve_workflow.py",
  "new_entrypoint": "scripts/generate_agent_manifest.py",
  "reason": "resolve_workflow outputs CTCP project workflow docs, not agent manifest",
  "agent_manifest_generation_entrypoint": "scripts/generate_agent_manifest.py --input <fixture.json> --output <output.json>",
  "test_commands_found": [
    ".venv\\Scripts\\python.exe -m unittest discover -s tests -p \"test_*.py\"",
    "powershell -ExecutionPolicy Bypass -File scripts\\verify_repo.ps1"
  ],
  "existing_schema_files": [
    "contracts/__init__.py",
    "contracts/agent_manifest.schema.json",
    "contracts/enums.py",
    "contracts/file_manifest.schema.json",
    "contracts/file_task.schema.json",
    "contracts/librarian_context_pack.schema.json",
    "contracts/librarian_experience_record.schema.json",
    "contracts/library_usage_verification.schema.json",
    "contracts/model_budget.schema.json",
    "contracts/module_freeze.json",
    "contracts/project_capability_bundles.json",
    "contracts/project_domain_matrix.json",
    "contracts/project_library_plan.schema.json",
    "contracts/retrieval_trace.schema.json",
    "contracts/validation.py",
    "contracts/version.py"
  ],
  "can_run_project": true,
  "blocking_issues": []
}
```

## Benchmark Summary
- phase1_pass_count: 6
- phase1_fail_count: 0
- phase1_unsupported_count: 0
- phase2_pass_count: 8
- phase2_fail_count: 0
- phase2_warning_count: 0
- phase2_unsupported_count: 0
- holdout_pass_count: 10
- holdout_fail_count: 0
- holdout_warning_count: 0
- holdout_unsupported_count: 0

### Phase 1 Structural Benchmark

| Case | Status | Key Failures |
|---|---|---|
| agent_factory | pass | none |
| devops_incident | pass | none |
| ecommerce_growth | pass | none |
| github_triage | pass | none |
| knowledge_research | pass | none |
| permission_attack | pass | none |

## Detailed Results

### agent_factory
- input fixture path: `tests/agent_factory_benchmark/fixtures/input_agent_factory.json`
- generated output path: `tests/agent_factory_benchmark/generated/output_agent_factory.json`
- validators run: schema_validator, permission_validator, workflow_validator, tool_validator
- passed assertions: 72
- failed assertions: 0
- unsupported features: 0

### devops_incident
- input fixture path: `tests/agent_factory_benchmark/fixtures/input_devops_incident.json`
- generated output path: `tests/agent_factory_benchmark/generated/output_devops_incident.json`
- validators run: schema_validator, permission_validator, workflow_validator, tool_validator
- passed assertions: 133
- failed assertions: 0
- unsupported features: 0

### ecommerce_growth
- input fixture path: `tests/agent_factory_benchmark/fixtures/input_ecommerce_growth.json`
- generated output path: `tests/agent_factory_benchmark/generated/output_ecommerce_growth.json`
- validators run: schema_validator, permission_validator, workflow_validator, tool_validator
- passed assertions: 144
- failed assertions: 0
- unsupported features: 0

### github_triage
- input fixture path: `tests/agent_factory_benchmark/fixtures/input_github_triage.json`
- generated output path: `tests/agent_factory_benchmark/generated/output_github_triage.json`
- validators run: schema_validator, permission_validator, workflow_validator, tool_validator
- passed assertions: 122
- failed assertions: 0
- unsupported features: 0

### knowledge_research
- input fixture path: `tests/agent_factory_benchmark/fixtures/input_knowledge_research.json`
- generated output path: `tests/agent_factory_benchmark/generated/output_knowledge_research.json`
- validators run: schema_validator, permission_validator, workflow_validator, tool_validator
- passed assertions: 92
- failed assertions: 0
- unsupported features: 0

### permission_attack
- input fixture path: `tests/agent_factory_benchmark/fixtures/input_permission_attack.json`
- generated output path: `tests/agent_factory_benchmark/generated/output_permission_attack.json`
- validators run: schema_validator, permission_validator, workflow_validator, tool_validator
- passed assertions: 183
- failed assertions: 0
- unsupported features: 0

# Phase 2 Semantic Stress Benchmark

- phase2_total_cases: 8
- phase2_pass_count: 8
- phase2_fail_count: 0
- phase2_warning_count: 0
- phase2_unsupported_count: 0

| Case | Structural Pass | Security Pass | Semantic Pass | Status | Key Failures | Warnings |
|---|---:|---:|---:|---|---|---|
| s1_product_feedback | yes | yes | yes | pass | none | none |
| s2_billing_refund | yes | yes | yes | pass | none | none |
| s3_prompt_injection | yes | yes | yes | pass | none | none |
| s4_cross_agent_bypass | yes | yes | yes | pass | none | none |
| s5_legal_contract_review | yes | yes | yes | pass | none | none |
| s6_release_notes | yes | yes | yes | pass | none | none |
| s7_ambiguous_customer_support | yes | yes | yes | pass | none | none |
| s8_conflicting_communication | yes | yes | yes | pass | none | none |

## Phase 2 Detailed Results

### s1_product_feedback
- input fixture path: `tests/agent_factory_benchmark/semantic_fixtures/input_s1_product_feedback.json`
- generated output path: `tests/agent_factory_benchmark/semantic_generated/output_s1_product_feedback.json`
- validators run: relevance_validator, overgeneration_validator, permission_bypass_validator, ambiguity_validator, conflict_resolution_validator
- passed assertions: 26
- failed assertions: 0
- warnings: 0
- unsupported features: 0

### s2_billing_refund
- input fixture path: `tests/agent_factory_benchmark/semantic_fixtures/input_s2_billing_refund.json`
- generated output path: `tests/agent_factory_benchmark/semantic_generated/output_s2_billing_refund.json`
- validators run: relevance_validator, overgeneration_validator, permission_bypass_validator, ambiguity_validator, conflict_resolution_validator
- passed assertions: 24
- failed assertions: 0
- warnings: 0
- unsupported features: 0

### s3_prompt_injection
- input fixture path: `tests/agent_factory_benchmark/semantic_fixtures/input_s3_prompt_injection.json`
- generated output path: `tests/agent_factory_benchmark/semantic_generated/output_s3_prompt_injection.json`
- validators run: relevance_validator, overgeneration_validator, permission_bypass_validator, ambiguity_validator, conflict_resolution_validator
- passed assertions: 28
- failed assertions: 0
- warnings: 0
- unsupported features: 0

### s4_cross_agent_bypass
- input fixture path: `tests/agent_factory_benchmark/semantic_fixtures/input_s4_cross_agent_bypass.json`
- generated output path: `tests/agent_factory_benchmark/semantic_generated/output_s4_cross_agent_bypass.json`
- validators run: relevance_validator, overgeneration_validator, permission_bypass_validator, ambiguity_validator, conflict_resolution_validator
- passed assertions: 29
- failed assertions: 0
- warnings: 0
- unsupported features: 0

### s5_legal_contract_review
- input fixture path: `tests/agent_factory_benchmark/semantic_fixtures/input_s5_legal_contract_review.json`
- generated output path: `tests/agent_factory_benchmark/semantic_generated/output_s5_legal_contract_review.json`
- validators run: relevance_validator, overgeneration_validator, permission_bypass_validator, ambiguity_validator, conflict_resolution_validator
- passed assertions: 31
- failed assertions: 0
- warnings: 0
- unsupported features: 0

### s6_release_notes
- input fixture path: `tests/agent_factory_benchmark/semantic_fixtures/input_s6_release_notes.json`
- generated output path: `tests/agent_factory_benchmark/semantic_generated/output_s6_release_notes.json`
- validators run: relevance_validator, overgeneration_validator, permission_bypass_validator, ambiguity_validator, conflict_resolution_validator
- passed assertions: 32
- failed assertions: 0
- warnings: 0
- unsupported features: 0

### s7_ambiguous_customer_support
- input fixture path: `tests/agent_factory_benchmark/semantic_fixtures/input_s7_ambiguous_customer_support.json`
- generated output path: `tests/agent_factory_benchmark/semantic_generated/output_s7_ambiguous_customer_support.json`
- validators run: relevance_validator, overgeneration_validator, permission_bypass_validator, ambiguity_validator, conflict_resolution_validator
- passed assertions: 31
- failed assertions: 0
- warnings: 0
- unsupported features: 0

### s8_conflicting_communication
- input fixture path: `tests/agent_factory_benchmark/semantic_fixtures/input_s8_conflicting_communication.json`
- generated output path: `tests/agent_factory_benchmark/semantic_generated/output_s8_conflicting_communication.json`
- validators run: relevance_validator, overgeneration_validator, permission_bypass_validator, ambiguity_validator, conflict_resolution_validator
- passed assertions: 30
- failed assertions: 0
- warnings: 0
- unsupported features: 0

# Phase 2.5 Holdout Generalization Audit

- holdout_total_cases: 10
- holdout_pass_count: 10
- holdout_fail_count: 0
- holdout_warning_count: 0
- holdout_unsupported_count: 0
- generator_frozen: true

| Case | Status | Failed Assertions | Warnings |
|---|---|---|---|
| h10_product_launch_coordination | pass | none | none |
| h1_personal_productivity | pass | none | none |
| h2_patient_intake | pass | none | none |
| h3_investment_research | pass | none | none |
| h4_homework_tutor | pass | none | none |
| h5_recruiting_screening | pass | none | none |
| h6_community_moderation | pass | none | none |
| h7_privacy_request | pass | none | none |
| h8_plugin_marketplace_review | pass | none | none |
| h9_battery_charging_station | pass | none | none |

## Phase 2.5 Detailed Results

### h10_product_launch_coordination
- input fixture path: `tests/agent_factory_benchmark/holdout_fixtures/input_h10_product_launch_coordination.json`
- generated output path: `tests/agent_factory_benchmark/holdout_generated/output_h10_product_launch_coordination.json`
- validators run: domain_precision_validator, regulated_domain_safety_validator, minimality_validator, action_risk_validator, similarity_validator
- passed assertions: 14
- failed assertions: 0
- warnings: 0
- unsupported features: 0

### h1_personal_productivity
- input fixture path: `tests/agent_factory_benchmark/holdout_fixtures/input_h1_personal_productivity.json`
- generated output path: `tests/agent_factory_benchmark/holdout_generated/output_h1_personal_productivity.json`
- validators run: domain_precision_validator, regulated_domain_safety_validator, minimality_validator, action_risk_validator, similarity_validator
- passed assertions: 14
- failed assertions: 0
- warnings: 0
- unsupported features: 0

### h2_patient_intake
- input fixture path: `tests/agent_factory_benchmark/holdout_fixtures/input_h2_patient_intake.json`
- generated output path: `tests/agent_factory_benchmark/holdout_generated/output_h2_patient_intake.json`
- validators run: domain_precision_validator, regulated_domain_safety_validator, minimality_validator, action_risk_validator, similarity_validator
- passed assertions: 17
- failed assertions: 0
- warnings: 0
- unsupported features: 0

### h3_investment_research
- input fixture path: `tests/agent_factory_benchmark/holdout_fixtures/input_h3_investment_research.json`
- generated output path: `tests/agent_factory_benchmark/holdout_generated/output_h3_investment_research.json`
- validators run: domain_precision_validator, regulated_domain_safety_validator, minimality_validator, action_risk_validator, similarity_validator
- passed assertions: 16
- failed assertions: 0
- warnings: 0
- unsupported features: 0

### h4_homework_tutor
- input fixture path: `tests/agent_factory_benchmark/holdout_fixtures/input_h4_homework_tutor.json`
- generated output path: `tests/agent_factory_benchmark/holdout_generated/output_h4_homework_tutor.json`
- validators run: domain_precision_validator, regulated_domain_safety_validator, minimality_validator, action_risk_validator, similarity_validator
- passed assertions: 15
- failed assertions: 0
- warnings: 0
- unsupported features: 0

### h5_recruiting_screening
- input fixture path: `tests/agent_factory_benchmark/holdout_fixtures/input_h5_recruiting_screening.json`
- generated output path: `tests/agent_factory_benchmark/holdout_generated/output_h5_recruiting_screening.json`
- validators run: domain_precision_validator, regulated_domain_safety_validator, minimality_validator, action_risk_validator, similarity_validator
- passed assertions: 17
- failed assertions: 0
- warnings: 0
- unsupported features: 0

### h6_community_moderation
- input fixture path: `tests/agent_factory_benchmark/holdout_fixtures/input_h6_community_moderation.json`
- generated output path: `tests/agent_factory_benchmark/holdout_generated/output_h6_community_moderation.json`
- validators run: domain_precision_validator, regulated_domain_safety_validator, minimality_validator, action_risk_validator, similarity_validator
- passed assertions: 14
- failed assertions: 0
- warnings: 0
- unsupported features: 0

### h7_privacy_request
- input fixture path: `tests/agent_factory_benchmark/holdout_fixtures/input_h7_privacy_request.json`
- generated output path: `tests/agent_factory_benchmark/holdout_generated/output_h7_privacy_request.json`
- validators run: domain_precision_validator, regulated_domain_safety_validator, minimality_validator, action_risk_validator, similarity_validator
- passed assertions: 20
- failed assertions: 0
- warnings: 0
- unsupported features: 0

### h8_plugin_marketplace_review
- input fixture path: `tests/agent_factory_benchmark/holdout_fixtures/input_h8_plugin_marketplace_review.json`
- generated output path: `tests/agent_factory_benchmark/holdout_generated/output_h8_plugin_marketplace_review.json`
- validators run: domain_precision_validator, regulated_domain_safety_validator, minimality_validator, action_risk_validator, similarity_validator
- passed assertions: 14
- failed assertions: 0
- warnings: 0
- unsupported features: 0

### h9_battery_charging_station
- input fixture path: `tests/agent_factory_benchmark/holdout_fixtures/input_h9_battery_charging_station.json`
- generated output path: `tests/agent_factory_benchmark/holdout_generated/output_h9_battery_charging_station.json`
- validators run: domain_precision_validator, regulated_domain_safety_validator, minimality_validator, action_risk_validator, similarity_validator
- passed assertions: 13
- failed assertions: 0
- warnings: 0
- unsupported features: 0

# Phase 4 End-to-End Agent Project Pipeline

- phase4_total_cases: 6
- phase4_pass_count: 6
- phase4_fail_count: 0
- phase4_unsupported_count: 0

| Case | Status | Manifest | Scaffold | Dry Run | Scaffold Tests | Permission Checks | Domain Checks | Failed Assertions |
|---|---|---:|---:|---:|---:|---:|---:|---|
| devops_incident | pass | True | True | True | True | True | True | none |
| permission_attack | pass | True | True | True | True | True | True | none |
| holdout_h1_personal_productivity | pass | True | True | True | True | True | True | none |
| holdout_h2_patient_intake | pass | True | True | True | True | True | True | none |
| holdout_h9_battery_charging | pass | True | True | True | True | True | True | none |
| holdout_h10_product_launch | pass | True | True | True | True | True | True | none |

## Phase 4 Detailed Results

### devops_incident
- input path: `tests/agent_factory_benchmark/fixtures/input_devops_incident.json`
- manifest path: `C:/Users/sunom/AppData/Local/Temp/ctcp_phase4_devops_incident_yllgnabs/agent_project/manifest.json`
- scaffold output dir: `C:/Users/sunom/AppData/Local/Temp/ctcp_phase4_devops_incident_yllgnabs/agent_project/scaffold`
- pipeline report generated: True
- pipeline report status: passed
- manifest generated: True
- scaffold generated: True
- scaffold tests generated: True
- dry-run passed: True
- generated scaffold tests passed: True
- permission checks passed: True
- domain regression checks passed: True
- failed assertions: 0

### permission_attack
- input path: `tests/agent_factory_benchmark/fixtures/input_permission_attack.json`
- manifest path: `C:/Users/sunom/AppData/Local/Temp/ctcp_phase4_permission_attack_gafzo308/agent_project/manifest.json`
- scaffold output dir: `C:/Users/sunom/AppData/Local/Temp/ctcp_phase4_permission_attack_gafzo308/agent_project/scaffold`
- pipeline report generated: True
- pipeline report status: passed
- manifest generated: True
- scaffold generated: True
- scaffold tests generated: True
- dry-run passed: True
- generated scaffold tests passed: True
- permission checks passed: True
- domain regression checks passed: True
- failed assertions: 0

### holdout_h1_personal_productivity
- input path: `tests/agent_factory_benchmark/holdout_fixtures/input_h1_personal_productivity.json`
- manifest path: `C:/Users/sunom/AppData/Local/Temp/ctcp_phase4_holdout_h1_personal_productivity_b7jabp0a/agent_project/manifest.json`
- scaffold output dir: `C:/Users/sunom/AppData/Local/Temp/ctcp_phase4_holdout_h1_personal_productivity_b7jabp0a/agent_project/scaffold`
- pipeline report generated: True
- pipeline report status: passed
- manifest generated: True
- scaffold generated: True
- scaffold tests generated: True
- dry-run passed: True
- generated scaffold tests passed: True
- permission checks passed: True
- domain regression checks passed: True
- failed assertions: 0

### holdout_h2_patient_intake
- input path: `tests/agent_factory_benchmark/holdout_fixtures/input_h2_patient_intake.json`
- manifest path: `C:/Users/sunom/AppData/Local/Temp/ctcp_phase4_holdout_h2_patient_intake_9hs3as7y/agent_project/manifest.json`
- scaffold output dir: `C:/Users/sunom/AppData/Local/Temp/ctcp_phase4_holdout_h2_patient_intake_9hs3as7y/agent_project/scaffold`
- pipeline report generated: True
- pipeline report status: passed
- manifest generated: True
- scaffold generated: True
- scaffold tests generated: True
- dry-run passed: True
- generated scaffold tests passed: True
- permission checks passed: True
- domain regression checks passed: True
- failed assertions: 0

### holdout_h9_battery_charging
- input path: `tests/agent_factory_benchmark/holdout_fixtures/input_h9_battery_charging_station.json`
- manifest path: `C:/Users/sunom/AppData/Local/Temp/ctcp_phase4_holdout_h9_battery_charging_crq43q9k/agent_project/manifest.json`
- scaffold output dir: `C:/Users/sunom/AppData/Local/Temp/ctcp_phase4_holdout_h9_battery_charging_crq43q9k/agent_project/scaffold`
- pipeline report generated: True
- pipeline report status: passed
- manifest generated: True
- scaffold generated: True
- scaffold tests generated: True
- dry-run passed: True
- generated scaffold tests passed: True
- permission checks passed: True
- domain regression checks passed: True
- failed assertions: 0

### holdout_h10_product_launch
- input path: `tests/agent_factory_benchmark/holdout_fixtures/input_h10_product_launch_coordination.json`
- manifest path: `C:/Users/sunom/AppData/Local/Temp/ctcp_phase4_holdout_h10_product_launch_85brjtb9/agent_project/manifest.json`
- scaffold output dir: `C:/Users/sunom/AppData/Local/Temp/ctcp_phase4_holdout_h10_product_launch_85brjtb9/agent_project/scaffold`
- pipeline report generated: True
- pipeline report status: passed
- manifest generated: True
- scaffold generated: True
- scaffold tests generated: True
- dry-run passed: True
- generated scaffold tests passed: True
- permission checks passed: True
- domain regression checks passed: True
- failed assertions: 0

## Critical Bugs
- Phase 1 failures would indicate structural or basic security regressions.
- Phase 2 semantic failures indicate domain mismatch, overgeneration, permission bypass, ambiguity, or conflict-resolution weakness.
- Phase 2.5 holdout failures indicate frozen-generator generalization gaps and are not repaired in this audit.
- Current semantic failure count: 0.
- Current holdout failure count: 0.

## Design Weaknesses
- The manifest generator remains deterministic and signal-based; phase 2 now checks whether those signals produce domain-specific manifests.
- Holdout results measure blind generalization without generator changes.
- Semantic validators are intentionally explicit and should grow with new benchmark scenarios.
- This entrypoint is separate from CTCP project-generation and should not be treated as full agent runtime execution.

## Semantic Failures
- none

## Overgeneration Warnings
- none

## Holdout Domain Confusion And Overgeneration Findings
- none

## Suggested Fixes
- Recommended generator improvements: add phrase-level negation handling for domain detection.
- Recommended generator improvements: add richer clause/message/risk taxonomies for legal and customer-communication domains.
- Recommended generator improvements from holdout: add regulated-domain packs for medical, finance, recruiting, privacy, education, moderation, marketplace review, and launch coordination.
- Recommended generator improvements: add learned examples only after deterministic benchmark regressions are stable.

## Reproduction Commands
- `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe tests\agent_factory_benchmark\run_benchmark.py`
- `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe scripts\generate_agent_manifest.py --input tests\agent_factory_benchmark\fixtures\input_devops_incident.json --output tests\agent_factory_benchmark\generated\output_devops_incident.json`
- `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe scripts\ctcp_orchestrate.py agent-project --input tests\agent_factory_benchmark\fixtures\input_devops_incident.json --output-dir runs\agent_project_devops`
