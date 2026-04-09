@echo off
title Vostok Web Terminal
echo.
echo  ========================================
echo    VOSTOK WEB TERMINAL - Starting...
echo  ========================================
echo.

cd /d "%~dp0"

:: Use the project's virtual environment
call venv\Scripts\activate.bat

:: Launch Streamlit
echo  Starting Streamlit on http://localhost:8501
echo  Press Ctrl+C to stop
echo.
streamlit run app.py --server.port 8501 --server.headless true

pause
