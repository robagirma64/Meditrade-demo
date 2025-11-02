@echo off
echo ========================================
echo 🏥 Blue Pharma Trading PLC Bot
echo ========================================
echo.

REM Use the full Python path we found
set PYTHON_PATH=C:\Users\hp\AppData\Local\Programs\Python\Python312\python.exe

echo ✅ Python found at: %PYTHON_PATH%
echo.

echo 🔧 Checking configuration...
%PYTHON_PATH% -c "from config.config import config; print('✅ Configuration loaded!'); config.validate_config()"

if %errorlevel% neq 0 (
    echo.
    echo ⚠️  Configuration issues detected.
    echo Please check your .env file:
    echo 1. Make sure BOT_TOKEN is set
    echo 2. Add your ADMIN_TELEGRAM_ID
    echo.
    pause
    exit /b 1
)

echo.
echo 🚀 Starting your Blue Pharma bot...
echo 📞 Bot will be available 24/7 until you stop it
echo 🛑 Press Ctrl+C to stop the bot
echo.

%PYTHON_PATH% bot.py

echo.
echo 👋 Bot stopped. Press any key to exit.
pause
