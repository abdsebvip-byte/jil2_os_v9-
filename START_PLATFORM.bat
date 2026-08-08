@echo off
title JIL-2 OS — منصة التداول الذكية
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ==========================================
echo  JIL-2 OS — بدء تشغيل المنصة الكاملة
echo ==========================================
echo.

REM إيقاف أي عمليات سابقة
taskkill /F /IM ngrok.exe >nul 2>&1
timeout /t 1 /nobreak >nul

echo [1/1] تشغيل حارس المنصة الدائم (Watchdog)...
.venv\Scripts\python.exe watchdog.py

pause
