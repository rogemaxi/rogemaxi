@echo off
rem Genesis Capital Intelligence - Windows launcher. Requires Python 3.11+ (python.org installer, "py" launcher).
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.11 or newer is required. Install it from https://www.python.org/downloads/windows/ then run this again.
  pause
  exit /b 1
)
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo Python 3.11 or newer is required.
  pause
  exit /b 1
)
py -3 -m gci serve %*
pause
