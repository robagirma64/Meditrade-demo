@echo off
title Blue Pharma Trading PLC Bot - 24/7 Mode
color 0a

echo ===============================================
echo  Blue Pharma Trading PLC Telegram Bot
echo  24/7 Auto-Restart Mode
echo ===============================================
echo.

:loop
echo [%date% %time%] Starting bot...
cd /d "C:\BluePharmaBot"
python main.py

echo.
echo [%date% %time%] Bot stopped. Restarting in 15 seconds...
echo Press Ctrl+C to stop the bot permanently.
timeout /t 15 /nobreak

goto loop
