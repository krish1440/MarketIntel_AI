@echo off
REM ========================================================
REM MarketIntel: Daily End-Of-Day Incremental Sync
REM Scheduled to run every weekday at 15:45 IST
REM ========================================================

cd /d D:\PROJECT\MarketIntel
set PYTHONIOENCODING=utf-8
call .\venv\Scripts\activate.bat
python scripts\daily_sync.py >> logs\daily_sync.log 2>&1
deactivate

