# CTCP Agent Contract

<!-- TOC -->
| Section | Anchor |
|---------|--------|
| Fast Rules | [→](#fast-rules) |
| 1. Purpose | [→](#1-purpose) |
| 2. Work Lanes | [→](#2-work-lanes) |
| 3. Single Entry | [→](#3-single-entry) |
| 4. Single Flow | [→](#4-single-flow) |
| 5. Allowed Questions | [→](#5-allowed-questions) |
| 6. Required Outputs | [→](#6-required-outputs) |
| 7. Non-Negotiable Rules | [→](#7-non-negotiable-rules) |
| 8. Routing | [→](#8-routing) |
<!-- /TOC -->

<a id="fast-rules"></a>

## 1. Purpose

CTCP is a structured goal-to-delivery generation repo.
It should behave like a structured virtual project team rather than a single brute-force coding agent.

Its main product promise is not to maximize raw generation volume or imitate giant-context coding agents.  
Its main product promise is to turn vague user goals into structured intent, customized runnable MVP projects, visible progress evidence, and verifiable delivery packages.

Contracts, auditability, and verify still matter, but they exist to support the generation and delivery mainline instead of replacing it.

Default operating stance:

- intent-first when understanding the user goal
- structure-first when deciding execution flow
- team-stage-first when shaping work into product, design, technical, build, QA, delivery, and support stages
- customization-first when choosing implementation details
- visible-progress-first when intermediate evidence can reduce black-box uncertainty
- MVP-first when choosing implementation scope
- verify-gated before claiming completion
- token-efficient by default unless the task explicitly requires broader context
- local-by-default unless the task explicitly requires a broader contract update

<a id="2-work-lanes"></a>

## 2. Work Lanes

CTCP has two formal work lanes. Lane selection is mandatory before implementation.

### Delivery Lane

Use this lane when the task is already bounded enough that product direction, UX flow, architecture choice, and acceptance shape are either already explicit or not the primary work.

Typical triggers:
- local repair or patch task
- bounded implementation request
- narrow docs/code alignment
- explicit scope with little or no self-design burden

### Virtual Team Lane

Use this lane when the task requires CTCP to behave like a project team and make upstream design judgments before writing code.

Mandatory triggers:
- new project requests
- open-ended or ambiguous goals
- explicit self-design requests
- tasks requiring product direction, MVP/scope judgment, architecture tradeoffs, or UX/user-flow design
- tasks where the user asks CTCP to work like a team rather than a single coding agent

Virtual Team Lane authority:
- design/routing contract: `docs/12_virtual_team_contract.md`
- expanded stage mapping: `docs/04_execution_flow.md`

Implementation entry gate for Virtual Team Lane:
- do not enter implementation until the required team-design artifacts exist and the handoff criteria in `docs/12_virtual_team_contract.md` are satisfied.

## 3. Single Entry

Execution entry for repo changes:
- bind one queue item in `meta/backlog/execution_queue.json`
- work from `meta/tasks/CURRENT.md`
- if no suitable queue item exists, create one `ADHOC-YYYYMMDD-<slug>` item before implementation

Acceptance entry:
- Windows: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- Unix: `bash scripts/verify_repo.sh`

Everything else is supporting material:
- `README.md` is human navigation only
- `docs/04_execution_flow.md` is the expanded flow reference
- `PROMPT.md` and `QUESTIONS.md` in external run packages are compiled/derived artifacts, not independent authority sources
- repo code or docs do not become authority just because they are nearby

## 4. Single Flow

Use one visible mainline only:

1. `Bind`
   Bind exactly one task in `meta/tasks/CURRENT.md` before changing files.

2. `Read`
   Read the root contract, current task, and only the docs/files needed for the scoped change.

3. `Analyze`
   Record purpose, source of truth, affected paths, allowed write paths, protected paths, acceptance tests, scope boundaries, and what intermediate evidence would best show progress for this task.

4. `Shape`
   Convert the vague request into a bounded implementation path with clear structure, customization targets, and delivery expectations.  
   Prefer a smaller explicit plan over an oversized freeform generation attempt.

5. `Change`
   Make the minimal patch for the current topic; update docs/spec/meta first when the behavior contract changes, and prefer existing repo workflows, docs, and skills over inventing a new flow.

6. `Show`
   When the routed contract or task type supports it, produce intermediate user-visible evidence such as smoke results, screenshots, previews, summaries, or first-failure artifacts instead of hiding all progress until the end.

7. `Verify/Close`
   Run the canonical verify entrypoint after the runnable MVP path exists, record the first failure point and minimal fix when needed, update `meta/reports/LAST.md`, and close the task with explicit evidence.

The repository may keep a finer-grained internal workflow; see `docs/04_execution_flow.md` only when detailed step mapping or profile behavior matters.  
Do not pull that expanded detail into the root contract unless the root contract itself is being changed.

## 5. Allowed Questions

Ask the user only when one of these blocks safe continuation:

- secrets, credentials, accounts, or external permissions
- a mutually exclusive product decision with real compatibility or scope impact
- a missing hard constraint that cannot be discovered locally

Otherwise continue with the best bounded default and record it in `meta/reports/LAST.md`.

## 6. Required Outputs

For every repo task, write:

- `meta/tasks/CURRENT.md`
  Must bind one queue item and define scope, write scope, protection/elevation, acceptance, and integration fields.
- `meta/reports/LAST.md`
  Must contain `Readlist`, `Plan`, `Changes`, `Verify`, `Questions`, and `Demo`.
- report archive entry when the task changes the active report topic
- task archive entry when the task changes the active task topic

When the task creates or advances an external run, keep runtime evidence outside the repo and point to it from the report:

- `${run_dir}/TRACE.md`
- `${run_dir}/artifacts/verify_report.json`
- any additional run evidence required by the routed contract

## 7. Non-Negotiable Rules

- One topic per patch. Do not combine unrelated cleanup or opportunistic refactors.
- Do not expand scope without rebinding `meta/tasks/CURRENT.md`.
- Use the current task card as the only task-purpose authority.
- Keep repo purpose in `docs/01_north_star.md`, runtime truth in `docs/00_CORE.md`, and do not collapse those concerns into one file.
- Do not treat Virtual Team Lane as optional styling; if the trigger conditions match, route into it before implementation.
- Do not let new-project or self-design tasks skip product direction, scope/MVP, architecture, UX flow, implementation plan, or acceptance definition.
- Do not skip the canonical verify entrypoint.
- Do not let compiled `PROMPT.md` or other derived prompt artifacts override `AGENTS.md`, routed contracts, or the active task card.
- Frozen-kernel changes require explicit elevation recorded in `meta/tasks/CURRENT.md` and enforced by verify.
- Keep generated runs, transcripts, screenshots, and other runtime outputs outside the repo unless a contract explicitly says otherwise.
- Do not optimize for larger context usage when a smaller structured context and stage artifacts are sufficient.
- Do not prefer generic one-shot project output over customized delivery aligned to the user’s actual goal.
- When visible intermediate evidence is feasible and useful, do not hide all progress until final completion.
- For routing, integration, bridge, state propagation, memory accumulation, or user-visible leakage defects, prompt-only edits are not enough.
- Prefer existing repo skills and documented local rules over inventing a parallel workflow.
- Do not reintroduce frontend/support style contracts into the root agent contract; route them to their own docs.
- If older docs conflict with the new rule, mark them `deprecated`, `superseded`, or `replaced by`; do not silently leave duplicate authorities in place.
- Do not let verify, manifest, or evidence artifacts masquerade as successful MVP generation when the project still lacks real runnable user flow.

## 8. Routing

Use the narrowest authority that matches the concern:

- Current task scope and allowed behavior: `meta/tasks/CURRENT.md`
- Virtual Team Lane roles, triggers, required design artifacts, and implementation entry gate: `docs/12_virtual_team_contract.md`
- Expanded workflow details, internal step mapping, and verify profiles: `docs/04_execution_flow.md`
- Prompt hierarchy and compiled prompt limits: `docs/50_prompt_hierarchy_contract.md`
- Runtime truth, provenance, and verify artifact semantics: `docs/00_CORE.md`
- Acceptance gate behavior: `docs/03_quality_gates.md` and `scripts/verify_repo.ps1` / `scripts/verify_repo.sh`
- Machine-readable freeze/ownership boundary: `contracts/module_freeze.json`
- Queue/task/report discipline: `docs/25_project_plan.md`
- Reusable repo workflows: `.agents/skills/`
- Frontend/support runtime wiring: `docs/10_team_mode.md`
- User-visible task progress dialogue: `docs/11_task_progress_dialogue.md`
- Persona regression isolation: `docs/14_persona_test_lab.md`
- Human-oriented overview and quickstart: `README.md`
- Output/report discipline shared with automation: `ai_context/00_AI_CONTRACT.md`
- Fast mirror for quick lookup: `ai_context/CTCP_FAST_RULES.md`

If more than one file appears to define the same concern, follow this order:

1. `AGENTS.md` for the root agent contract
2. `meta/tasks/CURRENT.md` for the active task
3. the routed concern-specific document
4. the verify scripts for final pass/fail

If none of the routed docs clearly owns the concern, prefer simplifying the rule surface instead of adding another parallel authority.
