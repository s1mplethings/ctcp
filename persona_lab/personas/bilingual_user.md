# bilingual_user

- persona_id: `bilingual_user`
- persona_role: `test_user`
- language_profile: `mixed zh-CN + en`

## Behavior Traits

- switches language mid-turn
- uses English action words inside Chinese requests
- expects style stability across language switches

## Common Utterances

- `不要客服腔，just tell me the issue and next action.`
- `这个 task 已经 clear 了，你别再 ask for clarification.`
- `Give me the judgment first，然后再说你要怎么推进。`

## Risk Points

- assistant may fall back to generic English customer support phrases
- assistant may dump bilingual filler instead of task-progress dialogue

## Test Purpose

- verify bilingual consistency
- verify no style degradation after language shifts
