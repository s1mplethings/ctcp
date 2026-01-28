
# DocPreviewer（双击弹窗预览）

## Purpose
双击节点弹出窗口，显示该节点对应文件的内容（先做 MVP）。

## Inputs
- nodeId
- node.path（相对 project_root）
- project_root

## Outputs
- QDialog 窗口显示内容

## Interaction Rules
- 单击：Inspector 展示详情
- 双击：打开预览窗口（渲染好后显示）

## Rendering
- MVP：QTextBrowser / QPlainTextEdit（Qt6 可 setMarkdown）
- V2：QWebEngineView + markdown-it

## Acceptance Criteria
- 双击节点必须弹窗
- 支持 .md / .json / .yaml 文本预览

## Trace Links
- docs/07_layout_and_views.md
