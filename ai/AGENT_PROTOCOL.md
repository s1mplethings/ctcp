# AGENT_PROTOCOL (唯一入口 / 强约束契约)

> 这份文件是本仓库 AI 改代码的唯一入口。任何 AI（Codex/Claude/Copilot/etc）在修改项目前必须先读它，并严格按流程产出交付物。

## 0. 不允许跳过的步骤（硬闸门）
1) **先扫描再改**：必须先生成 `report.json` + `report.md`（见 scripts/ai_apply）。
2) **必须使用预设（recipe）**：必须从 `ai/RECIPES/` 选择一个或多个 recipe；若没有合适 recipe，必须在报告里写明“缺少哪个 recipe”，并创建一个新的 `ai/RECIPES/<new>/recipe.json`（空也可以，但要写好 compat/verify）。
3) **必须交付可应用补丁**：最终交付必须包含 unified diff patch（可 `git apply`），并提供 apply/rollback/verify 步骤。

## 1. 允许/禁止的修改范围
- 允许新增：`ai/**`, `scripts/ai_apply/**`, `docs/**`, `specs/**`, `web/**`（如果是 web 相关 recipe）
- 默认禁止修改：构建脚本/核心业务（除非 recipe 明确允许），以及任何“与当前任务无关”的目录。
- 如果必须触及核心文件：必须在 plan 里写清楚理由、影响范围、回滚方式。

## 2. 标准工作流（必须按顺序）
### 2.1 扫描目标项目（本仓库或外部仓库）
```bash
python scripts/ai_apply/cli.py scan <TARGET_REPO> --out <OUT_DIR>
```

### 2.2 诊断 + 推荐可套用 recipe
```bash
python scripts/ai_apply/cli.py recommend <OUT_DIR>/report.json
```

### 2.3 生成迁移包（patch bundle）
```bash
python scripts/ai_apply/cli.py bundle <TARGET_REPO> --recipe <RECIPE_ID> --out <OUT_DIR>
```

## 3. 交付物格式（必须）
一个“迁移包”必须包含以下文件（路径固定）：
```
<OUT_DIR>/
  report.json
  report.md
  plan.md
  tokens.json
  patches/
    0001-*.patch
  verify.md
  rollback.md
```

## 4. 校验要求（至少做一种）
- `git apply --check patches/0001-*.patch`（推荐）
- 或在 plan 里写清楚为什么无法 check（例如目标仓库不是 git）

## 5. 记录成功案例（可复用）
当一次迁移成功后，必须把它沉淀为 recipe：
- 在 `ai/RECIPES/<id>/` 里补全：
  - `recipe.json`（适用条件/锚点/verify）
  - `patches/`（最终 patch）
  - `README.md`（人类说明）
- 并更新 `ai/RECIPES/recipe_index.json`
