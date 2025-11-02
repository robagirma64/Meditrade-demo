# 🐍 Install Python & Dependencies for Blue Pharma Bot

## Step 1: Install Python Properly

### Option A: Download from Official Site (Recommended)
1. **Go to**: https://www.python.org/downloads/
2. **Click**: "Download Python 3.12.x" (latest version)
3. **Run the installer**
4. **⚠️ IMPORTANT**: Check "Add Python to PATH" during installation
5. **Click**: "Install Now"

### Option B: Install from Microsoft Store
1. **Open**: Microsoft Store
2. **Search**: "Python 3.12"
3. **Install**: Python 3.12

## Step 2: Verify Installation
Open **Command Prompt** or **PowerShell** and run:
```cmd
python --version
```
You should see something like: `Python 3.12.x`

## Step 3: Install Dependencies
In the `C:\BluePharmaBot` folder, run:
```cmd
pip install -r requirements.txt
```

## Step 4: Test Your Setup
```cmd
python -c "print('✅ Python is working!')"
```

## Step 5: Start Your Bot
```cmd
python main.py
```

---

## If You Get Errors:

### "Python not found"
- Restart your command prompt after installing Python
- Make sure you checked "Add Python to PATH"

### "pip not found"
```cmd
python -m ensurepip --upgrade
```

### Dependencies fail to install
```cmd
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Quick Install Script (Run This!)
```cmd
python -m pip install --upgrade pip
python -m pip install python-telegram-bot==20.8
python -m pip install python-dotenv==1.0.1
python -m pip install python-dateutil==2.9.0
python -m pip install colorlog==6.8.2
python -m pip install validators==0.22.0
python -m pip install typing-extensions==4.12.2
```
