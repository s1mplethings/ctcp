# Report Archive - 2026-03-16 - Telegram 测试到项目生成 smoke 联通与启动检查

## Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/03_quality_gates.md`
- `docs/10_team_mode.md`
- `docs/40_reference_project.md`
- `PATCH_README.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`
- `.agents/skills/ctcp-failure-bundle/SKILL.md`

## Plan

1. Bind a Telegram-to-project-generation smoke task.
2. Run support selftest and a local project-intake smoke through `--stdin`.
3. Inspect the bound run gate state and record the first project-advance blocker.
4. Generate a live-reference scaffold project outside the repo and verify the generated project.
5. Attempt a real Telegram long-poll startup with the narrowest safe allowlist and record the first live blocker.
6. Run canonical verify and close with evidence only.

## Changes

- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260316-telegram-to-project-generation-smoke.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260316-telegram-to-project-generation-smoke.md`

## Verify

- `python (Telegram API getMe with user-provided token)` -> `0` (`ok=true`, `username=my_t2e5s9t_bot`)
- `python (Telegram API getUpdates with user-provided token)` -> `0` (`ok=true`, `count=0`)
- `python scripts/ctcp_support_bot.py --selftest` -> `0`
- `@'...project request...'@ | python scripts/ctcp_support_bot.py --stdin --chat-id local-telegram-smoke` -> `0`
- `python scripts/ctcp_orchestrate.py status --run-dir C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260316-134016-895506-orchestrate` -> `0`
- `python scripts/ctcp_orchestrate.py advance --run-dir C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260316-134016-895506-orchestrate --max-steps 8` -> `0` (`blocked: contract_guard failed`)
- `python scripts/ctcp_orchestrate.py scaffold --out D:\.c_projects\adc\generated_projects\telegram-smoke-20260316 --name telegram-smoke-20260316 --profile minimal --source-mode live-reference --force --runs-root C:\Users\sunom\AppData\Local\ctcp\runs` -> `0`
- `powershell -ExecutionPolicy Bypass -File D:\.c_projects\adc\generated_projects\telegram-smoke-20260316\scripts\verify_repo.ps1` -> `0`
- `python launcher -> python scripts/ctcp_support_bot.py telegram --poll-seconds 2 --allowlist 6092527664` -> `0` (`PID=37404`)
- `Get-CimInstance Win32_Process ... ctcp_support_bot.py telegram` -> `0` (`process alive`)
- `telegram_support_bot.stderr.log` -> `empty`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1` (`workflow gate: LAST.md missing mandatory workflow evidence`)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1` (`lite scenario replay`)
- first failure point:
  - gate: `lite scenario replay`
  - run_dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260316-153942`
  - summary: `passed=12`, `failed=2`
  - failed scenarios:
    - `S15_lite_fail_produces_bundle`: missing expected text `failure_bundle.zip`
    - `S16_lite_fixer_loop_pass`: missing expected text `"result": "PASS"`
- minimal fix strategy:
  - open a separate SimLab-only repair task scoped first to `S15_lite_fail_produces_bundle`
  - realign the fixer prompt / failure-bundle reference path so the outbox prompt still surfaces `failure_bundle.zip`
  - rerun canonical verify after the `S15` repair to confirm whether `S16` still fails independently
- triplet command references:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`

## Demo

- selftest run: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\support_sessions\selftest-1773639578`
- local support session: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\support_sessions\local-telegram-smoke`
- bound project run: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260316-134016-895506-orchestrate`
- external scaffold run: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260316-134602-734340-scaffold-telegram-smoke-20260316`
- generated project: `D:\.c_projects\adc\generated_projects\telegram-smoke-20260316`
- Telegram live stderr: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\telegram_bot_runtime\telegram_support_bot.stderr.log`
- Telegram live process: `PID 37404`
- final verify summary: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260316-153942\summary.json`
- first failing trace: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260316-153942\S15_lite_fail_produces_bundle\TRACE.md`
- second failing trace: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260316-153942\S16_lite_fixer_loop_pass\TRACE.md`

## Questions

- The running bot is currently allowlisted only for chat id `6092527664`. If that is not your testing account, I need your Telegram numeric chat id to narrow the allowlist correctly.
