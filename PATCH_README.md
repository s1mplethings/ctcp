# Patch / Zip Delivery

本仓库的交付默认是 **可应用的 patch**，并通过 `verify_repo` 验收。

## 推荐交付：unified diff patch

- 一个主题一个 patch
- 必须能 `git apply`：
  - `git apply your_change.patch`

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
