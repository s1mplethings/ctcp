# Update 2026-02-27 (pointcloud template concrete implementation + customer test)

### Goal
- Upgrade generated pointcloud project from placeholder skeleton to a concrete runnable baseline implementation, then run customer-style acceptance tests.

### Changes
- Updated template implementation:
  - `templates/pointcloud_project/minimal/scripts/run_v2p.py`
    - deterministic seed derivation from optional input file hash
    - parameterized generation (`--frames`, `--points`, `--voxel-size`, `--seed`, `--semantics`)
    - realistic multi-point cloud generation (not single-point stub)
    - outputs: `cloud.ply`, optional `cloud_sem.ply`, `scorecard.json`, `eval.json`, `stage_trace.json`
- Updated template smoke test:
  - `templates/pointcloud_project/minimal/tests/test_smoke.py`
    - validates semantics output + metrics + stage trace
- Updated template verify script for environment robustness:
  - `templates/pointcloud_project/minimal/scripts/verify_repo.ps1`
    - sets `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`
    - runs `pytest` on `tests/test_smoke.py` to avoid host plugin pollution
- Updated template README usage:
  - `templates/pointcloud_project/minimal/README.md`

### Customer Test (real run)
- Scaffolded project:
  - `python scripts/ctcp_orchestrate.py scaffold-pointcloud --out C:\Users\sunom\AppData\Local\Temp\ctcp_customer_impl_20260227_000242\v2p_projects\v2p_impl_demo --name v2p_impl_demo --profile minimal --force --runs-root C:\Users\sunom\AppData\Local\Temp\ctcp_customer_impl_20260227_000242\ctcp_runs --dialogue-script tests/fixtures/dialogues/scaffold_pointcloud.jsonl`
  - exit `0`
- Project-local verify:
  - `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1` (inside generated project)
  - exit `0` (`1 passed`)
- Project pipeline run:
  - `python scripts\run_v2p.py --out out --semantics --frames 48 --points 12000`
  - exit `0`
  - observed metrics:
    - `fps: 1275.0259`
    - `points_down: 12000`
    - `voxel_fscore: 0.9029`
- Dialogue benchmark run:
  - `python scripts/ctcp_orchestrate.py cos-user-v2p --repo <generated_project> --project v2p_impl_demo --testkit-zip tests/fixtures/testkits/stub_ok.zip --out-root <temp>/v2p_tests --runs-root <temp>/ctcp_runs --entry "python run_all.py" --dialogue-script tests/fixtures/dialogues/v2p_cos_user.jsonl --force`
  - exit `0`
  - report: `C:/Users/sunom/AppData/Local/Temp/ctcp_customer_impl_20260227_000242/ctcp_runs/cos_user_v2p/20260227-000322-520265-cos-user-v2p-v2p_impl_demo/artifacts/v2p_report.json`
  - result: `PASS` (testkit rc=0, pre/post verify rc=0, dialogue_turns=3)

### Verify
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `0`
  - replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260227-000359/summary.json` (`passed=14 failed=0`)
  - python unit tests: `Ran 69 tests, OK (skipped=3)`

