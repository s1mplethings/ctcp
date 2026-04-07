# Verify Contract (Evidence-First)

> Deprecated / superseded:
> - Runtime truth and verify authority now live in `docs/00_CORE.md`
> - Gate sequence and acceptance semantics now live in `docs/03_quality_gates.md`
> - Artifact naming and provenance now live in `docs/30_artifact_contracts.md`
> - Persona/style regression authority now lives in `docs/14_persona_test_lab.md`
>
> This file is retained for historical context only. If it conflicts with the sources above, this file loses.

This document defines what "tested" means in this repository.

## Rule Zero

- No evidence = not tested.
- `tools/adlc_gate.py` is the objective gate.
- If proof/log artifacts are missing, or `proof.result != PASS`, gate must fail (non-zero).

## Verify Command

Primary commands:

- Linux/macOS: `bash scripts/verify_repo.sh`
- Windows: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`

Both commands must run:

1. `cmake -S -B` (configure)
2. `cmake --build` (build)
3. `ctest --test-dir ...` (logic/runtime tests)
4. `cmake --install ... --prefix dist` (install check)
5. smoke run on installed app (`--smoke`)

Then run gate:

- `python tools/adlc_gate.py --proof-dir <latest_proof_dir>`

Optional contrast:

- `python tools/contrast_proof.py --old <old_proof.json> --new <new_proof.json> --out <contrast_report.md>`

## Gate Levels

- Lite (default in `verify_repo`):
  - headless build (default target)
  - workflow/contract/doc-index checks
  - 1-2 minimal replay scenarios (suite=`lite`)
- Full (opt-in):
  - enabled by `CTCP_FULL_GATE=1` or explicit `--full`
  - can include broader checks and tests

## Artifact Layout

`artifacts/verify/<timestamp>/` must include:

- `proof.json`
- `01_configure.log`
- `02_build.log`
- `03_ctest.log`
- `04_install.log`
- `05_smoke.log`

And `artifacts/verify/latest_proof_path.txt` points to latest run directory.

## proof.json Schema (required fields)

- `schema_version`
- `run_id`
- `generated_at`
- `result` (`PASS`/`FAIL`)
- `platform` (OS/arch/python/tool summary)
- `paths` (source/build/install/proof_dir)
- `inputs` (config/generator/args/smoke settings)
- `steps` (name/cmd/cwd/exit_code/duration/log_file/status)
- `metrics` (duration + optional test/install metrics)

## Return Code Contract

- `tools/run_verify.py`: `0` only when all required steps pass, else non-zero.
- `tools/adlc_gate.py`: `0` only when proof is complete and PASS, else non-zero.
- `scripts/verify.*`: return gate exit code.

## Smoke Strategy

Smoke mode is required (`<app> --smoke`).

- Run the headless target with a minimal startup/close path; no manual interaction is required.

Smoke must fail non-zero when app cannot initialize required runtime/plugins/resources.

## Failure Bundle Contract

For replay/adlc runs, failed execution must produce `failure_bundle.zip` containing at least:

- `TRACE.md`
- `diff.patch` (if git diff available)
- `logs/*` (step logs/stdout/stderr)
- key snapshots asserted during the run
