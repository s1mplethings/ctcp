# Optimization playbook (agent)

After implementing cos-user-v2p in CTCP:

1) Baseline run on your real point-cloud repo + real testkit zip.
2) Read run_dir/artifacts/v2p_report.json and the destination out/scorecard.json + out/eval.json.
3) Make ONE small change in the point-cloud repo (parameter tuning or compute reduction).
4) Re-run cos-user-v2p and compare metrics.
5) Keep changes only if the score improves under your rules.

Tip: make your real testkit accept env vars like V2P_SEMANTICS so CTCP dialogue can control it.
