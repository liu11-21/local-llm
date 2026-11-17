@echo off
call "%~dp0Run-Web-Workspace.cmd" stop %*
exit /b %errorlevel%
