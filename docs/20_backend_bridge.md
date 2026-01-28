# Backend Bridge: readTextFile + Rendered Preview Window

你需要后端提供 `readTextFile(path)`，让前端能渲染预览（Markdown/文本），而不是直接 txt 打开。

本补丁提供了可直接拷贝进项目的 C++ 代码：
- `src/sddai_bridge.h/.cpp`
- `src/preview_window.h/.cpp`

## 1) 在你的 QtWebEngine 项目里注册 QWebChannel
在创建 `QWebEngineView` 后（例如 MainWindow 构造里）：

```cpp
#include <QWebChannel>
#include "sddai_bridge.h"

auto* channel = new QWebChannel(view->page());
auto* bridge = new SddaiBridge(projectRootPath, this);
channel->registerObject("bridge", bridge);
view->page()->setWebChannel(channel);
```

前端 JS 会自动在 WebChannel 里找：`bridge` / `backend` / `SDDABridge`。

## 2) 方法说明
### readTextFile(relativePath) -> QString
- 输入：相对项目根目录的路径（例如 `docs/00_overview.md`）
- 输出：UTF-8 文本（最大 2MB，防止卡死）
- 安全：阻止绝对路径 / 路径穿越（必须在 projectRoot 内）

### openPath(relativePath)
- 打开一个 `PreviewWindow`：
  - `.md`：Qt >= 5.14 使用 Markdown 渲染
  - 其他：以 pre 风格渲染（仍然是 HTML 渲染，不是系统 txt）
