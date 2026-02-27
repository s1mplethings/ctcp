# Acceptance Checklist

PASS if all true:
1) CTCP `verify_repo.ps1` passes.
2) `cos-user-v2p --fixture-mode synth` records:
   - run_dir/artifacts/fixture_meta.json
   - USER_SIM_PLAN.md mentions fixture selection
3) Unit test `test_v2p_fixture_discovery` passes.
4) Templates and manifest exclude `.pytest_cache` / `__pycache__` / out/ / fixture/.
5) Generated project has scripts/clean_project.py and its test passes.
