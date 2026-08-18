@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [%date% %time%] Restart Django_APScheduler...
nssm\nssm.exe restart Django_APScheduler 2>nul

echo [%date% %time%] Done.

:: Wait for process to fully exit
timeout /t 10 /nobreak >nul

exit /b 0
