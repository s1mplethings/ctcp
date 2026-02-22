---
name: ctcp-doc-index-sync
description: Keep README Doc Index synchronized using the repo script and quality-gate check flow.
---

# ctcp-doc-index-sync

## When To Use
- README Doc Index check fails in verify/contract checks.
- User asks to sync documentation index safely.
- When invoked explicitly with `$ctcp-doc-index-sync`.

## When Not To Use
- Failure is unrelated to doc index synchronization.
- User requests broader doc refactor beyond index maintenance.

## Required Readlist
- `AGENTS.md`
- `docs/03_quality_gates.md` (if present)
- `README.md`
- `scripts/sync_doc_links.py`

## Fixed Order
1. Run check mode first: `python scripts/sync_doc_links.py --check`.
2. If check fails, run sync: `python scripts/sync_doc_links.py`.
3. Re-run check mode and confirm pass.
4. Run repo verify gate if requested/needed.
5. Report command trace and first failing point (if still failing).

## Output Discipline
- Record exact commands and return codes.
- Highlight first failing step and file.
- Keep changes minimal to index block only.
- State smallest next fix if gate still fails.
