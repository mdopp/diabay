@echo off
REM DiaBay Installer Wrapper for Windows
REM Launches PowerShell installer with proper execution policy

echo.
echo ========================================
echo  DiaBay Installer for Windows
echo ========================================
echo.

REM Check if PowerShell is available
where powershell >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PowerShell not found
    echo Please install PowerShell and try again
    pause
    exit /b 1
)

REM Run PowerShell installer
powershell -ExecutionPolicy Bypass -File "%~dp0install.ps1"

pause
