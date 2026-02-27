# CTCP Task Pack: Generate a FULL Point-Cloud Project + Dialogue Benchmark Runner

You are a programming agent working on the **CTCP** repository.

Earlier, cos-user-v2p was only a *test/benchmark runner* and does NOT create project source code.
This task pack upgrades CTCP so it can:
1) **Generate a complete point-cloud project** (source files) into a target folder (e.g., `D:\v2p_projects\<ProjectName>`)
2) **Run a dialogue-driven cos-user benchmark** against that project using an external testkit zip
3) Copy benchmark outputs to `D:\v2p_tests\<ProjectName>\<run_id>\out\`
4) Record full evidence (doc-first + dialogue + trace + report) in CTCP run_dir

Deliverables MUST pass CTCP `verify_repo.ps1`.

---

## A) Implement: scaffold-pointcloud (PROJECT GENERATOR)

### New command
Add to `scripts/ctcp_orchestrate.py`:

`scaffold-pointcloud --out <path> [--name <ProjectName>] [--profile minimal|standard] [--force] [--runs-root <path>] [--dialogue-script <path>] [--agent-cmd <cmd>]`

Rules:
- `--out` is the **project root** where project SOURCE FILES are created.
- Safety:
  - Fail if `--out` exists unless `--force`
  - If `--force`, only delete inside `--out` (never outside), and only if `--out` resolves to a directory (no drive root).
- Doc-first:
  - Create CTCP run_dir and write `artifacts/SCAFFOLD_PLAN.md` BEFORE writing project files.
  - Record steps into TRACE.md and events.jsonl.
- Generate `meta/manifest.json` in the new project listing generated files (relative paths).
- Templates are in CTCP:
  - `templates/pointcloud_project/minimal/`
  - `templates/pointcloud_project/standard/`
  Token replacement: `{{PROJECT_NAME}}`, `{{UTC_ISO}}`

Profiles:
- minimal: README, docs, meta, scripts, tests, pyproject, .gitignore
- standard: minimal + docs/behaviors/INDEX.md + workflow_registry stub

### Generated project (minimal) must include
- README.md
- .gitignore
- docs/00_CORE.md
- meta/tasks/CURRENT.md
- meta/reports/LAST.md
- meta/manifest.json  (generated, not template)
- scripts/run_v2p.py  (placeholder pipeline entry)
- scripts/verify_repo.ps1 (runs pytest)
- tests/test_smoke.py
- pyproject.toml

---

## B) Implement: cos-user-v2p (DIALOGUE BENCHMARK RUNNER)

Add to `scripts/ctcp_orchestrate.py`:

`cos-user-v2p --repo <path> --project <name> --testkit-zip <path> [--out-root <path>] [--runs-root <path>] [--entry <cmd>] [--copy <csv>] [--dialogue-script <path>] [--agent-cmd <cmd>] [--pre-verify-cmd <cmd>] [--post-verify-cmd <cmd>] [--force] [--skip-verify]`

Defaults:
- out-root: `D:\v2p_tests`
- entry: `python run_all.py`
- copy: `out/scorecard.json,out/eval.json,out/cloud.ply,out/cloud_sem.ply`

Hard rules:
- Testkit MUST run outside CTCP repo AND outside the tested repo (use run_dir/sandbox or tempfile).
- Doc-first: write `artifacts/USER_SIM_PLAN.md` before running anything.
- Dialogue: ask >=3 questions; record to events.jsonl; write `artifacts/dialogue.jsonl` + `artifacts/dialogue_transcript.md`.
- Report: write `artifacts/v2p_report.json` (schema included).

Verify:
- Default pre/post verify (inside `--repo`) should attempt:
  `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1`
- Log to `run_dir/logs/verify_pre.log` and `verify_post.log`

Return code 0 only if:
- testkit rc==0 and required outputs copied
- and (if verify enabled) both verify rc==0

---

## C) Add fixtures + tests + SimLab scenario

Copy fixtures from this task pack into CTCP:
- `tests/fixtures/dialogues/scaffold_pointcloud.jsonl`
- `tests/fixtures/dialogues/v2p_cos_user.jsonl`
- `tests/fixtures/testkits/stub_ok.zip`

Add tests:
- `tests/test_scaffold_pointcloud_project.py`
- `tests/test_cos_user_v2p_runner.py`

Add SimLab scenario:
- `simlab/scenarios/Syy_full_pointcloud_project_then_bench.yaml`

CI note:
- tests must use temp `--out`/`--out-root` and temp `--runs-root` (do not require D:\ in CI).

---

## D) Behaviors docs
Add and register in `docs/behaviors/INDEX.md`:
- B0xx: scaffold-pointcloud
- B0xy: cos-user-v2p-dialogue-runner

Patch-first, minimal changes only.
