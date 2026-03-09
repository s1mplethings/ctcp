## Telegram Bot Dataset V1

Data-driven cases for `tools/telegram_cs_bot.py` message entry behavior.

- `cases.jsonl`: each line is one test case.
- Focus:
  - unbound session behavior (no active run)
  - bound session behavior (active run)
  - intent handling around status/progress requests

Case fields:
- `id`, `title`, `text`
- `prebind_run`: whether a fake run is bound before sending input
- `session_lang`: optional (`zh` or `en`)
- `expect_run_bound`: whether run should remain bound after handling
- `expect_reply_contains_any`: optional token list (at least one must appear)
- `expect_reply_contains_all`: optional token list (all must appear)
- `expect_reply_not_contains_any`: optional token list (none may appear)

Strength target:
- Dataset size should stay at or above 30 cases to keep high-intensity coverage.
