# Persona Test Lab Assets

This directory stores repo-local static assets only.

What lives here:
- `personas/`: fixed production persona and test user persona definitions
- `rubrics/`: lint and scoring rules for transcript judging
- `cases/`: minimum regression scenarios

What must not live here:
- live transcripts
- scores from executed runs
- fail reasons from executed runs
- snapshots from executed runs

Those run outputs MUST stay outside the repo under:

`<CTCP_RUNS_ROOT>/<repo_slug>/persona_lab/<lab_run_id>/...`

Authority:
- `docs/14_persona_test_lab.md`
- `docs/11_task_progress_dialogue.md`
- `docs/30_artifact_contracts.md`

Language policy:
- English Contracts, Chinese Intent
- formal ids and fields stay in English
- Chinese appears only in scenario explanations and example utterances
