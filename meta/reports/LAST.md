# Demo Report - LAST

## Latest Report

- File: `meta/reports/LAST.md`
- Date: `2026-04-05`
- Topic: `Support PASS delivery + benchmark-mode isolation`

### Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `scripts/ctcp_front_bridge.py`
- `scripts/ctcp_support_bot.py`
- `frontend/support_reply_policy.py`
- `apps/cs_frontend/dialogue/requirement_collector.py`
- `tools/providers/project_generation_business_templates.py`
- `tests/test_support_to_production_path.py`
- `tests/test_project_generation_artifacts.py`

### Plan

1. Rebind the active task/report to this runtime hardening topic and preserve the fixed baseline + current working tree constraint.
2. Repair generic support reply fallback so PASS truth yields readable delivery output instead of stale failure wording.
3. Keep benchmark-mode ingress and stronger export shape isolated to explicit benchmark mode, with no benchmark fixture content added to production defaults.
4. Run focused regressions and record the first failure plus the minimal repair.

### Changes

- `scripts/ctcp_front_bridge.py`
  - production/common fix: clear stale runtime error/recovery state when canonical runtime truth is final PASS and no user decision is pending.
  - non-pollution reason: logic depends only on run status / verify truth, not on any benchmark payload or VN-specific field.
- `frontend/support_reply_policy.py`
  - production/common fix: prefer `deliver_result` when PASS truth exists even if provider status is stale-failed; render delivery fallback from manifest/artifact/runtime truth.
  - production/common fix: restore language-aware `deliver_result` fallback so Chinese requests do not fall through to English delivery text.
  - non-pollution reason: reply logic consumes generic runtime/manifest fields and contains no benchmark-case literals or benchmark-only reply branch.
- `apps/cs_frontend/dialogue/requirement_collector.py`
  - benchmark-only ingress plumbing: explicit benchmark/regression wording now maps to `project_generation_mode=benchmark_regression`.
  - non-pollution reason: it sets only a mode flag; it does not inject benchmark sample names, fixed角色/章节, or benchmark acceptance fields.
- `scripts/ctcp_support_bot.py`
  - benchmark-only ingress plumbing: pass frontend-derived constraints into `ctcp_new_run()` so explicit benchmark mode can be honored through the normal support entrypoint.
  - non-pollution reason: support bot forwards generic constraints; it does not synthesize benchmark payloads or hardcode VN content.
- `tools/providers/project_generation_business_templates.py`
  - benchmark-only generation fix: strengthen only the `benchmark_regression + narrative_copilot` branch to export structured benchmark deliverables (`story_bible/characters/outline/scene_cards/art_prompts/demo_script`) in addition to legacy files.
  - non-pollution reason: production narrative and generic branches are unchanged; the stronger shape is isolated behind explicit benchmark execution mode.
- `tests/test_support_to_production_path.py`
  - regression coverage for stale-error clearing, PASS-truth reply intent, and explicit benchmark-mode constraint extraction without fixture payload injection.
- `tests/test_project_generation_artifacts.py`
  - regression coverage proving production narrative requests stay non-benchmark by default and benchmark-mode export strengthening remains isolated to explicit benchmark mode.
- `meta/backlog/execution_queue.json`
  - rebound the active queue item to this repair topic.
- `meta/tasks/CURRENT.md`
  - replaced cleanup scope with the current support/runtime/mode-isolation scope and acceptance.
- `meta/reports/LAST.md`
  - replaced cleanup report with current task evidence.

### Verify

- `git rev-parse HEAD` -> `faeaedbd419aeb9de182c606cd7ce27eaa091e89`
- `git branch --show-current` -> `main`
- `git diff --shortstat faeaedbd419aeb9de182c606cd7ce27eaa091e89` -> `89 files changed, 2377 insertions(+), 5161 deletions(-)` before this round continued; work proceeded against baseline commit + current working tree.
- `python -m unittest discover -s tests -p "test_support_to_production_path.py" -v` -> first run failed at `test_reply_policy_prefers_deliver_result_when_pass_truth_exists_even_if_provider_failed` because `render_fallback_reply()` returned English delivery text for `lang_hint="zh"`; minimal fix was to move `deliver_result` handling back under the language branch and keep the Chinese fallback path active.
- `python -m unittest discover -s tests -p "test_support_to_production_path.py" -v` -> `0` (10 tests)
- `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v` -> `0` (5 tests)
- `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v` -> `0` (14 tests)
- `python -m unittest discover -s tests -p "test_support_reply_policy_regression.py" -v` -> `0` (9 tests)
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> first rerun failed in 3 tests because mocks still asserted the old `ctcp_new_run(goal=...)` signature after generic constraints started flowing into the same support entrypoint; minimal fix strategy: move default benchmark-mode constraint derivation into the bridge so the support entrypoint signature stays stable, then restore the legacy assertions.
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0` (58 tests)
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> first rerun failed at `test_support_bot_project_turn_calls_bridge_entrypoints_and_consumes_whiteboard_context` for the same old-signature assertion; minimal fix strategy: keep the signature stable and move default constraint derivation to `ctcp_front_bridge.ctcp_new_run()`.
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` (23 tests)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0` (3 tests)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0` (3 tests)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`
  - first failure point: `workflow gate (workflow checks)`
  - first failing reason: `meta/tasks/CURRENT.md` missing mandatory 10-step evidence sections and task-truth fields.
  - minimal fix strategy: expand `CURRENT.md` and `LAST.md` to carry the required workflow evidence, then rerun canonical verify.
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`
  - first failure point: `code health growth-guard`
  - first failing reason: `scripts/ctcp_front_bridge.py`, `scripts/ctcp_support_bot.py`, and large regression files exceeded growth limits after the initial support/benchmark-mode wiring changes.
  - minimal fix strategy: keep support-bot signature stable, move default constraint derivation to bridge, collapse equivalent bridge logic, and remove oversized repeated test assertion helpers from large files.
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`
  - first failure point: `lite scenario replay`
  - first failing reason: SimLab `S16_lite_fixer_loop_pass` used `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`, whose `meta/tasks/CURRENT.md` hunk still targeted the old task header and then became corrupt after manual adjustment.
  - minimal fix strategy: refresh the fixture hunk to current repo headers and fix the unified diff format so `git apply --check` succeeds again inside the scenario sandbox.
- `python simlab/run.py --suite lite --json-out %TEMP%\\simlab-lite-final.json` -> `0`
  - result: `passed=14, failed=0`
  - proof: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260405-195806`
- `$env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
  - rationale: repo-supported path after standalone lite replay proof was already captured
  - summary: workflow/plan/patch/contract/doc-index/growth-guard/triplet/python-unit/plan-evidence all passed

### Questions

- None.

### Demo

- connected: support entrypoint can forward explicit benchmark-mode constraints through the normal frontend bridge without introducing production fixture payloads.
- accumulated: runtime PASS truth, verify truth, manifest delivery fields, and artifact labels are accumulated into one generic delivery decision path.
- consumed: customer-facing fallback reply now consumes that truth to return readable delivery output instead of stale failure wording.
- pollution boundary: benchmark-specific stronger deliverables remain isolated to explicit `benchmark_regression` narrative generation and do not alter production default templates, verify gates, or reply wording.
- skillized: no, because this round is a bounded runtime hardening and mode-isolation repair inside existing flows, not a new reusable workflow asset.
