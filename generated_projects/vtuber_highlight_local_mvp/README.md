# VTuber Highlight Local MVP

一个本地可运行的 MVP：输入一段本地直播回放视频，自动找出“怪叫 / 鬼叫 / 高能反应 / 情绪爆发”候选片段，输出评分、原因、HTML 报告，并可导出 clips。

## 当前能力

- 输入本地 `mp4` / `mkv` / `webm`
- 使用 `ffmpeg` 抽取音频并做规则版高能检测
- 结合音量突增、峰值、频谱高频占比、过零率变化做候选打分
- 可选读取同名 `keywords.txt` / `--keywords-file` 里的时间戳文本，为“尖叫/笑/高能”类词增加加权
- 合并过近片段、过滤太短片段
- 导出 `JSON` / `CSV` / `HTML` 报告
- 可选导出切好的 clips
- 生成时间轴图和候选预览帧

## 这是不是模型版

不是。当前是规则版/混合接口版：

- 真识别：音频能量、峰值、过零率、高频占比、片段合并与排序
- 规则近似：对“怪叫/鬼叫/情绪爆发”的识别主要依赖音频模式和可选关键词侧信号
- 预留扩展：后续可以把 `keywords.py` / `detection.py` 中的关键词与事件打分替换为 Whisper、分类器或情绪声学模型

## 环境要求

- Python 3.11+
- `ffmpeg` / `ffprobe` 可执行

## 安装

```bash
python -m pip install -r requirements.txt
```

## 快速体验

```bash
python run_demo.py
```

输出默认写入：

`output/demo_run/`

关键结果：

- `output/demo_run/report.html`
- `output/demo_run/candidates.json`
- `output/demo_run/candidates.csv`
- `output/demo_run/timeline.png`
- `output/demo_run/clips/`

## 手动分析命令

```bash
python src/vtuber_highlight_mvp/cli.py analyze ^
  --input demo_assets/sample_vtuber_replay.mp4 ^
  --output output/manual_run ^
  --export-clips
```

可选指定关键词文件：

```bash
python src/vtuber_highlight_mvp/cli.py analyze ^
  --input demo_assets/sample_vtuber_replay.mp4 ^
  --keywords-file demo_assets/sample_vtuber_replay.keywords.txt ^
  --output output/manual_run ^
  --export-clips
```

## 测试

项目内最小测试：

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## 目录结构

```text
vtuber_highlight_local_mvp/
  config/
  demo_assets/
  output/
  src/vtuber_highlight_mvp/
  tests/
  run_demo.py
```

## Demo 素材

- 样例视频：`demo_assets/sample_vtuber_replay.mp4`
- 样例关键词：`demo_assets/sample_vtuber_replay.keywords.txt`
- 测试图片：`demo_assets/screenshots/`

## 预期输出

每个候选片段至少包含：

- `start_time`
- `end_time`
- `score`
- `reasons`
- `transcript_excerpt`
- `output_clip_path`

## 限制

- 当前没有直接接入大模型语音转写或声学分类器
- 对背景音乐很强、压缩失真很重的素材，规则版会有误报/漏报
- 关键词增强依赖外部提供的侧文件，不会自动识别字幕轨
