@echo off
cd /d "%~dp0"
if exist .venv\Scripts\pythonw.exe (
  start "" .venv\Scripts\pythonw.exe app.py
  exit /b 0
)
REM Fallback (v0.1 behaviour): system Python. Run install_windows.bat first for full features.
py -3 app.py
if errorlevel 1 (
 echo Python 3 not available or dependencies missing. Run install_windows.bat first.
 pause
)
