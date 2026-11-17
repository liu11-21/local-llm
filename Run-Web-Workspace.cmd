@echo off
setlocal DisableDelayedExpansion
chcp 65001 >nul
set "WEB_PYTHON="
set "WEB_SCRIPT=%~dp0web_launcher.py"
if exist "%~dp0app\web_launcher.py" set "WEB_SCRIPT=%~dp0app\web_launcher.py"
for /f "delims=" %%P in ('call "%~dp0Find-Web-Python.cmd"') do set "WEB_PYTHON=%%P"
if not defined WEB_PYTHON (
  echo Python could not be verified. Review the detection errors above.
  echo If Python is missing, install official Python 3.12.10+ x64 from https://www.python.org/downloads/windows/
  echo Keep Windows security enabled. No interpreter was installed or updated.
  if not defined LOCALLLM_NO_PAUSE pause
  exit /b 1
)
"%WEB_PYTHON%" -I -S -B "%WEB_SCRIPT%" %*
set "WEB_RESULT=%errorlevel%"
if not "%WEB_RESULT%"=="0" (
  echo See WEB-START-HERE.txt or run Diagnose-Web-Workspace.cmd. Keep Windows security enabled.
  if not defined LOCALLLM_NO_PAUSE pause
)
exit /b %WEB_RESULT%
