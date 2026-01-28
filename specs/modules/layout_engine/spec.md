
# LayoutEngine（Block Layout / Preset Positions）

## Purpose
为 Pipeline View 生成**稳定、可复现、不卡**的布局坐标：
- 先把图按 Phase 分块（块与块之间固定间距）
- 块内按“类型固定顺序 A”排布（不做力导向）
- 输出 positions，前端用 `preset` 直接渲染（不跑 cose/fcose）

## Inputs
- phases[]（来自 meta/pipeline_graph.json 或推断）
- nodes[]（GraphBuilder 的 nodes，包含 type / phase / parent）
- edges[]（用于可选的轻量排序，不做迭代布局）
- layout_config

### layout_config（建议默认）
- phase_order: ["Docs","Core","UI","Web","Contracts","Unassigned"]
- phase_gap_x: 700
- phase_origin: {x: 0, y: 0}
- block_padding: {x: 80, y: 80}
- type_rows: ["Doc","Module","Contract","Gate","Run"]   # **A：类型固定顺序**
- row_gap_y: 120
- col_gap_x: 220
- max_cols_per_row: 6
- node_size_hint: {w: 180, h: 60}

## Outputs
- positions: map[nodeId] -> {x,y}
- phase_boxes: map[phaseId] -> {x,y,w,h}

## Algorithm（A：类型固定顺序）
1) Phase 分组：每个 node 必须落到一个 phase（缺失 → Unassigned）
2) Phase 排列：按 phase_order 从左到右排列，每个 phase 一个大块
3) 块内按 type_rows 分行（Doc 在上，Module 其次，Contract 再其次）
4) 行内从左到右铺开，超 max_cols_per_row 换行
5) positions 写回 meta/pipeline_graph.json -> positions
6) 二次打开：优先使用缓存 positions（≥ 90% 覆盖）

## Acceptance Criteria
- 打开 Pipeline View：Phase 块必须肉眼分离（不允许混在一起）
- 块内必须按 type_rows 成行
- 默认不允许跑 cose/fcose（仅可作为手动按钮）
- 100 节点级别：首次 < 1s；二次打开（有 positions）< 200ms（目标）

## Trace Links
- docs/07_layout_and_views.md
- meta/pipeline_graph.json
- specs/contract_output/graph.schema.json
