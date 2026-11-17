@echo off
call "%~dp0Run-Web-Workspace.cmd" diagnose %*
exit /b %errorlevel%
