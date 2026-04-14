# Batch Image Processor

本地 Web 工具，用于批量上传图片并进行统一处理，支持结果预览、单张下载和批量 ZIP 下载。

## 功能

- 一次上传多张 `jpg/jpeg/png`
- 原图列表与缩略图预览
- 统一宽高缩放
- 按比例缩放
- 输出格式转换：`png/jpg`
- JPG 压缩质量调整
- 重命名规则：保留原名 / 增加前缀 / 增加序号
- 结果预览
- 单张下载
- 一键打包下载全部结果

## 环境

- Python 3.10+
- 已安装依赖见 `requirements.txt`

## 启动

```powershell
python app.py --serve
```

默认地址：

`http://127.0.0.1:5085`

## 使用说明

1. 打开首页后选择多张图片。
2. 设置处理模式、输出格式、压缩质量和重命名规则。
3. 点击“开始处理”。
4. 页面会显示原图缩略图、处理结果、单张下载入口和 ZIP 下载入口。

## 最小自测

```powershell
python scripts/smoke_test.py
```

## 入口

- Web 入口：`app.py`
- 模板：`templates/index.html`
- 样式：`static/styles.css`
- 冒烟脚本：`scripts/smoke_test.py`

## 项目结构

- `app.py`：本地 Web 服务与图片处理逻辑
- `artifacts/uploads/`：上传缓存
- `artifacts/processed/`：处理输出与 ZIP 包
- `artifacts/screenshots/`：项目截图
- `scripts/`：本地脚本
- `tests/`：最小测试占位
