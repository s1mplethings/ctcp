# Demo Report - LAST

## Latest Report

- File: `meta/reports/LAST.md`
- Date: `2026-04-06`
- Topic: `support delivery evidence surface`

### Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `apps/project_backend/application/service.py`
- `apps/project_backend/orchestrator/job_runner.py`
- `scripts/ctcp_front_bridge.py`
- `scripts/project_manifest_bridge.py`
- `apps/cs_frontend/dialogue/response_renderer.py`
- `apps/cs_frontend/application/handle_user_message.py`
- `apps/cs_frontend/domain/presentable_event.py`
- repo-local search for `event_result`, `project_manifest`, `output_artifacts`, and delivery-related rendering paths

### Plan

1. Rebind the repo task from local project generation to delivery-evidence surfacing.
2. Add a stable backend/bridge delivery evidence manifest.
3. Thread that manifest through backend result objects and frontend presentable events.
4. Render user-facing delivery evidence in completion replies.
5. Run focused tests and canonical verify, then close with evidence.

### Changes

- Added a first-class delivery evidence contract at `contracts/schemas/delivery_evidence.py`.
- Added `scripts/project_delivery_evidence_bridge.py` so the bridge can explicitly build and write `artifacts/delivery_evidence_manifest.json`.
- Updated `scripts/ctcp_front_bridge.py` to expose delivery evidence as a stable backend-facing bridge capability and include it in support context.
- Updated backend result assembly so `event_result` now carries `delivery_evidence` explicitly instead of only developer-oriented artifacts.
- Updated frontend presentable results and renderer so completion replies show user-facing evidence summary, report path, view-now items, verification summary, limitations, and next actions.
- Added focused tests for backend evidence propagation, frontend evidence rendering, integration compatibility, and bridge manifest writing.
- Fixed a provider-resolution inconsistency in `scripts/ctcp_dispatch.py` so `mock_agent` mode can actually keep `librarian/context_pack` on `mock_agent` during deterministic mock-pipeline tests instead of being silently forced back to `ollama_agent`.
- Hardened `tools/providers/ollama_agent.py` Windows bootstrap behavior so detached `ollama serve` startup no longer hands a run-dir log handle to the child process and lock temp cleanup.

### Verify

- `python -m unittest discover -s tests -p "test_delivery_evidence_bridge.py" -v` -> `0`
  - result: bridge evidence builder writes a stable manifest file and returns the expected user-facing fields
- `python -m unittest discover -s tests/backend -p "test_backend_service.py" -v` -> `0`
  - result: backend completion events now carry explicit `delivery_evidence`
- `python -m unittest discover -s tests/frontend -p "test_frontend_handler.py" -v` -> `0`
  - result: frontend completion replies surface delivery evidence directly and preserve the structured field on `PresentableEvent`
- `python -m unittest discover -s tests/integration -p "test_frontend_backend_integration.py" -v` -> `0`
  - result: frontend/backend mainline remains compatible after evidence propagation
- `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` -> `0`
  - result: older frontend rendering boundary regressions remain stable
- `python -m unittest discover -s tests -p "test_provider_selection.py" -v` -> `0`
  - result: provider resolution now keeps mock-mode librarian dispatch deterministic without weakening the hard local-model rule for non-mock modes
- `python -m unittest discover -s tests -p "test_ollama_agent.py" -v` -> `0`
  - result: Windows detached bootstrap path is covered and verified to avoid run-dir log-handle inheritance
- `python -m unittest discover -s tests -p "test_mock_agent_pipeline.py" -v` -> `0`
  - result: mock fault-injection replay is deterministic again and no longer hangs/locks temp runs on local-model startup
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `covered by canonical verify`
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `covered by canonical verify`
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `covered by canonical verify`
- first failure point: `workflow gate (workflow checks)` during canonical `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`
  - reason: `meta/reports/LAST.md` was still missing mandatory workflow evidence strings for first failure/minimal fix/triplet command evidence
- minimal fix strategy: update `meta/reports/LAST.md` with the required failure evidence and triplet command references, then rerun canonical verify before touching code again
- second failure point: `lite scenario replay` during canonical `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`
  - reason: `S16_lite_fixer_loop_pass` still used a stale fixer patch fixture that no longer matched the current README doc-index and active `CURRENT/LAST` headers
- minimal fix strategy: rebase `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` to the current README doc-index plus current task/report headers, rerun `python simlab\run.py --suite lite --json-out artifacts\delivery_evidence_simlab.json`, then rerun canonical verify
- `python simlab\run.py --suite lite --json-out artifacts\delivery_evidence_simlab.json` -> `0`
  - result: `14` scenarios passed, `0` failed
- third failure point: `python unit tests` during canonical `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`
  - reason: `tests/test_mock_agent_pipeline.py::test_robustness_fault_injection` left local-model startup behavior mixed into mock-mode replay and, on Windows, temp run cleanup could fail behind a lingering `ollama_serve.log` handle
- minimal fix strategy: make `mock_agent` mode respect its configured librarian provider in `_resolve_provider`, keep the robustness test on deterministic mock dispatch, and remove detached child inheritance of run-dir log handles in `ollama_agent`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `0`
  - result: canonical verify passed end-to-end after delivery-evidence wiring plus provider/bootstrap cleanup
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` (post-close rerun after CURRENT/LAST/queue finalization) -> `0`
  - result: final repo closure state still passes canonical verify, so the completed task/report metadata does not regress workflow gating

### Questions

- None.

### Demo

- Goal: users should be able to see project delivery evidence directly in the frontend/support completion result, without browsing zip/output directories manually.
- User-facing result shape now includes:
  - one-line delivery summary
  - “现在可以直接看” evidence items
  - primary report path
  - verification summary
  - limitations
  - next actions
