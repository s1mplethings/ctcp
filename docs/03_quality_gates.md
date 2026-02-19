# Quality Gates (DoD)

本仓库的“合格交付”主判定方式：`scripts/verify.*` 通过（证据 gate）。
`scripts/verify_repo.*` 仍用于 workflow/contract/doc-index 的基础门禁。

“没证据=没测试”硬规则：
- 必须生成 `artifacts/verify/<timestamp>/proof.json` 与步骤日志。
- 必须通过 `tools/adlc_gate.py`。
- `proof.result != PASS` 或日志缺失 -> 直接 fail。

verify_repo 必须保证：

1) headless lite path (default)
- `CTCP_ENABLE_GUI=OFF` build path (if cmake exists)
- lite ctest set
- lite replay scenario(s)

2) workflow gate
- meta/tasks/CURRENT.md 存在
- ai_context/00_AI_CONTRACT.md 存在
- ai_context/templates/aidoc 存在
- 默认禁止代码：未授权时不允许改代码目录

3) contract checks
- scripts/contract_checks.py 通过

4) doc index check
- scripts/sync_doc_links.py --check 通过

5) full checks（可选）
- `CTCP_FULL_GATE=1` 时才跑更重测试（如 GUI 相关）

附加约束（forge full suite preflight）：
- 入口脚本必须存在：`tools/checks/suite_gate.py`
- live suite 清单必须存在：`tests/fixtures/adlc_forge_full_bundle/suites/forge_full_suite.live.yaml`
- 若入口缺失，必须在预检中给出明确缺失路径，避免误判为功能通过

如果你发现 verify_repo 没覆盖到某类失败，就把它补进 verify_repo，并新增一个 tests/cases 用例。

证据闭环工具：
- `tools/run_verify.py`
- `tools/adlc_gate.py`
- `tools/contrast_proof.py`
