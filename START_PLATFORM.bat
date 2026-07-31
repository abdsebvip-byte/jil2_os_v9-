@echo off
REM ====================================================
REM  START_PLATFORM.bat - تشغيل المنصة كاملة تلقائياً
REM  يُشغَّل عند بدء تشغيل Windows عبر Task Scheduler
REM ====================================================

SET PROJECT_DIR=C:\Users\sahar\.gemini\antigravity\scratch\jil2_os_v9
SET VENV_PY=%PROJECT_DIR%\.venv\Scripts\python.exe
SET NGROK_TOKEN=3HH31BrkYd4vyvgHi26bbQtRVQN_5QaCW31BwMPk5wQRMAEt4
SET NGROK_DOMAIN=bush-subdued-epilogue.ngrok-free.dev
SET NGROK_EXE=%PROJECT_DIR%\ngrok.exe

cd /d "%PROJECT_DIR%"

REM --- 1. تسجيل ngrok authtoken (مرة واحدة، لا تضر التكرار) ---
"%NGROK_EXE%" config add-authtoken %NGROK_TOKEN%

REM --- 2. تشغيل Streamlit في الخلفية ---
start "Streamlit" /min cmd /c "%VENV_PY% -m streamlit run app_v10.py --server.headless true >> streamlit.log 2>&1"

REM --- 3. الانتظار 5 ثوانٍ حتى يبدأ Streamlit ---
timeout /t 5 /nobreak >nul

REM --- 4. تشغيل ngrok بالرابط الثابت ---
start "ngrok" /min cmd /c "\"%NGROK_EXE%\" http --url=%NGROK_DOMAIN% 8501 >> ngrok.log 2>&1"

REM --- 5. تشغيل دaemon الفحص التلقائي ---
start "AutoScanner" /min cmd /c "%VENV_PY% auto_scanner.py >> auto_scanner.log 2>&1"

REM --- 6. تشغيل دaemon البوت ---
start "BotListener" /min cmd /c "%VENV_PY% bot_listener.py >> bot_listener.log 2>&1"

echo Platform started. URL: https://%NGROK_DOMAIN%
