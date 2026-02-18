# 文件防冗余准则（新增文件前必看）

## 目标
- 避免把临时调试产物、备份文件、一次性草稿带入仓库主线。

## 新增文件前 5 步检查
1. `职责检查`：这个文件是否属于本仓库目录边界（`src/`、`web/`、`meta/`、`tests/`、`scripts/` 等）？
2. `可复现检查`：它是源码/规范，还是可由脚本再生成的产物？可再生产物默认不入库。
3. `唯一性检查`：是否已有同用途文件（同主题多份 README、同输入多份 fixture）？
4. `命名检查`：禁止 `_tmp*`、`patch_debug*`、`*.bak` 这类临时命名入库。
5. `验收检查`：提交前必须跑 `scripts/verify_repo.*`，并确认 `redundancy_guard` 通过。

## 推荐命名规则
- 任务：`meta/tasks/YYYYMMDD-<topic>.md`
- 选型：`meta/externals/<topic>.md`
- 测试输入：`tests/fixtures/<domain>/<file>`
- 测试用例：`tests/cases/<case>.case.json`
- 禁止：根目录散落的版本便签文件（如 `1.2.3.txt`）、临时脚本、编辑器备份。

## 自动化防线
- `tools/checks/redundancy_guard.py`
  - 扫描 `git ls-files`
  - 阻止提交已知临时文件名与 `*.bak`
  - 阻止根目录纯版本号便签文件（`X.Y.Z.txt`）
- 已接入：
  - `scripts/verify_repo.ps1`
  - `scripts/verify_repo.sh`

## 发现冗余后的处理策略
1. 先删无引用、无业务价值的文件（最小改动）。
2. 若文件有审计价值，迁移到 `meta/` 或 `docs/` 并重命名为语义化名称。
3. 把“为什么保留”写入任务单，避免后续重复清理。
