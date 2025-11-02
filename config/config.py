# -*- coding: utf-8 -*-
"""
Configuration management for Blue Pharma Trading PLC Telegram Bot
Handles all environment variables and settings
"""

import os
from dotenv import load_dotenv
from typing import Optional

class Config:
    """Configuration manager for the Blue Pharma bot"""
    
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # Telegram Bot Configuration
        self.BOT_TOKEN = os.getenv('BOT_TOKEN')
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")
        
        # Database Configuration
        self.DATABASE_PATH = os.getenv('DATABASE_PATH', 'database/bluepharma.db')
        
        # Logging Configuration
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = os.getenv('LOG_FILE', 'logs/bot.log')
        
        # Business Information
        self.BUSINESS_NAME = os.getenv('BUSINESS_NAME', 'Blue Pharma Trading PLC')
        self.CONTACT_PHONE = os.getenv('CONTACT_PHONE', '+1-234-567-8900')
        self.CONTACT_EMAIL = os.getenv('CONTACT_EMAIL', 'info@bluepharma.com')
        self.BUSINESS_HOURS = os.getenv('BUSINESS_HOURS', 
            'Monday-Friday: 9:00 AM - 6:00 PM, Saturday: 9:00 AM - 2:00 PM')
        self.ADDRESS = os.getenv('ADDRESS', 
            '123 Pharmacy Street, Medical District, City, State 12345')
        
        # Security Settings
        self.ADMIN_TELEGRAM_ID = self._get_int_env('ADMIN_TELEGRAM_ID')
        self.MAX_ORDER_QUANTITY = self._get_int_env('MAX_ORDER_QUANTITY', 1000)
        self.RATE_LIMIT_MESSAGES = self._get_int_env('RATE_LIMIT_MESSAGES', 30)
        self.RATE_LIMIT_WINDOW = self._get_int_env('RATE_LIMIT_WINDOW', 60)
        
        # Payment Settings (Optional)
        self.PAYMENT_PROVIDER = os.getenv('PAYMENT_PROVIDER', 'stripe')
        self.PAYMENT_TOKEN = os.getenv('PAYMENT_TOKEN')
        
        # Notification Settings
        self.ENABLE_NOTIFICATIONS = self._get_bool_env('ENABLE_NOTIFICATIONS', True)
        self.NOTIFICATION_CHAT_ID = self._get_int_env('NOTIFICATION_CHAT_ID')
        
        # Development Settings
        self.DEBUG_MODE = self._get_bool_env('DEBUG_MODE', False)
        self.WEBHOOK_URL = os.getenv('WEBHOOK_URL')
    
    def _get_int_env(self, key: str, default: Optional[int] = None) -> Optional[int]:
        """Get integer environment variable"""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default
    
    def _get_bool_env(self, key: str, default: bool = False) -> bool:
        """Get boolean environment variable"""
        value = os.getenv(key, '').lower()
        return value in ('true', '1', 'yes', 'on')
    
    def validate_config(self) -> bool:
        """Validate required configuration"""
        if not self.BOT_TOKEN:
            print("❌ BOT_TOKEN is required")
            return False
        
        if self.BOT_TOKEN == 'your_bot_token_here':
            print("❌ Please update BOT_TOKEN in .env file")
            return False
        
        if not self.ADMIN_TELEGRAM_ID:
            print("⚠️  Warning: ADMIN_TELEGRAM_ID not set. You'll need to add it later for admin functions.")
        
        print("✅ Configuration validated successfully")
        return True
    
    def print_config(self):
        """Print current configuration (without sensitive data)"""
        print("🔧 Blue Pharma Bot Configuration:")
        print(f"   Business Name: {self.BUSINESS_NAME}")
        print(f"   Database Path: {self.DATABASE_PATH}")
        print(f"   Log Level: {self.LOG_LEVEL}")
        print(f"   Log File: {self.LOG_FILE}")
        print(f"   Contact Phone: {self.CONTACT_PHONE}")
        print(f"   Contact Email: {self.CONTACT_EMAIL}")
        print(f"   Max Order Quantity: {self.MAX_ORDER_QUANTITY}")
        print(f"   Rate Limit: {self.RATE_LIMIT_MESSAGES} msgs/{self.RATE_LIMIT_WINDOW}s")
        print(f"   Debug Mode: {self.DEBUG_MODE}")
        print(f"   Bot Token: {'✅ Set' if self.BOT_TOKEN else '❌ Missing'}")

# Create global config instance
config = Config()
