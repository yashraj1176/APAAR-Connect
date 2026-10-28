@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.10+ and enable Add Python to PATH.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 goto :error
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -r requirements.txt
if errorlevel 1 goto :error
python -m streamlit run app.py
if errorlevel 1 goto :error
exit /b 0
:error
echo Setup or app startup failed. Check the message above and the README troubleshooting steps.
pause
exit /b 1
