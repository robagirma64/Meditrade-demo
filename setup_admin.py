"""
Helper script to set up admin Telegram ID in .env file
"""

import os
from pathlib import Path

def update_env_file():
    """Update the .env file with admin Telegram ID"""
    env_file = Path('.env')
    
    if not env_file.exists():
        print("❌ .env file not found!")
        return False
    
    print("🆔 Setting up Admin Telegram ID")
    print()
    print("📋 How to get your Telegram ID:")
    print("1. Open Telegram")
    print("2. Message @userinfobot")
    print("3. Copy the number it gives you")
    print()
    
    telegram_id = input("Enter your Telegram ID: ").strip()
    
    if not telegram_id.isdigit():
        print("❌ Please enter a valid number")
        return False
    
    # Read current .env file
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Update the admin ID line
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('ADMIN_TELEGRAM_ID='):
            lines[i] = f'ADMIN_TELEGRAM_ID={telegram_id}\n'
            updated = True
            break
    
    if updated:
        # Write back to file
        with open(env_file, 'w') as f:
            f.writelines(lines)
        
        print(f"✅ Admin Telegram ID set to: {telegram_id}")
        print("🎉 Your bot is now ready to run!")
        print()
        print("🚀 Next step: Double-click 'run_bot.bat' to start your bot")
        return True
    else:
        print("❌ Could not find ADMIN_TELEGRAM_ID line in .env file")
        return False

if __name__ == "__main__":
    update_env_file()
    input("\nPress Enter to continue...")
