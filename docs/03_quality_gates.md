# Quality Gates (DoD)

本仓库的“合格交付”主判定方式：`scripts/verify.*` 通过（证据 gate）。
`scripts/verify_repo.*` 仍用于 workflow/contract/doc-index 的基础门禁。

“没证据=没测试”硬规则：
- 必须生成 `artifacts/verify/<timestamp>/proof.json` 与步骤日志。
- 必须通过 `tools/adlc_gate.py`。
- `proof.result != PASS` 或日志缺失 -> 直接 fail。

verify_repo 必须保证：

1) workflow gate
- meta/tasks/CURRENT.md 存在
- ai_context/00_AI_CONTRACT.md 存在
- ai_context/templates/aidoc 存在
- 默认禁止代码：未授权时不允许改代码目录

2) contract checks
- scripts/contract_checks.py 通过

3) doc index check
- scripts/sync_doc_links.py --check 通过

4) tests
- scripts/test_all.* 通过（当前为流程一致性测试 + case 结构检查）

如果你发现 verify_repo 没覆盖到某类失败，就把它补进 verify_repo，并新增一个 tests/cases 用例。

证据闭环工具：
- `tools/run_verify.py`
- `tools/adlc_gate.py`
- `tools/contrast_proof.py`
