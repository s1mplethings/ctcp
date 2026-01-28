# Build (Windows/macOS/Linux)

## Prereqs
- Qt 6.x with modules: Widgets, WebEngineWidgets, WebChannel  
  (Qt 5.15+ works too; set `CMAKE_PREFIX_PATH` accordingly)
- CMake ≥ 3.21
- A C++17 compiler (MSVC, clang, or gcc)
- Ninja or your preferred CMake generator

## Steps
```bash
cd sddai_gui_qtwebengine
cmake -S . -B build -G "Ninja" -DCMAKE_PREFIX_PATH="C:/Qt/6.6.1/msvc2019_64"
cmake --build build
```

On success the executable is at `build/sddai_gui_qtwebengine.exe` (or `./build/sddai_gui_qtwebengine` on Unix). Launch it, click “Open Project…”, and select a SDDAI directory; the graph will render in the embedded Cytoscape view.
