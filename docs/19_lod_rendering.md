# Line Drawing & Display Optimization（画线与显示优化，不影响性能）

目标：线/标签太多时不“堆成一坨”、不卡、还能看清结构。

## 规则（默认启用）
### 1) Focus-Edges（边过多自动开启）
- 当当前视图（非 Summary）边数量 > **420**：自动开启
- 开启后：默认隐藏全部边；点击某节点后，仅显示与该节点相连的边（connectedEdges）
- 目的：把渲染复杂度从 **O(E)** 降到 **O(deg(v))**

### 2) 缩放隐藏边（LOD）
- zoom < **0.38**：隐藏全部边（edgeHiddenZoom）
- zoom 回来恢复

### 3) 缩放隐藏标签（LOD）
- zoom < **0.28**：隐藏全部 node label（labelHidden）

## 快捷键
- `H`：手动切换 Focus-Edges 开关
