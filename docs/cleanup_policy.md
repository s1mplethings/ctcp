# Cleanup Policy

This file defines the cleanup policy for repository knowledge assets.

Authority: `docs/00_CORE.md` (runtime truth), `docs/04_execution_flow.md` (workflow).

## Default Strategy: Archive-First

Repository knowledge assets (docs, meta content, decision logs, reports) MUST use
archive-first cleanup by default.

- **Archive-first**: move to a dated archive location before removal.
- **Hard delete**: only permitted for clearly disposable artifacts (see below).

## Archive-First Scope

The following content types require archive-first cleanup:

- Markdown documentation (`docs/`, `specs/`, `meta/`)
- Decision logs and reports (`meta/reports/`, `ai_context/decision_log.md`)
- Task cards and backlog items (`meta/tasks/`, `meta/backlog/`)
- Contract and governance sources (`contracts/`, `ai_context/`)
- Workflow registry entries (`workflow_registry/`)
- Agent protocol and playbook files (`ai/`)

Archive location: `meta/archive/` with dated subfolder (`YYYY-MM-DD_slug/`).

## Hard Delete Scope

Hard delete is permitted ONLY for:

- Build outputs (`build/`, `build_lite/`, `build_verify/`)
- Run artifacts and caches (`runs/`, `simlab/_runs/`)
- Temporary files (`_tmp_*`, `*.tmp`)
- Generated distribution outputs (`dist/`, `generated_projects/`)
- CI/pipeline caches

## Evidence Requirements

Any cleanup action MUST satisfy at least one of:

1. **No remaining references**: grep confirms no live references to the target.
2. **Replaced by authoritative source**: a newer canonical source supersedes the target.
3. **Generated during current run**: the artifact is a transient run output, not a knowledge asset.
4. **Not in protected paths**: the target is not under a protected knowledge-asset path.

## Daily Worktree Cleanliness

Every task should end with an explicit dirty-state decision. A dirty worktree is
allowed only when it is intentional, scoped, and recorded in `meta/reports/LAST.md`.

Before starting a new task:

1. Run `git status --short --untracked-files=all`.
2. If available, run `python scripts/worktree_cleanliness_report.py`.
3. Treat existing dirty files as inherited state; do not revert them unless the
   user explicitly asks for that exact file or change.

Before claiming a task is closed:

1. Runtime outputs must be outside the repo, normally under `CTCP_RUNS_ROOT`.
2. Generated run/build outputs inside the repo must be removed only when they
   match the hard-delete scope in this policy.
3. Source, tests, docs, and task/report archives must be grouped by queue item
   before commit, stash, or handoff.
4. `meta/reports/LAST.md` must record whether `git status --short` is clean. If
   it is not clean, record the dirty count and the next non-destructive cleanup
   action.

Recommended cleanup order:

1. Move or delete runtime/generated outputs that match the hard-delete scope.
2. Review untracked source/test files and either add them to the intended patch
   or move them out of the repo.
3. Group modified tracked source/docs by task topic before commit or stash.
4. Commit task/report archives together with the task that produced them.
5. Re-run verify with `CTCP_RUNS_ROOT` outside the repo and local smoke-test
   provider overrides cleared unless the active task requires them.

Do not use `git reset --hard`, `git checkout --`, or broad recursive deletes as
routine cleanup. Those commands can destroy user work and are outside this
policy unless the user explicitly requests them.

## Protected Paths

The following paths are protected knowledge assets and MUST NOT be hard-deleted:

- `docs/00_CORE.md`
- `docs/04_execution_flow.md`
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `README.md`

## Markdown Object Lifecycle

Cleanup of stateful markdown objects follows `docs/20_STATE_MACHINE.md`:

```
active -> deprecated -> disabled -> removed -> archived
```

Destructive jumps (`active -> removed`, `active -> archived`) are forbidden.
