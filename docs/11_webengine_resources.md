
# QtWebEngine 资源加载（必读）

如果你看到：
- 页面显示 `ERR_FILE_NOT_FOUND`
- 控制台打印 `QResource '/web/index.html' not found or is empty`

通常原因是：**QWebEngineView 没有用 qrc:// 路径加载**，或者 **.qrc 没有被编译进程序**。

## 推荐方式：用 Qt Resource（QRC）打包 web 资源
### 1) 把 web 资源编进 qrc
你可以用 `resources/app.qrc`（路径相对 qrc 文件）。

qmake：
- 在 .pro 中加入：`RESOURCES += resources/app.qrc`

CMake（Qt6）：
- `qt_add_resources(<target> app_res resources/app.qrc)`
- 或开启 `CMAKE_AUTORCC` 并把 .qrc 加到 target sources

### 2) 用 qrc URL 加载 index.html
必须使用：
- `qrc:/web/index.html`

不要用：
- `file:///web/index.html`
- `:/web/index.html`（QWebEngine 不一定按你期望解析）

### 3) qwebchannel.js 的加载
推荐用 Qt 自带的：
- `qrc:///qtwebchannel/qwebchannel.js`

## 备用方式：从磁盘加载（不推荐，但可用于调试）
把 `web/` 文件夹复制到 exe 同目录（或固定路径），然后：
- `QUrl::fromLocalFile(appDir + "/web/index.html")`

## 快速自检（C++）
- `QFile(":/web/index.html").exists()` 应该为 true（否则 qrc 没进来或路径错）


## 常见坑：前缀和文件路径重复导致 `/web/web/index.html`
如果你的 .qrc 写成：
- `<qresource prefix="/web">`
- `<file>web/index.html</file>`

那么资源路径会变成：
- `:/web/web/index.html`

这时你加载 `qrc:/web/index.html` 一定会报 “not found”。

解决办法：
- 方案 A（推荐）：把 prefix 改成 `/`，保持 file 为 `web/index.html`
- 方案 B：保留 prefix 为 `/web`，但给 file 加 alias：`<file alias="index.html">web/index.html</file>`
