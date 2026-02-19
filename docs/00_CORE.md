# CTCP Core Protocol

若本文件与其它文档冲突，以本文件为准。

## 0.1 规范关键字

本文件使用 RFC 风格关键字：
- `MUST` / `SHALL`：强制要求，不满足即不合规
- `SHOULD`：强建议，允许有限例外但必须记录原因
- `MAY`：可选项

## 0. 北极星定义

CTCP 的核心不是 GUI。CTCP 的核心是一个可执行、可验收、可迭代的工程执行机：

- 以 ADLC 作为契约化流水线：`doc -> analysis -> find -> plan -> build/verify -> contrast -> fix -> deploy/merge`
- 以 `workflow_registry` + resolver(`find`) 作为“复用最佳流程”的更新机制
- 以 SimLab（回放/验收/证据链）作为“可运行的证明”
- 以 failure bundle 作为“失败的唯一事实来源”
- GUI 仅作为可选示例/可视化器，不属于默认构建/默认验收链路

## 1. 术语与边界

### 1.1 ADLC 流程（唯一权威执行链）

`doc -> analysis -> find -> plan -> [build <-> verify] -> contrast -> fix -> deploy/merge`

### 1.2 Find 的真实含义（非常重要）

- find 不是上网找资料
- find 是 Workflow Resolver：从已有流程库/历史成功记录中，挑选最适合当前 goal 的现成 workflow（recipe）作为依赖来执行
- Web 只能作为更新流程库的离线输入，不允许成为主链路硬依赖

### 1.3 GUI 的定位

GUI（Qt/Cytoscape）用于：
- 展示工程结构示例（docs/specs/modules/contracts/gates/runs）
- 可选可视化 runs、graph、流程关系

GUI 默认不参与：
- `verify_repo` 默认 gate
- Lite scenarios
- 核心 runner 执行链

## 2. 仓库结构约定（AI 必须遵守）

### 2.1 核心目录

- `workflow_registry/`: 流程库（find 的主要输入）
- `scripts/`: 入口脚本（workflow dispatch、verify）
- `simlab/`: 最小回放/验收框架（scenarios + run engine）
- 外部 runs root（`CTCP_RUNS_ROOT`）: 所有默认执行产物（TRACE、bundle、events）
- `meta/run_pointers/`: 仓库内轻量指针（只记录外部 run 目录路径）
- `meta/`: 工程关系/视图/配置
- `specs/`: 契约与 schema
- `docs/`: 核心规则与 DoD
- `meta/runs/`、`simlab/_runs/`: deprecated，非默认产物目录

### 2.2 运行产物目录（固定）

标准落点（默认）：
- `runs_root = env(CTCP_RUNS_ROOT)`；若未设置，默认 `~/.ctcp/runs`
- `repo_slug = <repo 根目录名归一化>`
- `run_dir = <runs_root>/<repo_slug>/<run_id>/`
- Team Mode / ADLC / SimLab 默认 `MUST` 写入该外部 `run_dir`

仓库内允许写入（轻量）：
- `meta/run_pointers/LAST_RUN.txt`（绝对路径）
- 可选 pointer（例如 `LAST_QUESTIONS.txt`、`LAST_TRACE.txt`）

例外（门禁回放）：
- `verify_repo` 的 Lite replay 可继续写入仓库内 gate 目录（如 `simlab/_runs_repo_gate/<run_id>/...` 或 fixtures），用于固定验收流程。

每次运行 `MUST` 写入：
- `TRACE.md`
- `artifacts/`（至少包含 find/plan/verify 相关产物）

失败时 `MUST` 写入：
- `failure_bundle.zip`

## 3. 核心不变量（任何 agent 不得违反）

- Doc-first：任何实质改动前 `MUST` 读取 `docs/00_CORE.md` + `AGENTS.md` + 相关 specs
- 默认 headless：默认验收 `SHALL` 不依赖 GUI/Qt
- 最小变更：修复 `SHALL` 只针对失败证据，禁止顺手重构
- 失败唯一事实源：Fixer `MUST` 只依据 `failure_bundle.zip`
- 交付可应用：补丁 `MUST` 为 unified diff（`diff.patch` 可 `git apply`）
- find 可消费：find 输出 `MUST` 结构化，plan `MUST` 消费它
- 两级 gate：默认 `SHALL` 只跑 Lite；Full `MUST` 显式开启

## 4. 执行角色（多 agent 最小组织）

可单 agent 实现，但接口输出需兼容以下角色：

- DocGatekeeper: `artifacts/guardrails.md`
- Analyzer: `artifacts/analysis.md`
- Resolver(Find): `artifacts/find_result.json`
- Planner: `artifacts/PLAN.md`
- PatchMaker: `artifacts/diff.patch`
- Verifier: `TRACE.md` + `artifacts/verify_report.md`
- Fixer: 输入 `failure_bundle.zip`，输出新 `diff.patch`
- ReleaseReporter: `artifacts/release_report.md`

## 5. 每一步必须输入/输出（MUST）

### 5.1 doc
- 输入：repo tree、`docs/00_CORE.md`、`AGENTS.md`、相关 specs
- 输出：`artifacts/guardrails.md`
- 判定：未生成 guardrails 直接 FAIL

### 5.2 analysis
- 输入：goal + guardrails + 关键文件摘要
- 输出：`artifacts/analysis.md`
- 判定：只做问题定义/约束确认，不写大段计划细节

### 5.3 find（Resolver）
- 输入：goal + analysis + `workflow_registry/index.json` + 历史成功记录
- 输出：`artifacts/find_result.json`
- 最小字段：
  - `selected_workflow_id`
  - `selected_version`
  - `params`
  - `top_candidates`(<=3)
  - `decision`
- 判定：找不到 workflow 时必须输出 `selected_workflow_id=null`，并在 plan 走 fallback minimal workflow

### 5.4 plan
- 输入：`find_result.json` + guardrails + analysis
- 输出：`artifacts/PLAN.md`
- 必须包含：workflow id/version、参数填充、gates、预计改动路径

### 5.5 build <-> verify
- 输入：`PLAN.md` + repo state
- 输出：`TRACE.md` + `artifacts/verify_report.md`
- 失败：必须产出 `failure_bundle.zip` 并进入 contrast/fix

### 5.6 contrast -> fix
- 输入（唯一可信）：`failure_bundle.zip`
- 输出：新 `diff.patch`，可选 `artifacts/fix_notes.md`
- 判定：修复后必须重新 build/verify，直到 Lite gate 绿或预算耗尽

### 5.7 deploy/merge
- 输入：最后一次 PASS verify_report + diff.patch
- 输出：`artifacts/release_report.md`

## 6. Workflow Registry（find 核心依赖）

### 6.1 目录规范
- `workflow_registry/<workflow_id>/recipe.yaml` 需声明：输入/输出/steps/gates/cost hints
- `workflow_registry/index.json` 需支持：tags、supported goals、dependency level、last_known_good

### 6.2 Fallback Minimal Workflow（保底）

必须存在最小 workflow（例如 `wf_minimal_patch_verify`）：
- 只做：plan -> patch -> Lite verify -> 证据打包
- 目标：find 找不到时仍可继续执行而不阻塞

## 7. SimLab（证据链规则）

### 7.1 最小 step 类型（MVP）
- `run`
- `write`
- `expect_path`
- `expect_text`
- 可选：`expect_bundle`

### 7.2 TRACE.md 必须记录
- 每一步命令、cwd、返回码
- stdout/stderr 摘要
- 关键产物路径

### 7.3 failure_bundle.zip 最小内容
- `TRACE.md`
- `diff.patch`（若有）
- `logs/*`
- `snapshot/*`（至少关键文件/目录快照）

## 8. Gate Matrix（默认 Lite，Full 可选）

### 8.1 Lite（默认必须）
- headless build（不需要 Qt）
- 跑 1~2 个最小 scenario（如 `S01_init_task` / `S02_doc_first_gate`）
- 输出 TRACE 与 verify_report

### 8.2 Full（显式开启）
- GUI build（仅 `CTCP_ENABLE_GUI=ON` 且依赖满足）
- 更完整 scenarios 与更严格检查

## 9. GUI 挂起策略（可选化原则）

- 构建开关：`CTCP_ENABLE_GUI`（默认 `OFF`）
- `verify_repo` 默认不触发 GUI
- 仅在显式要求 GUI 或 Full gate 开启且环境具备 Qt 时，GUI 参与 build/verify

## 10. 核心一句话（系统提示）

- find = 从本地流程库/历史成功中解析并选择 workflow
- patch = 外部 agent 产物输入，runner 负责吸收并应用
- verify = 唯一判定步骤，必须在可回放环境里产出 TRACE
- fail = 必须产出 failure_bundle，修复只能依据 bundle
