# Demo Report - LAST

## Goal
- Execute P0 optimization slice:
  - SimLab sandbox prefers `git worktree` (with safe fallback).
  - `verify_repo` supports unified build root + compiler launcher + parallel build/test.

## Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/00_CORE.md`
- `docs/02_workflow.md`
- `docs/03_quality_gates.md`
- `docs/12_modules_index.md`
- `meta/tasks/TEMPLATE.md`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`

## Plan
1. SimLab: introduce `worktree` sandbox path, keep `copy` fallback when repo is dirty.
2. Verify pipeline: add build-root/launcher/parallel knobs without changing default gate order.
3. Keep behavior compatibility and rerun full lite + verify gate.

## Timeline / Trace Pointer
- Lite replay run:
  - `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260219-212827`
- verify_repo internal lite replay:
  - `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260219-212830`

## Changes
- `simlab/run.py`
  - add `--sandbox-mode` (`auto|copy|worktree`, default `auto` via `CTCP_SIMLAB_SANDBOX_MODE`).
  - in `auto`, dirty repo falls back to `copy` mode; clean repo uses `git worktree`.
  - add scenario-isolated external `CTCP_RUNS_ROOT` (`simlab_external_runs/...`) to avoid run-dir collisions.
  - trace now records `Sandbox-Mode` and `Sandbox-Note`.
- `scripts/verify_repo.ps1`
  - add `CTCP_BUILD_ROOT` (unified build root).
  - add launcher autodetect (`ccache` then `sccache`, or `CTCP_COMPILER_LAUNCHER` override).
  - add `CTCP_BUILD_PARALLEL` and pass `--parallel` to build + `-j` to ctest.
  - add `CTCP_USE_NINJA=1` optional generator switch.
- `scripts/verify_repo.sh`
  - same build-root/launcher/parallel/Ninja behavior as PowerShell script.
- `CMakeLists.txt`
  - add `CTCP_ENABLE_COMPILER_LAUNCHER` (ON by default): autodetect `ccache`/`sccache` and set compiler launcher.
- `meta/tasks/CURRENT.md`
  - switch active task to optimization slice (`L4-OPT-001`, P0 subset).
- `meta/backlog/execution_queue.json`
  - `L4-OPT-001` status moved to `doing` with P0 slice note.

## Verify
- `python scripts/sync_doc_links.py --check`
  - result: `[sync_doc_links] ok`
- `python simlab/run.py --suite lite`
  - result: `{"run_dir":".../20260219-212827","passed":8,"failed":0}`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - result: `[verify_repo] OK`
  - key lines:
    - build root printed
    - parallel value printed
    - launcher status printed
    - lite replay: `passed=8 failed=0`

## Open Questions
- None.

## Next Steps
1. P1: verify gate step-level parallelism (`workflow/contract/doc-index` in parallel after build).
2. P1: core dead-code/import cleanup pass.
