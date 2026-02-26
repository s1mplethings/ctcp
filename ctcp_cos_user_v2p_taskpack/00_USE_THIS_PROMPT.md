# CTCP: cos-user-v2p (point-cloud) dialogue test runner — Implementation Task

You are a programming agent working on the **CTCP** repository.
Your job is to add a **single, deterministic, replayable** test workflow that:
- Runs an external point-cloud testkit (3D video → point cloud, optional semantics)
- Forces **doc-first**
- Produces a **real dialogue** (CTCP ↔ test-agent) and records it
- Copies outputs to a **fixed D:\ destination** (with safe fallback for CI)
- Does **NOT** pollute the CTCP repo (no fixture explosion / max_files failures)

Deliverables MUST pass `verify_repo.ps1` in CTCP.

---

## A) What to implement (core)

### 1) New orchestrate command
Add a subcommand:

`python scripts/ctcp_orchestrate.py cos-user-v2p ...`

Required args:
- `--repo <path>`: path to the point-cloud project repository to test
- `--project <name>`: project name used for output folder
- `--testkit-zip <path>`: external testkit zip path
Optional args (must be supported):
- `--out-root <path>` default **D:\v2p_tests**
- `--runs-root <path>` default env `CTCP_RUNS_ROOT` else CTCP default runs dir
- `--entry <cmd>` default `python run_all.py`
- `--copy <csv>` default `out/scorecard.json,out/eval.json,out/cloud.ply,out/cloud_sem.ply`
- `--dialogue-script <path>`: JSONL script that simulates the test agent replies
- `--agent-cmd <cmd>`: real agent command (optional; if set, CTCP asks questions by running this command)
- `--pre-verify-cmd <cmd>` and `--post-verify-cmd <cmd>`: verify commands executed inside `--repo`
- `--force`: allow overwriting the output destination directory run folder if it exists

### 2) Doc-first + evidence
Before running anything:
- Create run_dir: `<runs_root>/cos_user_v2p/<run_id>/`
- Write **artifacts/USER_SIM_PLAN.md** (doc-first evidence) including all args, resolved paths, and acceptance thresholds.
- Start `TRACE.md` and `events.jsonl` (reuse existing CTCP logging style)

### 3) Dialogue (real Q/A) + recording
CTCP must ask at least 3 questions and record Q/A turns as events:
- Q1: Confirm ProjectName + output destination
- Q2: Semantics on/off (store in plan; pass to testkit via env or args if supported; if not supported, still record decision)
- Q3: Thresholds (fps min, points min, fscore min) — default: 1.0 / 10000 / 0.85

Two modes:
- Script mode: `--dialogue-script` is JSONL that provides answers to Q ids.
- Live mode: `--agent-cmd` is executed; CTCP sends question text (stdin or temp file) and reads answer (stdout).

Outputs in run_dir:
- `artifacts/dialogue.jsonl` (raw)
- `artifacts/dialogue_transcript.md` (human-readable)

### 4) Run testkit **outside** the CTCP repo
Implement a small runner in CTCP (suggest: `tools/testkit_runner.py`):
- unzip `--testkit-zip` to `run_dir/sandbox/testkit/` or a temp dir
- execute `--entry` within that directory
- collect files listed by `--copy` from the testkit working dir
- copy them to **fixed destination**:

`<out_root>\<project>\<run_id>\out\`

Never copy the whole testkit or fixture into the CTCP repo.

### 5) Verify the tested repo (not CTCP)
Run:
- pre-verify (inside `--repo`) before testkit run
- post-verify after testkit run
Log both to `run_dir/logs/verify_pre.log` and `verify_post.log` (and record events).

Default verify command (Windows): `powershell -ExecutionPolicy Bypass -File verify_repo.ps1`
Fallback: if that doesn't exist, skip only if explicitly `--skip-verify` (optional; default is NOT skipping)

### 6) Final report (machine-readable)
Write `artifacts/v2p_report.json` summarizing:
- run_id, timestamps, resolved paths
- pre/post verify rc
- testkit rc + runtime
- copied outputs existence
- extracted metrics from scorecard/eval (if present)
- dialogue turn count

Return code:
- 0 only if: testkit rc==0 and required outputs exist; if verify is enabled, both verify rcs==0

---

## B) SimLab scenario + fixtures + tests (deterministic)

1) Add a SimLab scenario:
`simlab/scenarios/Sxx_cos_user_v2p_dialogue_to_D_drive.yaml`
- run: the new command with `--dialogue-script tests/fixtures/dialogues/v2p_cos_user.jsonl`
- use a **stub testkit zip** in `tests/fixtures/testkits/stub_ok.zip`
- expect_path checks:
  - run_dir contains `TRACE.md`, `events.jsonl`, `artifacts/USER_SIM_PLAN.md`, `artifacts/v2p_report.json`
  - D:\ output folder contains copied files

2) Add fixtures:
- `tests/fixtures/dialogues/v2p_cos_user.jsonl` (provided in this taskpack)
- `tests/fixtures/testkits/stub_ok.zip` (provided in this taskpack)

3) Add unit test:
`tests/test_cos_user_v2p_runner.py`
- Use temp dirs.
- For CI without D:\, tests pass `--out-root <tmp>`.

---

## C) Behaviors + plan bookkeeping (CTCP style)
- Add new behavior doc: `docs/behaviors/B0xx-cos-user-v2p-dialogue-runner.md` (Reason/Behavior/Result)
- Register it in `docs/behaviors/INDEX.md`
- Update `artifacts/PLAN.md` to include the behavior reference if CTCP requires it.

---

## D) Acceptance
- `verify_repo.ps1` in CTCP passes.
- The new command works with the provided stub testkit + dialogue script.
- No repo pollution: testkit runs outside CTCP repo; only run_dir + destination get outputs.

---

## E) Patch-first
Deliver changes as a minimal patch set.
Do not refactor unrelated code.
