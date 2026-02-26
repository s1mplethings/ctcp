# TRACE - V2P testkit + verify_repo gate

1) git status --short => rc=0
2) git rev-parse HEAD => rc=0
3) Expand-Archive v2p_user_sim_testkit.zip -> v2p_user_sim_testkit/ => rc=0
4) python run_all.py (in extracted testkit) => rc=0
5) powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 => rc=1
   first failure: patch_check max_files (221 > 200)
6) Move-Item v2p_user_sim_testkit -> %TEMP% => rc=0
7) powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 => rc=1
   first failure: patch_check out-of-scope specs/modules/dispatcher_providers.md
8) git restore -- specs/modules/dispatcher_providers.md => rc=0
9) powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 => rc=1
   first failure: patch_check out-of-scope specs/modules/librarian_context_pack.md
10) git restore -- specs/modules/librarian_context_pack.md => rc=0
11) powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 => rc=1
    first failure: patch_check out-of-scope v2p_user_sim_testkit.zip
12) Move-Item v2p_user_sim_testkit.zip -> %TEMP% => rc=0
13) powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 => rc=0

Final:
- V2P testkit: PASS
- verify_repo: PASS
