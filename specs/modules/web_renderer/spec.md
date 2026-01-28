
# Web Renderer（Cytoscape）

## Purpose
渲染 typed graph，支持布局、缩放、拖拽、过滤、选择、边编辑，并通过 QWebChannel 与 C++ 通信。

## Inputs
- graph.json（nodes/edges）
- UI state（filters, currentRun）

## Outputs
- 用户交互事件：nodeSelected/edgeSelected/editEdge

## Process
- layout：默认 cose/fcose
- phase：使用 compound nodes 或 parent 字段
- style：按 type/statusFlags 映射样式（Doc/Module/Contract/Gate/Run）

## Acceptance Criteria
- Given graph.json
- When render
- Then 用户能缩放拖拽并点击查看详情


## Trace Links
- docs/11_webengine_resources.md
- specs/contract_output/graph.schema.json
- docs/05_navigation.md
