@echo off
TITLE MarketIntel - Institutional Quantitative Market Intelligence & AI Paper Trading
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

echo Starting MarketIntel Master System Orchestrator...
python scripts\launch_system.py

pause

