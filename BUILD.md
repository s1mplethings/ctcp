# Build (Windows/macOS/Linux)

## Prereqs
- Qt 6.x with modules: Widgets, WebEngineWidgets, WebChannel
  - (Qt 5.15+ 也可；通过 `CMAKE_PREFIX_PATH` 指定)
- CMake ≥ 3.21
- A C++17 compiler (MSVC / clang / gcc)
- Ninja（可选）

## Steps

### Windows (PowerShell)
```powershell
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="C:/Qt/6.6.1/msvc2019_64"
cmake --build build --config Release
```

### Linux/macOS
```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

成功后可执行文件通常在：
- Windows: `build/<config>/...exe`（verify 脚本会把 Release 复制到 `build/` 便于发现）
- Unix: `build/<exe>`

