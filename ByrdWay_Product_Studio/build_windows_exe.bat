@echo off
REM Builds dist\ByrdWayStudio\ByrdWayStudio.exe with PyInstaller.
REM STATUS: packaging configuration provided; the Windows executable has NOT been built or tested
REM by the developer (no Windows machine was available). Run CLEAN_MACHINE_SMOKE_TEST in USER_GUIDE.md after building.
cd /d "%~dp0"
if not exist .venv ( echo Run install_windows.bat first. & pause & exit /b 1 )
call .venv\Scripts\activate.bat
for /f "delims=" %%v in ('python -c "from version import __version__; print(__version__)"') do set BWVER=%%v
echo ByrdWay Product Engineering Studio version %BWVER% (from version.py)
python -m pip install -r requirements-build.txt || goto :fail
python -m unittest discover -s tests || goto :fail
pyinstaller --noconfirm byrdway_studio.spec || goto :fail
echo Built: dist\ByrdWayStudio\ByrdWayStudio.exe
pause
exit /b 0
:fail
echo Build FAILED.
pause
exit /b 1
