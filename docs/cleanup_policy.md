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
