#!/usr/bin/env python3
"""
Check admin status and bot configuration
"""

import sys
from database.db_init import DatabaseManager
from user_manager import UserManager, UserRoles
from config.config import config

def check_admin_status():
    """Check if admin is properly configured"""
    
    print("🔍 Checking Admin Status for Blue Pharma Bot")
    print("=" * 50)
    
    # Check configuration
    admin_id = config.ADMIN_TELEGRAM_ID
    print(f"📋 Admin Telegram ID in config: {admin_id}")
    
    if not admin_id:
        print("❌ No admin ID configured!")
        return
    
    # Check database
    try:
        db = DatabaseManager()
        user_manager = UserManager(db)
        
        # Get user info
        user_data = user_manager.get_or_create_user(admin_id)
        if user_data:
            print(f"👤 User found: {user_data['first_name']}")
            print(f"🎭 Current role: {user_data['role']}")
            print(f"🏢 Company: {user_data['company_name']}")
        else:
            print("❌ User not found in database")
            return
        
        # Check admin permissions
        role = user_manager.get_user_role(admin_id)
        is_admin = user_manager.is_admin(admin_id)
        is_staff = user_manager.is_staff(admin_id)
        
        print(f"🎯 Role check: {role}")
        print(f"👑 Is Admin: {is_admin}")
        print(f"👨‍💼 Is Staff: {is_staff}")
        
        if is_admin:
            print("✅ ADMIN STATUS CONFIRMED!")
            print()
            print("🎉 You have full admin access to:")
            print("   • View all orders and statistics")
            print("   • Manage inventory and pricing")
            print("   • Approve wholesale clients")
            print("   • Access all staff commands")
            print()
            print("🤖 Admin Commands Available:")
            print("   • /stats - Business statistics")
            print("   • /view_orders - All orders")
            print("   • /update_stock - Inventory management")
            print("   • /update_price - Price management")
            print("   • /approve_wholesale - Client management")
            print("   • /pending_requests - Wholesale requests")
        else:
            print("⚠️ Admin status not confirmed")
            
        # Check bot configuration
        print()
        print("🤖 Bot Configuration:")
        print(f"   • Business: {config.BUSINESS_NAME}")
        print(f"   • Contact: {config.CONTACT_PHONE}")
        print(f"   • Email: {config.CONTACT_EMAIL}")
        print(f"   • Bot Token: {'✅ Configured' if config.BOT_TOKEN else '❌ Missing'}")
        
    except Exception as e:
        print(f"❌ Error checking admin status: {e}")

if __name__ == "__main__":
    check_admin_status()
    input("\nPress Enter to continue...")
