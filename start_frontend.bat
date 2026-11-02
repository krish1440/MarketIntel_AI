@echo off
TITLE MarketIntel - Frontend UI (Port 3000)
COLOR 0A
cls

echo ===============================================================================
echo     MarketIntel AI: Institutional Frontend UI Console
echo     Running at http://localhost:3000
echo ===============================================================================
echo.

cd frontend
call npm run dev
pause

