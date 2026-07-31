@echo off
REM ============================================================
REM  SETUP_AUTOSTART.bat - تسجيل المنصة في Task Scheduler
REM  شغّل هذا الملف مرة واحدة كـ Administrator
REM ============================================================

SET PROJECT_DIR=C:\Users\sahar\.gemini\antigravity\scratch\jil2_os_v9
SET TASK_NAME=JIL2_Platform_AutoStart

REM حذف المهمة القديمة إن وجدت
schtasks /Delete /TN "%TASK_NAME%" /F 2>nul

REM إنشاء مهمة جديدة تعمل عند تسجيل الدخول بأعلى صلاحيات
schtasks /Create /TN "%TASK_NAME%" ^
  /TR "\"%PROJECT_DIR%\START_PLATFORM.bat\"" ^
  /SC ONLOGON ^
  /RU "%USERNAME%" ^
  /RL HIGHEST ^
  /DELAY 0001:00 ^
  /F

echo.
echo ✅ تم التسجيل بنجاح في Task Scheduler
echo المنصة ستبدأ تلقائياً عند كل تشغيل لـ Windows
echo.
pause
