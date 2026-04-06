# Demo Report - 20260404 Story Business Project-Generation Mainline

Archived because the active report topic moved from “固定 叙事业务项目生成主链” to “project-generation contract mode separation”.

### Readlist

- `AGENTS.md`
- `meta/tasks/CURRENT.md`
- `docs/41_low_capability_project_generation.md`
- `docs/backend_interface_contract.md`
- `tools/providers/project_generation_artifacts.py`
- `scripts/project_generation_gate.py`
- `tests/manual_backend_interface_narrative_project_runner.py`

### Plan

1. Deliver real story business code on the project-generation mainline.
2. Force `context_pack.json` to be consumed by source generation.
3. Raise gate and regression coverage above scaffold-only completion.

### Changes

- Business-deliverable story output contracts landed.
- `source_generation` now records and exposes `consumed_context_pack`.
- story regression and project-generation gate now require business delivery semantics.

### Verify

- `python tests/manual_backend_interface_narrative_project_runner.py` -> `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- first failure point: `PASS`
- minimal fix strategy: none for archived scope

### Questions

- None.

### Demo

- Archived handoff gap: fixed benchmark-sample flow was integrated, but the authoritative project-generation contract still needed an explicit production-vs-benchmark split so the benchmark sample would not be misread as the production default.
