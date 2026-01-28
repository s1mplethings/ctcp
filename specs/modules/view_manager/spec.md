
# ViewManager（Summary / Drill-down / Breadcrumb）

## Purpose
把“开始只显示大类（Summary）→ 点击进入细节（Drill-down）→ 返回（Breadcrumb）”写成确定行为。
目标：**默认不加载全量节点**，保证永远不会一上来挤成一团、也不会卡。

## Views
- Summary（默认启动）
- Pipeline（Phase + Module + Contract）
- Docs（Doc + docs_link）
- Contracts（Contract + Producer/Consumer）

## State Model
- current_view: "Summary" | "Pipeline" | "Docs" | "Contracts"
- focus_node_id: string | null     # Drill-down 的入口（例如 category.Modules）
- breadcrumb: [{view, focus_node_id, label}]

## API（C++ ↔ JS）
- requestGraph(view, focusNodeId=null)
- drillDown(nodeId)
- goBack()
- setDefaultView(view)

## Drill-down Rules
- Summary 下点击 category 节点：
  - category.Docs      -> Docs view (focus=category.Docs)
  - category.Modules   -> Pipeline view (focus=category.Modules)
  - category.Contracts -> Contracts view (focus=category.Contracts)
  - category.Meta/Runs/Gates -> 可选子图（先占位）

## Mutable / Tier Rules
- mutable=true 的节点：Inspector 显示更多动作（编辑/展开/保存布局）
- mutable=false 的节点：只读预览（打开/复制路径）

## Acceptance Criteria
- 打开项目默认显示 Summary（≤ 12 个节点）
- 点击 Modules 才加载 modules 子图（不允许启动全量加载）
- goBack 必须回到 Summary（或上一级 breadcrumb）

## Trace Links
- docs/07_layout_and_views.md
- docs/08_summary_drilldown.md
- meta/pipeline_graph.json (ui.default_view / ui.summary)
