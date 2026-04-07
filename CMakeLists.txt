cmake_minimum_required(VERSION 3.21)

project(ctcp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
include(CTest)
include(GNUInstallDirs)

option(CTCP_ENABLE_COMPILER_LAUNCHER "Enable compiler launcher (ccache/sccache) auto-detection" ON)

if(CTCP_ENABLE_COMPILER_LAUNCHER)
  find_program(CTCP_CCACHE_PROGRAM ccache)
  find_program(CTCP_SCCACHE_PROGRAM sccache)
  if(CTCP_CCACHE_PROGRAM)
    set(CTCP_COMPILER_LAUNCHER "${CTCP_CCACHE_PROGRAM}")
  elseif(CTCP_SCCACHE_PROGRAM)
    set(CTCP_COMPILER_LAUNCHER "${CTCP_SCCACHE_PROGRAM}")
  else()
    set(CTCP_COMPILER_LAUNCHER "")
  endif()

  if(CTCP_COMPILER_LAUNCHER)
    message(STATUS "CTCP compiler launcher: ${CTCP_COMPILER_LAUNCHER}")
    set(CMAKE_C_COMPILER_LAUNCHER "${CTCP_COMPILER_LAUNCHER}" CACHE STRING "C compiler launcher" FORCE)
    set(CMAKE_CXX_COMPILER_LAUNCHER "${CTCP_COMPILER_LAUNCHER}" CACHE STRING "CXX compiler launcher" FORCE)
  endif()
endif()

# Headless engine target (default and only runtime target).
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

if(BUILD_TESTING)
  find_package(Python3 COMPONENTS Interpreter QUIET)
  if(Python3_Interpreter_FOUND)
    add_test(
      NAME verify_tools_selftest
      COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tools/tests/test_verify_tools.py
    )
  endif()
endif()
