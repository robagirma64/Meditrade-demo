@echo off
echo ========================================
echo Blue Pharma Bot - Dependency Installer
echo ========================================
echo.

echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo.
    echo Please install Python first:
    echo 1. Go to https://python.org/downloads
    echo 2. Download and install Python 3.8+
    echo 3. Make sure to check "Add Python to PATH"
    echo 4. Restart this script after installation
    echo.
    pause
    exit /b 1
)

echo ✅ Python found!
python --version

echo.
echo Installing/upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing Bot Dependencies...
echo.

echo Installing python-telegram-bot...
python -m pip install python-telegram-bot==20.8

echo Installing python-dotenv...
python -m pip install python-dotenv==1.0.1

echo Installing python-dateutil...
python -m pip install python-dateutil==2.9.0

echo Installing colorlog...
python -m pip install colorlog==6.8.2

echo Installing validators...
python -m pip install validators==0.22.0

echo Installing typing-extensions...
python -m pip install typing-extensions==4.12.2

echo.
echo ========================================
echo ✅ Installation Complete!
echo ========================================
echo.
echo Your Blue Pharma bot is ready to run!
echo.
echo Next steps:
echo 1. Add your Telegram ID to the .env file
echo 2. Run: python main.py
echo.
pause
