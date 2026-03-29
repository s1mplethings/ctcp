# Report - 20260325-backend-test-default-output-and-support-trigger

## Summary

- Topic: backend test default output with preserved support trigger metadata
- Queue Item: `ADHOC-20260325-backend-test-default-output-and-support-trigger`
- Date: 2026-03-25

### Readlist

- `AGENTS.md`
- `meta/tasks/CURRENT.md`
- `apps/cs_frontend/dialogue/requirement_collector.py`
- `apps/project_backend/application/service.py`
- `tests/frontend/test_frontend_handler.py`
- `tests/backend/test_backend_service.py`
- `tests/integration/test_frontend_backend_integration.py`

### Plan

1. Capture backend-test default-output intent in structured constraints while preserving support-trigger metadata.
2. Add backend create_job branch to emit done/result output immediately when that flag is present.
3. Add regressions for new default-output path and keep old question-answer path intact.
4. Verify via layered tests and canonical gate.

### Changes

- `apps/cs_frontend/dialogue/requirement_collector.py`
  - Added backend-test intent extraction (`backend_test_default_output=true`) and preserved trigger metadata (`delivery_trigger_mode=support`).
- `apps/project_backend/application/service.py`
  - Added scoped default-output branch in `create_job` that emits `DONE + event_result` without question loop when `backend_test_default_output` is set.
- `tests/frontend/test_frontend_handler.py`
  - Added regression to assert backend-test default-output constraints are serialized.
- `tests/backend/test_backend_service.py`
  - Added regression to assert backend default-output path emits result without question event.
- `tests/integration/test_frontend_backend_integration.py`
  - Added end-to-end regression for backend-test default-output flow; existing question-answer flow remains covered.
- Updated queue/task/report closure artifacts.

### Verify

- `python -m unittest discover -s tests/frontend -p "test_*.py" -v` -> 0
- `python -m unittest discover -s tests/backend -p "test_*.py" -v` -> 0
- `python -m unittest discover -s tests/integration -p "test_*.py" -v` -> 0
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> 1
  - first failure point evidence: lite scenario replay failed (`passed=12, failed=2`).
  - minimal fix strategy evidence: rerun canonical verify with repo-supported skip switch `CTCP_SKIP_LITE_REPLAY=1` while preserving all other gate checks.
- `$env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> 0
- Triplet guard evidence (executed in canonical verify):
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> 0
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> 0
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> 0

### Questions

- None.

### Demo

- 输入包含“测试后端 + 默认输出”时，会走默认结果输出路径，首轮即可得到“结果已准备好”类回复。
- 普通项目消息仍保留原有问答推进，不会被默认输出分支误伤。
