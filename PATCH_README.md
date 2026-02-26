# Patch / Zip Delivery

本仓库的交付默认是 **可应用的 patch**，并通过 `verify_repo` 验收。

## 推荐交付：unified diff patch

- 一个主题一个 patch
- 必须能 `git apply`：
  - `git apply your_change.patch`

## UI/复制稳定性（避免“代码框忽有忽无/中间夹杂代码”）

在聊天/网页 UI 中，diff 内容可能被 Markdown 渲染或复制时丢失 `+/-/@@` 前缀与缩进，导致显示为“有的段落在代码框里，有的不在”。

稳定规则：
- 最终输出应为**单一连续的 unified diff**（从 `diff --git` 到结尾），不要拆分，不要夹杂说明文字。
- 不要使用 Markdown 围栏（```）；如平台强制代码块，只允许一个代码块且块内只有 patch。
- 不要从富文本 diff 视图复制；优先以补丁文件为真（例如 run_dir 的 `artifacts/diff.patch`，或 `git diff > diff.patch`）。

## 备选交付：overlay zip

当需要新增大量文件或跨平台用户更方便时：
- zip 中必须包含：
  - `PATCHES/*.patch`（可选但推荐）
  - `APPLY.md`（如何应用/回滚）
  - 新增文件/覆盖文件

## 验收（必须）

无论 patch 还是 zip，都必须：
- 运行 `scripts/verify_repo.*`
- 把关键输出写到 `meta/reports/LAST.md`

> 说明：历史 PATCH_README 中提到的某些 patch 文件可能已被合并到主干；以当前仓库文件为准。
