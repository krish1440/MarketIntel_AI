@echo off
TITLE MarketIntel - FastAPI Backend Server
COLOR 0B
cls

echo ===============================================================================
echo     MarketIntel AI: High-Performance FastAPI Backend Server
echo     REST API & WebSockets for Quantitative Analytics and Paper Trading
echo ===============================================================================
echo.

IF NOT EXIST "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment 'venv' not found!
    pause
    exit /b 1
)

echo Activating Python Virtual Environment...
call venv\Scripts\activate.bat
echo.
echo Launching Uvicorn Server at http://127.0.0.1:8000 ...
python scripts\run_server.py
pause

