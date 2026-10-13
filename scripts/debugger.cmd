@echo off
setlocal

set "SCRIPT_DIR=%~dp0"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 "%SCRIPT_DIR%debugger.py" %*
  exit /b %ERRORLEVEL%
)

python "%SCRIPT_DIR%debugger.py" %*
exit /b %ERRORLEVEL%
