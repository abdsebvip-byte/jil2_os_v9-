@echo off
:: JIL2-NGROK-KEEPER — يحافظ على ngrok حياً للأبد
:: ضعه في Task Scheduler ليبدأ مع Windows

:loop
echo [%date% %time%] Starting ngrok...
"%~dp0ngrok.exe" http 8501
echo [%date% %time%] ngrok died — restarting in 3 seconds...
timeout /t 3 /nobreak >nul
goto loop
