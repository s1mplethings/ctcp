# B038 cos-user-v2p-dialogue-runner

## Reason
- Provide a deterministic CTCP workflow to run an external V2P testkit with auditable dialogue and fixed-destination outputs.

## Behavior
- Trigger: `python scripts/ctcp_orchestrate.py cos-user-v2p --repo ... --project ... --testkit-zip ...`.
- Inputs / Outputs: repo path + testkit zip + dialogue source -> run_dir evidence + copied outputs under `<out_root>/<project>/<run_id>/out/`.
- Invariants:
  - run_dir is created under external runs root and writes `TRACE.md` + `events.jsonl`.
  - doc-first evidence (`artifacts/USER_SIM_PLAN.md`) is written before verify/testkit execution.
  - dialogue collects at least 3 Q/A turns and stores both JSONL and transcript artifacts.
  - testkit is unpacked/executed outside CTCP repo (`run_dir/sandbox/testkit`), and only declared outputs are copied.
  - return code is PASS only when testkit succeeds, required outputs exist, and verify commands pass (unless `--skip-verify`).

## Result
- Acceptance: reproducible v2p report with verify status, copied outputs, extracted metrics, and dialogue turn count.
- Evidence: `scripts/ctcp_orchestrate.py`, `tools/testkit_runner.py`, `tests/test_cos_user_v2p_runner.py`, `simlab/scenarios/S28_cos_user_v2p_dialogue_to_D_drive.yaml`.
- Related Gates: workflow_gate
