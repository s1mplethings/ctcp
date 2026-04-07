# Build (Headless-first)

## Prereqs
- CMake ≥ 3.21
- A C++17 compiler (MSVC / clang / gcc)
- Ninja（可选）

## Steps

### Windows (PowerShell)
```powershell
cmake -S . -B build_lite -DCMAKE_BUILD_TYPE=Release
cmake --build build_lite --config Release
```

### Linux/macOS
```bash
cmake -S . -B build_lite -DCMAKE_BUILD_TYPE=Release
cmake --build build_lite
```

默认可执行文件：
- headless: `ctcp_headless`
