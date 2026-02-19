# Agent TeamNet Contract (v0.2)

`docs/00_CORE.md` is authoritative. This file turns that contract into role wiring for multi-agent execution.

## TeamNet Mesh

```text
                     (adversarial reviews only)
      +--------------------+         +--------------------+
      | ContractGuardian   |-------->|                    |
      | cost/contract gate |         |                    |
      +--------------------+         |                    |
                                     |   Chair/Planner    |
      +--------------------+         | (ONLY decision)    |
      | CostController     |-------->|                    |
      | budget gate        |         |                    |
      +--------------------+         +----------+---------+
                                                |
                                                v
 +--------------------+    context_pack   +----+---------------+
 | Local Librarian    |------------------>| PatchMaker / Fixer |
 | read-only supplier |                   | execution only      |
 +----------+---------+                   +----+----------------+
            ^                                  |
            | file_request                     | diff.patch
            |                                  v
 +----------+---------+                 +------+--------------+
 | Local Orchestrator |---------------->| Local Verifier      |
 | gate driver only   |<----------------| fact judge only     |
 +----------+---------+   verify result +------+--------------+
            ^
            | externals_pack (optional candidate input)
 +----------+---------+
 | Web Researcher     |
 | offline source pack|
 +--------------------+
```

## Role Contract

| Role | Inputs | Outputs | MUST NOT | ADLC Binding |
|---|---|---|---|---|
| Chair/Planner | `analysis.md`, `find_result.json`, reviews, context pack | `PLAN_draft.md`, signed `PLAN.md`, adjudication | Delegate final decision | `analysis`, `plan`, `deploy/merge` |
| Local Orchestrator | artifact presence/state, signed plan, gate results | status transitions, run pointer updates, gate triggers | Decide workflow/plan, write patch, approve reviews | all steps as driver |
| Local Librarian | `file_request.json` | `context_pack.json` | Decide solution, patch code | `analysis -> plan` support |
| Web Researcher | guardrails + query budget | `meta/externals/<goal_slug>/externals_pack.json` | Replace resolver result, execute patch | optional input before `plan` |
| ContractGuardian | `PLAN_draft.md`, contract docs | `reviews/review_contract.md` (`APPROVE/BLOCK`) | Edit source code or patch | `plan` gate |
| CostController | `PLAN_draft.md`, budgets, stop conditions | `reviews/review_cost.md` (`APPROVE/BLOCK`) | Edit source code or patch | `plan` gate |
| PatchMaker/Fixer | signed `PLAN.md`, failure bundle | `artifacts/diff.patch` | Expand scope outside plan, self-approve | `fix` and execute loop |
| Local Verifier | repo/run state, verify entrypoint | `TRACE.md`, `artifacts/verify_report.json`, `failure_bundle.zip` (on fail) | Decide acceptance policy | `[build<->verify]`, `contrast` |

## Hard Boundaries

- Unique decision authority: `Chair/Planner` only.
- Local Orchestrator/Librarian are low-cost context providers and gate drivers, not strategists.
- Web Researcher provides offline, structured candidate evidence only; cannot become execution single point of failure.
- Adversarial roles (`ContractGuardian`, `CostController`, optional red-team) exist to block unsafe plans; they cannot write code directly.

## Dispatcher/Provider Wiring

- Orchestrator MAY call a local dispatcher when blocked by missing artifacts.
- Dispatcher input authority remains the same gate state; it does not change workflow selection authority.
- Provider types:
  - `local_exec`: local script execution, restricted to librarian context-pack generation.
  - `manual_outbox`: writes standardized outbox prompts for external/manual agents.
- `manual_outbox` prompts must constrain write scope to run_dir target artifacts only.
- `manual_outbox` prompts must not instruct any direct repo edits.
- When `max_outbox_prompts` budget is exceeded, dispatcher must stop creating prompts (`budget_exceeded`).
