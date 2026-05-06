# Task Archive - Support Bot Slimming

- Queue Item: `ADHOC-20260502-support-bot-slimming`
- Date: `2026-05-02`
- Status: `done` for the support-bot slimming slice; canonical full PASS remains blocked by an unrelated/flaky project-generation variant-content test.

## Scope

The slice reduced `scripts/ctcp_support_bot.py` by extracting constant and pattern tables into Python modules. It did not move runtime behavior into Markdown and did not intentionally change support bot behavior.

## Completed DoD

- [x] `scripts/ctcp_support_bot.py` no longer owns the large support pattern and path constant table.
- [x] Extracted support constants/patterns live in narrow Python modules instead of Markdown.
- [x] Targeted support-bot regressions and workflow checks pass.

## Verification

- `python -m py_compile scripts\ctcp_support_bot.py scripts\ctcp_support_bot_constants.py scripts\ctcp_support_bot_text_patterns.py` passed.
- `python -m unittest discover -s tests -p "test_support_chain_breakpoints.py" -v` passed.
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` passed.
- `python scripts\workflow_checks.py` passed.
- Canonical verify progressed through simlab lite (`15` passed, `0` failed) and failed at full Python unit tests on `test_project_generation_variant_content.py::test_narrative_sample_pipeline_same_goal_uses_run_variant_content`; the same test passed when rerun alone.
