@echo off
setlocal enabledelayedexpansion

set ROOT=%~dp0
set BUILD=%ROOT%build

if not exist "%BUILD%" mkdir "%BUILD%"

echo [build_v6] Configure...
cmake -S "%ROOT%" -B "%BUILD%" -DCMAKE_BUILD_TYPE=Release %*
if errorlevel 1 exit /b 1

echo [build_v6] Build...
cmake --build "%BUILD%" --config Release
exit /b %errorlevel%
