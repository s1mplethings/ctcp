# INDEX

## 先看哪些文件
- `00_task/original_task.md`: 本次外部复审的原始任务要求
- `00_task/task_conversation_record.md`: 无法导出完整对话时的忠实过程记录
- `01_project/README.md`: 项目运行说明
- `02_images/final-ui.png`: 最终高价值成品截图
- `03_delivery/support_public_delivery.json`: 交付闭环主证据
- `03_delivery/replay_report.json`: 冷回放结果
- `04_env/environment_manifest.md`: 环境和命令清单
- `05_reports/command_results.md`: 仓库级检查通过/失败总览

## 目录说明
- `00_task/`: 任务说明、执行计划、过程记录
- `01_project/`: 最终项目 zip、项目目录副本、README、入口和运行说明
- `02_images/`: 成品截图和冷回放截图
- `03_delivery/`: delivery / replay / manifest / completion gate 相关证据
- `04_env/`: 环境信息、关键命令、关键路径
- `05_reports/`: workflow / virtual delivery / simlab / verify 的日志与摘要

## 复查顺序
1. 先看 `02_images/final-ui.png` 确认页面是成品工具页。
2. 再看 `01_project/project_dir/` 或 `01_project/csv-cleaner-web-tool.zip`，按 README 运行项目。
3. 查看 `03_delivery/support_public_delivery.json`，确认 `sent` 同时包含 `photo` 和 `document`，且 `errors` 为空。
4. 查看 `03_delivery/completion_gate.json`，确认 `passed=true`。
5. 查看 `03_delivery/replay_report.json` 和 `02_images/replayed_screenshot.png`，确认冷回放通过。
6. 查看 `05_reports/command_results.md` 与对应日志，确认哪些仓库级检查通过、哪些失败以及首个失败点。
