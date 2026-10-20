@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [NSA] Creating local Python environment...
    py -3 -m venv .venv
    if errorlevel 1 (echo Python 3.11+ is required & pause & exit /b 1)
)
echo [NSA] Installing required dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (echo Dependency installation failed. Check internet access. & pause & exit /b 1)
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo [NSA] Created .env - set NSA_ADMIN_PASSWORD and NSA_SESSION_SECRET to unlock staff dashboard.
)
start "" "http://127.0.0.1:8080"
echo [NSA] Starting website on local computer...
".venv\Scripts\python.exe" run_local.py
pause
