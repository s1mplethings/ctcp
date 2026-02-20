# Patch Contract

This repository accepts patch outputs only when they satisfy all required rules below.

## Required Format

1. The patch must be unified diff text.
2. The patch must start with `diff --git`.
3. Each changed file section must include:
   - `--- a/<path>`
   - `+++ b/<path>`
   - unified hunks (`@@ ... @@`)
4. The patch must be directly applicable with:
   - `git apply <patch-file>`

## Required Evidence

Every patch request/response must include evidence references for each intended change:

- file path
- line number or line range
- short evidence snippet

Evidence references should come from Local Librarian search results when available.

## Intent Statement

For each file change, include one short intent statement:

- what is being changed
- why this is the minimal safe change

## Scope and Safety

1. Patch scope must stay within the approved contract guard limits.
2. If contract guard fails, patch application is rejected.
3. Any rejected patch must produce:
   - `reviews/contract_review.json`
   - brief reason summary in run artifacts

## Non-Goals

1. No prose-only output in place of patch.
2. No opaque binary edits without textual diff metadata.
3. No bypass of `verify_repo` or workflow/contract/doc gates.
