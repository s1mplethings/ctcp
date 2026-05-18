# Live Provider Medium Project Benchmark

## Summary
- status: `passed`
- case_count: `4`
- accepted_count: `0`
- repaired_count: `4`
- fallback_count: `0`
- failed_count: `0`
- provider_request_count: `26`
- provider_plan_valid_count: `4`
- provider_manifest_valid_count: `4`
- provider_batch_count: `12`
- provider_project_candidate_count: `4`

## Cases
| case | plan_valid | manifest_valid | batch_count | candidate_count | outcome | repair_attempts | fallback_reason | provider_authored_file_ratio |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| `live_provider_inventory_manager_app` | `True` | `True` | `3` | `1` | `repaired` | `1` | `` | `0.714` |
| `live_provider_knowledge_base_app` | `True` | `True` | `3` | `1` | `repaired` | `1` | `` | `0.714` |
| `live_provider_event_booking_app` | `True` | `True` | `3` | `1` | `repaired` | `1` | `` | `0.714` |
| `live_provider_invoice_manager_app` | `True` | `True` | `3` | `1` | `repaired` | `1` | `` | `0.714` |

## Diagnostics
- `live_provider_inventory_manager_app` raw responses: `artifacts/provider_medium_raw_batch_1_attempt_1.json, artifacts/provider_medium_raw_batch_1_attempt_2.json, artifacts/provider_medium_raw_batch_2_attempt_1.json, artifacts/provider_medium_raw_batch_3_attempt_1.json, artifacts/provider_medium_raw_batch_3_attempt_2.json`
- `live_provider_inventory_manager_app` normalized manifest: `artifacts/provider_medium_normalized_manifest.json`
- `live_provider_inventory_manager_app` medium project contract: `C:\Users\sunom\AppData\Local\Temp\ctcp_live_provider_medium_project_runs\ctcp\medium-live_provider_inventory_manager_app-1779105761-8a0e07\artifacts\medium_project_contract.json`
- `live_provider_inventory_manager_app` validation failures: `artifacts/provider_medium_validation_failures.json`
- `live_provider_inventory_manager_app` repair report: `artifacts/provider_medium_repair_report.json`
- `live_provider_inventory_manager_app` attribution: `C:\Users\sunom\AppData\Local\Temp\ctcp_live_provider_medium_project_runs\ctcp\medium-live_provider_inventory_manager_app-1779105761-8a0e07\artifacts\generation_attribution.json`
- `live_provider_knowledge_base_app` raw responses: `artifacts/provider_medium_raw_batch_1_attempt_1.json, artifacts/provider_medium_raw_batch_1_attempt_2.json, artifacts/provider_medium_raw_batch_2_attempt_1.json, artifacts/provider_medium_raw_batch_3_attempt_1.json, artifacts/provider_medium_raw_batch_3_attempt_2.json`
- `live_provider_knowledge_base_app` normalized manifest: `artifacts/provider_medium_normalized_manifest.json`
- `live_provider_knowledge_base_app` medium project contract: `C:\Users\sunom\AppData\Local\Temp\ctcp_live_provider_medium_project_runs\ctcp\medium-live_provider_knowledge_base_app-1779106057-71321f\artifacts\medium_project_contract.json`
- `live_provider_knowledge_base_app` validation failures: `artifacts/provider_medium_validation_failures.json`
- `live_provider_knowledge_base_app` repair report: `artifacts/provider_medium_repair_report.json`
- `live_provider_knowledge_base_app` attribution: `C:\Users\sunom\AppData\Local\Temp\ctcp_live_provider_medium_project_runs\ctcp\medium-live_provider_knowledge_base_app-1779106057-71321f\artifacts\generation_attribution.json`
- `live_provider_event_booking_app` raw responses: `artifacts/provider_medium_raw_batch_1_attempt_1.json, artifacts/provider_medium_raw_batch_1_attempt_2.json, artifacts/provider_medium_raw_batch_2_attempt_1.json, artifacts/provider_medium_raw_batch_2_attempt_2.json, artifacts/provider_medium_raw_batch_3_attempt_1.json, artifacts/provider_medium_raw_batch_3_attempt_2.json`
- `live_provider_event_booking_app` normalized manifest: `artifacts/provider_medium_normalized_manifest.json`
- `live_provider_event_booking_app` medium project contract: `C:\Users\sunom\AppData\Local\Temp\ctcp_live_provider_medium_project_runs\ctcp\medium-live_provider_event_booking_app-1779106266-53512c\artifacts\medium_project_contract.json`
- `live_provider_event_booking_app` validation failures: `artifacts/provider_medium_validation_failures.json`
- `live_provider_event_booking_app` repair report: `artifacts/provider_medium_repair_report.json`
- `live_provider_event_booking_app` attribution: `C:\Users\sunom\AppData\Local\Temp\ctcp_live_provider_medium_project_runs\ctcp\medium-live_provider_event_booking_app-1779106266-53512c\artifacts\generation_attribution.json`
- `live_provider_invoice_manager_app` raw responses: `artifacts/provider_medium_raw_batch_1_attempt_1.json, artifacts/provider_medium_raw_batch_1_attempt_2.json, artifacts/provider_medium_raw_batch_2_attempt_1.json, artifacts/provider_medium_raw_batch_2_attempt_2.json, artifacts/provider_medium_raw_batch_3_attempt_1.json, artifacts/provider_medium_raw_batch_3_attempt_2.json`
- `live_provider_invoice_manager_app` normalized manifest: `artifacts/provider_medium_normalized_manifest.json`
- `live_provider_invoice_manager_app` medium project contract: `C:\Users\sunom\AppData\Local\Temp\ctcp_live_provider_medium_project_runs\ctcp\medium-live_provider_invoice_manager_app-1779106526-f4fcf1\artifacts\medium_project_contract.json`
- `live_provider_invoice_manager_app` validation failures: `artifacts/provider_medium_validation_failures.json`
- `live_provider_invoice_manager_app` repair report: `artifacts/provider_medium_repair_report.json`
- `live_provider_invoice_manager_app` attribution: `C:\Users\sunom\AppData\Local\Temp\ctcp_live_provider_medium_project_runs\ctcp\medium-live_provider_invoice_manager_app-1779106526-f4fcf1\artifacts\generation_attribution.json`
