@echo off
title EPC Solar Engine Premium v0.4.1
echo ========================================================
echo     EPC Solar Engine - Executive Decision Platform
echo ========================================================
echo.
echo Starting local calculation engine and interface...
echo.

:: Launch FastAPI server in background
start /B "" "backend\.venv\Scripts\python.exe" -m uvicorn api:app --host 127.0.0.1 --port 8000 --app-dir backend

:: Wait 2 seconds for server startup
timeout /t 2 /nobreak >nul

:: Open default web browser
start "" "http://127.0.0.1:8000/static_app/index.html"

echo.
echo Application running at: http://127.0.0.1:8000/static_app/index.html
echo (Keep this window open while using the software. Close to stop engine.)
echo.
