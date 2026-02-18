# CTCP — Agent Contract (Hard Rules)

> 目标：让 agent 变成“项目团队”：自驱推进、可验证交付、只问必要问题、能演示全过程。

这份文件是 **强约束**：任何 agent/自动化必须遵守。违反即视为失败交付。

---

## 0) 允许提问的唯一条件（否则不要问）

你只能在下面场景提问（写入 `meta/runs/<ts>/QUESTIONS.md`）：

1. 需要用户提供 **密钥/账号/外部权限**（例如 API key、访问令牌）
2. 需要用户在 **互斥方案** 中拍板（例如“重命名项目/大重构/破坏兼容”）
3. 缺少关键约束导致无法继续（例如目标平台、必须支持的版本、许可证限制）

除此之外，全部用默认策略推进，并在报告里写明默认选择与可替代项。

---

## 1) 必读文件（开始任何动作之前）

必须读取并总结（写入 `meta/reports/LAST.md` 的 Readlist）：

- `ai_context/00_AI_CONTRACT.md`
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
4. **代码改动（受门禁）**：只有当 `meta/tasks/CURRENT.md` 勾选了
   - [x] Code changes allowed
   才允许改 `src/ web/ scripts/ tools/ include/` 等代码目录
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

## 4) 强制交付格式（agent 最终输出必须包含）

1. Readlist（读了哪些文件 + 关键约束）
2. Plan（分阶段：Docs/Spec → Code → Verify → Report）
3. Changes（文件清单 + 关键 diff 摘要）
4. Verify（命令 + 关键输出 / 失败原因）
5. Questions（若有：阻塞问题 + 选项 + 默认建议）
6. Demo（指出 `meta/reports/LAST.md` 与 `meta/runs/<ts>/TRACE.md`）

---

## 5) 最小改动原则

- 一个 patch 只做一件事（一个主题）
- 新依赖必须记录到 `third_party/THIRD_PARTY.md`（若目录存在）
- 任何绕过 gate 的行为必须写入 `ai_context/decision_log.md`

