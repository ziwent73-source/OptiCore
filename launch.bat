@echo off
title OptiCore

echo ============================================
echo   OptiCore - Optical System Calculator
echo   Starting...
echo ============================================
echo.

:: Quick check that Python and deps are available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please run run.bat first to set up the environment.
    pause
    exit /b
)

python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Dependencies not installed. Running setup first...
    call "%~dp0run.bat"
)

echo Starting OptiCore...
echo Browser will open automatically.
echo.

python -m streamlit run "%~dp0app.py" --server.headless true

pause
