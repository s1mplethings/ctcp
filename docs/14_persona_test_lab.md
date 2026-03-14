# Persona Test Lab Contract (Single Authority)

Scope boundary:
- This file is the authoritative contract for isolated style regression of the production assistant.
- It does not redefine task-progress dialogue rules; those remain in `docs/11_task_progress_dialogue.md`.
- It does not replace real task execution, production support runs, or canonical verify truth.

## 1) Why This Exists

Current failure classes:
- production support dialogue and style testing can leak into the same conversation, causing context pollution
- repeated user complaints such as `不要机械式回答` have not had a dedicated isolated test ground
- the repo lacked a fixed set of test user personas, scoring rubrics, and regression cases
- style checks were too subjective and could not produce transcript + score + fail reasons evidence
- multilingual turns and long conversations could drift back into receptionist tone without a clean regression harness

Persona Test Lab fixes those gaps by turning style complaints into isolated, scored, repeatable tests.

## 2) System Goal

Target statement:

`production assistant`, `test user personas`, and `judge/scoring` remain three separate layers; every test case starts from a fresh session; results are scoreable, repeatable, and auditable.

Non-goals:
- not a fun roleplay system
- not a replacement for real task execution
- not a parallel role hierarchy that changes CTCP mainline flow
- not an excuse to optimize for “chatty” behavior over task progression

## 3) Three-Layer Separation

### 3.1 Production Persona

- Role: the same formal execution persona used for customer-facing task replies
- Authority:
  - `docs/11_task_progress_dialogue.md`
  - `docs/10_team_mode.md`
- Must:
  - answer as a task-progress assistant
  - stay fixed during one persona-lab run
- Must not:
  - generate its own score
  - decide whether its own reply passes
  - read previous persona-lab case transcripts unless the case fixture explicitly includes them

### 3.2 Test User Personas

- Role: scripted user behavior designed to pressure the production persona
- Must be fixed per case
- May vary by:
  - tone
  - patience
  - clarity
  - language mix
  - insistence on directness
- Must not:
  - mutate production conversation state
  - self-grade the assistant

### 3.3 Judge / Scoring Layer

- Role: evaluate transcript output against contract rules and rubrics
- Inputs:
  - fixed case spec
  - transcript
  - rubrics
  - referenced authority docs
- Outputs:
  - `score.json`
  - `fail_reasons.md`
  - `summary.md`
- Must not:
  - rewrite production assistant replies
  - feed hidden hints back into the running test session
  - claim pass/fail without explicit rule hits or dimension scores

## 4) Independent Session Rule

Every persona case MUST:
- use a new session id
- use one fixed `production_assistant`
- use one fixed `test_user_persona`
- use one fixed task input or scripted turn list
- use a fixed `turn_limit` or explicit stop conditions
- produce standardized artifacts

Hard isolation rules:
- no case may inherit transcript history from another case
- no case may reuse production support-session memory
- no persona-lab run may write into production `RUN.json`, `support_session_state.json`, or customer-visible reply artifacts
- if a case needs fixture context, that fixture must be declared in the case file, not pulled from chat memory

## 5) Language Policy: English Contracts, Chinese Intent

Formal language policy:
- core rules, rubric ids, artifact fields, lint names, and state fields use English
- design motivation, Chinese scenario explanations, and persona example lines may use Chinese
- do not repeat the same rule paragraph in both languages
- each formal concept has one canonical English term only
- Chinese is explanation and scenario material, not a second contract vocabulary

## 6) Repo Layout

Repo-local static assets only:

- `persona_lab/README.md`
- `persona_lab/personas/production_assistant.md`
- `persona_lab/personas/*.md`
- `persona_lab/rubrics/*.yaml`
- `persona_lab/cases/*.yaml`

Run outputs stay outside repo:

- `<CTCP_RUNS_ROOT>/<repo_slug>/persona_lab/<lab_run_id>/summary.md`
- `<CTCP_RUNS_ROOT>/<repo_slug>/persona_lab/<lab_run_id>/cases/<case_id>/transcript.md`
- `<CTCP_RUNS_ROOT>/<repo_slug>/persona_lab/<lab_run_id>/cases/<case_id>/transcript.json`
- `<CTCP_RUNS_ROOT>/<repo_slug>/persona_lab/<lab_run_id>/cases/<case_id>/score.json`
- `<CTCP_RUNS_ROOT>/<repo_slug>/persona_lab/<lab_run_id>/cases/<case_id>/fail_reasons.md`
- `<CTCP_RUNS_ROOT>/<repo_slug>/persona_lab/<lab_run_id>/cases/<case_id>/summary.md`

The repo MUST NOT store live persona-lab transcripts, scores, or snapshots.

## 7) Static Asset Meaning and Minimum Fields

### 7.1 Persona Files

Each persona file defines one stable actor.

Minimum fields:
- `persona_id`
- `persona_role`
- `language_profile`
- `behavior_traits`
- `common_utterances`
- `risk_points`
- `test_purpose`

### 7.2 Rubric Files

Each rubric file defines either lint checks or scored dimensions.

Minimum fields:
- `schema_version`
- `rubric_id`
- `purpose`
- `authorities`
- `checks` or `dimensions`
- `pass_thresholds`
- `fail_reason_templates`

### 7.3 Case Files

Each case file defines one regression scenario.

Minimum fields:
- `schema_version`
- `case_id`
- `purpose`
- `assistant_persona`
- `user_persona`
- `initial_task` or `user_script`
- `turn_limit`
- `stop_conditions`
- `must_pass_checks`
- `fail_conditions`
- `expected_response_traits`

## 8) Required Test User Personas

The minimum supported persona set is:

1. `direct_user`
2. `confused_user`
3. `angry_user`
4. `overcontrolling_user`
5. `bilingual_user`
6. `expert_user`
7. `casual_user`

Each persona definition MUST include:
- behavior traits
- common sayings
- risk points
- primary test purpose

The fixed production assistant persona lives in `persona_lab/personas/production_assistant.md`.

## 9) Lint and Scoring Model

Persona Test Lab evaluates task-progress dialogue, not generic friendliness.

Mandatory lint targets:
1. banned phrase hit
2. empty greeting or receptionist opening
3. first sentence enters the task directly
4. explicit judgment exists
5. explicit next action exists
6. repeated user goal echo
7. unnecessary question
8. lack of task advancement
9. receptionist fallback under pressure
10. bilingual or long-context style degradation

Mandatory scoring dimensions:
- task entry directness
- judgment clarity
- next action clarity
- question discipline
- non-repetition
- task advancement
- pressure stability
- bilingual consistency
- context cleanliness

Hard rules:
- fail-fast lint hits produce immediate case failure even if total score is high
- score without fail reasons is invalid
- human summary without transcript + score is invalid

## 10) Fail Reasons and Pass/Fail Standard

Every failing case MUST produce:
- rule or dimension id
- offending turn reference
- one-sentence failure statement
- why it violates task-progress dialogue
- minimum repair direction

Pass standard:
- no fail-fast lint hit
- required `must_pass_checks` all pass
- total score meets the case threshold
- no evidence of cross-case or production-state contamination

Fail standard:
- any fail-fast lint hit
- missing required artifact
- fresh-session rule broken
- judge cannot explain why the case failed

## 11) Minimum Regression Pack

The minimum built-in regression pack MUST include at least these cases:

1. user explicitly says `不要客服腔`
2. user already gave a clear task, so empty clarification is forbidden
3. user criticizes the system, so the reply must not open with greeting or soft apology shell
4. user asks for a direct problem statement, so judgment must come before action
5. bilingual input must keep style stable
6. overcontrolling or angry pressure must not collapse into apology loops
7. vague input must still receive partial judgment before the missing gap is named
8. long conversation must not reset into `你好呀 / 我在 / 我来帮你` style reopening

Repo-local case specs under `persona_lab/cases/` are the minimum regression baseline for this pack.

## 12) Relationship to Production Execution

Persona Test Lab:
- is not the production execution chain itself
- is a dedicated test layer for the production assistant
- is part of regression and style acceptance
- must not pollute production conversation state
- must not substitute for real task execution
- exists to prove whether style defects were actually repaired

## 13) Integration Rule for Future Runtime Work

Any future runner or judge implementation for Persona Test Lab MUST declare:
- upstream entrypoint
- transcript source of truth
- judge source of truth
- failure behavior
- automated acceptance path

Prompt-only “we now speak better” claims do not count as persona-lab completion.

## 14) Next-Stage Roadmap

Current patch lands the contracts and static assets only.

Next-stage goals:
- build a persona-lab runner that starts a fresh session per case
- build a judge executor that emits `score.json` and `fail_reasons.md`
- connect persona-lab regression into style acceptance and CI/verify policy when runtime support exists
- extend SimLab or replay tooling with snapshot-capable scene replay so visible UI or chat-step evidence can be bound to persona transcripts without mixing them into production runs
