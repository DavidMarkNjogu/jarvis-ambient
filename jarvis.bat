@echo off
cd /d "%~dp0"
if not exist .env ".venv\Scripts\python.exe" -m jarvis.setup
".venv\Scripts\python.exe" -m jarvis %*
if errorlevel 1 pause
