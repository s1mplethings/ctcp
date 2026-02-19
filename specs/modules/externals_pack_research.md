# Externals Pack Research (Candidate-Only)

## Purpose
- Capture optional external evidence under strict guardrails as candidate input.

## Scope
- Generate `find_web`/externals pack artifacts when enabled by guardrails.

## Non-Goals
- Replace resolver-selected `find_result.json`.
- Become mandatory in resolver-only mode.

## Inputs
- `${run_dir}/artifacts/guardrails.md` (`find_mode`, web constraints).
- approved web policy constraints.

## Outputs
- `${run_dir}/artifacts/find_web.json` (optional),
- `meta/externals/<goal_slug>/externals_pack.json` (candidate evidence path).

## Dependencies
- Resolver-first workflow contract.
- Research role boundaries.

## Gates
- find-web contract checks and lite web-contract scenario.

## Failure Evidence
- Invalid web artifacts must not override resolver result and must surface as blocked reason.

## Owner Roles
- Researcher (manual/API role) and Chair adjudication.
