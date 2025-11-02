# Blue Pharma Trading PLC Bot - Advanced 24/7 Runner
# Run this script to keep the bot running 24/7 with monitoring

param(
    [string]$BotPath = "C:\BluePharmaBot",
    [string]$LogFile = "C:\BluePharmaBot\bot_log.txt"
)

# Set console title and colors
$Host.UI.RawUI.WindowTitle = "Blue Pharma Bot - 24/7 Monitor"
Clear-Host

Write-Host "================================================" -ForegroundColor Cyan
Write-Host " Blue Pharma Trading PLC Telegram Bot" -ForegroundColor Green
Write-Host " 24/7 Advanced Monitoring & Auto-Restart" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Create log file if it doesn't exist
if (-not (Test-Path $LogFile)) {
    New-Item -ItemType File -Path $LogFile -Force | Out-Null
}

# Function to write logs
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    # Write to console with colors
    switch ($Level) {
        "ERROR" { Write-Host $logEntry -ForegroundColor Red }
        "WARN"  { Write-Host $logEntry -ForegroundColor Yellow }
        "INFO"  { Write-Host $logEntry -ForegroundColor Green }
        default { Write-Host $logEntry -ForegroundColor White }
    }
    
    # Write to log file
    Add-Content -Path $LogFile -Value $logEntry
}

# Main monitoring loop
$restartCount = 0
$startTime = Get-Date

Write-Log "Bot monitor started. Press Ctrl+C to stop."
Write-Log "Bot directory: $BotPath"
Write-Log "Log file: $LogFile"

while ($true) {
    try {
        Write-Log "Starting Blue Pharma Bot (Restart #$restartCount)..."
        
        # Change to bot directory
        Set-Location $BotPath
        
        # Start the bot process
        $process = Start-Process -FilePath "python" -ArgumentList "main.py" -Wait -PassThru -NoNewWindow
        
        $restartCount++
        $runtime = (Get-Date) - $startTime
        
        if ($process.ExitCode -eq 0) {
            Write-Log "Bot stopped normally after running for $($runtime.ToString('hh\:mm\:ss'))" -Level "INFO"
        } else {
            Write-Log "Bot crashed with exit code $($process.ExitCode) after $($runtime.ToString('hh\:mm\:ss'))" -Level "ERROR"
        }
        
        # Check if too many restarts
        if ($restartCount -gt 50) {
            Write-Log "Too many restarts ($restartCount). Increasing delay to 5 minutes." -Level "WARN"
            Start-Sleep -Seconds 300
        } elseif ($restartCount -gt 20) {
            Write-Log "Multiple restarts detected. Waiting 2 minutes before restart..." -Level "WARN"
            Start-Sleep -Seconds 120
        } else {
            Write-Log "Restarting in 30 seconds..." -Level "INFO"
            Start-Sleep -Seconds 30
        }
        
        $startTime = Get-Date
        
    } catch {
        Write-Log "Error starting bot: $($_.Exception.Message)" -Level "ERROR"
        Write-Log "Waiting 60 seconds before retry..." -Level "WARN"
        Start-Sleep -Seconds 60
    }
}

Write-Log "Bot monitor stopped." -Level "INFO"
