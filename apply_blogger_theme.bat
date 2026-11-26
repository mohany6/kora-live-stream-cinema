@echo off
title Kora Live - Apply Blogger Theme
cd /d "%~dp0"
chcp 65001 > nul
.\.venv\Scripts\python.exe scripts\copy_theme_to_clipboard.py
echo.
pause
