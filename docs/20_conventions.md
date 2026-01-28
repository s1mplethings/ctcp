
# Conventions（约定）

- 小步提交、小步改动；任何 API/Contract 变化必须更新 specs 与 tests
- 关系编辑的权威落盘：只写 `meta/pipeline_graph.json`（不要直接让工具乱改 md）
- 自动化必须走 verify（语义入口），OS 对应实现脚本
- 文件写入建议原子写（tmp + rename）
- 遇到坑必须记录：`ai_context/problem_registry.md`；临时豁免必须记录：`ai_context/decision_log.md`
