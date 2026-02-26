# Acceptance Criteria (cos-user-v2p)

PASS if:
1) cos-user-v2p returns 0
2) run_dir contains TRACE.md, events.jsonl (>=3 dialogue turns), artifacts/USER_SIM_PLAN.md, artifacts/v2p_report.json
3) destination contains scorecard.json, eval.json, cloud.ply (and cloud_sem.ply if semantics enabled)
4) CTCP verify_repo passes after implementation
