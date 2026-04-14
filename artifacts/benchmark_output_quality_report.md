# Benchmark Output Quality Report

## 1. 任务列表

- `landing_page_showcase` | 落地页 / 单页展示站
  - 原始需求: 做一个中文单页落地页，介绍 CTCP 的目标、工作流和交付方式。页面要有 hero、功能区、FAQ、联系 CTA，适合直接展示。
- `tool_form_planner` | 小型工具页 / 表单交互页
  - 原始需求: 做一个中文小工具页，输入活动预算、人数和场地类型，输出简化方案与采购清单。页面至少要有表单、结果区和重置按钮。
- `upload_process_export_app` | 带上传 / 处理 / 导出的轻应用
  - 原始需求: 做一个本地轻应用，支持上传 CSV，按类别汇总金额并导出结果 JSON/CSV。页面要能上传、查看汇总、导出。
- `vague_narrative_copilot` | 模糊需求任务
  - 原始需求: 我想要生成一个可以帮助创作者制作叙事项目的助手。它重点服务悬疑 / 解谜 / 猎奇风格。它需要能帮助用户梳理故事线、角色关系、章节结构、分支结局，还能生成角色立绘、表情、背景、CG 的提示词，最后输出成可以继续用于叙事制作的结构化内容。
- `likely_fail_multimodal_assistant` | 当前系统最容易失败的任务
  - 原始需求: 做一个本地可运行的创作助手 MVP，最好把剧情树、角色关系、参考图、语音分镜、导出包都串起来，还要能给我一个可展示的界面和最终交付包。

## 2. 运行结果总表

| task_name | run_id | intent | spec | smoke | screenshot | package | delivery | verify | first_failure_stage | short_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| landing_page_showcase | 20260413-015547-257570-orchestrate | PASS | FAIL | PASS | PASS | FAIL | FAIL | FAIL | Spec | structural gate: source_generation status must be pass |
| landing_page_showcase | 20260413-020000-477634-orchestrate | PASS | FAIL | PASS | PASS | FAIL | FAIL | FAIL | Spec | structural gate: source_generation status must be pass |
| landing_page_showcase | 20260413-020315-688447-orchestrate | PASS | FAIL | PASS | PASS | FAIL | FAIL | FAIL | Spec | structural gate: source_generation status must be pass |
| tool_form_planner | 20260413-020646-284141-orchestrate | PASS | PASS | PASS | PASS | PASS | PASS | PASS | none | all_pass |
| tool_form_planner | 20260413-021012-927452-orchestrate | PASS | PASS | PASS | PASS | PASS | PASS | PASS | none | all_pass |
| tool_form_planner | 20260413-021310-779020-orchestrate | PASS | PASS | PASS | PASS | PASS | PASS | PASS | none | all_pass |
| upload_process_export_app | 20260413-021528-807228-orchestrate | PASS | FAIL | PASS | PASS | FAIL | FAIL | FAIL | Spec | structural gate: source_generation status must be pass |
| upload_process_export_app | 20260413-021848-241776-orchestrate | PASS | FAIL | PASS | PASS | FAIL | FAIL | FAIL | Spec | structural gate: source_generation status must be pass |
| upload_process_export_app | 20260413-022142-068870-orchestrate | PASS | FAIL | PASS | PASS | FAIL | FAIL | FAIL | Spec | structural gate: source_generation status must be pass |
| vague_narrative_copilot | 20260413-022444-495352-orchestrate | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | Screenshot | screenshot missing or low-value: none |
| vague_narrative_copilot | 20260413-022721-930012-orchestrate | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | Screenshot | screenshot missing or low-value: none |
| vague_narrative_copilot | 20260413-023000-451536-orchestrate | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | Screenshot | screenshot missing or low-value: none |
| likely_fail_multimodal_assistant | 20260413-023218-120367-orchestrate | PASS | PASS | PASS | PASS | PASS | PASS | PASS | none | all_pass |
| likely_fail_multimodal_assistant | 20260413-023404-798755-orchestrate | PASS | PASS | PASS | PASS | PASS | PASS | PASS | none | all_pass |
| likely_fail_multimodal_assistant | 20260413-023850-481702-orchestrate | PASS | PASS | PASS | PASS | PASS | PASS | PASS | none | all_pass |

## 3. 聚合统计

- Intent: `15/15 (100.0%)`
- Spec: `9/15 (60.0%)`
- Smoke: `15/15 (100.0%)`
- Screenshot: `12/15 (80.0%)`
- Package: `9/15 (60.0%)`
- Delivery: `9/15 (60.0%)`
- Verify: `9/15 (60.0%)`
- 最常见首个失败层: `Spec`

## 4. 失败样例分析

- `landing_page_showcase` / `20260413-015547-257570-orchestrate`
  - 首败层: `Spec`
  - 原因: structural gate: source_generation status must be pass
  - 类型: 需求收敛问题
- `landing_page_showcase` / `20260413-020000-477634-orchestrate`
  - 首败层: `Spec`
  - 原因: structural gate: source_generation status must be pass
  - 类型: 需求收敛问题
- `landing_page_showcase` / `20260413-020315-688447-orchestrate`
  - 首败层: `Spec`
  - 原因: structural gate: source_generation status must be pass
  - 类型: 需求收敛问题

## 5. 结论

- 当前最弱层: `Spec`
- 当前最常见首败层: `Spec`
- 当前是否仍主要是前段问题: `是`
- 下一步最值得优先修的 1~2 个点:
  - 继续压缩 `Spec` 首败，尤其是仍停在 source_generation / manifest 的任务。
  - 把 verify-pass 但未形成强 smoke 的 web/gui 任务继续推向更稳定的 package + delivery 常态化闭环。
