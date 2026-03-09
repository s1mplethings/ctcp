# Agent Mode Matrix (Single Responsibility by Mode)

This matrix defines mode boundaries so one role does not silently act as all roles.

| Mode | Primary purpose | Allowed changes | Forbidden changes | Required outputs |
|---|---|---|---|---|
| planner | Bind task and define execution intent | queue/task/report planning artifacts | direct implementation without plan | queue binding, DoD mapping, scoped plan |
| analyst | Establish wiring and truth-path analysis | analysis/find sections, integration check fields | skipping entrypoint/downstream/source-of-truth analysis | explicit break-point analysis and wiring map |
| builder | Implement minimal scoped change | code/docs/tests within approved scope | goal redefinition, out-of-scope refactor | minimal patch + scope alignment evidence |
| checker | Run local checks and iterative fixes | tests/check scripts, minimal corrective edits | declaring done without check/fix loop | check logs, first failure point, minimal fix strategy |
| verifier | Run canonical final gate | `scripts/verify_repo.ps1` / `.sh` and gate evidence | replacing canonical verify with ad hoc checks | canonical verify result and executed gates evidence |
| frontend/support | User-facing interaction and clarification | mode classification, requirement summary, safe reply rendering | direct backend state mutation outside bridge, raw error leakage | user-visible reply + bridge/runtime-consistent state |
| orchestrator | Advance execution by artifacts/gates | runtime progression and gate evaluation | strategy invention without contract artifacts | run state transitions and trace artifacts |
| archivist | Record auditable closure artifacts | `meta/reports/LAST.md`, issue memory updates, decision logs | inventing engineering truth from chat memory | Readlist/Plan/Changes/Verify/Demo and closure decisions |

Boundary rules:

- Purpose ownership is in [docs/01_north_star.md](docs/01_north_star.md), not in mode execution notes.
- Canonical flow ownership is in [docs/04_execution_flow.md](docs/04_execution_flow.md), not in mode-local shortcuts.
- Current task truth ownership is in `meta/tasks/CURRENT.md`.
- Runtime engineering truth ownership is in `run_dir` artifacts + canonical verify outputs + explicit repository report links.
