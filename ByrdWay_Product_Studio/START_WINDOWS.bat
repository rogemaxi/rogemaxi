@echo off
cd /d "%~dp0"
py -3 app.py
if errorlevel 1 (
 echo Python 3 not available. Install Python 3.11+ and try again.
 pause
)
