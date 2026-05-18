# CTCP Live Provider Full Candidate Review Pack

## Live Provider Full Candidate Summary
| Case | Provider Called | Requests | Candidate Count | Accepted | Repaired | Fallback | Generated Files | Runtime Valid |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| live_provider_text_stats_cli | `True` | `1` | `1` | `True` | `False` | `False` | `project_output/live_provider_text_stats_cli/README.md, project_output/live_provider_text_stats_cli/sample.txt, project_output/live_provider_text_stats_cli/tests/__init__.py, project_output/live_provider_text_stats_cli/tests/test_text_stats.py, project_output/live_provider_text_stats_cli/text_stats.py` | `True` |
| live_provider_password_policy_package | `True` | `1` | `1` | `False` | `True` | `False` | `` | `True` |
| invalid_provider_candidate_fallback | `True` | `1` | `1` | `False` | `False` | `True` | `` | `False` |

## Deterministic Guardrails
- Ordinary mainline remains `new-run/status/advance`.
- Provider returns a structured file manifest and cannot write outside `project_output`.
- Candidate paths, safety, syntax, generated tests, imports, and runtime behavior are validated.
- Invalid candidates fall back to deterministic materializers with attribution evidence.

## Benchmark Summary
- live provider full candidate benchmark: `2/3`
- provider request count: `3`
- provider project candidate count: `3`
- accepted candidate count: `1`
- fallback count: `1`
- report: `D:\.c_projects\adc\ctcp\tests\live_provider_full_candidate_benchmark\benchmark_report.md`
- summary: `D:\.c_projects\adc\ctcp\tests\live_provider_full_candidate_benchmark\generated\live_provider_full_candidate_summary.json`

## Reproduction Commands
- `.\.venv\Scripts\python.exe tests\live_provider_full_candidate_benchmark\run_live_provider_full_candidate_benchmark.py`
- `.\.venv\Scripts\python.exe -m unittest tests.test_live_provider_full_candidate_generation -v`
- `.\.venv\Scripts\python.exe -m unittest tests.test_live_provider_full_candidate_attribution -v`
- `.\.venv\Scripts\python.exe -m unittest tests.test_live_provider_full_candidate_validation -v`
- `.\.venv\Scripts\python.exe -m unittest tests.test_live_provider_full_candidate_fallback -v`
- `.\.venv\Scripts\python.exe -m unittest tests.test_live_provider_full_candidate_safety -v`
- `.\.venv\Scripts\python.exe -m unittest tests.test_live_provider_full_candidate_review_pack -v`

## Risks For Human Review
- Full candidate mode is intentionally limited to two small non-server project types.
- Provider-authored candidates remain accepted only after deterministic validation or repaired/fallback materialization.

## Phase 20 Acceptance Hardening Summary
- previous accepted/repaired/fallback counts: `0/3/2`
- new accepted/repaired/fallback counts: `2/3/0`
- acceptance_rate: `0.4`
- accepted_or_repaired_rate: `1.0`
- gate passed: `True`
- changed logic: provider prompt contract, self-check requirements, manifest normalization, and strict gate metrics.
- fixture lowering: `no`

## Phase 21B Medium Candidate Recovery Summary

- medium cases: `4`
- provider request count: `26`
- provider plan valid count: `4`
- provider manifest valid count: `4`
- provider batch count: `12`
- provider project candidate count: `4`
- accepted count: `0`
- repaired count: `4`
- fallback count: `0`
- failed count: `0`
- ordinary mainline: `new-run/status/advance`
- agent-project/scaffold substitution: `no`
