@echo off
call "%~dp0Run-Web-Workspace.cmd" update %*
exit /b %errorlevel%
