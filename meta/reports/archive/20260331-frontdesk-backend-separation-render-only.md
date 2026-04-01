# Report - frontdesk-backend-separation-render-only

## Latest Report

- Date: 2026-03-31
- Topic: Frontdesk/support strict frontend-backend separation (render-only frontdesk + interface-only BFF + orchestration-only controller)

### Readlist

- `AGENTS.md`
- `meta/tasks/CURRENT.md`
- `frontend/frontdesk_state_machine.py`
- `frontend/response_composer.py`
- `scripts/ctcp_front_bridge.py`
- `scripts/ctcp_support_controller.py`
- `scripts/ctcp_support_bot.py`
- `docs/42_frontend_backend_separation_contract.md`
- `docs/frontend_runtime_boundary.md`
- `docs/backend_interface_contract.md`
- `docs/shared_state_contract.md`
- `tests/test_frontdesk_state_machine.py`
- `tests/test_backend_interface_contract_apis.py`
- `tests/test_support_controller_boundary.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_support_runtime_acceptance.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_support_to_production_path.py`
- `simlab/scenarios/S15_lite_fail_produces_bundle.yaml`
- `simlab/scenarios/S16_lite_fixer_loop_pass.yaml`
- `tests/fixtures/patches/lite_fail_bad_readme_link.patch`
- `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`

### Plan

1. Make frontdesk state machine render-only (display truth only, no execution truth inference).
2. Restrict support controller to dedupe/throttle/notification orchestration only.
3. Remove bridge primary dependence on RUN/outbox/verify/QUESTIONS internal file peeking.
4. Enforce canonical decision/result/artifact interface consumption in tests.
5. Add explicit separation contract doc and route docs to this authority.
6. Run focused tests and full `verify_repo` gate; close first failure with minimal fix.

### Changes

- Refactored `frontend/frontdesk_state_machine.py` to allowed display states only:
  - `idle`, `collecting_input`, `showing_progress`, `waiting_user_reply`, `showing_decision`, `showing_result`, `showing_error`
- Updated `frontend/response_composer.py` to consume new frontdesk state names and map decision/result/error from render-only semantics.
- Refactored `scripts/ctcp_support_controller.py`:
  - primary signal from `render_snapshot` + `current_snapshot` + canonical runtime decision rows
  - result notification requires render done + payload evidence
  - decision prompt source from render/runtime/formal decision rows only
- Refactored `scripts/ctcp_front_bridge.py`:
  - canonical runtime snapshot first
  - no RUN/outbox/verify/QUESTIONS file-peeking as primary status synthesis
  - support context includes `render_snapshot`, `current_snapshot`, `output_artifacts`
- Updated support-side wiring in `scripts/ctcp_support_bot.py` for new frontdesk display states.
- Added separation authority doc: `docs/42_frontend_backend_separation_contract.md`.
- Updated routed contracts:
  - `docs/frontend_runtime_boundary.md`
  - `docs/backend_interface_contract.md`
  - `docs/shared_state_contract.md`
  - `docs/13_contracts_index.md`
  - `README.md` index link
- Added/updated regression tests:
  - `tests/test_frontdesk_state_machine.py`
  - `tests/test_backend_interface_contract_apis.py`
  - `tests/test_support_controller_boundary.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_runtime_acceptance.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_support_to_production_path.py`
- Updated simlab fixtures/scenarios for deterministic fixer-loop replay:
  - `simlab/scenarios/S15_lite_fail_produces_bundle.yaml`
  - `simlab/scenarios/S16_lite_fixer_loop_pass.yaml`
  - `tests/fixtures/patches/lite_fail_bad_readme_link.patch`
  - `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`

### Verify

- `python -m unittest discover -s tests -p "test_frontdesk_state_machine.py" -v` -> OK
- `python -m unittest discover -s tests -p "test_backend_interface_contract_apis.py" -v` -> OK
- `python -m unittest discover -s tests -p "test_support_controller_boundary.py" -v` -> OK
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> OK
- `python -m unittest discover -s tests -p "test_support_runtime_acceptance.py" -v` -> OK
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> OK
- `python -m unittest discover -s tests -p "test_support_to_production_path.py" -v` -> OK
- `python simlab/run.py --suite lite --json-out simlab_last.json` -> `passed=14 failed=0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> OK

First failure chain and minimal fix:
- First full-gate failure: simlab lite replay (`S15`/`S16`) due fixture/Scope-Allow drift and patch application mismatch.
- Minimal fix:
  - align S15/S16 scenario `Scope-Allow` with intended touched files,
  - rebuild bad/fix fixture patches to deterministic current baseline.
- Second full-gate failure: one unit test (`test_support_to_production_path`) still assumed outbox-derived pending decision truth.
- Minimal fix:
  - convert fixture to canonical `support_runtime_state.json` decision lifecycle and backend-consume transition.

### Questions

- None.

### Demo

- Frontdesk no longer self-declares done/decision from backend internals.
- Pending decision is shown only when backend formal decision payload exists.
- Result display requires render done + explicit payload/manifest evidence.
- Bridge/BFF remains interface aggregator instead of run-dir parser.
