@echo off
title Spotify Downloader Pro
cls

echo ========================================================
echo         SPOTIFY DOWNLOADER PRO - LAUNCHER
echo ========================================================
echo.

cd /d "%~dp0"

IF EXIST ".venv\Scripts\python.exe" (
    echo [INFO] Activating virtual environment (.venv)...
    call .venv\Scripts\activate.bat
    python run_app.py
) ELSE (
    echo [INFO] Virtual environment not found, using system Python...
    python run_app.py
)

pause
