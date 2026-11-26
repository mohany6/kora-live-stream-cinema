@echo off
title Kora Live Platform Launcher
chcp 65001 > nul
echo ======================================================================
echo           ⚽ تشغيل منصة كورة لايف بالكامل مجاناً ⚽
echo ======================================================================
cd /d "%~dp0"

echo [*] جاري تشغيل خادم FastAPI الخلفي على المنفذ 8000...
start "Kora-Backend" /min .\.venv\Scripts\python.exe -m uvicorn live_score.api.main:app --host 0.0.0.0 --port 8000

echo [*] جاري تفعيل المنفذ 80 المباشر (Port 80 Forwarder)...
start "Kora-Port80" /min .\.venv\Scripts\python.exe scripts/port80_forwarder.py

echo [*] جاري تفعيل المزامنة التلقائية مع DuckDNS (kora-live)...
start "Kora-DuckDNS" /min .\.venv\Scripts\python.exe scripts/duckdns_sync.py --domain kora-live --token f1cd22f6-bfbc-4534-94b6-a1cfdce0d8b5 --interval 600

echo [*] جاري تشغيل نفق Cloudflare المشفر بـ HTTPS...
start "Kora-Cloudflare-Tunnel" .\.tools\cloudflared.exe tunnel --url http://127.0.0.1:8000

echo.
echo ======================================================================
echo [✓] تم تشغيل جميع الخدمات بنجاح!
echo 🌍 دومين DuckDNS المباشر: http://kora-live.duckdns.org
echo ⚙️ لوحة التحكم: http://kora-live.duckdns.org/admin
echo ======================================================================
pause
