# Formal Benchmarks

This document defines the fixed CTCP formal benchmark entrypoints for the Plane-lite / Focalboard-lite team task management line.

These benchmarks measure the project-generation mainline. They are intentionally reported separately from repo-level canonical verify. A benchmark can PASS while `scripts/verify_repo.ps1` still fails on unrelated dirty worktree or module-protection state.

## Entry Points

### formal_basic_benchmark

Windows entry:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_formal_basic_benchmark.ps1
```

Python entry:

```powershell
python scripts/formal_benchmark_runner.py --profile basic --mode run --benchmark-zip plane_lite_team_pm_test_pack.zip
```

Purpose:

- Uses `plane_lite_team_pm_test_pack.zip` as benchmark source.
- Reads `benchmark_case.json` and scripted turns.
- Forces `CTCP_FORCE_PROVIDER=api_agent`.
- Forces `CTCP_FORMAL_API_ONLY=1`.
- Creates a temporary writable `CTCP_RUNS_ROOT` if none is supplied.
- Runs the support scripted customer session and advances the canonical orchestrator.
- Emits `formal_basic_benchmark_summary.json`.

### formal_hq_benchmark

Windows entry:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_formal_hq_benchmark.ps1
```

Python entry:

```powershell
python scripts/formal_benchmark_runner.py --profile hq --mode run --benchmark-zip plane_lite_team_pm_test_pack.zip
```

Purpose:

- Uses the same Plane-lite benchmark pack as the base project definition.
- Adds the formal high-quality / extended profile directive before scripted turns.
- Forces real API and forbids mock/fake success.
- Forces `CTCP_FORMAL_API_ONLY=1`.
- Requires extended product-depth evidence in addition to normal verify/delivery evidence.
- Emits `formal_hq_benchmark_summary.json`.

### formal_endurance_benchmark

Windows entry:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_formal_endurance_benchmark.ps1
```

Python entry:

```powershell
python scripts/formal_benchmark_runner.py --profile endurance --mode run
```

Purpose:

- Uses the fixed Indie Studio Production Hub Endurance rough goal as the benchmark source.
- Forces `CTCP_FORCE_PROVIDER=api_agent`.
- Forces `CTCP_FORMAL_API_ONLY=1`.
- Creates a temporary writable `CTCP_RUNS_ROOT` if none is supplied.
- Starts from the real support-bot entrypoint and advances the canonical orchestrator until the run closes or a hard blocker surfaces.
- Emits `benchmark_endurance_summary.json` and `benchmark_endurance_summary.md`.
- Prints the run path, support session path, runtime/user verdicts, replay state, and final/evidence bundle paths.

## Formal API-Only Lock

Formal benchmark, portfolio, and endurance runs treat the formal project-generation mainline as API-only.

- `librarian/context_pack` is the only local exception.
- Every other project-impacting role or step must execute through `api_agent`.
- A non-librarian step that resolves to `local_exec`, `ollama_agent`, `manual_outbox`, `mock_agent`, or any other non-`api_agent` provider must fail fast.
- Silent fallback to local generation, local normalizer synthesis, or manual/local success artifacts must not count as formal success.
- Formal PASS requires provider-ledger coverage proving the critical steps were API-executed.

Provider-ledger artifacts for each formal run:

- `artifacts/provider_ledger.jsonl`
- `artifacts/provider_ledger_summary.json`

Summary outputs must report API coverage from the provider ledger, including:

- critical API steps executed vs. critical steps required
- whether `all_critical_steps_api=true`
- the first provider-ledger coverage failure when formal PASS is denied

## Summary-Only Mode

Both PowerShell wrappers can validate an existing run and write the standard summary without starting a new API run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_formal_basic_benchmark.ps1 -Mode summarize -RunDir <run_dir>
powershell -ExecutionPolicy Bypass -File scripts/run_formal_hq_benchmark.ps1 -Mode summarize -RunDir <run_dir>
powershell -ExecutionPolicy Bypass -File scripts/run_formal_endurance_benchmark.ps1 -Mode summarize -RunDir <run_dir>
```

## Golden Archive Mode

Both wrappers can archive a known PASS run into `artifacts/benchmark_goldens/`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_formal_basic_benchmark.ps1 -Mode archive-golden -RunDir <run_dir>
powershell -ExecutionPolicy Bypass -File scripts/run_formal_hq_benchmark.ps1 -Mode archive-golden -RunDir <run_dir>
powershell -ExecutionPolicy Bypass -File scripts/run_formal_endurance_benchmark.ps1 -Mode archive-golden -RunDir <run_dir>
```

Golden archives preserve:

- formal transcript, when present
- `api_calls.jsonl`
- `provider_ledger.jsonl`
- `provider_ledger_summary.json`
- `project_spec.json`
- `output_contract_freeze.json`
- `verify_report.json`
- `support_public_delivery.json`
- `final_project_bundle.zip`
- `intermediate_evidence_bundle.zip`
- final benchmark summary

The endurance golden additionally preserves:

- `source_generation_report.json`
- `project_manifest.json`
- `deliverable_index.json`
- final screenshots
- Markdown summary (`benchmark_endurance_summary.md`)

## Reporting Separation

Benchmark PASS means the CTCP project-generation mainline met the benchmark contract for that run.

Repo-level canonical verify is separate. It may still fail because of:

- dirty worktree files outside the active task scope
- module-protection ownership failures
- unrelated frozen-kernel edits
- unrelated docs/test drift

Reports must state both results independently.
