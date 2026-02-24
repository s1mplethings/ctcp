
# Quickstart（最短路径）

1) 编译运行本 GUI（QtWebEngine + WebChannel）
2) Open Project 选择你的 SDDAI 工程根目录
3) 看到图：Pipeline View（按 phase 分块）/ Contract View（以协议为中心）
4) 点节点/边看详情与协议标签
5) 编辑边（produces/consumes/verifies）→ 写回 meta/pipeline_graph.json
6) 跑 verify：
   - Linux/macOS：`bash scripts/verify_repo.sh`
   - Windows：`powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`

Auto loop（给 AI 代理用）：Discover → Plan → Patch → Verify → Record → Report


## WebEngine 资源加载
- 推荐用 QRC：把 web/ 打包进 .qrc，然后用 `qrc:/web/index.html` 加载。
- 详见：docs/11_webengine_resources.md

## 排障（页面找不到）
- 在 C++ 中先检查：`QFile(":/web/index.html").exists()` 必须为 true
- 再用：`view->load(QUrl("qrc:/web/index.html"))`
- 如果你误配置成 `:/web/web/index.html`，见 docs/11_webengine_resources.md
