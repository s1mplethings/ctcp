# Task — workflow-enforcement

## Context
- Need hard-enforced workflow for agents after repo rename and process drift.
- Goal is to make violations fail in verify gate, not remain as documentation-only guidance.

## Acceptance (must be checkable)
- [x] DoD written (this section is complete)
- [x] Research logged (if needed): `meta/externals/YYYYMMDD-<topic>.md`
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`)
- [x] `scripts/verify_repo.*` passes
- [x] Performance sanity check noted (node/edge count + basic interaction)

## Plan
1) Research-first (if needed)
2) Update docs/specs (spec-first)
3) Implement (patch)
4) Verify (run verify_repo)
5) Record (problem_registry / decision_log if needed)

## Notes / Decisions
- Use `scripts/verify_repo.*` as authoritative gate.
- Keep `scripts/verify.*` as thin wrappers to prevent command breakage.

## Results
- Added hard contract file: `ai_context/00_AI_CONTRACT.md`.
- Added hard workflow checker: `scripts/workflow_checks.py`.
- Added helper generator: `tools/ctcp_assistant.py`.
- Added top-level AIDoc templates: `ai_context/templates/aidoc/*.md`.
- Promoted `scripts/verify_repo.*` to full gate (build + web build + workflow + contract + doclinks).
- Reduced `scripts/verify.*` to wrappers.
- Updated template and zip hygiene rules.
- Verify:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` PASS
  - `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1` PASS
  - `bash scripts/verify.sh` PASS
