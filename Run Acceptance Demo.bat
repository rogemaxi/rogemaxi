@echo off
cd /d "%~dp0"
py -3 -m gci demo --amount 40 --out demo_output
py -3 -m gci demo --amount 10000 --out demo_output
py -3 -m unittest discover -s tests -t .
pause
