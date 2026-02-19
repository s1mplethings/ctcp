# Task - p0-simlab-and-build-performance

## Queue Binding
- Queue Item: `L4-OPT-001`
- Layer/Priority: `L4 / P0-slice`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context
- Implement the highest-priority optimization slice from the provided matrix:
  - SimLab sandbox prefers `git worktree` (with safe fallback).
  - verify/build path uses unified build root and compiler launcher (ccache/sccache) + parallel build.
- Preserve existing contracts and behavior gates.

## DoD Mapping (from execution_queue.json)
- [x] DoD-1: `parallel execution policy documented`
- [x] DoD-2: `token/context budget strategy documented and enforceable` (N/A for this P0 slice)
- [x] DoD-3: `GUI optional path remains non-blocking for core gates`

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [x] Research logged (if needed): N/A (repo-local optimization slice)
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) SimLab acceleration:
   - add sandbox mode switch (`auto|copy|worktree`) with dirty-repo fallback.
   - isolate scenario-level `CTCP_RUNS_ROOT` to avoid external run collisions.
2) Build acceleration:
   - add build-root env support (`CTCP_BUILD_ROOT`) in verify scripts.
   - add launcher autodetect (`ccache`/`sccache`) and parallel knobs.
3) Verify:
   - `sync_doc_links --check`
   - `simlab/run.py --suite lite`
   - `scripts/verify_repo.ps1`
4) Report:
   - update `meta/reports/LAST.md` with behavior and command evidence.

## Notes / Decisions
- `worktree` mode is enabled for clean repos; dirty repos automatically use copy mode to preserve local uncommitted state.
- compiler launcher is best-effort and optional; no new dependency is required.

## Results
- `simlab/run.py`: added `--sandbox-mode` (`auto` default), git-worktree sandbox path, dirty fallback to copy, and per-scenario external `CTCP_RUNS_ROOT`.
- `scripts/verify_repo.ps1` + `scripts/verify_repo.sh`: added unified build root, launcher autodetect, and parallel build/test args.
- `CMakeLists.txt`: added optional compiler launcher autodetect toggle.
- validation passed: `sync_doc_links`, `simlab --suite lite`, `verify_repo.ps1`.
