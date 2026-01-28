
# Performance Rules（必须遵守）

1) 后台线程：扫描/解析/构图全部在 worker thread；UI 线程不做重活
2) Cytoscape 只初始化一次：更新用 batch，不允许每次 new
3) 默认 preset：不跑力导向；positions 写回 meta 并复用
4) 默认只显示 Pipeline View：Docs View 单独切换，避免节点爆炸
