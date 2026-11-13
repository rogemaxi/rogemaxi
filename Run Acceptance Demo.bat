@echo off
cd /d "%~dp0"
set "GCI_PY=python"
where py >nul 2>nul && set "GCI_PY=py -3"
%GCI_PY% -m gci acceptance --out acceptance_output
%GCI_PY% -m unittest discover -s tests -t .
pause
