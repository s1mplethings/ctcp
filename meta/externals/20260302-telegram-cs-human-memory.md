# External Research - Telegram CS Bot Humanization + Memory (2026-03-02)

## Goal
- Find stable, production-oriented patterns to make `tools/telegram_cs_bot.py` less mechanical and more human:
  - daily small talk handling
  - explicit session memory
  - bounded clarification questions

## Sources
- Rasa docs (slots as assistant memory):
  - https://rasa.com/docs/reference/primitives/slots
- AWS Lex V2 docs (session attributes for per-session memory):
  - https://docs.aws.amazon.com/lexv2/latest/dg/context-mgmt-session-attribs.html
- Google Dialogflow docs (small talk module):
  - https://cloud.google.com/dialogflow/es/docs/small-talk
- Microsoft Bot Framework state management:
  - https://learn.microsoft.com/en-us/azure/bot-service/bot-builder-concept-state?view=azure-bot-service-4.0

## Key Takeaways
1) Memory should be structured and scoped, not free-form dumps.
   - Rasa and Bot Framework both emphasize explicit state buckets (slots / user+conversation state).
2) Session memory should be bounded.
   - Lex session attributes are per-session and updated per turn, suitable for short-term context carry-over.
3) Small talk should be an explicit route.
   - Dialogflow treats small talk as a dedicated built-in capability; it should not trigger heavy execution flows.
4) Clarification should be minimal.
   - State-driven routing plus a single key question avoids repetitive, script-like questioning.

## Applied Design (this patch)
- Keep using `artifacts/support_session_state.json` but extend it with slot-like memory:
  - `memory_slots.customer_name`
  - `memory_slots.preferred_style`
  - `memory_slots.current_topic`
  - `memory_slots.last_request`
- Add a local small-talk fast path before router handoff when input is pure greeting/thanks/help.
- De-duplicate repeated follow-up questions based on state (`open_questions`), so the bot does not keep asking equivalent prompts.
