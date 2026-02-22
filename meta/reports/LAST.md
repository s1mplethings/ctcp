# Demo Report - LAST

## Goal
- 验证：是否可以通过 `librarian` 的尽量少输入，让 `api_agent` 输出 `PLAN.md` 与 `diff.patch`。
- 给出最小可行输入（MVP）和边界行为（何时 librarian 失败/跳过仍会发生什么）。

## Readlist
- `ai_context/00_AI_CONTRACT.md`
  - 约束：最小改动、patch-first。
- `README.md`
  - 约束：仓库基础门禁入口为 `scripts/verify_repo.*`。
- `BUILD.md`
  - 约束：默认 headless/lite 构建路径。
- `PATCH_README.md`
  - 约束：验证输出必须进入 `meta/reports/LAST.md`。
- `TREE.md`
  - 约束：docs/spec/meta 审计路径可追踪。
- `docs/03_quality_gates.md`
  - 约束：workflow/contract/doc-index/tests 统一由 `verify_repo` 把关。
- `ai_context/problem_registry.md`
  - 约束：无证据不算验证。
- `ai_context/decision_log.md`
  - 约束：无 gate 绕过（本次无）。
- `scripts/ctcp_orchestrate.py`
  - 观察：`current_gate` 在 `context_pack.json` 不存在时阻塞于 librarian gate。
- `scripts/ctcp_dispatch.py`
  - 观察：`PatchMaker` 可直接分发到 `api_agent`。
- `tools/providers/api_agent.py`
  - 观察：`api_agent` 构造上下文时使用 `local_librarian.search`，不直接读取 `artifacts/context_pack.json`。

## Plan
1) Docs/Spec：更新 `meta/tasks/CURRENT.md` 为“最小输入驱动”专项。  
2) Implement：执行最小输入矩阵（3 个最小输入 + 2 个边界/对照）并记录 gate 前后状态。  
3) Verify：运行 `scripts/verify_repo.ps1`。  
4) Report：回填 `meta/reports/LAST.md` 与 JSON 证据路径。

## Changes
- `meta/tasks/CURRENT.md`
  - 切换为 `librarian-min-input-drives-apiagent`，DoD/Acceptance 完成勾选。
- `meta/reports/librarian_min_input_apiagent_eval.json`
  - 新增最小输入链路评测证据（cases/stability/stub requests）。
- `meta/reports/LAST.md`
  - 更新为本次最小输入驱动专项闭环报告。

## Verify
- 专项评测（最小输入矩阵）
  - Command:
    - `python -`（内联脚本；构造 run_dir，执行 `ctcp_orchestrate.current_gate` + `ctcp_dispatch.dispatch_once`，并用本地 HTTP stub 提供 OpenAI responses）
  - Cases:
    - `min_snippet`: `needs` 仅 1 个 snippet（1 行）
    - `empty_needs`: `needs=[]`
    - `tiny_budget`: `max_total_bytes=1`（触发 `too_large`）
    - `invalid_schema`: schema 错误（librarian 失败边界）
    - `control_skip_librarian`: 跳过 librarian（对照）
  - Key Output:
    - `min_snippet`: librarian `executed`, api_agent `executed`, patch exists
    - `empty_needs`: librarian `executed`, api_agent `executed`, patch exists
    - `tiny_budget`: librarian `executed`, api_agent `executed`, patch exists
    - `invalid_schema`: librarian `exec_failed`, api_agent `executed`
    - `control_skip_librarian`: librarian `skipped`, api_agent `executed`
    - MVP input:
      - `case_id=empty_needs`
      - `file_request_bytes=168`
      - `context_pack_summary=included=0 omitted=0 used_bytes=0 budget_files=1 budget_bytes=64`
    - Stability:
      - `runs=10`, `ok_runs=10`, `unique_patch_hashes=1`, `stable=true`
    - Stub evidence:
      - `/v1/responses` 被调用，plan/patch 均有请求，且携带 `Authorization` header
  - Artifact:
    - `meta/reports/librarian_min_input_apiagent_eval.json`

- 仓库唯一验收入口
  - Command:
    - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - Key Output:
    - `ctest lite`: `100% tests passed, 0 tests failed out of 2`
    - `workflow_checks`: `ok`
    - `contract_checks`: `ok`
    - `sync_doc_links --check`: `ok`
    - `lite scenario replay`: `passed=9, failed=0`
    - `python unit tests`: `Ran 36 tests ... OK`
  - Final Result:
    - `verify_repo` 全链路通过，`[verify_repo] OK`。

## Questions
- None.

## Demo
- Report: `meta/reports/LAST.md`
- Eval Artifact: `meta/reports/librarian_min_input_apiagent_eval.json`
- Run Pointer: `meta/run_pointers/LAST_RUN.txt`
- External TRACE: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260221-120322-prompt-source-probe\TRACE.md`
