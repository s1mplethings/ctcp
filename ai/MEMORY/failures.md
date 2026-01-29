# 常见失败（failures）
## 1) patch 无法应用
- 可能原因：目标仓库已有同名文件/目录；或路径不同
- 解决：用 tokens 映射；或把 recipe 拆成模板+锚点插入

## 2) Qt WebChannel 不工作
- 可能原因：未注册 QWebChannel；对象名不一致（GraphBridge/bridge）
- 解决：统一桥接对象名，或在 web 端做多名字兼容

## 3) 渲染慢/卡顿
- 可能原因：O(n^2) 力导向；每帧全量重绘；节点过多
- 解决：阈值降级（只画局部/抽样）；分层缓存；worker 并行预计算
