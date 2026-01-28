# Visual Rules（硬性规定：别挤、别乱、别难看）

## 1) 默认只画 Summary（大类）
- 启动 view = Summary
- Summary 只允许：Category + pinned 节点（<= 12）
- Summary edges：只允许 aggregate（极少）或为空
- Summary layout：固定网格 preset（绝不使用力导向）

## 2) Label 规则（必须）
- node.label 必须是短文本（<= 18 字符）
- 完整文本放到：node.fullLabel
- path/括号内容不允许出现在 label 里（避免 UI 爆炸）
- 边默认不显示 label（edge.label = ""）

## 3) 视图切换（钻取）
- 双击 Category：drillDown 进入子图
- 子图默认也用 preset（positions 来自 LayoutEngine/meta.positions）
- 返回 Summary：由 ViewManager 控制

## 4) 样式规则（可改但默认要好看）
- 背景深色，文字高对比
- Node 支持 wrap + max width
- Selected 高亮边框
