@echo off
setlocal
chcp 65001 >nul
set "WEB_SCRIPT=%~dp0web_launcher.py"
if exist "%~dp0app\web_launcher.py" set "WEB_SCRIPT=%~dp0app\web_launcher.py"
py -3.12 -I -S -B "%WEB_SCRIPT%" start %*
if errorlevel 1 (
  echo.
  echo Please install official Python 3.12 x64 from https://www.python.org/downloads/windows/
  echo Keep Windows security enabled. See WEB-START-HERE.txt or run Diagnose-Web-Workspace.cmd.
  pause
)
