@echo off
cd /d "%~dp0"
if not exist "data\tmp" mkdir "data\tmp"
set "TEMP=%CD%\data\tmp"
set "TMP=%CD%\data\tmp"
set "PIP_CACHE_DIR=%CD%\data\pip-cache"
where python >nul 2>nul
if errorlevel 1 (
  echo Install Python 3.11 or newer from https://www.python.org/downloads/ and enable Add Python to PATH.
  pause
  exit /b 1
)
where ollama >nul 2>nul
if errorlevel 1 (
  echo Install Ollama from https://ollama.com/download/windows then reopen this script.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if errorlevel 1 goto fail
set "POLICYBOT_REQUIREMENTS=requirements.txt"
if exist "requirements-lock.txt" set "POLICYBOT_REQUIREMENTS=requirements-lock.txt"
".venv\Scripts\python.exe" -m pip install -r "%POLICYBOT_REQUIREMENTS%"
if errorlevel 1 goto fail
".venv\Scripts\python.exe" local_models.py --pull
if errorlevel 1 goto fail
echo Ready! Double-click start.bat to open Policybot.
pause
exit /b 0
:fail
echo Setup failed. Check the message above and retry.
pause
exit /b 1
