@echo off
title Kora Live - Facebook Page Studio
cd /d "%~dp0"
chcp 65001 > nul
start "" .\.venv\Scripts\pythonw.exe scripts\facebook_studio_gui.py
if errorlevel 1 (
    .\.venv\Scripts\python.exe scripts\facebook_studio_gui.py
)
