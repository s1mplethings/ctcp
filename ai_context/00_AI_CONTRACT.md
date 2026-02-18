# CTCP / SDDAI — AI Contract (Hard Rules)

本文件是“工程化约束”入口：用脚本与门禁把 agent 行为固定下来。

---

## A. 目标态（你要达到什么）

你只提供一个目标（Goal），系统必须做到：

1) 自己拆解 → 自己推进 → 自己验收 → 自己记录  
2) 只在“必须由你决策/提供信息”时提问  
3) 给出可回放演示：做了什么、为什么、如何复现、验证结果

---

## B. 产物（必须生成/维护）

- 任务单：`meta/tasks/CURRENT.md`
- 调研记录（如需要）：`meta/externals/<date>-*.md`
- 运行包：`meta/runs/<timestamp>/`
  - `PROMPT.md`：给 coding agent 的输入（唯一）
  - `QUESTIONS.md`：阻塞问题（唯一允许提问渠道）
  - `TRACE.md`：全过程日志（演示）
- 演示报告：`meta/reports/LAST.md`
- 问题记忆：`ai_context/problem_registry.md`
- 决策记录：`ai_context/decision_log.md`

---

## C. 强制门禁（由 verify_repo 执行）

### C1) 禁止代码（默认）
在 `meta/tasks/CURRENT.md` 未勾选 `[x] Code changes allowed` 前：
- 允许：docs/ specs/ meta/ ai_context/ 等
- 禁止：src/ include/ web/ scripts/ tools/ CMakeLists.txt package*.json 等

### C2) 唯一验收入口
只跑 `scripts/verify_repo.*`。

### C3) 文档索引必须同步
`scripts/sync_doc_links.py --check` 必须通过（README 的 Doc Index 区块必须一致）。

---

## D. 提问策略（必须遵守）

除非满足以下任一条件，否则不得提问：

1) 需要你提供密钥/权限  
2) 需要你在互斥方案中拍板  
3) 缺少关键约束导致无法继续

提问必须写到 `meta/runs/<ts>/QUESTIONS.md`，并包含：
- 问题
- 可选项 A/B/C（带利弊）
- 默认建议（如果你不回，系统将按默认继续）

---

## E. 演示格式（最后一定要能“给你演示”）

`meta/reports/LAST.md` 结构固定：

1. Goal
2. Readlist
3. Plan
4. Timeline / Trace pointer
5. Changes (file list)
6. Verify (commands + output)
7. Open questions (if any)
8. Next steps

