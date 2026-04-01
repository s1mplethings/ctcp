# Code Health Backlog (2026-04-01)

Source report: `python scripts/code_health_check.py --top 40 --output-json .agent_private/code_health_report.json`

## Priority A (Critical)

| File | Risk | Total | Code | Imports | Funcs | Max Func | Churn90d | Why first |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `scripts/ctcp_support_bot.py` | 334 | 6575 | 6000 | 46 | 205 | 390 | 12 | 5000+ god file, entrypoint overweight, mixed responsibility, hot churn |
| `scripts/ctcp_orchestrate.py` | 227 | 3412 | 3073 | 27 | 84 | 633 | 15 | orchestrator core + highest churn hotspot |
| `scripts/ctcp_front_bridge.py` | 138 | 1499 | 1297 | 15 | 71 | 134 | 4 | entrypoint overweight + bridge responsibilities mixed |
| `scripts/ctcp_dispatch.py` | 123 | 1188 | 1008 | 12 | 44 | 128 | 13 | dispatch hotspot + mixed orchestration/io/persistence |
| `tools/providers/api_agent.py` | 105 | 1236 | 1087 | 11 | 42 | 255 | 9 | adapter + transport + fallback + formatting mixed |
| `frontend/response_composer.py` | 103 | 1390 | 1261 | 12 | 39 | 263 | 10 | presentation + policy + state coupling and hot churn |

## Priority B (High)

| File | Risk | Total | Code | Imports | Funcs | Max Func | Churn90d | Why next |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `tests/test_support_bot_humanization.py` | 81 | 2494 | 2319 | 9 | 78 | 81 | 11 | huge coupled scenario test file, brittle hotspot |
| `tests/test_runtime_wiring_contract.py` | 72 | 1017 | 925 | 12 | 53 | 107 | 8 | contract assertions too concentrated |
| `scripts/workflows/adlc_self_improve_core.py` | 70 | 955 | 853 | 13 | 29 | 327 | 5 | long-function workflow file |
| `scripts/ctcp_persona_lab.py` | 67 | 852 | 740 | 13 | 50 | 63 | 2 | entrypoint overweight, mixed responsibilities |
| `tests/test_support_runtime_acceptance.py` | 60 | 848 | 804 | 11 | 23 | 151 | 2 | long acceptance tests coupled by flow |

## Minimal Decomposition Order

1. `scripts/ctcp_support_bot.py`
2. `scripts/ctcp_orchestrate.py`
3. `scripts/ctcp_dispatch.py`
4. `scripts/ctcp_front_bridge.py`
5. `frontend/response_composer.py`
6. `tools/providers/api_agent.py`
7. test mega-files (`test_support_bot_humanization.py`, `test_runtime_wiring_contract.py`)

Order rule:
- first cut highest churn + highest size + entrypoint files
- keep behavior stable via extraction-only patches
- no parallel broad refactor

## Target Module Boundaries

### 1) `scripts/ctcp_support_bot.py`

Extract pure strategy first:
- intent classification policy
- reply selection/ranking policy
- dedupe policy
- status digest policy

Extract adapter/runner later:
- telegram polling adapter
- provider call adapter
- session persistence adapter
- bridge invocation adapter

### 2) `scripts/ctcp_orchestrate.py`

Extract pure strategy first:
- gate transition decision table
- failure classification policy
- retry/stop policy

Extract adapter/runner later:
- run-dir IO adapter
- command execution runner
- event append adapter

### 3) `scripts/ctcp_dispatch.py`

Extract pure strategy first:
- provider selection policy
- fallback ordering policy
- budget guard policy

Extract adapter/runner later:
- provider transport adapters
- filesystem outbox writer
- subprocess runner wrapper

### 4) `scripts/ctcp_front_bridge.py`

Extract pure strategy first:
- status projection rules
- artifact-selection rules
- decision-merge policy

Extract adapter/runner later:
- backend API adapter
- shared-state read/write adapter

### 5) `frontend/response_composer.py`

Extract pure strategy first:
- response intent mapping
- style constraint policy
- progress summary policy

Extract adapter/runner later:
- locale/template rendering adapters
- channel-specific presentation adapters

### 6) `tools/providers/api_agent.py`

Extract pure strategy first:
- payload build policy
- response normalization policy
- retry/backoff policy

Extract adapter/runner later:
- HTTP client adapter
- subprocess adapter
- credential source adapter

## Guardrail After Each Split

Every split patch must keep:

- zero feature-scope expansion
- `scripts/code_health_check.py --enforce --changed-only --baseline-ref HEAD` passing
- canonical `scripts/verify_repo.*` result recorded

