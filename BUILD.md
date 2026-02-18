# Build (Headless-first)

## Prereqs
- CMake ≥ 3.21
- A C++17 compiler (MSVC / clang / gcc)
- Ninja（可选）

GUI only (optional):
- Qt 6.x (or Qt 5.15+) with Widgets, WebEngineWidgets, WebChannel
- set `CMAKE_PREFIX_PATH`/`Qt6_DIR` for GUI build

## Steps

### Windows (PowerShell)
```powershell
cmake -S . -B build_lite -DCMAKE_BUILD_TYPE=Release -DCTCP_ENABLE_GUI=OFF
cmake --build build_lite --config Release
```

### Linux/macOS
```bash
cmake -S . -B build_lite -DCMAKE_BUILD_TYPE=Release -DCTCP_ENABLE_GUI=OFF
cmake --build build_lite
```

### GUI Example Build (optional)

```powershell
cmake -S . -B build_gui -DCMAKE_BUILD_TYPE=Release -DCTCP_ENABLE_GUI=ON -DCMAKE_PREFIX_PATH="C:/Qt/6.6.1/msvc2019_64"
cmake --build build_gui --config Release
```

默认可执行文件：
- headless: `ctcp_headless`
- gui (optional): `ctcp`
