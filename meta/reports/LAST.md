# Demo Report — LAST

## Goal
- Land an ADLC evidence-closed-loop for this CMake + GUI project:
  configure -> build -> test -> install -> smoke -> proof -> gate -> contrast.

## Readlist
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/00_AI_CONTRACT.md`
- `CMakeLists.txt`
- `src/main.cpp`
- `scripts/verify.sh`
- `scripts/verify.ps1`
- `scripts/verify_repo.sh`
- `scripts/verify_repo.ps1`
- `.github/workflows/gate-matrix.yml`

## Plan
1) Define verify contract and ADLC stage artifacts in docs.
2) Implement proof/gate/contrast tools under `tools/`.
3) Add GUI `--smoke` mode and CMake install/CTest hooks.
4) Make `scripts/verify.*` one-command drivers.
5) Add cross-platform CI verify workflow and artifact upload.

## Timeline / Trace pointer
- Latest verify proof: `artifacts/verify/20260218-214027/proof.json`
- Latest contrast report: `artifacts/verify/20260218-214027/contrast_report.md`
- Latest gate matrix summary: `tests/fixtures/adlc_forge_full_bundle/runs/_suite_eval_summary.json`

## Changes (file list)
- `tools/run_verify.py`: unified configure/build/ctest/install/smoke driver with structured evidence output.
- `tools/adlc_gate.py`: hard gate that fails on missing proof/logs or non-PASS proof.
- `tools/contrast_proof.py`: compares two proof runs and outputs markdown contrast.
- `tools/tests/test_verify_tools.py`: logic self-test for verify command construction/metrics.
- `tools/__init__.py`: enables importable tools package for tests.
- `scripts/verify.sh`: one-command verify + gate + optional contrast (Linux/macOS).
- `scripts/verify.ps1`: one-command verify + gate + optional contrast (Windows).
- `src/main.cpp`: added `--smoke` mode with deterministic startup + short event loop + explicit fatal stderr.
- `CMakeLists.txt`: fixed Qt6->Qt5 fallback, added install rule, CTest smoke test, and Python logic self-test registration.
- `docs/verify_contract.md`: evidence contract, proof schema, return codes, headless smoke policy.
- `docs/adlc_pipeline.md`: executable ADLC stage/output mapping.
- `docs/03_quality_gates.md`: enforced "no evidence = no test" rule and tool references.
- `ai_context/problem_registry.md`: added root-cause/prevention entry for unverifiable verification.
- `README.md`: clarified verify command paths (`scripts/verify.*` + `verify_repo.*` roles).
- `.github/workflows/verify.yml`: Ubuntu + Windows verify pipeline with artifact upload.
- `.gitignore`: ignore `artifacts/verify/`.

## Verify (commands + output)
- `python tools/tests/test_verify_tools.py`
  - exit: `0`
  - output: `[verify_tools_test] ok`
- `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1`
  - exit: `1` (script returns gate fail code)
  - proof path: `artifacts/verify/20260218-214027/proof.json`
  - gate output: `FAIL` (configure step failed, downstream steps skipped)
  - root failure from `01_configure.log`: Qt package resolution mismatch in local environment
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - exit: `0`
  - workflow/contract/doc-index checks pass in current environment
- `python tools/checks/gate_matrix_runner.py`
  - exit: `0`
  - summary: `PASS 26 / FAIL 0 / SKIP 1`

## Open questions (if any)
- None

## Next steps
- For a full PASS proof on this machine, align Qt package versions (or set `CMAKE_PREFIX_PATH`/`Qt6_DIR` to a compatible Qt SDK) and rerun `scripts/verify.ps1`.
- Optional: add a non-scoring GUI integration smoke suite on top of this proof pipeline for richer runtime coverage.

