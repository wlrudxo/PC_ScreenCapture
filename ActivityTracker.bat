@echo off
setlocal
cd /d "%~dp0"

REM Prefer project venv if present, fall back to system Python.
if exist "venv313\Scripts\pythonw.exe" (
  set "PYTHONW=venv313\Scripts\pythonw.exe"
) else if exist "venv\Scripts\pythonw.exe" (
  set "PYTHONW=venv\Scripts\pythonw.exe"
) else if exist ".venv\Scripts\pythonw.exe" (
  set "PYTHONW=.venv\Scripts\pythonw.exe"
) else (
  set "PYTHONW=pythonw"
)

start "" /B "%PYTHONW%" main_webview.pyw
endlocal
