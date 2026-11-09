@echo off
REM ByrdWay Product Engineering Studio - one-time setup on Windows 11
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.11+ is not installed. Install it from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^) and run this again.
  pause
  exit /b 1
)
if not exist .venv (
  echo Creating private Python environment in .venv ...
  py -3 -m venv .venv || goto :fail
)
call .venv\Scripts\activate.bat
for /f "delims=" %%v in ('python -c "from version import __version__; print(__version__)"') do set BWVER=%%v
echo ByrdWay Product Engineering Studio version %BWVER% (from version.py)
python -m pip install --upgrade pip || goto :fail
python -m pip install -r requirements.txt || goto :fail
echo.
echo Browser tests need the Chromium browser engine (about 150 MB download from Microsoft's Playwright CDN).
choice /M "Download Chromium for browser tests now"
if errorlevel 2 goto :skipbrowser
python -m playwright install chromium || goto :fail
:skipbrowser
echo.
echo Running self-test ...
python -m unittest discover -s tests
echo.
echo Setup finished. Start the Studio with START_WINDOWS.bat
pause
exit /b 0
:fail
echo Setup FAILED. See the messages above.
pause
exit /b 1
