# Optimization playbook (agent)

Once CTCP implements:
- scaffold-pointcloud (generate project files)
- cos-user-v2p (dialogue benchmark runner)

You can:
1) Generate a fresh project at `D:\v2p_projects\<name>`
2) Run benchmarks to `D:\v2p_tests\<name>\<run_id>\out`
3) Iterate changes in the generated project and re-run cos-user-v2p
4) Accept only improvements based on scorecard/eval metrics

All CTCP run evidence lives in the run_dir (plan/trace/dialogue/report).
