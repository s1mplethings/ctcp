# support_bot_suite_v1

This fixture set validates CTCP support bot humanization behavior under dual-channel constraints.

Goals:
- Human-like multi-paragraph replies (2-4 paragraphs, no list formatting).
- Proactive progression with at most one key question.
- Persistent memory usage (reuse confirmed choices, avoid repeated generic asks).
- Local-first routing with API/human handoff escalation when needed.
- Customer channel cleanliness (no internal traces/logs/paths/tool jargon).

Files:
- `suite_rules.json`: global constraints and style/routing defaults.
- `cases_core.jsonl`: foundational behavior and quality checks.
- `cases_memory.jsonl`: memory persistence and non-repetition checks.
- `cases_routing.jsonl`: local/api/need_more_info/handoff routing checks.
- `cases_tone.jsonl`: tone, wording variation, anti-template checks.
- `cases_safety.jsonl`: privacy/safety and destructive-action confirmation checks.

Execution model:
- Fast lane: run core + tone only.
- Full lane: run all case files.
