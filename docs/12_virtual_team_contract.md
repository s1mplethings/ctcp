# Virtual Team Contract (Single Authority)

Scope boundary:
- This file is the authoritative contract for CTCP's Virtual Team Lane.
- It defines role boundaries, lane triggers, mandatory design artifacts, and the gate from design into implementation.
- It does not replace repo purpose (`docs/01_north_star.md`), runtime truth (`docs/00_CORE.md`), or user-visible dialogue rules (`docs/11_task_progress_dialogue.md`).

## 1) Why This Lane Exists

Virtual Team Lane exists so CTCP can handle new-project, open-ended, and self-design tasks like a real project team instead of jumping directly from goal intake to code output.

Target behavior:
- first judge the goal
- then shape the product
- then decide scope and MVP
- then choose architecture and UX flow
- then define implementation and acceptance
- only then enter implementation

This is a real governance lane, not a naming layer.

## 2) Trigger Conditions

CTCP MUST enter Virtual Team Lane when any of the following is true:

- the task is a new project
- the user gives a vague or open-ended goal and expects CTCP to decide structure
- the user explicitly asks CTCP to design the product, flow, or architecture
- the task needs information architecture, UX flow, module boundaries, or MVP tradeoffs
- the user asks CTCP to work like a project team

CTCP SHOULD stay in Delivery Lane when the task is already bounded enough that those design decisions are either already made or not material to the work.

## 3) Team Roles and Boundaries

### 3.1 Product Lead

Responsibilities:
- interpret the goal into user value
- define product direction
- identify target users, main user path, and outcome expectations

Must produce:
- `intent_brief.md`
- `product_direction.md`

### 3.2 Project Manager

Responsibilities:
- define MVP boundary
- decide scope, priorities, sequencing, and handoff timing
- keep non-goals explicit

Must produce or update:
- `product_direction.md`
- `decision_log.md`
- `acceptance_matrix.md`

### 3.3 Solution Architect

Responsibilities:
- choose system structure, module boundaries, data shape, and technical route
- record tradeoffs instead of pretending only one path exists

Must produce:
- `architecture_decision.md`

### 3.4 UX / Interaction Designer

Responsibilities:
- define primary user flow
- define key screens, state transitions, success states, and failure states
- decide the first usable path the MVP must support

Must produce:
- `ux_flow.md`

### 3.5 Implementation Lead

Responsibilities:
- turn the approved design artifacts into an execution-ready build plan
- define implementation order and module landing sequence
- reject premature coding when upstream artifacts are missing

Must produce:
- `implementation_plan.md`

### 3.6 QA / Reviewer

Responsibilities:
- define acceptance checks
- define smoke expectations and first-failure interpretation
- make pass/fail criteria explicit before delivery claims

Must produce:
- `acceptance_matrix.md`

### 3.7 Delivery Lead

Responsibilities:
- define what evidence must exist for user-facing delivery
- ensure screenshots, package/readme, replay/delivery evidence, and handoff clarity are explicit
- summarize completed work only; do not invent missing upstream decisions

Must consume:
- the approved design artifacts
- QA outcome
- delivery evidence required by the routed contract

## 4) Mandatory Team-Design Artifacts

Virtual Team Lane MUST produce these artifacts before implementation can begin:

1. `intent_brief.md`
   - goal judgment
   - target user
   - main problem and desired outcome
2. `product_direction.md`
   - product direction
   - MVP scope
   - non-goals
   - priority choices
3. `architecture_decision.md`
   - architecture choice
   - module boundaries
   - technical tradeoffs
   - key constraints
4. `ux_flow.md`
   - primary user flow
   - key screens or states
   - success path and failure path
5. `implementation_plan.md`
   - build order
   - handoff sequence
   - implementation stop conditions
6. `acceptance_matrix.md`
   - acceptance criteria
   - smoke checks
   - success/failure evaluation points
7. `decision_log.md`
   - unresolved decisions
   - accepted assumptions
   - explicit rationale for major tradeoffs

Rules:
- one file may combine multiple sections only if all required headings remain explicit and machine/audit-readable
- generic placeholders are invalid
- artifact names may differ only when the active task card explicitly maps them one-to-one to this contract

## 5) Design-to-Implementation Gate

Virtual Team Lane MUST NOT enter implementation until all of the following are true:

- product direction exists in written form
- MVP boundary and non-goals are explicit
- architecture decision is explicit
- UX flow is explicit
- implementation order is explicit
- acceptance matrix is explicit
- unresolved decisions are either closed or bounded in `decision_log.md`

If any of these are missing, implementation is blocked.

## 6) Forbidden Shortcuts

For Virtual Team Lane tasks, the following are forbidden:

- starting code implementation before the mandatory design artifacts exist
- renaming a single agent into PM / Architect / Designer without changing outputs
- using a generic workflow plan as a fake substitute for product direction
- using a generic acceptance report as a fake substitute for acceptance design
- using a generic project bundle as proof that design decisions were completed
- letting support/frontdesk output pretend the team already decided product, UX, or architecture when no artifact exists

## 7) Lane Output Sequence

The expected Virtual Team Lane sequence is:

1. Goal / intent judgment
2. Product direction
3. Scope / MVP judgment
4. Architecture decision
5. UX flow design
6. Implementation plan
7. Acceptance matrix
8. Implementation
9. QA
10. Delivery

The runtime may compress execution, but it must not skip the sequence contract.

## 8) Completion Standard

Virtual Team Lane success is not just:
- code written
- tests passed

It also requires:
- design judgment written down
- user main flow explicit
- architecture tradeoffs explicit
- acceptance standard explicit
- delivery evidence expectation explicit

If CTCP only implemented code without these upstream artifacts, the task is not complete under this lane.

## 9) Relationship to Neighbor Contracts

- `AGENTS.md` decides that lane selection is mandatory and points here for Virtual Team Lane authority.
- `docs/04_execution_flow.md` defines the expanded stage sequence and mapping.
- `docs/10_team_mode.md` owns support/frontdesk/runtime wiring only; it does not redefine design behavior.
- `docs/11_task_progress_dialogue.md` defines how user-visible progress must expose active role, decisions made, open items, and updated artifacts.
- `docs/14_persona_test_lab.md` is an isolated regression layer; it must not override this lane's role model.
