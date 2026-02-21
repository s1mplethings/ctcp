# Self-Check & Self-Improve（Python 版）

## 你要解决的问题
让程序能“自己检查功能有没有完成”，不通过就继续迭代（输出 patch → apply → 再检查）。

这里的关键是把“完成”定义成机器可判定的 **PASS/FAIL**。

## 结构
- `specs/*.checks.json`：每个功能一个 checks 清单（机器命令）
- `scripts/self_check.py`：执行所有 checks，输出报告（PASS/FAIL）
- `tools/checks/*`：具体检查器（例如对蛛网图做 E2E）
- `scripts/self_improve.py`：循环（check → fail → 生成 prompt → 调外部 LLM 输出 patch → apply → 再 check）

## 强约束（避免 AI 乱改）
- 每轮必须输出 **unified diff patch**
- 每轮应用 patch 后必须重新跑 `self_check`
- 设定最大轮数 `--max-rounds`（默认 3）
- 任何 `git apply` 失败 / verify 变红：立即停止

## 接入 Codex（通用）
设置环境变量 `SDDAI_PATCH_CMD`，支持占位符：
- `{PROMPT_PATH}`：本轮生成的 prompt 路径
- `{REPO_ROOT}`：仓库根目录

脚本会把 stdout 中从 `diff --git` 开始的内容提取为 patch 并尝试 `git apply`。

## OpenAI API 外部化（ADLC core）
如果你希望明确走自己的 OpenAI API 计费通道，不走 `codex exec` 会话：

1) 设置 API Key：
- `OPENAI_API_KEY`

2) 可选设置模型：
- `SDDAI_OPENAI_MODEL`（默认 `gpt-4.1-mini`）
- 或分别设置 `SDDAI_OPENAI_PLAN_MODEL` / `SDDAI_OPENAI_PATCH_MODEL`

3) 设置命令模板（支持 workflow 占位符）：
- `SDDAI_PLAN_CMD`:
  - `python scripts/externals/openai_plan_api.py "{CONTEXT_PATH}" "{CONSTRAINTS_PATH}" "{FIX_BRIEF_PATH}" "{GOAL}" "{ROUND}" "{REPO_ROOT}"`
- `SDDAI_PATCH_CMD`:
  - `python scripts/externals/openai_patch_api.py "{PLAN_PATH}" "{CONTEXT_PATH}" "{CONSTRAINTS_PATH}" "{FIX_BRIEF_PATH}" "{GOAL}" "{ROUND}" "{REPO_ROOT}"`
