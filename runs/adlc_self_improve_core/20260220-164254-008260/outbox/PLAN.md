# PLAN �� forge-full-suite self optimize (Round 1)

## Metadata
- Label: `BOOTSTRAP`
- Goal: `forge-full-suite self optimize`
- verify_rc: `N/A`

## Constraints Snapshot
- Policy source: `contracts/allowed_changes.yaml`
- Max changed files: `10`
- Max added lines: `800`
- Max deleted lines: `800`
- Max total changed lines: `800`
- Allowed paths: `scripts/`, `tools/`, `docs/`, `workflow_registry/`, `simlab/`, `tests/`, `contracts/`, `README.md`
- Blocked paths: `.github/`, `runs/`, `build/`, `dist/`

## Minimal Execution Plan

### Phase 1: Docs/Spec First
1. Create a minimal spec doc in `docs/` for the bootstrap scope:
   - objective, inputs, outputs, constraints, stop conditions.
2. Add/update one workflow registration file in `workflow_registry/` linking:
   - goal id
   - entry script/tool
   - verification command (`scripts/verify_repo.ps1`).

### Phase 2: Minimal Bootstrap Implementation
3. Add one small bootstrap executor in `scripts/` (or `tools/`) that:
   - reads/accepts policy path
   - validates goal name
   - prints planned stages (Docs/Spec -> Code -> Verify -> Report)
   - returns nonzero on invalid config.
4. Add one focused test in `tests/` for:
   - valid invocation success
   - invalid/missing policy failure.

### Phase 3: Contract Alignment
5. If needed, add a short contract companion note under `contracts/` clarifying how bootstrap respects `allowed_changes.yaml` (no policy relaxation).

### Phase 4: Verify + Patch Emission
6. Run repository verification:
   - Windows: `scripts/verify_repo.ps1`
   - record key pass/fail lines and any explicit skips with reasons.
7. Emit external patch as unified diff:
   - must start with `diff --git`
   - must stay within file/line budgets and allowed paths only.

## Acceptance Criteria
1. All modifications are inside allowed paths; zero edits in blocked paths.
2. Diff stats satisfy all max limits (files/add/delete/total).
3. Bootstrap command succeeds for valid config and fails for invalid config.
4. At least one automated test covers bootstrap argument/policy validation.
5. `scripts/verify_repo.ps1` is executed and results are captured.
6. Patch output format is valid unified diff beginning with `diff --git`.

## Planned Change Budget (Target)
- Target files changed: `5-8`
- Target total changed lines: `< 400` (buffer under `800`)
