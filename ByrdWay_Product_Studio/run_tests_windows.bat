@echo off
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python -m unittest discover -s tests -v > test_results_windows.txt 2>&1
type test_results_windows.txt | more
echo Full results saved to test_results_windows.txt
pause
