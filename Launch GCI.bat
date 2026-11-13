@echo off
rem Genesis Capital Intelligence - Windows launcher. Requires Python 3.11+ (python.org installer).
cd /d "%~dp0"
set "GCI_PY="
where py >nul 2>nul && set "GCI_PY=py -3"
if not defined GCI_PY (
  where python >nul 2>nul && set "GCI_PY=python"
)
if not defined GCI_PY (
  echo Python 3.11 or newer is required. Install it from https://www.python.org/downloads/windows/ then run this again.
  pause
  exit /b 1
)
%GCI_PY% -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo Python 3.11 or newer is required.
  pause
  exit /b 1
)
%GCI_PY% -m gci serve %*
pause
