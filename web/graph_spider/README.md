# Spider Web Graph (Canvas)

这个目录提供一个“蛛网/Obsidian 风格”的关系网可视化页面（纯原生 Canvas + JS，无第三方依赖）。

- 入口：`web/graph_spider/index.html`
- 特性：缩放/平移、拖拽节点、点击选择、右侧信息面板、搜索与聚焦、可选 QWebChannel 集成
- 如果没有 Qt Bridge，会自动加载 `demo_graph.json` 作为预览数据。

## Qt (可选) Bridge 约定

页面会尝试通过 QWebChannel 找到对象：`bridge` / `sddai` / `app` 其一。

推荐实现（任选其一）：

1) **拉取模式**：提供 slot `getGraphJson() -> QString`，返回完整 JSON 字符串  
2) **推送模式**：提供 signal `graphJson(QString)` 或 `graphJsonChanged(QString)`，页面收到后刷新  
3) **请求模式**：提供 slot `requestGraph()`，并配合推送模式 signal 回传

节点点击打开（可选）：

- `openNode(QString id)` 或 `openPath(QString path)`

## JSON 格式

```json
{
  "nodes":[{"id":"A","label":"xxx","path":"...","group":"...","r":4,"meta":{}}],
  "links":[{"source":"A","target":"B","w":1.0}]
}
```
