# Demo Report - Agent League benchmark review layer

Archived from `meta/reports/LAST.md` when switching to `ADHOC-20260423-indie-studio-hub-generation-test`.

## Latest Report

- Date: `2026-04-23`
- Topic: `Agent League benchmark review layer`
- Mode: `Delivery Lane post-benchmark review tooling`

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/45_formal_benchmarks.md`
- `docs/46_benchmark_pass_contracts.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/tasks/CURRENT.md`
- `artifacts/benchmark_goldens/formal_basic_benchmark/summary.json`
- `artifacts/benchmark_goldens/formal_hq_benchmark/summary.json`

### Plan
1. Add Agent League documentation defining purpose, roles, inputs, outputs, scoring, and benchmark relationship.
2. Add structured role checklists for Customer, Product Reviewer, QA/Adversarial, and Delivery Critic agents.
3. Implement a sequential deterministic `scripts/run_agent_league.py` runner over one existing benchmark `run_dir`.
4. Generate four markdown role reports plus `agent_league_summary.json` and `agent_league_summary.md`.
5. Validate on existing formal HQ and basic PASS runs without rerunning benchmarks or changing benchmark gates.

### Changes
- Added `docs/47_agent_league.md`.
- Added `agent_league_cases/customer_persona_case.json`.
- Added `agent_league_cases/product_review_checklist.json`.
- Added `agent_league_cases/qa_checklist.json`.
- Added `agent_league_cases/delivery_checklist.json`.
- Added `scripts/run_agent_league.py`.
- Updated `meta/tasks/CURRENT.md` for this scoped Agent League task.
- Agent League outputs were generated under each selected run's `artifacts/agent_league/` directory, outside the repo source tree.

### Verify
- PASS: `python -m py_compile scripts/run_agent_league.py`.
- PASS: `python scripts/run_agent_league.py --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_plane_lite_hq_repair_full_20260422-192808\runs\ctcp\20260422-192810-441222-orchestrate`
- PASS: `python scripts/run_agent_league.py --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_plane_lite_deliver_retry_final_20260422-152011\runs\ctcp\20260422-152013-552970-orchestrate`
- first failure point: none after final validation.

### Questions
- None.

### Demo
- HQ league summary: `C:\Users\sunom\AppData\Local\Temp\ctcp_plane_lite_hq_repair_full_20260422-192808\runs\ctcp\20260422-192810-441222-orchestrate\artifacts\agent_league\agent_league_summary.json`.
- Basic league summary: `C:\Users\sunom\AppData\Local\Temp\ctcp_plane_lite_deliver_retry_final_20260422-152011\runs\ctcp\20260422-152013-552970-orchestrate\artifacts\agent_league\agent_league_summary.json`.
- Skill decision (`skillized: yes`): used `ctcp-workflow` for scoped implementation, verification, and report closure.
