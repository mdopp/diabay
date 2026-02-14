@echo off
REM Production Deployment Script for DiaBay (Windows)
REM This builds the frontend and runs the backend in production mode

echo.
echo ========================================
echo  DiaBay - Windows Production Deployment
echo ========================================
echo.

REM Check if Node.js is installed (only needed if building frontend)
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Node.js not found - using pre-built frontend
    echo [INFO] To build frontend yourself, install Node.js: winget install OpenJS.NodeJS
    goto :skip_build
)

REM Build frontend
echo [1/2] Building frontend...
cd frontend
if exist node_modules (
    echo [INFO] Dependencies already installed
) else (
    echo [INFO] Installing dependencies...
    call npm install
)
call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Frontend build failed
    exit /b 1
)
cd ..
echo [OK] Frontend built successfully
echo.

:skip_build

REM Check if dist folder exists
if not exist "frontend\dist" (
    echo [ERROR] Frontend build not found at frontend\dist
    echo [ERROR] Please run: cd frontend ^&^& npm run build
    exit /b 1
)

REM Start backend (which will serve the built frontend)
echo [2/2] Starting backend in production mode...
cd backend

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate
) else (
    echo [WARNING] Virtual environment not found at backend\.venv
    echo [WARNING] Using global Python - recommend creating venv first
)

echo.
echo ========================================
echo  Starting DiaBay Backend
echo ========================================
echo  Access DiaBay at: http://localhost:8000
echo  Press Ctrl+C to stop
echo ========================================
echo.

python main.py
