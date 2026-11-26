@echo off
title Kora Live - Auto Trend Publisher
cd /d "%~dp0"
chcp 65001 > nul
.\.venv\Scripts\python.exe scripts\auto_blogger_publisher.py
if errorlevel 1 (
    echo.
    echo [ERROR] An error occurred while generating today's article.
    pause
    exit /b 1
)
echo.
pause
