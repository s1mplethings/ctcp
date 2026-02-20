# Analysis

- Goal: Self improve core loop
- Flow: doc -> analysis -> find -> plan -> build -> verify -> contrast -> fix -> stop

## Read Summary
- `D:/.c_projects/adc/ctcp/README.md`:
  # CTCP — ADLC + Multi-Agent Execution Engine
  
  本仓库核心定位：核心 = ADLC 执行引擎（证据链 + failure bundle），把“项目实现”变成可验证、可回放、可审计的执行闭环。
  - 默认路径是 **headless**（不依赖 GUI/Qt）。
  - GUI 仅作为示例/可视化器，可选开启，不影响核心流程。
  - find = workflow resolver（从本地 `workflow_registry/` + 历史成功记录解析最佳 workflow，不依赖联网检索）。
  - 可选开启受控 web find（`resolver_plus_web`，由外部 Researcher 提供 `find_web.json`），默认仍不依赖联网。
  - GUI 可选/默认挂起（不影响核心 gate）。
  
  系统目标：
- `D:/.c_projects/adc/ctcp/docs/03_quality_gates.md`:
  # Quality Gates (DoD)
  
  本仓库的“合格交付”主判定方式：`scripts/verify.*` 通过（证据 gate）。
  `scripts/verify_repo.*` 仍用于 workflow/contract/doc-index 的基础门禁。
  
  “没证据=没测试”硬规则：
  - 必须生成 `artifacts/verify/<timestamp>/proof.json` 与步骤日志。
  - 必须通过 `tools/adlc_gate.py`。
  - `proof.result != PASS` 或日志缺失 -> 直接 fail。
  
- `D:/.c_projects/adc/ctcp/docs/SELF_CHECK_SYSTEM.md`:
  # Self-Check & Self-Improve（Python 版）
  
  ## 你要解决的问题
  让程序能“自己检查功能有没有完成”，不通过就继续迭代（输出 patch → apply → 再检查）。
  
  这里的关键是把“完成”定义成机器可判定的 **PASS/FAIL**。
  
  ## 结构
  - `specs/*.checks.json`：每个功能一个 checks 清单（机器命令）
  - `scripts/self_check.py`：执行所有 checks，输出报告（PASS/FAIL）
- `D:/.c_projects/adc/ctcp/ai_context/00_AI_CONTRACT.md`:
  # CTCP / SDDAI — AI Contract (Hard Rules)
  
  本文件是“工程化约束”入口：用脚本与门禁把 agent 行为固定下来。
  
  ---
  
  ## A. 目标态（你要达到什么）
  
  你只提供一个目标（Goal），系统必须做到：
  
