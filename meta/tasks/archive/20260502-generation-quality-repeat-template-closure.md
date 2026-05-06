# Task Archive - Generation Quality Repeat Template Closure

## Queue Binding

- Queue Item: `ADHOC-20260502-generation-quality-repeat-template-closure`
- Layer/Priority: `L1 / P0`
- Lane: Delivery Lane
- Status: done

## Purpose

Fully close the user-visible generation-quality gaps:

- repeated or overly long Telegram replies for the same status/result context
- final project delivery that makes deterministic local materializer output look like customized API/agent-authored source

## Scope

- `frontend/support_reply_policy.py`
- `scripts/ctcp_support_bot.py`
- `tools/providers/project_generation_provenance.py`
- `tools/providers/project_generation_artifacts.py`
- `tests/test_support_reply_policy_regression.py`
- `tests/test_project_generation_provenance.py`
- `docs/03_quality_gates.md`
- `ai/MEMORY/ISSUE_MEMORY.md`
- task/report metadata

## Check/Contrast/Fix Loop Evidence

- check/contrast/fix loop evidence: complete.
- check:
  - support regression proves long replies compact and duplicate proactive delivery suppresses
  - provenance regression proves materializer-only source blocks final package and API content allows final delivery
  - project-generation artifact regression and code-profile verify pass
- contrast:
  - final zip delivery must be blocked by provenance, not only explained in prose
  - suppressed support replies must clear actual sendable text, not only metadata
- fix:
  - added `source_customization_completion`
  - gated `final_project_bundle.zip`
  - compacted and deduped reply policy
  - made support bot consume suppression correctly

## Completion Criteria Evidence

- completion criteria evidence: `connected + accumulated + consumed` proven.
- connected:
  - source-map API evidence reaches source-generation provenance
  - reply policy suppression reaches support final reply build
- accumulated:
  - manifest carries `source_customization_completion`
  - reply memory carries context signatures
- consumed:
  - deliverable index refuses final zip when completion fails
  - Telegram-bound reply text is empty when policy suppresses

## Acceptance

- [x] Support reply repetition/length regression added and passing.
- [x] Template/materializer-only source generation regression added and passing.
- [x] Canonical code-profile verify passed with `CTCP_SKIP_LITE_REPLAY=1`.
- [x] Telegram bot restarted with current runtime code.
