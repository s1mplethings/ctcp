# ai_apply scripts

提供一个最小闭环：
- scan：扫描目标项目结构，输出 report.json + report.md
- recommend：基于 detectors 与 recipe_index 输出推荐
- bundle：选择 recipe，输出标准迁移包目录（可再压成 zip）

## 用法
```bash
python scripts/ai_apply/cli.py scan <TARGET_REPO> --out out_scan
python scripts/ai_apply/cli.py recommend out_scan/report.json
python scripts/ai_apply/cli.py bundle <TARGET_REPO> --recipe qtweb-graph-force --out out_bundle
```
