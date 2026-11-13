@echo off
cd /d "%~dp0"
py -3 -m gci acceptance --out acceptance_output
py -3 -m unittest discover -s tests -t .
pause
