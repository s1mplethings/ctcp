# Team Mode (Autonomous Coding Team)

目标：让你只输入一次 Goal，系统像项目团队一样持续推进，并给你演示。

## 核心目录
- `meta/tasks/CURRENT.md`：任务单（验收/计划/是否允许改代码）
- `meta/runs/<timestamp>/`：一次“团队运行包”
  - `PROMPT.md`：给 coding agent 的输入（唯一入口）
  - `QUESTIONS.md`：阻塞问题（唯一允许提问渠道）
  - `TRACE.md`：全过程日志（演示）
- `meta/reports/LAST.md`：面向你的演示报告（可回放）

## 使用
1) 创建运行包：
```powershell
python tools\ctcp_team.py start "your goal"
```

2) 把 `meta/runs/<ts>/PROMPT.md` 交给你的 coding agent（Codex/Claude/你自己的 agent 都行）

3) agent 产出 patch/改动后，跑：
```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1
```

4) 演示：
- 打开 `meta/reports/LAST.md`
- 跟着 Trace 指针回放 `meta/runs/<ts>/TRACE.md`

> 下一步想做到“全自动”，就在 `ctcp_team.py` 里加 provider：直接调用 codex CLI 或 OpenAI Agents SDK。
