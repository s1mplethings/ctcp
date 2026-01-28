
# GraphBuilder

## Purpose
把 docs/specs/meta/runs 合成 typed graph，并输出给前端渲染的 Graph JSON。

## Inputs
- indexed_files（来自 FileIndexer）
- module_specs（SpecExtractor 的抽取结果）
- contract_schemas（SchemaLoader 的抽取结果）
- meta_graph（MetaStore 读入）
- run_state（RunLoader 读入，可为空）

## Outputs
- graph.json（见 contract_output/graph.schema.json）

## Process（合并策略）
1) 自动推导：从 module spec 的 IO/Trace Links 与 contract schema 推导 produces/consumes/verifies
2) 读取 meta：对 edges 做覆盖/补充（manual 优先）
3) phase 分组：优先 meta 的 phase，缺失则按 workflow/architecture 推测
4) statusFlags：覆盖率与 run_state 叠加到 node/edge

## Acceptance Criteria
- Given 一个包含 docs/specs/meta 的工程
- When buildGraph()
- Then 输出 graph.json 通过 schema 校验，且 nodes/edges 数量 > 0

## Trace Links
- specs/contract_output/graph.schema.json
- meta/pipeline_graph.json
- docs/06_graph_map.md
- docs/12_modules_index.md
- docs/05_navigation.md

## Layout Contract（必须）
- GraphBuilder 输出的 graph.json 允许携带 node.position（x,y）
- Pipeline View 默认 layout = preset（不允许默认跑力导向）
- Phase 分组：node.parent = phaseId（compound nodes）


## Summary View（默认启动）
GraphBuilder 必须支持生成 Summary 图：
- nodes：category 节点（Docs/Modules/Contracts/Meta/Runs/Gates） + pinned core nodes（可选）
- edges：聚合边 aggregate=true，weight=汇总的真实边数量
- positions：使用固定网格（preset），保证不可能叠在一起
- 点击 category 节点后，再按 view 生成对应 detail 子图

## Mutable / Tier
- tier=core + mutable=true：默认进入 Summary（pinned=true 或属于核心集合）
- tier=settings + mutable=false：默认不进入 Summary，仅在侧库或预览中出现
