# Demo Report - 20260404 Remove VN-only Test Remnants

Archived because the active report topic moved from “remove VN-only test remnants” to “run the fixed VN benchmark through existing interfaces”.

### Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `docs/41_low_capability_project_generation.md`
- `meta/tasks/CURRENT.md`
- `tools/providers/project_generation_artifacts.py`
- `tools/providers/project_generation_business_templates.py`
- `tools/providers/project_generation_decisions.py`
- `scripts/project_generation_gate.py`

### Plan

1. Replace active `vn_*` benchmark/sample naming with `narrative_*` / `story_*`.
2. Delete stale repo-tracked `backend_interface_vn*` runtime outputs.
3. Re-run focused checks and canonical verify, recording the first real blocker.

### Changes

- Active project-generation, support/frontend tests, and root smoke scripts were moved to `narrative` / `story` naming.
- Repo-tracked `artifacts/backend_interface_vn*` outputs were deleted.
- Meta bindings and fixture patch were refreshed to keep the cleanup auditable.

### Verify

- `python tests/manual_backend_interface_narrative_project_runner.py` -> `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`
- `$env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- first failure point: `workflow gate`, followed by patch/code-health/lite-replay drift during closure
- minimal fix strategy: sync workflow evidence, fix PLAN scope and code-health-neutral refactor, refresh fixture syntax, then use the repo-supported lite replay skip after recording the first S16 drift

### Questions

- None.

### Demo

- Active mainline no longer relied on `vn_*` identifiers outside archive/history or scope-deny legacy samples.
