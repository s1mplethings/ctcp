# Update 2026-02-26 (v2p testkit + verify_repo rerun loop)

Experiment: V2P testkit + verify_repo gate

Repo SHA: 620b6e0b2b61246f4dc1e3a27aed326584a18a38

V2P testkit: PASS

fps: 9.076324102703188

points_down: 40022

voxel_fscore: 0.996370601875189

outputs: cloud.ply / cloud_sem.ply / scorecard.json / eval.json (OK)

verify_repo.ps1: PASS

first failure stage: patch_check (changed file count exceeds PLAN max_files: 221 > 200)

first failing file (if any): N/A on first failure; subsequent first-file failures were `specs/modules/dispatcher_providers.md`, `specs/modules/librarian_context_pack.md`, `v2p_user_sim_testkit.zip`

Fixes applied (minimal):

`v2p_user_sim_testkit/`: moved out of repo to temp because extracted testkit files were not patch scope and triggered `max_files` overflow.

`specs/modules/dispatcher_providers.md`: reverted because out-of-scope for this experiment and not required for V2P regression.

`specs/modules/librarian_context_pack.md`: reverted because out-of-scope for this experiment and not required for V2P regression.

`v2p_user_sim_testkit.zip`: moved out of repo to temp because it is out-of-scope for patch_check and not required in repo worktree after execution.

Re-run results:

verify_repo exit code: 0

Evidence paths:

`artifacts/verify_repo.log`

`artifacts/TRACE.md`

`artifacts/verify_report.json`

`C:/Users/sunom/AppData/Local/Temp/v2p_user_sim_testkit_20260226_161858/out/cloud.ply`

`C:/Users/sunom/AppData/Local/Temp/v2p_user_sim_testkit_20260226_161858/out/cloud_sem.ply`

`C:/Users/sunom/AppData/Local/Temp/v2p_user_sim_testkit_20260226_161858/out/scorecard.json`

`C:/Users/sunom/AppData/Local/Temp/v2p_user_sim_testkit_20260226_161858/out/eval.json`


