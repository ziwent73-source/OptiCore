@echo off
title OptiCore Setup

echo ============================================
echo   OptiCore - Environment Setup
echo ============================================
echo.

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH!
    echo.
    echo Please install Python 3.10+ from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b
)

:: Show Python version
for /f "delims=" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo Python detected: %PY_VER%
echo.

:: Check and install dependencies
echo Checking dependencies...
:: Check if streamlit is importable
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies, please wait...
    python -m pip install streamlit numpy pandas matplotlib
    if errorlevel 1 (
        echo [WARNING] Retrying with pip...
        pip install streamlit numpy pandas matplotlib
    )
    echo.
    echo Setup complete! You can now double-click launch.bat to start.
) else (
    echo Dependencies already installed.
    echo You can double-click launch.bat to start OptiCore.
)

echo.
pause
