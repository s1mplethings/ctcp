# CTCP — Agent Contract (Hard Rules)

> 目标：让 agent 变成“项目团队”：自驱推进、可验证交付、只问必要问题、能演示全过程。

这份文件是 **强约束**：任何 agent/自动化必须遵守。违反即视为失败交付。

---

## 6) Patch 输出稳定性（避免 UI 渲染/复制导致“代码框忽有忽无”）

你看到“程序框一会有一会没有”，通常不是 agent 真输出不一致，而是：
- Markdown 渲染把某些片段识别为代码（缩进/围栏/关键字触发）
- 从富文本 diff 视图复制时丢失了 `+/-/@@` 或缩进，导致分段被当作普通文本

**稳定输出规则（强约束）**：
1. Chat/控制台最终输出必须是 **patch-only**：只输出 ONE unified diff patch，不得夹杂任何说明文字。
2. 输出必须是**单一连续 patch**：从第一行 `diff --git` 开始到最后一行结束，中间不得分段、不得插入普通文本。
3. 不要使用 Markdown 围栏（```）；如平台强制代码块，只允许一个代码块且块内只有 patch。
4. 不要从富文本 diff 视图复制；优先以补丁文件为准（例如 run_dir 的 `artifacts/diff.patch`，或 `git diff > diff.patch`）。
5. Readlist/Plan/Verify/Demo 等报告正文写入 `meta/reports/LAST.md`，不要写进 chat 输出（遵守 `ai_context/00_AI_CONTRACT.md`）。

### Prompt 模板（UI-safe + MD-driven）

```text
你是 ctcp 仓库的 patch-first agent。先读 AGENTS.md / ai_context/00_AI_CONTRACT.md / PATCH_README.md，再按门禁推进。

硬约束：
- 最终输出必须且只能是一份 unified diff patch（git apply compatible）。
- 输出必须单一连续：从 `diff --git` 到结尾，不拆分、不夹杂说明文字。
- 不要使用 ``` 围栏；如平台强制代码块，只允许一个代码块且块内只有 patch。
- 报告正文（Readlist/Plan/Verify/Demo）写入 meta/reports/LAST.md，不写进 chat 输出。
- 验收只走 scripts/verify_repo.ps1 / scripts/verify_repo.sh。

交付：只输出 ONE unified diff patch。
```

冲突处理优先级：`docs/00_CORE.md` > `AGENTS.md` > `ai_context/00_AI_CONTRACT.md`。

---

## Fast Rules（前两屏必须可见）

1. **唯一验收入口（DoD Gate）**
   - Windows: `scripts/verify_repo.ps1`
   - Unix: `scripts/verify_repo.sh`
2. **输出规则（Chat/控制台/patch 输出）**
   - Chat/控制台最终输出：**patch-only**（unified diff），不得包含报告正文。
   - 报告正文落盘：`meta/reports/LAST.md`
   - run_dir 证据链：`TRACE.md`、`artifacts/verify_report.json` 等
   - 快速硬规则速览：`ai_context/CTCP_FAST_RULES.md`
3. **允许提问的唯一条件**
   - 仅限：密钥/账号/权限；互斥方案拍板；缺少关键约束导致无法继续。
4. **执行顺序**
   - Docs/Spec → Gate → Verify → Report（详见第 2 节）

---

## 0) 允许提问的唯一条件（否则不要问）

你只能在下面场景提问（写入外部 run 包的 `QUESTIONS.md`，通过 `meta/run_pointers/LAST_RUN.txt` 定位）：

1. 需要用户提供 **密钥/账号/外部权限**（例如 API key、访问令牌）
2. 需要用户在 **互斥方案** 中拍板（例如“重命名项目/大重构/破坏兼容”）
3. 缺少关键约束导致无法继续（例如目标平台、必须支持的版本、许可证限制）

除此之外，全部用默认策略推进，并在报告里写明默认选择与可替代项。

---

## 1) 必读文件（开始任何动作之前）

必须读取并总结（写入 `meta/reports/LAST.md` 的 Readlist）：

- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`（如果存在）
- `docs/03_quality_gates.md`（如果存在）
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`

---

## 2) 执行顺序（不可跳过）

1. **创建/更新任务单**：`meta/tasks/CURRENT.md`（模板：`meta/tasks/TEMPLATE.md`）
2. **Research-first（如需要）**：记录到 `meta/externals/<date>-*.md`
3. **Spec-first**：先更新 docs/spec/meta（让流程可被审计）
4. **代码改动（受门禁）**：只有当 `meta/tasks/CURRENT.md` 勾选了 `Code changes allowed` 才允许改 `src/ web/ scripts/ tools/ include/` 等代码目录
5. **验收闭环（必须）**：运行 `scripts/verify_repo.*` 并记录输出
6. **演示报告（必须）**：更新 `meta/reports/LAST.md`

---

## 3) 唯一验收入口（DoD Gate）

只允许使用：

- Windows: `scripts/verify_repo.ps1`
- Unix: `scripts/verify_repo.sh`

`verify_repo` 必须覆盖：

- build / web build（可跳过但要明确日志原因）
- workflow gate（禁止代码/必须任务单/必须契约文件）
- contract checks
- doc index check
- tests（如果存在）

---

## 4) 强制交付

### 强制交付内容（必须具备）

1. Readlist（读了哪些文件 + 关键约束）
2. Plan（分阶段：Docs/Spec → Code → Verify → Report）
3. Changes（文件清单 + 关键 diff 摘要）
4. Verify（命令 + 关键输出 / 失败原因）
5. Questions（若有：阻塞问题 + 选项 + 默认建议）
6. Demo（指出 `meta/reports/LAST.md` 与外部 run_dir 证据链文件路径）

### 强制交付位置（必须落盘）

- 上述 1~6 的正文必须写入 `meta/reports/LAST.md`。
- 外部 run 包证据链必须写入 run_dir 的对应文件（例如 `TRACE.md`、`artifacts/verify_report.json`）。
- Chat/控制台的最终输出必须遵守 `ai_context/00_AI_CONTRACT.md`：patch-only（unified diff），不得附带报告正文。

---

## 5) 最小改动原则

- 一个 patch 只做一件事（一个主题）
- 新依赖必须记录到 `third_party/THIRD_PARTY.md`（若目录存在）
- 任何绕过 gate 的行为必须写入 `ai_context/decision_log.md`

---

## Codex Skills（repo-local）

- `ctcp-workflow`：固定执行 CTCP/ADLC 流程（spec-first -> gate -> verify -> report，失败走证据链）
  - path: `.agents/skills/ctcp-workflow/SKILL.md`
  - invoke: `$ctcp-workflow`
- `ctcp-verify`：执行仓库唯一验收入口并给出首个失败点与最小修复策略
  - path: `.agents/skills/ctcp-verify/SKILL.md`
  - invoke: `$ctcp-verify`
- `ctcp-failure-bundle`：在失败后收集证据链并输出可审计失败闭环
  - path: `.agents/skills/ctcp-failure-bundle/SKILL.md`
  - invoke: `$ctcp-failure-bundle`
- `ctcp-gate-precheck`：改动前检查任务门禁与契约前置条件
  - path: `.agents/skills/ctcp-gate-precheck/SKILL.md`
  - invoke: `$ctcp-gate-precheck`
- `ctcp-doc-index-sync`：处理 README Doc Index 同步与复检闭环
  - path: `.agents/skills/ctcp-doc-index-sync/SKILL.md`
  - invoke: `$ctcp-doc-index-sync`
- `ctcp-orchestrate-loop`：驱动 `ctcp_orchestrate` 的状态推进与阻塞分流
  - path: `.agents/skills/ctcp-orchestrate-loop/SKILL.md`
  - invoke: `$ctcp-orchestrate-loop`
- `ctcp-patch-guard`：执行 patch 范围/契约守卫并给出最小修复策略
  - path: `.agents/skills/ctcp-patch-guard/SKILL.md`
  - invoke: `$ctcp-patch-guard`
- `ctcp-simlab-lite`：运行轻量 SimLab 回放并输出首个失败点
  - path: `.agents/skills/ctcp-simlab-lite/SKILL.md`
  - invoke: `$ctcp-simlab-lite`
- `ctcp-run-report`：汇总 run 证据并生成可审计报告
  - path: `.agents/skills/ctcp-run-report/SKILL.md`
  - invoke: `$ctcp-run-report`
