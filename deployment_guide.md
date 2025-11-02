# Blue Pharma Trading PLC Bot - 24/7 Deployment Guide

## 🌐 Cloud Hosting Options (Recommended)

### **1. Heroku (Free Tier Available)**
```bash
# Install Heroku CLI first
# Create requirements.txt
pip freeze > requirements.txt

# Create Procfile
echo "worker: python main.py" > Procfile

# Deploy to Heroku
heroku create bluepharma-bot
heroku config:set TELEGRAM_BOT_TOKEN=your_token_here
git add .
git commit -m "Deploy Blue Pharma Bot"
git push heroku main
heroku ps:scale worker=1
```

### **2. Railway (Modern, Easy)**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway new
railway add --database postgresql  # Optional: for production DB
railway deploy
railway variables set TELEGRAM_BOT_TOKEN=your_token_here
```

### **3. DigitalOcean App Platform**
```bash
# Create app.yaml
echo "name: bluepharma-bot
services:
- name: worker
  source_dir: /
  github:
    repo: your-repo/bluepharma-bot
    branch: main
  run_command: python main.py
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: TELEGRAM_BOT_TOKEN
    value: your_token_here" > app.yaml
```

### **4. Google Cloud Run**
```dockerfile
# Create Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

CMD ["python", "main.py"]
```

## 🖥️ Local Windows Solutions

### **Option 2: Windows Service**
```python
# Create windows_service.py
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import subprocess

class BluePharmaService(win32serviceutil.ServiceFramework):
    _svc_name_ = "BluePharmaBot"
    _svc_display_name_ = "Blue Pharma Trading PLC Telegram Bot"
    _svc_description_ = "24/7 Telegram Bot for Blue Pharma Trading PLC"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                            servicemanager.PYS_SERVICE_STARTED,
                            (self._svc_name_, ''))
        self.main()

    def main(self):
        # Change to bot directory
        os.chdir(r'C:\BluePharmaBot')
        
        # Run the bot
        while True:
            try:
                subprocess.run([sys.executable, 'main.py'], check=True)
            except Exception as e:
                servicemanager.LogErrorMsg(f"Bot crashed: {e}")
                time.sleep(30)  # Wait before restart

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(BluePharmaService)
```

### **Option 3: Task Scheduler with Auto-Restart**
```batch
@echo off
:loop
cd /d "C:\BluePharmaBot"
python main.py
echo Bot stopped at %date% %time%. Restarting in 10 seconds...
timeout /t 10
goto loop
```

### **Option 4: PowerShell Script with Monitoring**
```powershell
# Create run_bot_24_7.ps1
$BotPath = "C:\BluePharmaBot"
$PythonPath = "python"  # or full path to python.exe

while ($true) {
    try {
        Write-Host "$(Get-Date): Starting Blue Pharma Bot..." -ForegroundColor Green
        Set-Location $BotPath
        
        $process = Start-Process -FilePath $PythonPath -ArgumentList "main.py" -Wait -PassThru
        
        if ($process.ExitCode -eq 0) {
            Write-Host "$(Get-Date): Bot stopped normally" -ForegroundColor Yellow
        } else {
            Write-Host "$(Get-Date): Bot crashed with exit code $($process.ExitCode)" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "$(Get-Date): Error starting bot: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host "$(Get-Date): Restarting in 30 seconds..." -ForegroundColor Cyan
    Start-Sleep -Seconds 30
}
```

## 🛠️ VPS/Server Solutions

### **Option 5: VPS with Screen/tmux**
```bash
# For Linux VPS
sudo apt update
sudo apt install python3 python3-pip screen -y

# Upload your bot files
# Install dependencies
pip3 install -r requirements.txt

# Run in screen session
screen -S bluepharma_bot
python3 main.py
# Press Ctrl+A, then D to detach

# To reattach later:
screen -r bluepharma_bot
```

### **Option 6: Docker Container**
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

CMD ["python", "main.py"]
```

```bash
# Build and run
docker build -t bluepharma-bot .
docker run -d --name bluepharma-bot --restart unless-stopped \
  -e TELEGRAM_BOT_TOKEN=your_token_here \
  bluepharma-bot
```

## ⚙️ Setup Instructions

### **Quick Start - Windows Task Scheduler (Easiest)**

1. **Create batch file:**
