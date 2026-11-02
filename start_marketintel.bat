@echo off
TITLE MarketIntel - Institutional Quantitative Market Intelligence & AI Trading
COLOR 0A
cls

echo ===============================================================================
echo     MarketIntel AI: Institutional Quantitative Trading Platform
echo     Mode: Strict Paper Trading (Rs.10,00,000 Virtual Capital)
echo ===============================================================================
echo.

IF NOT EXIST "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment 'venv' not found!
    echo Please create the virtual environment and install requirements first.
    pause
    exit /b 1
)

echo Activating Python Virtual Environment...
call venv\Scripts\activate.bat
echo.

:MENU
cls
echo ===============================================================================
echo     MarketIntel AI: Institutional Master Control Panel
echo ===============================================================================
echo.
echo   [1] Start Live Paper Trading Engine (Premarket 09:08 AM -> 03:30 PM)
echo   [2] Run EOD Data Ingestion Pipeline (Silver -> Gold Lakehouse Update)
echo   [3] Run Weekend Walk-Forward MLOps Model Retraining Tournament
echo   [4] Run Full 2-Year Out-Of-Sample Vault Simulation Audit
echo   [5] Start FastAPI REST & WebSocket Backend Server (Port 8000)
echo   [6] Exit
echo.
echo ===============================================================================
set /p choice="Enter choice [1-6]: "

if "%choice%"=="1" (
    echo.
    echo Starting Live Paper Trading Engine...
    python scripts\launch_system.py
    pause
    goto MENU
)

if "%choice%"=="2" (
    echo.
    echo Running Automated EOD Data Ingestion Pipeline...
    python scripts\run_eod_pipeline.py top300
    pause
    goto MENU
)

if "%choice%"=="3" (
    echo.
    echo Running Weekend MLOps Retraining & Champion Promotion Tournament...
    python scripts\test_champion_governance.py
    pause
    goto MENU
)

if "%choice%"=="4" (
    echo.
    echo Running 2-Year Vault Out-Of-Sample Simulation Audit...
    python scripts\run_real_day_by_day_vault_simulation.py
    pause
    goto MENU
)

if "%choice%"=="5" (
    echo.
    echo Launching FastAPI REST & WebSocket Backend Server...
    python scripts\run_server.py
    pause
    goto MENU
)

if "%choice%"=="6" (
    exit /b 0
)

echo Invalid choice. Please enter a number between 1 and 6.
timeout /t 2 >nul
goto MENU
