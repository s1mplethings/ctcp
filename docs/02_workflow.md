# 工作流

> 规范优先级：若本文件与 `docs/00_CORE.md` 冲突，以 `docs/00_CORE.md` 为准。

## 核心执行链（默认）
- `doc -> analysis -> find -> plan -> build/verify -> contrast -> fix -> deploy/merge`
- `find` 的含义是 workflow resolver（从本地流程库/历史成功记录选 recipe），不是上网检索。
- 默认 headless，GUI 仅可选示例路径，不进入默认验收链路。

## Orchestrator 工件推进（Local Orchestrator 唯一驱动）
- Local agent 角色定义为 Local Orchestrator：基于 run_dir 工件存在性推进状态，不直接承担 Researcher/Librarian/Reviewer 的内容生产。
- 默认 run 目录使用外置 `CTCP_RUNS_ROOT`，仓库内只保留 `meta/run_pointers/LAST_RUN.txt` 指针。
- `find` 双通道：
  - `find_local`（必做）：resolver 产出 `artifacts/find_result.json`
  - `find_web`（可选）：Researcher 产出 `artifacts/find_web.json`
- 模式门禁：
  - `resolver_only`：`find_result.json` 必须存在即可通过 find gate
  - `resolver_plus_web`：`find_result.json` 与 `find_web.json` 均必须存在，缺任一项状态为 blocked（等待 Researcher）
- 注意：`find_web.json` 仅作为输入补充，最终用于 plan 的决策工件仍是 `find_result.json`。

## 使用流程（用户视角）
1. 打开工程目录
   - GUI 扫描并识别 SDDAI 结构（docs/specs/scripts/ai_context/runs）
2. 查看 Pipeline View（按阶段分块）
   - Module 节点按 phase 分组
   - Contract 节点可显示 schema 摘要
3. 查看 Contract View（以协议为中心）
   - Producer/Consumer 一眼可见
4. 查看进度
   - 静态：spec/contract/tests/trace 覆盖率
   - 运行时：选择某个 run，显示卡点/耗时/产物路径
5. 编辑关系
   - 在图上或 Inspector 增删边（produces/consumes/verifies）
   - 修改写回 `meta/pipeline_graph.json`
   - 图自动刷新（manual 覆盖 auto）

## 维护流程（开发者视角，Spec-first）
- 任何新增/修改模块：先写 `specs/modules/<module>/spec.md`
- 任何新增/修改协议：先写 `specs/contract_output/<contract>.schema.json`
- 任何变更：必须跑 verify（见 docs/03_quality_gates.md）
- 失败：写入 `ai_context/problem_registry.md`
- 临时豁免：写入 `ai_context/decision_log.md` 并注明回补计划

## Drift 规则
- 自动推导与实际工程不一致时：以 meta 文件为权威
- meta 文件变更建议更新相关 spec 的 Trace Links（可选）
- 文件重命名/移动：必须同步更新 meta（避免图断链）

## Trace Links
- docs/05_navigation.md
- docs/12_modules_index.md
- docs/13_contracts_index.md
