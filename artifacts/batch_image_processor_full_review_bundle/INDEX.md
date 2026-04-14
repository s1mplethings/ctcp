# INDEX.md

这个总包用于外部复审 `Batch Image Processor` 的真实项目生成、交付与复现链路。

## 先看什么
1. `00_task/original_project_request.md`
2. `01_project/README.md`
3. `02_images/final-ui.png`
4. `03_delivery/support_public_delivery.json`
5. `03_delivery/replay_report.json`
6. `05_reports/command_results.md`
7. `04_env/environment_manifest.md`

## 目录说明
- `00_task/`: 原始项目要求、D 盘打包要求、任务卡、报告副本、过程记录。
- `01_project/`: 最终项目 zip、项目目录副本、README、入口说明。
- `02_images/`: 成品截图、补充截图、cold replay 截图。
- `03_delivery/`: 对外交付 manifest、cold replay report、support session trace、虚拟 delivery E2E json。
- `04_env/`: 环境、依赖、关键命令、git commit 与关键路径说明。
- `05_reports/`: workflow/triplet/project smoke/virtual delivery/simlab/verify 日志，以及失败与修复记录。

## 如何复查
- 查看 `01_project/entrypoint.md` 和 `01_project/README.md` 获取启动方法。
- 查看 `03_delivery/support_public_delivery.json` 确认 `sent` 中存在 `photo` 和 `document`，且 `errors` 为空。
- 查看 `03_delivery/replay_report.json` 确认 `overall_pass == true`。
- 查看 `05_reports/command_results.md` 了解本次 bundle 组装时的失败和修复过程。
- 查看 `05_reports/verify_repo.log` 获取仓库级最终验证结果。

## 缺失/失败项声明
- 无最终缺失项。
- 历史上存在两类中间失败，已保留在 `05_reports/command_results.md`:
  - bundle 任务卡/报告初始不满足 workflow gate
  - 初次 `simlab --suite lite` 因 bundle 元数据漂移而失败，随后修正并复跑通过
