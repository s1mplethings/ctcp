# casual_user

- persona_id: `casual_user`
- persona_role: `test_user`
- language_profile: `zh-CN`

## Behavior Traits

- speaks loosely
- may look like smalltalk at first glance
- can accidentally trigger greeting templates

## Common Utterances

- `诶那个，反正你先帮我往前推一下。`
- `就先弄个能看的吧，别整客服那套。`
- `先别寒暄，直接说你准备怎么弄。`

## Risk Points

- assistant may misclassify the turn as greeting/smalltalk
- assistant may answer casually without concrete action

## Test Purpose

- verify that casual tone does not trigger receptionist openings
- verify task advancement under low-formality input
