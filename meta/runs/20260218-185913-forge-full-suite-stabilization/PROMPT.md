# CTCP Team Packet — PROMPT

## Goal
forge-full-suite-stabilization

## Your role
You are the internal coding team. Follow repo contract strictly.

## Hard rules
- Read: AGENTS.md, ai_context/00_AI_CONTRACT.md, README.md, BUILD.md, PATCH_README.md, ai_context/problem_registry.md, ai_context/decision_log.md
- Spec-first: docs/spec/meta before code
- Code changes only if meta/tasks/CURRENT.md ticks: [x] Code changes allowed
- Always run verify: scripts/verify_repo.* and paste key results into meta/reports/LAST.md
- If blocked, write questions ONLY to: meta/runs/20260218-185913-forge-full-suite-stabilization/QUESTIONS.md

## Delivery
Prefer one patch per theme. Put patches under PATCHES/ (create if missing), and list them in meta/reports/LAST.md.

## Trace / Demo
Write a short running log to: meta/runs/20260218-185913-forge-full-suite-stabilization/TRACE.md
Include:
- decisions
- commands run
- failures and fixes

## Expected finish state
- verify_repo passes
- README Doc Index is in sync (scripts/sync_doc_links.py --check passes)
- meta/reports/LAST.md updated and points to meta/runs/20260218-185913-forge-full-suite-stabilization

