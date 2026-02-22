# B007 verify-repo-doc-index-gate

## Reason
- Ensure README doc index block is synchronized.

## Behavior
- Trigger: Verifier runs doc index consistency check.
- Inputs / Outputs: README.md and curated doc list -> sync pass/fail.
- Invariants: Curated index block must stay deterministic and auditable.

## Result
- Acceptance: sync_doc_links --check non-zero blocks verify_repo.
- Evidence: scripts/sync_doc_links.py,README.md
- Related Gates: doc_index_check

