# Back Navigation + Rendered Preview（返回上一层 + 渲染预览）

你反馈的问题：
- 点进下一层后**回不到上一级**
- 打开文件只是 txt，不是渲染后的内容

这个实现的硬规则：

## 1) 返回上一层（Back/Home）
- 前端维护 `viewStack`
- Drill-down 前 push 当前 payload
- Back 直接 pop 并恢复上一个 payload（不依赖后端）
- Home 清空 stack 并请求 Summary

快捷键：
- `Alt + ←` 或 `Backspace`：Back
- `Esc`：关闭预览

## 2) 渲染预览（不是 txt）
- 单击普通节点：优先调用后端 `readTextFile(path)` 获取文本
- 前端用轻量 Markdown 渲染器渲染到 Preview Modal（带标题、可滚动）
- “Open External” 可选调用 `openPath(path)`（如果你想用自定义 Qt 窗口打开）

### 后端 bridge 需要提供的方法（QWebChannel）
必需：
- `readTextFile(path: string) -> string`
  - 读取 project_root 下的相对路径文件，返回 UTF-8 文本
  - .md / .json / .yaml 都当文本返回（前端会渲染）

可选：
- `requestGraph(view: string, focus: string) -> string(JSON)`
- `openPath(path: string)`
