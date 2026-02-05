cmake_minimum_required(VERSION 3.21)

project(sddai_gui_qtwebengine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

# Try Qt 6 first, fall back to Qt 5 if necessary.
find_package(Qt6 COMPONENTS Widgets WebEngineWidgets WebChannel REQUIRED QUIET)
if(NOT Qt6_FOUND)
  find_package(Qt5 COMPONENTS Widgets WebEngineWidgets WebChannel REQUIRED)
  set(QT_PREFIX Qt5)
else()
  set(QT_PREFIX Qt6)
endif()

set(SRC
    src/main.cpp
    src/MainWindow.cpp
    src/ProjectScanner.cpp
    src/SpecExtractor.cpp
    src/SchemaLoader.cpp
    src/MetaStore.cpp
    src/RunLoader.cpp
    src/GraphBuilder.cpp
    src/Bridge.cpp
    src/FileIndexer.cpp
    src/LayoutEngine.cpp
    src/DocPreviewer.cpp
    src/sddai_bridge.cpp
    src/preview_window.cpp
)

set(HDR
    include/MainWindow.h
    include/ProjectScanner.h
    include/SpecExtractor.h
    include/SchemaLoader.h
    include/MetaStore.h
    include/RunLoader.h
    include/GraphBuilder.h
    include/Bridge.h
    include/GraphTypes.h
    include/FileIndexer.h
    include/LayoutEngine.h
    include/DocPreviewer.h
    src/sddai_bridge.h
    src/preview_window.h
)

if(QT_PREFIX STREQUAL "Qt6")
  qt_add_resources(QRC resources/app.qrc)
else()
  qt5_add_resources(QRC resources/app.qrc)
endif()

add_executable(${PROJECT_NAME} ${SRC} ${HDR} ${QRC})

target_include_directories(${PROJECT_NAME} PRIVATE include)

target_link_libraries(${PROJECT_NAME} PRIVATE
    ${QT_PREFIX}::Widgets
    ${QT_PREFIX}::WebEngineWidgets
    ${QT_PREFIX}::WebChannel
)

if(MSVC)
  target_compile_options(${PROJECT_NAME} PRIVATE /W4 /permissive- /EHsc)
else()
  target_compile_options(${PROJECT_NAME} PRIVATE -Wall -Wextra -Wpedantic)
endif()
