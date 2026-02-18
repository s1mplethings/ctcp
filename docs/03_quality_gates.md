
# 质量门（Quality Gates）

## Gate 顺序（推荐）
1) lint
2) unit
3) integration
4) contract checks
5) golden（可选）

## 强制要求
- integration 必跑（至少覆盖：打开工程 → 构图 → 输出 Graph JSON）
- contract checks 必跑（至少覆盖：Graph JSON / Meta JSON / Events JSONL 的 schema 约束）

## 单一入口（语义）
- 语义入口：verify
- 实现：
  - Linux/macOS：`bash scripts/verify_repo.sh`
  - Windows：`powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`

## 失败处理
- gate 失败：记录到 `ai_context/problem_registry.md`（含复现命令 + 关键日志）
- 临时跳过：记录到 `ai_context/decision_log.md`（含原因 + 回补计划）

## Trace Links
- docs/13_contracts_index.md
- specs/contract_output/graph.schema.json
- specs/contract_output/meta_pipeline_graph.schema.json
- specs/contract_output/run_events.schema.json
