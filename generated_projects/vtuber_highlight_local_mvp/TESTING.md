# Testing Guide

## 最小测试素材

- 输入视频：`demo_assets/sample_vtuber_replay.mp4`
- 关键词侧文件：`demo_assets/sample_vtuber_replay.keywords.txt`

## 运行命令

```bash
python run_demo.py
```

或：

```bash
python src/vtuber_highlight_mvp/cli.py analyze ^
  --input demo_assets/sample_vtuber_replay.mp4 ^
  --keywords-file demo_assets/sample_vtuber_replay.keywords.txt ^
  --output output/smoke_run ^
  --export-clips
```

## 预期结果

- 产出 `output/smoke_run/report.html`
- 产出 `output/smoke_run/candidates.json`
- 产出 `output/smoke_run/candidates.csv`
- 产出 `output/smoke_run/timeline.png`
- `output/smoke_run/clips/` 至少有 `1` 个 clip
- 候选片段大概率会命中 `3` 段：
  - 约 `2.6s - 4.7s`
  - 约 `6.7s - 9.0s`
  - 约 `10.6s - 13.1s`

## 复现用户视角证据

先跑一次 demo：

```bash
python run_demo.py
```

再生成截图和 gif：

```bash
python tools/generate_demo_evidence.py
```

预期会补齐：

- `demo_assets/screenshots/`
- `demo_assets/demo_walkthrough.gif`

## 最小测试

项目内测试：

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

仓库级 smoke 测试：

```bash
python -m unittest discover -s ..\\..\\tests -p "test_generated_vtuber_highlight_local_mvp.py" -v
```
