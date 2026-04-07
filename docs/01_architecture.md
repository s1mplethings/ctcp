
# 架构

> Deprecated: legacy GUI-lane documentation retained for historical context only.
> CTCP no longer ships a repo GUI target; use `README.md`, `BUILD.md`, and `docs/00_CORE.md` for active build/runtime guidance.

## 总体：C++ 后端 + Web 图渲染
- C++（Qt Widgets）负责：扫描工程、解析 spec/contract、构图、读取 runs、写回 meta
- Web（Cytoscape.js）负责：布局、缩放、拖拽、选择、过滤、边编辑交互

两端通过 **QWebChannel** 通信：
- JS 调 C++：openProject / requestGraph / requestNodeDetail / editEdge / openFile
- C++ 推送 JS：graphChanged / runProgressChanged / toast

## 组件分层
### Core（C++）
- ProjectScanner：识别 docs/specs/scripts/ai_context/runs 根
- FileIndexer：索引与监听变更（QFileSystemWatcher）
- MarkdownLiteParser：轻量抽取 links/sections（不做全 AST）
- SpecExtractor：从 spec.md 抽 Inputs/Outputs/AC/Trace Links
- SchemaLoader：读取 contract schema（*.schema.json）
- MetaStore：读写 meta/pipeline_graph.json（权威关系层）
- GraphBuilder：合并自动推导 + meta 覆盖，输出 Graph JSON
- RunLoader：读取 runs（MVP：文件存在性推断；增强：events.jsonl）
- Bridge（QWebChannel）：对外提供 API，推送更新

### UI（Qt Widgets）
- Explorer：Docs/Modules/Contracts/Gates/Runs 列表 + 搜索
- GraphView：QWebEngineView（加载 web/index.html）
- Inspector：显示节点/边详情 + 编辑 produces/consumes/verifies
- Progress/Logs：静态 coverage + run timeline + verify 结果摘要

### Web（Cytoscape）
- 接收 Graph JSON → 渲染 nodes/edges
- 按 phase 分组（compound nodes 或 parent 字段）
- 以 type/statusFlags 映射样式
- 边编辑：add/remove/update → 调 C++ editEdge → 写回 meta → 刷新

## 数据流
1) openProject(root) → 扫描并索引文件
2) 解析 specs/contract_output → Contract nodes
3) 解析 specs/modules → Module nodes（IO/Trace Links）
4) 解析 docs links/workflow → phases（辅助）
5) 合并 meta/pipeline_graph.json → 覆盖/修正边
6) 输出 Graph JSON → 前端渲染
7) 读取 runs → 生成 run_touches 边与状态叠加


## 工程识别（ProjectScanner）
- Marker 优先：`meta/sddai_project.json` / `.sddai/project.json` / `sddai.project.json`
- Heuristic + 评分选根：见 docs/04_project_detection.md

## Trace Links
- docs/06_graph_map.md
- docs/12_modules_index.md
- docs/13_contracts_index.md

## Front Gateway Overlay（Nanobot 风格前台）

新增 Front Gateway 仅作为“对话壳层”，不替代 CTCP ADLC 核心：

- Bridge：`scripts/ctcp_front_bridge.py` + `scripts/ctcp_front_api.py`
  - 只允许调用受限桥接 API（new-run/status/advance/report/decision/upload）。
  - 执行入口仍是 `scripts/ctcp_orchestrate.py`。
  - 验收入口仍是 `scripts/verify_repo.ps1` / `scripts/verify_repo.sh`。
- Frontend Gateway：`web/frontend_gateway/*`
  - 负责会话管理、消息归一化、进度口径翻译、决策提问路由。
  - 会话记忆与工程事实分离：工程事实必须回读 run artifacts。

契约见：
- `docs/architecture/contracts/frontend_bridge_contract.md`
- `docs/architecture/contracts/frontend_session_contract.md`

