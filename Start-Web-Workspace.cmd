@echo off
call "%~dp0Run-Web-Workspace.cmd" start %*
exit /b %errorlevel%
