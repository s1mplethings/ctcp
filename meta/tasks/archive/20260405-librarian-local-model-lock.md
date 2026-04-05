# Task Archive - librarian-local-model-lock

## Archive Reason

- Topic switched on `2026-04-05` because the active work moved to a temporary validation task.
- Status at archive time: `done`.

## Queue Binding

- Queue Item: `ADHOC-20260404-librarian-local-model-lock`
- Previous Status: `doing`
- Baseline lock: `repo=D:/.c_projects/adc/ctcp`, `branch=main`, `commit=faeaedbd419aeb9de182c606cd7ce27eaa091e89`, `subject=3.3.4 + current working tree`.

## Archived Summary

- Previous scope: hard-lock `librarian/context_pack` to the true local-model provider, block silent remote fallback, and align evidence/docs/tests with that rule.
- Archived reason: active topic moved to a temporary validation task; the librarian topic is preserved as completed background context, not the current task.

## Prior Evidence Snapshot

- The active task/report recorded the librarian route as hard-locked to `ollama_agent`.
- The task/report claimed focused regressions plus canonical verify closure.
- The current worktree remained dirty relative to baseline and was preserved as-is for the next topic.
