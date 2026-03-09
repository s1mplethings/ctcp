# telegram_human_dialogue_sim_v1

Simulated user-side multi-turn dialogue cases for human-like support replay.

Purpose:
- Provide user-authored style prompts (as if from real customers/ops owners).
- Replay cases through `tools/telegram_cs_bot.py` in local test mode.
- Validate baseline conversational hygiene:
  - non-empty reply,
  - no internal trace/path leakage,
  - bounded number of questions per reply.

Notes:
- This fixture is generated from simulated user conversations, not production chat logs.
- Cases are intentionally mixed (zh/en, product/support/ops tone, calm/urgent mood).
