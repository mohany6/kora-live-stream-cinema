@echo off
title Kora Live Platform Launcher (Free & Non-Admin Mode)
chcp 65001 > nul
echo ======================================================================
echo       ⚽ تشغيل منصة كورة لايف بالكامل مجاناً وبدون صلاحيات أدمن ⚽
echo ======================================================================
cd /d "%~dp0"

:: 1. تشغيل خادم FastAPI على المنفذ 8000
echo [*] جاري تشغيل خادم المنصة الموحد (FastAPI)...
start "Kora-Backend" /min .\.venv\Scripts\python.exe run.py

:: 2. تنظيف ملفات سجل ورابط النفق السابقة لمنع استخدام روابط قديمة
if exist ".tools\tunnel.log" del ".tools\tunnel.log"
if exist "data\tunnel_url.txt" del "data\tunnel_url.txt"

:: 3. تشغيل نفق Cloudflare المشفر دون طلب صلاحيات مسؤول
echo [*] جاري إطلاق نفق Cloudflare المشفر (HTTPS)...
start "Kora-Tunnel-Engine" /min cmd /c ".\.tools\cloudflared.exe tunnel --url http://127.0.0.1:8000 > .tools\tunnel.log 2>&1"

:: 4. استخراج الرابط العام التلقائي ونسخه للحافظة
echo [*] جاري استخراج الرابط العام العالمي...
.\.venv\Scripts\python.exe scripts/extract_tunnel_url.py .tools/tunnel.log
if errorlevel 1 (
    echo.
    echo [-] تنبيه: تعذر استخراج رابط النفق خلال المهلة المحددة.
    echo يرجى فحص ملف السجل: .tools\tunnel.log والتأكد من اتصال الإنترنت.
    echo ======================================================================
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo [تعليمات الاستخدام مع Blogger]:
echo 1. تم نسخ الرابط العام العالمي تلقائياً إلى الحافظة (Clipboard).
echo 2. يمكنك لصق هذا الرابط في زر "مشاهدة المباراة" داخل مقال Blogger.
echo 3. لإدارة الإعلانات والمباريات، افتح لوحة التحكم عبر الرابط أعلاه متبوعاً بـ /admin
echo ======================================================================
pause
