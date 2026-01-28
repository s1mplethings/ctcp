
# SDDAI GUI (QtWebEngine + Cytoscape) 总览

## 目标
做一个 C++ 桌面 GUI：打开一个工程目录后，自动识别 SDDAI 文档/规范结构，生成一张“流程 + 协议 + 进度”的交互式图。

你可以：
- 看到所有流程（按阶段分块）
- 看到模块之间通过哪些协议/产物（Contract）连接
- 看到进度/卡点（静态覆盖率 + 运行时 run）
- 在 GUI 上编辑关系（produces/consumes/verifies），写回 `meta/pipeline_graph.json`

## 非目标（本包不覆盖）
- 不包含 RAG 功能
- 不包含实时录制（stream_monitor）实现与可视化
- 不做富文本 Markdown 编辑器（先做“打开文件 + 关系编辑 + 图渲染”）

## 目录结构
- `docs/`：总文档与流程/质量门（与 SDDAI 同编号风格）
- `specs/modules/`：每个模块一个 spec（Purpose / IO / Process / AC / Trace）
- `specs/contract_output/`：Graph/Meta/RunEvents 等输出协议 schema
- `meta/`：权威关系文件（GUI 编辑写回）
- `scripts/`：verify 入口（sh/ps1）与 contract checks
- `ai_context/`：问题记忆、决策记录、任务卡模板
- `web/`：前端资源占位（Cytoscape + app.js + index.html）
- `resources/`：Qt 资源占位（建议用 .qrc 打包 web 资源）

## 关键概念
- **Module**：功能模块（ProjectScanner / GraphBuilder / RunLoader / Bridge…）
- **Contract**：模块间协议（Graph JSON、Meta JSON、Events JSONL…）
- **Gate**：质量门（lint/unit/integration/contract/golden）
- **Run**：一次运行的进度与产物（可由目录推断或由 events.jsonl 精确驱动）

## verify（语义单入口 + OS 实现）
- Linux/macOS：`bash scripts/verify.sh`
- Windows：`powershell -ExecutionPolicy Bypass -File scripts/verify.ps1`


## 工程识别（建议）
- 建议在目标工程根添加 Marker：`meta/sddai_project.json`
- 识别规则详见：docs/04_project_detection.md

## Navigation
- 入口索引：docs/05_navigation.md
- 图示：docs/06_graph_map.md
- 模块索引：docs/12_modules_index.md
- 协议索引：docs/13_contracts_index.md

- [05_navigation.md](05_navigation.md)
- [06_graph_map.md](06_graph_map.md)
- [12_modules_index.md](12_modules_index.md)
- [13_contracts_index.md](13_contracts_index.md)

- 布局与视图硬规则：docs/07_layout_and_views.md
- 性能硬规则：docs/15_performance_rules.md
