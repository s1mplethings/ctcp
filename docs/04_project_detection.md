
# Project Detection（工程识别规则）

本 GUI 的核心能力之一是：用户选择一个目录后，自动识别该目录是否为“SDDAI 工程根”，并定位：
- docs_root / specs_root / scripts_root / ai_context_root / runs_root

为了保证“识别稳定”，采用 **Marker 优先 + Heuristic 兜底 + 人工选择回填 Marker** 三段式。

## 1) Marker 优先（强推荐）
若在候选根目录存在以下任一文件，视为命中 Marker：
- `meta/sddai_project.json`
- `.sddai/project.json`
- `sddai.project.json`

命中后：直接按 Marker 中的路径定位各 root（相对路径以 Marker 文件所在目录为基准）。

### Marker 文件最小示例
```json
{
  "schema_version": "1.0.0",
  "project_type": "SDDAI",
  "docs_root": "docs",
  "specs_root": "specs",
  "scripts_root": "scripts",
  "ai_context_root": "ai_context",
  "runs_root": "runs"
}
```

## 2) Heuristic 兜底（无 Marker 时）
### 2.1 候选 docs_root 规则
按优先级匹配：
1) `<root>/docs/` 且包含：`00_overview.md` 或 `02_workflow.md`
2) `<root>/` 直接包含：`00_overview.md` 或 `02_workflow.md`（允许 docs 不在子目录）
3) `<root>/docs/` 存在但不含上述文件：视为弱命中（给 warning）

### 2.2 候选 specs_root 规则
按优先级匹配：
1) `<root>/specs/` 且包含：`modules/` 或 `contract_output/`
2) `<root>/spec/`（兼容旧命名，弱命中）
3) 未找到：允许仅文档模式（Doc-only），但必须强提示“无法构建协议边/模块边”

### 2.3 scripts_root / ai_context_root / runs_root
- scripts_root：优先 `<root>/scripts/` 且存在 `verify.ps1` 或 `verify.sh`
- ai_context_root：优先 `<root>/ai_context/` 且存在 `problem_registry.md` 或 `decision_log.md`
- runs_root：优先 `<root>/runs/`（可缺省）

## 3) 评分与多候选选择
若存在多个候选根（例如用户选了上级目录），对每个子目录评分：
- +10：命中 Marker
- +4：docs_root 命中（规则 1 或 2）
- +4：specs_root 强命中（specs + modules/contract_output）
- +2：scripts_root 命中（verify.* 存在）
- +2：ai_context_root 命中（problem_registry/decision_log 存在）
- +1：runs_root 存在

选择得分最高者作为 project_root；若最高分 < 6：判定识别失败，进入人工选择。

## 4) 人工选择与回填 Marker（强烈建议实现）
当识别失败或用户想覆盖时：
- GUI 提供“选择 docs_root/specs_root…”对话框
- 用户确认后，生成 `meta/sddai_project.json` 写入该工程根（或写到本 GUI 的 workspace）
- 下次打开可 100% 稳定识别

## 5) 错误输出要求（便于排障）
ProjectScanner 必须输出：
- candidates 列表（路径 + 得分 + 命中原因）
- warnings（缺少哪些关键目录/文件）
- chosen_root 与定位结果
