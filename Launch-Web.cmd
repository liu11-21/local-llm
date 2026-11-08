@echo off
cd /d "%~dp0"
python web_bridge.py
if errorlevel 1 pause
