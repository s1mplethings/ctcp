# VTuber Highlight Local MVP 实现过程

## 阶段 1：需求理解与方案拆解

### 理解/判断

目标不是做零散脚本，而是落一个完整本地项目：本地视频输入、真实处理链、可视化结果、可导出 clips、可测试、可演示。  
第一版优先保证闭环可跑，不追求在线服务或重模型。

### 本阶段实际修改

- 绑定仓库任务到 `ADHOC-20260406-vtuber-highlight-local-mvp`
- 在 `generated_projects/vtuber_highlight_local_mvp/` 下建立项目骨架
- 明确选择 `CLI + HTML 报告` 路径，而不是先做薄 Web UI

### 当前验证结果

- 范围确定
- 主链确定为：本地视频 -> 音频提取 -> 候选检测 -> 评分/合并 -> 报告 -> clips

## 阶段 2：技术栈与项目结构确定

### 理解/判断

为了优先保证本地可跑和复现稳定，技术上采用 `Python + ffmpeg + numpy + matplotlib`。  
主业务放在 `src/vtuber_highlight_mvp/`，测试放在 `tests/`，样例素材放在 `demo_assets/`。

### 本阶段实际修改

- 新增 `README.md`
- 新增 `requirements.txt`
- 新增 `pyproject.toml`
- 新增 `config/default_config.json`
- 新增 `run_demo.py`

### 当前验证结果

- 项目结构成型
- 运行入口和依赖入口明确

## 阶段 3：核心处理链实现

### 理解/判断

在外部模型不可依赖的情况下，先做规则版检测是合理降级，但不能伪装成模型理解。  
因此真实实现的是音频启发式检测，并保留关键词侧信号增强。

### 本阶段实际修改

- 新增 `src/vtuber_highlight_mvp/media.py`
  - 负责 `ffmpeg` 音频提取、裁剪 clips、导出候选帧
- 新增 `src/vtuber_highlight_mvp/detection.py`
  - 负责音量、峰值、高频、过零率窗口评分
- 新增 `src/vtuber_highlight_mvp/keywords.py`
  - 负责读取独立关键词文件并转成增强信号
- 新增 `src/vtuber_highlight_mvp/reporting.py`
  - 负责输出 JSON / CSV / HTML / timeline
- 新增 `src/vtuber_highlight_mvp/pipeline.py`
  - 负责把媒体处理、检测、评分、导出串成主流程
- 新增 `src/vtuber_highlight_mvp/cli.py`
  - 提供命令行入口

### 当前验证结果

- 主业务链已能跑通
- 输出不只是 JSON，而是 HTML + CSV + timeline + clips

## 阶段 4：测试素材准备

### 理解/判断

不能把“请用户自己找 VTuber 素材”当成交付，所以要主动生成最小可复现的模拟直播回放。  
素材必须能真实驱动检测链，而不是只做空壳视频。

### 本阶段实际修改

- 新增 `tools/generate_demo_assets.py`
- 生成：
  - `demo_assets/sample_vtuber_replay.mp4`
  - `demo_assets/sample_vtuber_replay.keywords.txt`

### 当前验证结果

- 样例视频可直接作为 smoke 输入
- 关键词侧文件能真实增强候选打分

## 阶段 5：测试图片 / 用户视角证据生成

### 理解/判断

交付不能只给开发者日志，还要给用户能直接看的东西。  
这些证据必须来自真实运行结果，不能在主业务里硬编码伪页面。

### 本阶段实际修改

- 固定截图：
  - `demo_assets/screenshots/timeline_overview.png`
  - `demo_assets/screenshots/candidate_01_frame.png`
  - `demo_assets/screenshots/candidate_02_frame.png`
- 新增 `tools/generate_demo_evidence.py`
  - 从真实 `output/demo_run` 生成：
    - `demo_assets/screenshots/candidate_03_frame.png`
    - `demo_assets/screenshots/report_summary.png`
    - `demo_assets/screenshots/output_overview.png`
    - `demo_assets/demo_walkthrough.gif`

### 当前验证结果

- 已提供 `6` 张真实截图
- 已提供 `1` 个 gif

## 阶段 6：smoke run / 测试执行

### 理解/判断

“可运行”必须通过真实执行证明，而不是只凭代码结构判断。  
因此需要同时验证 demo、项目内测试、repo smoke 和 canonical verify。

### 本阶段实际修改

- 执行 `python generated_projects\vtuber_highlight_local_mvp\run_demo.py`
- 执行 `python generated_projects\vtuber_highlight_local_mvp\tools\generate_demo_evidence.py`
- 执行项目内测试
- 执行仓库级 smoke 测试
- 执行 canonical verify

### 当前验证结果

- demo 通过，生成 `3` 个候选片段
- clip 导出通过，生成 `3` 个 clips
- 项目内测试通过
- 仓库级 smoke 测试通过
- canonical verify 通过

## 阶段 7：最终交付收口

### 理解/判断

除了项目本体，还需要给用户一份可直接拿走的包，不用再翻聊天记录。  
所以把结论和过程另存成中文交付文档，并重新打 zip。

### 本阶段实际修改

- 新增 `delivery/DELIVERY_SUMMARY_ZH.md`
- 新增 `delivery/IMPLEMENTATION_PROCESS_ZH.md`
- 刷新：
  - `generated_projects/vtuber_highlight_local_mvp_package.zip`
  - `generated_projects/vtuber_highlight_local_mvp_user_bundle.zip`

### 当前验证结果

- 交付文档已落盘
- 用户可直接打开项目目录或 zip 查看结论、过程和结果证据
