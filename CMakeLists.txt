cmake_minimum_required(VERSION 3.21)

project(ctcp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
include(CTest)
include(GNUInstallDirs)

option(CTCP_ENABLE_GUI "Build Qt GUI example target" OFF)

if(CTCP_ENABLE_GUI)
  set(CMAKE_AUTOMOC ON)
  # GUI example target (optional).
  find_package(Qt6 COMPONENTS Widgets WebEngineWidgets WebChannel QUIET)
  if(Qt6_FOUND)
    set(QT_PREFIX Qt6)
  else()
    find_package(Qt5 COMPONENTS Widgets WebEngineWidgets WebChannel REQUIRED)
    set(QT_PREFIX Qt5)
  endif()

  set(GUI_SRC
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

  set(GUI_HDR
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

  add_executable(ctcp ${GUI_SRC} ${GUI_HDR} ${QRC})
  target_include_directories(ctcp PRIVATE include)
  target_link_libraries(ctcp PRIVATE
      ${QT_PREFIX}::Widgets
      ${QT_PREFIX}::WebEngineWidgets
      ${QT_PREFIX}::WebChannel
  )

  if(MSVC)
    target_compile_options(ctcp PRIVATE /W4 /permissive- /EHsc)
  else()
    target_compile_options(ctcp PRIVATE -Wall -Wextra -Wpedantic)
  endif()

  install(TARGETS ctcp RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})

  if(BUILD_TESTING)
    add_test(NAME app_smoke COMMAND $<TARGET_FILE:ctcp> --smoke)
    if(UNIX AND NOT APPLE)
      set_tests_properties(app_smoke PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
    endif()
  endif()
else()
  # Headless engine target (default).
  add_executable(ctcp_headless src/headless_main.cpp)
  if(MSVC)
    target_compile_options(ctcp_headless PRIVATE /W4 /permissive- /EHsc)
  else()
    target_compile_options(ctcp_headless PRIVATE -Wall -Wextra -Wpedantic)
  endif()

  install(TARGETS ctcp_headless RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})

  if(BUILD_TESTING)
    add_test(NAME headless_smoke COMMAND $<TARGET_FILE:ctcp_headless> --smoke)
  endif()
endif()

if(BUILD_TESTING)
  find_package(Python3 COMPONENTS Interpreter QUIET)
  if(Python3_Interpreter_FOUND)
    add_test(
      NAME verify_tools_selftest
      COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tools/tests/test_verify_tools.py
    )
  endif()
endif()
