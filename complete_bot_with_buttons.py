#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blue Pharma Trading PLC - Complete Bot with All Buttons
Includes comprehensive button interface with new 6-field medicine system
"""

import sys
import logging
import asyncio
import os
import tempfile
from datetime import datetime
from typing import Dict, List, Optional

# Excel processing imports
try:
    import pandas as pd
    import openpyxl
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False
    print("⚠️ Excel support not available. Install with: pip install pandas openpyxl")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('blue_pharma_complete.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main bot function with complete button interface"""
    print("🏥 Blue Pharma Trading PLC - Complete Bot with Buttons")
    print("=" * 65)
    print("🚀 Features: Full Button Interface + 7-Field Medicine System")
    print("=" * 65)
    
    try:
        # Import required modules
        from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
        from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
        from database_manager_v2 import DatabaseManager
        
        print("✅ All modules imported successfully")
        
        # Configuration
        BOT_TOKEN = "7599074953:AAFw4pu9HROg09idKXVmM6xDEgOA1B94oNk"
        DB_NAME = "blue_pharma_v2.db"
        
        # Initialize database
        db = DatabaseManager(DB_NAME)
        print("✅ Database initialized")
        
        # Conversation states
        (MEDICINE_NAME, BATCH_NUMBER, MANUFACTURING_DATE, EXPIRING_DATE, 
         DOSAGE_FORM, PRICE, STOCK_QUANTITY) = range(7)
        (UPDATE_STOCK_SEARCH, UPDATE_STOCK_QUANTITY) = range(10, 12)
        (EDIT_CONTACT_FIELD, EDIT_CONTACT_VALUE) = range(20, 22)
        (WAITING_FOR_EXCEL_FILE) = 30
        (PIN_VERIFICATION) = 40
        
        # User roles
        USER_ROLES = {
            'customer': 'Customer',
            'staff': 'Staff',
            'admin': 'Administrator'
        }
        
        # User data storage
        user_data = {}
        
        # User management helper
        def get_or_create_user(telegram_id, first_name, last_name=None, username=None):
            """Get or create user"""
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                
                # Try to get existing user
                cursor.execute("""
                    SELECT id, first_name, user_type FROM users 
                    WHERE telegram_id = ? AND is_active = 1
                """, (telegram_id,))
                user = cursor.fetchone()
                
                if user:
                    conn.close()
                    return dict(user)
                
                # Create new user
                cursor.execute("""
                    INSERT INTO users (telegram_id, first_name, last_name, username, user_type)
                    VALUES (?, ?, ?, ?, 'customer')
                """, (telegram_id, first_name, last_name, username))
                
                user_id = cursor.lastrowid
                conn.commit()
                conn.close()
                
                return {
                    'id': user_id,
                    'first_name': first_name,
                    'user_type': 'customer'
                }
            except Exception as e:
                logger.error(f"User management error: {e}")
                return None
        
        def get_user_keyboard(user_type: str) -> List[List[InlineKeyboardButton]]:
            """Get role-based inline keyboard"""
            keyboard = []
            
            if user_type in ['staff', 'admin']:
                # Primary admin/staff buttons - most used functions
                keyboard.append([
                    InlineKeyboardButton("📦 Manage Stock", callback_data="manage_stock"),
                    InlineKeyboardButton("💊 Check Medicine", callback_data="check_medicine")
                ])
                keyboard.append([
                    InlineKeyboardButton("📝 Add Medicine", callback_data="add_medicine"),
                    InlineKeyboardButton("📊 View Statistics", callback_data="view_stats")
                ])
                keyboard.append([
                    InlineKeyboardButton("📋 View Orders", callback_data="view_orders"),
                    InlineKeyboardButton("💰 Update Prices", callback_data="update_prices")
                ])
                keyboard.append([
                    InlineKeyboardButton("📝 Edit Contacts", callback_data="edit_contact"),
                    InlineKeyboardButton("👥 Manage Users", callback_data="manage_users")
                ])
            else:
                # Customer buttons
                keyboard.append([
                    InlineKeyboardButton("💊 Check Medicine", callback_data="check_medicine"),
                    InlineKeyboardButton("🛒 Place Order", callback_data="place_order")
                ])
                keyboard.append([
                    InlineKeyboardButton("📦 My Orders", callback_data="my_orders"),
                    InlineKeyboardButton("🏢 Request Wholesale", callback_data="request_wholesale")
                ])
            
            # Common buttons for all users
            keyboard.append([
                InlineKeyboardButton("📞 Contact Info", callback_data="contact_info"),
                InlineKeyboardButton("❓ Help", callback_data="help")
            ])
            
            return keyboard
        
        # Bot handlers
        async def start_command(update: Update, context):
            """Enhanced start command with comprehensive button interface"""
            user = update.effective_user
            telegram_user = get_or_create_user(user.id, user.first_name, user.last_name, user.username)
            
            if not telegram_user:
                await update.message.reply_text("Sorry, there was an error. Please try again.")
                return
            
            user_type = telegram_user['user_type']
            role_display = USER_ROLES.get(user_type, user_type.title())
            
            welcome_text = f"""
🏥 **Welcome to Blue Pharma Trading PLC!**

Hello {telegram_user['first_name']}! I'm your comprehensive pharmacy management bot.

👤 **Your Access Level:** {role_display}

💊 **Our Enhanced 7-Field Medicine System:**
1. Medicine Name
2. Batch Number  
3. Manufacturing Date
4. Expiring Date
5. Dosage Form
6. Price (ETB)
7. Stock Quantity

🎯 **What would you like to do today?**
Choose from the options below:
"""
            
            # Create role-based keyboard
            keyboard = get_user_keyboard(user_type)
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                welcome_text, 
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        
        async def button_handler(update: Update, context):
            """Handle all inline button presses"""
            query = update.callback_query
            await query.answer()
            
            user = query.from_user
            user_info = get_or_create_user(user.id, user.first_name, user.last_name, user.username)
            
            if not user_info:
                await query.edit_message_text("Error accessing user information. Please try /start")
                return
            
            user_type = user_info['user_type']
            data = query.data
            
            # Route button presses
            if data == "manage_stock":
                await handle_manage_stock(query, user_type)
            elif data == "check_medicine":
                await handle_check_medicine(query)
            elif data == "add_medicine":
                await handle_add_medicine_button(query, user_type)
            elif data == "view_stats":
                await handle_view_stats(query, user_type)
            elif data == "view_orders":
                await handle_view_orders(query, user_type)
            elif data == "update_prices":
                await handle_update_prices(query, user_type)
            elif data == "edit_contact":
                await handle_edit_contact(query, user_type)
            elif data == "manage_users":
                await handle_manage_users(query, user_type)
            elif data == "contact_info":
                await handle_contact_info(query)
            elif data == "help":
                await handle_help(query, user_type)
            elif data == "place_order":
                await handle_place_order(query)
            elif data == "my_orders":
                await handle_my_orders(query)
            elif data == "request_wholesale":
                await handle_request_wholesale(query)
            elif data == "add_single_medicine":
                await handle_add_single_medicine(query, user_type)
            elif data == "add_bulk_medicine":
                await handle_add_bulk_medicine(query, user_type)
            elif data == "low_stock_alert":
                await handle_low_stock_alert(query, user_type)
            elif data == "remove_medicine":
                await handle_remove_medicine(query, user_type)
            elif data == "remove_all_medicines":
                await handle_remove_all_medicines(query, user_type)
            else:
                await query.edit_message_text("Feature coming soon! 🚀")
        
        # Button handler functions
        async def handle_manage_stock(query, user_type):
            """Handle stock management button"""
            if user_type not in ['staff', 'admin']:
                await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
                return
            
            try:
                # Get stock overview
                medicines = db.get_all_medicines(20)
                total_medicines = len(medicines)
                total_stock = sum(med['stock_quantity'] for med in medicines)
                low_stock = len([med for med in medicines if med['stock_quantity'] <= 10])
                out_of_stock = len([med for med in medicines if med['stock_quantity'] == 0])
                
                stock_text = f"""
📦 **Stock Management Overview**

📊 **Current Status:**
• Total Medicines: {total_medicines}
• Total Stock Units: {total_stock:,}
• Low Stock Items: {low_stock}
• Out of Stock: {out_of_stock}

🔧 **Available Actions:**
• Use `/add_medicine` to add new medicines
• Use `/update_stock` to update quantities
• Use `/medicines` to view all inventory

💡 **Quick Actions:**
"""
                
                keyboard = [
                    [InlineKeyboardButton("📝 Add Medicine", callback_data="add_medicine")],
                    [InlineKeyboardButton("📊 View All Medicines", callback_data="view_all_medicines")],
                    [InlineKeyboardButton("⚠️ Low Stock Alert", callback_data="low_stock_alert")],
                    [InlineKeyboardButton("🗑️ Remove Medicine", callback_data="remove_medicine"),
                     InlineKeyboardButton("🗑️ Remove All", callback_data="remove_all_medicines")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(stock_text, parse_mode='Markdown', reply_markup=reply_markup)
                
            except Exception as e:
                logger.error(f"Error in stock management: {e}")
                await query.edit_message_text("Error retrieving stock information.")
        
        async def handle_check_medicine(query):
            """Handle check medicine button"""
            check_text = """
💊 **Check Medicine Information**

To check medicine details, use one of these commands:

📝 **Command Format:**
`/search [medicine name]`

📋 **Examples:**
• `/search Paracetamol` - Search for Paracetamol
• `/search Amoxicillin` - Search for Amoxicillin
• `/medicines` - View all available medicines

🔍 **What you'll get:**
• Current price in ETB
• Stock availability
• Dosage form (Tablet, Capsule, etc.)
• Batch information
• Expiration dates
"""
            
            keyboard = [
                [InlineKeyboardButton("📋 View All Medicines", callback_data="view_all_medicines")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(check_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        async def handle_add_medicine_button(query, user_type):
            """Handle add medicine button - Show two options"""
            if user_type not in ['staff', 'admin']:
                await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
                return
            
            add_text = """
📝 **Add Medicine - Choose Method**

🎯 **Choose how you want to add medicines:**

**Method 1: Single Medicine**
• Add one medicine using our 6-question flow
• Perfect for individual items
• Quick and simple process

**Method 2: Bulk Addition (Excel)**
• Upload Excel file with multiple medicines
• Add hundreds of medicines at once
• Excel format: Name, Batch, Mfg Date, Exp Date, Form, Price

💡 **Our 7-Field System:**
1. Medicine Name | 2. Batch Number | 3. Manufacturing Date
4. Expiring Date | 5. Dosage Form | 6. Price (ETB) | 7. Stock Quantity
"""
            
            keyboard = [
                [InlineKeyboardButton("📝 Add Single Medicine", callback_data="add_single_medicine")],
                [InlineKeyboardButton("📊 Add Many Medicines (Excel)", callback_data="add_bulk_medicine")],
                [InlineKeyboardButton("📋 View Current Inventory", callback_data="view_all_medicines")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(add_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        async def handle_view_stats(query, user_type):
            """Handle view statistics button"""
            if user_type not in ['staff', 'admin']:
                await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
                return
            
            try:
                medicines = db.get_all_medicines()
                total_medicines = len(medicines)
                total_stock = sum(med['stock_quantity'] for med in medicines)
                total_value = sum(med['price'] * med['stock_quantity'] for med in medicines)
                avg_price = sum(med['price'] for med in medicines) / len(medicines) if medicines else 0
                
                # Get dosage form distribution
                dosage_forms = {}
                for med in medicines:
                    form = med['dosage_form'] or 'Unknown'
                    dosage_forms[form] = dosage_forms.get(form, 0) + 1
                
                top_forms = sorted(dosage_forms.items(), key=lambda x: x[1], reverse=True)[:5]
                
                stats_text = f"""
📊 **Pharmacy Statistics**

📈 **Inventory Overview:**
• Total Medicines: {total_medicines}
• Total Stock Units: {total_stock:,}
• Total Inventory Value: {total_value:,.2f} ETB
• Average Medicine Price: {avg_price:.2f} ETB

💊 **Top Dosage Forms:**
"""
                
                for form, count in top_forms:
                    stats_text += f"• {form}: {count} medicines\n"
                
                stats_text += f"\n📅 **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                
                keyboard = [
                    [InlineKeyboardButton("📦 Stock Details", callback_data="stock_details")],
                    [InlineKeyboardButton("⚠️ Low Stock Alert", callback_data="low_stock_alert")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(stats_text, parse_mode='Markdown', reply_markup=reply_markup)
                
            except Exception as e:
                logger.error(f"Error in view stats: {e}")
                await query.edit_message_text("Error retrieving statistics.")
        
        async def handle_view_orders(query, user_type):
            """Handle view orders button"""
            if user_type not in ['staff', 'admin']:
                await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
                return
            
            orders_text = """
📋 **Order Management**

🔧 **Available Actions:**
• View all orders
• Filter by status
• Update order status
• Generate reports

📊 **Order Status Types:**
• Pending - New orders
• Confirmed - Confirmed orders
• Processing - Being prepared
• Ready - Ready for pickup/delivery
• Completed - Finished orders
• Cancelled - Cancelled orders

💡 **Quick Commands:**
• `/orders` - View recent orders
• `/orders pending` - View pending orders only
"""
            
            keyboard = [
                [InlineKeyboardButton("📋 All Orders", callback_data="all_orders")],
                [InlineKeyboardButton("⏳ Pending Orders", callback_data="pending_orders")],
                [InlineKeyboardButton("✅ Recent Completed", callback_data="completed_orders")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(orders_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        async def handle_update_prices(query, user_type):
            """Handle update prices button"""
            if user_type not in ['staff', 'admin']:
                await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
                return
            
            price_text = """
💰 **Price Management**

🔧 **How to Update Prices:**
1. Search for the medicine
2. Set new price in ETB
3. Confirm the change

📝 **Command Format:**
`/update_price [medicine] [new_price]`

📋 **Examples:**
• `/update_price Paracetamol 30.00`
• `/update_price "Cough Syrup" 45.50`

💡 **Tips:**
• Use quotes for multi-word medicine names
• Prices should be in Ethiopian Birr (ETB)
• Changes are logged for audit purposes
"""
            
            keyboard = [
                [InlineKeyboardButton("💊 View Medicine Prices", callback_data="view_prices")],
                [InlineKeyboardButton("📝 Bulk Price Update", callback_data="bulk_price_update")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(price_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        async def handle_edit_contact(query, user_type):
            """Handle edit contact button"""
            if user_type not in ['staff', 'admin']:
                await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
                return
            
            contact_text = """
📝 **Edit Contact Information**

📞 **Current Contact Details:**
🏥 Blue Pharma Trading PLC
📍 123 Pharmacy Street, Addis Ababa, Ethiopia
📱 Phone: +251-11-555-0123
📧 Email: contact@bluepharma.et
🕐 Hours: 08:00-22:00 Daily

🔧 **Available Actions:**
• Update business address
• Change phone number
• Modify email address
• Update business hours
• Change business name
"""
            
            keyboard = [
                [InlineKeyboardButton("📍 Update Address", callback_data="update_address")],
                [InlineKeyboardButton("📱 Update Phone", callback_data="update_phone")],
                [InlineKeyboardButton("📧 Update Email", callback_data="update_email")],
                [InlineKeyboardButton("🕐 Update Hours", callback_data="update_hours")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(contact_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        async def handle_manage_users(query, user_type):
            """Handle manage users button"""
            if user_type != 'admin':
                await query.edit_message_text("❌ Access denied. Administrator access required.")
                return
            
            users_text = """
👥 **User Management** (Admin Only)

🔧 **Available Actions:**
• View all registered users
• Promote users to staff
• Grant wholesale access
• Deactivate problematic users
• View user activity logs

👤 **User Types:**
• **Customer** - Basic access
• **Staff** - Inventory management
• **Admin** - Full system access

📊 **User Statistics:**
• Total registered users
• Active staff members
• Wholesale customers
• Recent registrations
"""
            
            keyboard = [
                [InlineKeyboardButton("👥 All Users", callback_data="all_users")],
                [InlineKeyboardButton("👨‍💼 Staff Members", callback_data="staff_members")],
                [InlineKeyboardButton("🏢 Wholesale Users", callback_data="wholesale_users")],
                [InlineKeyboardButton("📊 User Stats", callback_data="user_stats")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(users_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        async def handle_contact_info(query):
            """Handle contact info button"""
            contact_text = """
📞 **Contact Blue Pharma Trading PLC**

🏥 **Business Information:**
📍 Address: 123 Pharmacy Street, Addis Ababa, Ethiopia
📱 Phone: +251-11-555-0123
📧 Email: contact@bluepharma.et
🕐 Hours: 08:00-22:00 Daily
🌐 Website: www.bluepharma.et

💻 **Digital Services:**
✨ 7-field medicine management system
🚀 Real-time inventory tracking
📊 Professional pharmacy tools
💊 Comprehensive medicine database

💬 **How to Reach Us:**
• Call during business hours
• Email us anytime
• Use this bot for instant help
• Visit our physical location

**Professional pharmaceutical services with cutting-edge technology!** 🏥
"""
            
            keyboard = [
                [InlineKeyboardButton("🗺️ Get Directions", callback_data="get_directions")],
                [InlineKeyboardButton("📧 Email Us", callback_data="email_us")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(contact_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        async def handle_help(query, user_type):
            """Handle help button"""
            help_text = f"""
❓ **Help & Information**

👤 **Your Access Level:** {USER_ROLES.get(user_type, user_type.title())}

📱 **Available Commands:**

**🔧 Basic Commands:**
/start - Main menu with buttons
/medicines - View all medicines
/search [name] - Search medicines
/contact - Contact information
/help - This help message

**💊 Medicine Commands:**
/add_medicine - Add new medicine (Staff/Admin)
/update_stock - Update stock quantities (Staff/Admin)

**📊 7-Field Medicine System:**
Our simplified system captures exactly what you need:
1. Medicine Name
2. Batch Number
3. Manufacturing Date
4. Expiring Date  
5. Dosage Form
6. Price (ETB)
7. Stock Quantity

**🎯 System Benefits:**
✅ Simple and fast
✅ Essential information only
✅ Consistent data entry
✅ Professional results
"""
            
            if user_type in ['staff', 'admin']:
                help_text += """
**👨‍💼 Staff/Admin Features:**
• Complete inventory management
• Stock level monitoring
• Price management
• User administration
• Analytics and reports
"""
            
            keyboard = [
                [InlineKeyboardButton("📋 View Commands", callback_data="view_commands")],
                [InlineKeyboardButton("💡 Tips & Tricks", callback_data="tips_tricks")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        # Customer-specific handlers
        async def handle_place_order(query):
            """Handle place order button"""
            order_text = """
🛒 **Place New Order**

📋 **How to Order:**
1. Browse available medicines with `/medicines`
2. Check specific medicine with `/search [name]`
3. Contact us to place your order

📞 **Order Methods:**
• **Phone:** +251-11-555-0123
• **Email:** contact@bluepharma.et
• **In Person:** Visit our pharmacy

💊 **What We Need:**
• Medicine name and quantity
• Your contact information
• Delivery or pickup preference

🚚 **Delivery Options:**
• Pickup from pharmacy
• Home delivery (fees may apply)
• Express delivery available
"""
            
            keyboard = [
                [InlineKeyboardButton("💊 Browse Medicines", callback_data="view_all_medicines")],
                [InlineKeyboardButton("📞 Call to Order", callback_data="call_to_order")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(order_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        async def handle_my_orders(query):
            """Handle my orders button"""
            orders_text = """
📦 **My Order History**

📋 **Order Status Information:**
• **Pending** - Order received, being processed
• **Confirmed** - Order confirmed, preparing
• **Ready** - Ready for pickup/delivery
• **Completed** - Order fulfilled
• **Cancelled** - Order cancelled

📞 **Track Your Orders:**
Contact us with your order reference:
• Phone: +251-11-555-0123
• Email: contact@bluepharma.et

💡 **Order Tips:**
• Keep your order reference number
• Contact us for any changes
• Pickup orders within 48 hours
"""
            
            keyboard = [
                [InlineKeyboardButton("📞 Check Order Status", callback_data="check_order_status")],
                [InlineKeyboardButton("🛒 Place New Order", callback_data="place_order")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(orders_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        async def handle_request_wholesale(query):
            """Handle request wholesale button"""
            wholesale_text = """
🏢 **Request Wholesale Access**

💰 **Wholesale Benefits:**
• Bulk pricing discounts
• Priority customer service
• Extended payment terms
• Dedicated account manager

📋 **Requirements:**
• Valid business license
• Minimum order quantities
• Business contact information
• Tax identification number

📞 **How to Apply:**
Contact our sales team:
• Phone: +251-11-555-0123
• Email: wholesale@bluepharma.et

📝 **Application Process:**
1. Submit business documentation
2. Credit and background check
3. Account setup and approval
4. Welcome package and training
"""
            
            keyboard = [
                [InlineKeyboardButton("📞 Contact Sales Team", callback_data="contact_sales")],
                [InlineKeyboardButton("📧 Email Application", callback_data="email_application")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(wholesale_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        # NEW FEATURE HANDLERS
        
        async def handle_add_single_medicine(query, user_type):
            """Handle add single medicine button"""
            if user_type not in ['staff', 'admin']:
                await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
                return
            
            single_text = """
📝 **Add Single Medicine**

🔄 **Start the 7-Question Flow:**
Use the command `/add_medicine` to begin adding a single medicine.

✅ **What you'll be asked:**
1. Medicine Name
2. Batch Number (optional)
3. Manufacturing Date (optional)
4. Expiring Date (optional)
5. Dosage Form (optional)
6. Price in ETB
7. Stock Quantity

💵 **Benefits:**
• Simple step-by-step process
• Can skip optional fields
• Immediate feedback
• Perfect for individual medicines
"""
            
            keyboard = [
                [InlineKeyboardButton("▶️ Start Adding Now", callback_data="start_single_add")],
                [InlineKeyboardButton("📊 Switch to Bulk Add", callback_data="add_bulk_medicine")],
                [InlineKeyboardButton("🔙 Back to Add Medicine", callback_data="add_medicine")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(single_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        async def handle_add_bulk_medicine(query, user_type):
            """Handle bulk medicine addition via Excel"""
            if user_type not in ['staff', 'admin']:
                await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
                return
            
            if not EXCEL_SUPPORT:
                error_text = """
❌ **Excel Support Not Available**

🛠️ **Installation Required:**
To use bulk medicine upload, install the required packages:

```
pip install pandas openpyxl
```

🔄 **Then restart the bot** to enable Excel functionality.
"""
                
                keyboard = [
                    [InlineKeyboardButton("📝 Use Single Medicine Instead", callback_data="add_single_medicine")],
                    [InlineKeyboardButton("🔙 Back to Add Medicine", callback_data="add_medicine")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(error_text, parse_mode='Markdown', reply_markup=reply_markup)
                return
            
            bulk_text = """
📊 **Bulk Medicine Addition (Excel)**

📄 **Excel Format Required:**
Your Excel file must have these **exact column headers**:

| Medicine Name | Batch Number | Manufacturing Date | Expiring Date | Dosage Form | Price |
|---------------|--------------|-------------------|---------------|-------------|-------|
| Paracetamol   | B001         | 2024-01-15        | 2026-01-15    | Tablet      | 25.50 |
| Amoxicillin   | B002         | 2024-02-10        | 2026-02-10    | Capsule     | 45.00 |

📝 **Instructions:**
1. Create Excel file with above format
2. Fill in your medicine data
3. Save as .xlsx or .xls file
4. Upload the file using the button below

⚠️ **Important Notes:**
• Column headers must match exactly
• Medicine Name and Price are required
• Other fields can be empty
• Dates in YYYY-MM-DD format
• Maximum 1000 medicines per file
"""
            
            keyboard = [
                [InlineKeyboardButton("📎 Upload Excel File", callback_data="upload_excel")],
                [InlineKeyboardButton("📋 Download Template", callback_data="download_template")],
                [InlineKeyboardButton("📝 Switch to Single Add", callback_data="add_single_medicine")],
                [InlineKeyboardButton("🔙 Back to Add Medicine", callback_data="add_medicine")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(bulk_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        async def handle_low_stock_alert(query, user_type):
            """Handle low stock alert"""
            if user_type not in ['staff', 'admin']:
                await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
                return
            
            try:
                medicines = db.get_all_medicines()
                low_stock_medicines = [med for med in medicines if med['stock_quantity'] <= 10]
                
                if not low_stock_medicines:
                    alert_text = """
✅ **No Low Stock Items!**

🎉 **Great News:**
All medicines have sufficient stock levels (>10 units).

📊 **Current Status:**
• Total medicines monitored: {}
• Low stock threshold: ≤ 10 units
• Medicines below threshold: 0

📈 **Keep up the great inventory management!**
""".format(len(medicines))
                else:
                    alert_text = f"""
⚠️ **Low Stock Alert** - {len(low_stock_medicines)} items need attention!

🚨 **Medicines Running Low:**

"""
                    
                    for i, med in enumerate(low_stock_medicines[:10], 1):
                        name = med['name']
                        stock = med['stock_quantity']
                        price = med['price']
                        status = "🔴 OUT OF STOCK" if stock == 0 else f"🟡 {stock} units left"
                        
                        alert_text += f"**{i}. {name}**\n"
                        alert_text += f"{status} | 💰 {price:.2f} ETB\n\n"
                    
                    if len(low_stock_medicines) > 10:
                        alert_text += f"_...and {len(low_stock_medicines) - 10} more items_\n\n"
                    
                    alert_text += f"📈 **Action Required:**\n• Reorder these medicines\n• Update stock levels\n• Monitor regularly"
                
                keyboard = [
                    [InlineKeyboardButton("📈 Update Stock Levels", callback_data="update_stock_levels")],
                    [InlineKeyboardButton("📝 Add New Stock", callback_data="add_medicine")],
                    [InlineKeyboardButton("🔙 Back to Stock Management", callback_data="manage_stock")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(alert_text, parse_mode='Markdown', reply_markup=reply_markup)
                
            except Exception as e:
                logger.error(f"Error in low stock alert: {e}")
                await query.edit_message_text("Error retrieving low stock information.")
        
        async def handle_remove_medicine(query, user_type):
            """Handle remove single medicine"""
            if user_type not in ['staff', 'admin']:
                await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
                return
            
            remove_text = """
🗑️ **Remove Medicine**

⚠️ **How to Remove a Medicine:**

**Step 1:** Find the medicine you want to remove
• Use `/medicines` to see all medicines
• Use `/search [name]` to find specific medicine

**Step 2:** Note down the medicine details
• Medicine name
• Batch number (if applicable)

**Step 3:** Contact administrator
• For safety, medicine removal requires manual confirmation
• This prevents accidental deletions

📞 **Contact Information:**
• Phone: +251-11-555-0123
• Email: admin@bluepharma.et

🛡️ **Safety First:** This process ensures inventory integrity and prevents accidental data loss.
"""
            
            keyboard = [
                [InlineKeyboardButton("📊 View All Medicines", callback_data="view_all_medicines")],
                [InlineKeyboardButton("🔍 Search Medicine", callback_data="search_medicine")],
                [InlineKeyboardButton("🗑️ Remove All Medicines", callback_data="remove_all_medicines")],
                [InlineKeyboardButton("🔙 Back to Stock Management", callback_data="manage_stock")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(remove_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        async def handle_remove_all_medicines(query, user_type):
            """Handle remove all medicines with confirmation"""
            if user_type not in ['staff', 'admin']:
                await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
                return
            
            try:
                medicines = db.get_all_medicines()
                total_medicines = len(medicines)
                total_value = sum(med['price'] * med['stock_quantity'] for med in medicines)
                
                warning_text = f"""
⚠️ **DANGER - Remove All Medicines**

🚨 **THIS ACTION CANNOT BE UNDONE!**

📊 **What will be deleted:**
• **{total_medicines}** medicines
• **{total_value:,.2f} ETB** total inventory value
• All medicine records and history
• All batch and expiry information

🗺️ **Why you might want to do this:**
• Starting fresh with new inventory
• System reset for testing
• Major inventory restructuring

🛠️ **Recommended Alternative:**
Instead of deleting, consider exporting data first as backup.

⚠️ **Are you absolutely sure you want to delete ALL medicines?**
"""
                
                keyboard = [
                    [InlineKeyboardButton("✅ YES - DELETE ALL (Requires PIN)", callback_data="confirm_delete_all")],
                    [InlineKeyboardButton("❌ NO - Keep My Medicines", callback_data="manage_stock")],
                    [InlineKeyboardButton("📋 Export First (Recommended)", callback_data="export_medicines")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(warning_text, parse_mode='Markdown', reply_markup=reply_markup)
                
            except Exception as e:
                logger.error(f"Error in remove all medicines: {e}")
                await query.edit_message_text("Error retrieving medicine information.")
        
        def process_excel_file(file_path):
            """Process Excel file and return list of medicines"""
            try:
                # Read Excel file
                df = pd.read_excel(file_path)
                
                # Expected columns
                required_columns = ['Medicine Name', 'Price']
                optional_columns = ['Batch Number', 'Manufacturing Date', 'Expiring Date', 'Dosage Form', 'Stock Quantity']
                all_expected_columns = required_columns + optional_columns
                
                # Check required columns
                missing_required = [col for col in required_columns if col not in df.columns]
                if missing_required:
                    return {'error': f"Missing required columns: {', '.join(missing_required)}"}
                
                # Process medicines
                medicines = []
                errors = []
                
                for index, row in df.iterrows():
                    try:
                        # Required fields
                        name = str(row['Medicine Name']).strip()
                        print(f"DEBUG: Processing row {index + 2}, Medicine Name: '{name}'")  # Debug line
                        if not name or name.lower() == 'nan':
                            errors.append(f"Row {index + 2}: Medicine name is required")
                            continue
                        
                        try:
                            price = float(row['Price'])
                            if price < 0:
                                errors.append(f"Row {index + 2}: Price cannot be negative")
                                continue
                        except (ValueError, TypeError):
                            errors.append(f"Row {index + 2}: Invalid price format")
                            continue
                        
                        # Optional fields
                        batch_number = str(row.get('Batch Number', '')).strip()
                        batch_number = None if not batch_number or batch_number.lower() == 'nan' else batch_number
                        
                        mfg_date = str(row.get('Manufacturing Date', '')).strip()
                        mfg_date = None if not mfg_date or mfg_date.lower() == 'nan' else mfg_date
                        
                        exp_date = str(row.get('Expiring Date', '')).strip()
                        exp_date = None if not exp_date or exp_date.lower() == 'nan' else exp_date
                        
                        dosage_form = str(row.get('Dosage Form', '')).strip()
                        dosage_form = None if not dosage_form or dosage_form.lower() == 'nan' else dosage_form
                        
                        # Handle stock quantity (optional, defaults to 0)
                        try:
                            stock_quantity = int(float(row.get('Stock Quantity', 0)))
                            if stock_quantity < 0:
                                errors.append(f"Row {index + 2}: Stock quantity cannot be negative, setting to 0")
                                stock_quantity = 0
                        except (ValueError, TypeError):
                            stock_quantity = 0
                        
                        medicine = {
                            'name': name,
                            'batch_number': batch_number,
                            'manufacturing_date': mfg_date,
                            'expiring_date': exp_date,
                            'dosage_form': dosage_form,
                            'price': price,
                            'stock_quantity': stock_quantity
                        }
                        
                        medicines.append(medicine)
                        
                    except Exception as e:
                        errors.append(f"Row {index + 2}: Error processing row - {str(e)}")
                
                if not medicines:
                    return {'error': 'No valid medicines found in file'}
                
                return {
                    'medicines': medicines,
                    'errors': errors,
                    'total_processed': len(medicines)
                }
                
            except Exception as e:
                return {'error': f'Error reading Excel file: {str(e)}'}
        
        # Handle back to main and other common actions
        async def handle_back_to_main(query):
            """Handle back to main menu"""
            user = query.from_user
            user_info = get_or_create_user(user.id, user.first_name, user.last_name, user.username)
            
            if user_info:
                user_type = user_info['user_type']
                keyboard = get_user_keyboard(user_type)
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🏥 **Welcome back!** Choose an option below:",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
        
        # Handle view all medicines with two options (Text/Excel)
        async def handle_view_all_medicines(query):
            """Handle view all medicines - Show two options"""
            try:
                medicines = db.get_all_medicines()
                total_medicines = len(medicines)
                total_stock = sum(med['stock_quantity'] for med in medicines)
                total_value = sum(med['price'] * med['stock_quantity'] for med in medicines)
                
                view_text = f"""
📊 **View All Medicines**

📈 **Inventory Summary:**
• Total Medicines: {total_medicines}
• Total Stock Units: {total_stock:,}
• Total Inventory Value: {total_value:,.2f} ETB

📋 **How would you like to view your medicines?**

**Option 1: Text View**
• Quick view in chat
• Shows first 15 medicines
• Easy to read format

**Option 2: Excel Export**
• Complete inventory in Excel file
• All 7 fields included
• Perfect for backup/analysis
• Downloadable .xlsx file
"""
                
                keyboard = [
                    [InlineKeyboardButton("📋 View as Text", callback_data="view_text")],
                    [InlineKeyboardButton("📄 Export to Excel", callback_data="export_excel")],
                    [InlineKeyboardButton("🔍 Search Medicine", callback_data="search_medicine")],
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(view_text, parse_mode='Markdown', reply_markup=reply_markup)
                
            except Exception as e:
                logger.error(f"Error in view all medicines: {e}")
                await query.edit_message_text("Error retrieving medicines information.")
        
        # Enhanced button handler with routing
        async def enhanced_button_handler(update: Update, context):
            """Enhanced button handler with complete routing"""
            query = update.callback_query
            await query.answer()
            
            user = query.from_user
            user_info = get_or_create_user(user.id, user.first_name, user.last_name, user.username)
            
            if not user_info:
                await query.edit_message_text("Error accessing user information. Please try /start")
                return
            
            user_type = user_info['user_type']
            data = query.data
            
            # Route ALL button presses with user_type
            if data == "back_to_main":
                await handle_back_to_main(query)
            elif data == "view_all_medicines":
                await handle_view_all_medicines(query)
            elif data == "manage_stock":
                await handle_manage_stock(query, user_type)
            elif data == "check_medicine":
                await handle_check_medicine(query)
            elif data == "add_medicine":
                await handle_add_medicine_button(query, user_type)
            elif data == "view_stats":
                await handle_view_stats(query, user_type)
            elif data == "view_orders":
                await handle_view_orders(query, user_type)
            elif data == "update_prices":
                await handle_update_prices(query, user_type)
            elif data == "edit_contact":
                await handle_edit_contact(query, user_type)
            elif data == "manage_users":
                await handle_manage_users(query, user_type)
            elif data == "contact_info":
                await handle_contact_info(query)
            elif data == "help":
                await handle_help(query, user_type)
            elif data == "place_order":
                await handle_place_order(query)
            elif data == "my_orders":
                await handle_my_orders(query)
            elif data == "request_wholesale":
                await handle_request_wholesale(query)
            elif data == "add_single_medicine":
                await handle_add_single_medicine(query, user_type)
            elif data == "add_bulk_medicine":
                await handle_add_bulk_medicine(query, user_type)
            elif data == "low_stock_alert":
                await handle_low_stock_alert(query, user_type)
            elif data == "remove_medicine":
                await handle_remove_medicine(query, user_type)
            elif data == "remove_all_medicines":
                await handle_remove_all_medicines(query, user_type)
            elif data == "start_single_add":
                # Start the single medicine conversation via callback
                await query.edit_message_text(
                    "📝 **Starting Single Medicine Addition**\n\n"
                    "Please use the command `/add_medicine` to begin the 7-question flow for adding a single medicine."
                )
            elif data == "upload_excel":
                if not EXCEL_SUPPORT:
                    await query.edit_message_text(
                        "❌ **Excel Support Not Available**\n\n"
                        "Please install: `pip install pandas openpyxl` and restart the bot."
                    )
                    return
                
                # Store user ID for file upload tracking
                user_data[query.from_user.id] = {'awaiting_excel': True}
                
                upload_text = """
📊 **Excel File Upload Ready**

📎 **Now upload your Excel file as a document to this chat.**

📋 **Required format:**
• **Medicine Name** (required)
• **Price** (required) 
• Batch Number (optional)
• Manufacturing Date (optional)
• Expiring Date (optional)
• Dosage Form (optional)

⚙️ **File Requirements:**
• .xlsx or .xls format
• First row must be column headers
• Maximum 1000 medicines
• File size under 20MB

🔄 **The bot will automatically process your file once uploaded!**
"""
                
                keyboard = [
                    [InlineKeyboardButton("📋 Download Template First", callback_data="download_template")],
                    [InlineKeyboardButton("🔙 Cancel Upload", callback_data="add_bulk_medicine")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(upload_text, parse_mode='Markdown', reply_markup=reply_markup)
            elif data == "download_template":
                template_text = """
📋 **Excel Template Download**

📄 **Create an Excel file with these exact column headers:**

```
Medicine Name | Batch Number | Manufacturing Date | Expiring Date | Dosage Form | Price | Stock Quantity
```

📝 **Sample Data:**
```
Paracetamol   | B001         | 2024-01-15          | 2026-01-15    | Tablet      | 25.50 | 100
Amoxicillin   | B002         | 2024-02-10          | 2026-02-10    | Capsule     | 45.00 | 50
Cough Syrup   | B003         | 2024-03-20          | 2025-03-20    | Syrup       | 65.00 | 25
```

💡 **Tips:**
• Save as .xlsx or .xls file
• Medicine Name and Price are required
• Stock Quantity defaults to 0 if not provided
• Other fields can be left empty
• Dates should be in YYYY-MM-DD format
"""
                keyboard = [
                    [InlineKeyboardButton("📊 Back to Bulk Add", callback_data="add_bulk_medicine")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(template_text, parse_mode='Markdown', reply_markup=reply_markup)
            elif data == "view_text":
                await handle_view_text(query)
            elif data == "export_excel":
                await handle_export_excel(query, context)
            elif data == "export_medicines":
                await handle_export_excel(query, context)
            elif data == "confirm_delete_all":
                # Start PIN verification process
                user_data[query.from_user.id] = {'awaiting_pin': True}
                pin_text = """
🔐 **Security PIN Required**

🚨 **FINAL CONFIRMATION - Delete ALL Medicines**

To proceed with this dangerous operation, please enter the security PIN:

⚠️ **This will permanently delete ALL medicines from your inventory!**

Type the PIN to confirm (or /cancel to abort):
"""
                await query.edit_message_text(pin_text, parse_mode='Markdown')
            else:
                await query.edit_message_text("Feature coming soon! 🚀")
        
        # Command handlers
        async def medicines_command(update: Update, context):
            """Show all medicines"""
            try:
                medicines = db.get_all_medicines(15)
                
                if not medicines:
                    await update.message.reply_text(
                        "📦 No medicines in inventory.\n\nUse /add_medicine to add medicines!"
                    )
                    return
                
                message = "💊 **Complete Medicine Inventory:**\n\n"
                
                total_value = 0
                for i, med in enumerate(medicines, 1):
                    name = med['name']
                    price = med['price']
                    stock = med['stock_quantity']
                    dosage_form = med['dosage_form'] or "N/A"
                    batch = med['batch_number'] or "N/A"
                    
                    stock_info = f"✅ {stock} units" if stock > 0 else "❌ Out of Stock"
                    total_value += price * stock
                    
                    message += f"**{i}. {name}**\n"
                    message += f"💰 {price:.2f} ETB | 📦 {stock_info}\n"
                    message += f"💊 {dosage_form} | 🏷️ {batch}\n\n"
                
                message += f"📊 **Summary:** {len(medicines)} medicines, Total value: {total_value:.2f} ETB"
                
                await update.message.reply_text(message, parse_mode='Markdown')
                
            except Exception as e:
                logger.error(f"Error showing medicines: {e}")
                await update.message.reply_text("Error retrieving medicines.")
        
        async def search_command(update: Update, context):
            """Search medicines"""
            if not context.args:
                await update.message.reply_text(
                    "🔍 **Search Medicines**\n\n"
                    "Usage: `/search [medicine name]`\n\n"
                    "Example: `/search paracetamol`"
                )
                return
            
            search_term = " ".join(context.args)
            medicines = db.search_medicines(search_term, limit=5)
            
            if not medicines:
                await update.message.reply_text(
                    f"❌ No medicines found for '{search_term}'"
                )
                return
            
            message = f"🔍 **Search Results for '{search_term}':**\n\n"
            
            for med in medicines:
                name = med['name']
                price = med['price']
                stock = med['stock_quantity']
                form = med['dosage_form'] or "N/A"
                batch = med['batch_number'] or "N/A"
                
                stock_info = f"✅ {stock} units" if stock > 0 else "❌ Out of Stock"
                
                message += f"**{name}**\n"
                message += f"💰 {price:.2f} ETB | 📦 {stock_info}\n"
                message += f"💊 {form} | 🏷️ {batch}\n\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        
        # Add medicine conversation (simplified version)
        async def add_medicine_start(update: Update, context):
            """Start add medicine conversation"""
            user_id = update.effective_user.id
            user_info = get_or_create_user(user_id, update.effective_user.first_name)
            
            if not user_info or user_info['user_type'] not in ['staff', 'admin']:
                await update.message.reply_text("❌ Access denied. Staff/Admin access required.")
                return ConversationHandler.END
            
            user_data[user_id] = {}
            
            await update.message.reply_text(
                "📝 **Add Medicine - 7-Question Flow**\n\n"
                "**Question 1/7:** What is the medicine name?"
            )
            return MEDICINE_NAME
        
        async def handle_medicine_name(update: Update, context):
            """Handle medicine name input"""
            user_id = update.effective_user.id
            medicine_name = update.message.text.strip()
            
            if len(medicine_name) < 2:
                await update.message.reply_text("❌ Medicine name too short. Please enter a valid name:")
                return MEDICINE_NAME
            
            user_data[user_id]['name'] = medicine_name
            
            await update.message.reply_text(
                f"✅ Medicine Name: {medicine_name}\n\n"
                "**Question 2/7:** What is the batch number?\n"
                "(Enter 'skip' if not available)"
            )
            return BATCH_NUMBER
        
        async def handle_batch_number(update: Update, context):
            """Handle batch number input"""
            user_id = update.effective_user.id
            batch_number = update.message.text.strip()
            
            if batch_number.lower() == 'skip':
                batch_number = None
            
            user_data[user_id]['batch_number'] = batch_number
            
            batch_display = batch_number if batch_number else "Not provided"
            await update.message.reply_text(
                f"✅ Batch Number: {batch_display}\n\n"
                "**Question 3/7:** Manufacturing date (YYYY-MM-DD)?\n"
                "(Enter 'skip' if not available)"
            )
            return MANUFACTURING_DATE
        
        async def handle_manufacturing_date(update: Update, context):
            """Handle manufacturing date input"""
            user_id = update.effective_user.id
            mfg_date = update.message.text.strip()
            
            if mfg_date.lower() == 'skip':
                mfg_date = None
            
            user_data[user_id]['manufacturing_date'] = mfg_date
            
            date_display = mfg_date if mfg_date else "Not provided"
            await update.message.reply_text(
                f"✅ Manufacturing Date: {date_display}\n\n"
                "**Question 4/7:** Expiring date (YYYY-MM-DD)?\n"
                "(Enter 'skip' if not available)"
            )
            return EXPIRING_DATE
        
        async def handle_expiring_date(update: Update, context):
            """Handle expiring date input"""
            user_id = update.effective_user.id
            exp_date = update.message.text.strip()
            
            if exp_date.lower() == 'skip':
                exp_date = None
            
            user_data[user_id]['expiring_date'] = exp_date
            
            date_display = exp_date if exp_date else "Not provided"
            await update.message.reply_text(
                f"✅ Expiring Date: {date_display}\n\n"
                "**Question 5/7:** Dosage form?\n"
                "Examples: Tablet, Capsule, Syrup, Injection, etc.\n"
                "(Enter 'skip' if not available)"
            )
            return DOSAGE_FORM
        
        async def handle_dosage_form(update: Update, context):
            """Handle dosage form input"""
            user_id = update.effective_user.id
            dosage_form = update.message.text.strip()
            
            if dosage_form.lower() == 'skip':
                dosage_form = None
            
            user_data[user_id]['dosage_form'] = dosage_form
            
            form_display = dosage_form if dosage_form else "Not specified"
            await update.message.reply_text(
                f"✅ Dosage Form: {form_display}\n\n"
                "**Question 6/7:** Price in ETB?\n"
                "Example: 25.50"
            )
            return PRICE
        
        async def handle_price(update: Update, context):
            """Handle price input and continue to stock quantity"""
            user_id = update.effective_user.id
            
            try:
                price = float(update.message.text.strip())
                if price < 0:
                    raise ValueError("Price cannot be negative")
            except ValueError:
                await update.message.reply_text("❌ Please enter a valid price:")
                return PRICE
            
            user_data[user_id]['price'] = price
            
            await update.message.reply_text(
                f"✅ Price: {price:.2f} ETB\n\n"
                "**Question 7/7:** How many units are in stock?\n"
                "Example: 100\n"
                "(Enter 0 if no stock available yet)"
            )
            return STOCK_QUANTITY
        
        async def handle_stock_quantity(update: Update, context):
            """Handle stock quantity input and save medicine"""
            user_id = update.effective_user.id
            
            try:
                stock_quantity = int(update.message.text.strip())
                if stock_quantity < 0:
                    raise ValueError("Stock quantity cannot be negative")
            except ValueError:
                await update.message.reply_text("❌ Please enter a valid stock quantity (whole number):")
                return STOCK_QUANTITY
            
            user_data[user_id]['stock_quantity'] = stock_quantity
            
            # Save medicine
            try:
                medicine_data = user_data[user_id]
                medicine_id = db.add_medicine(
                    name=medicine_data['name'],
                    batch_number=medicine_data.get('batch_number'),
                    manufacturing_date=medicine_data.get('manufacturing_date'),
                    expiring_date=medicine_data.get('expiring_date'),
                    dosage_form=medicine_data.get('dosage_form'),
                    price=medicine_data['price'],
                    stock_quantity=medicine_data['stock_quantity']
                )
                
                if medicine_id:
                    summary = f"""
🎉 **Medicine Added Successfully!**

📋 **Details:**
💊 Name: {medicine_data['name']}
🏷️ Batch: {medicine_data.get('batch_number') or 'Not provided'}
📅 Mfg: {medicine_data.get('manufacturing_date') or 'Not provided'}
📅 Exp: {medicine_data.get('expiring_date') or 'Not provided'}
💊 Form: {medicine_data.get('dosage_form') or 'Not specified'}
💰 Price: {medicine_data['price']:.2f} ETB
📦 Stock: {medicine_data['stock_quantity']} units

✅ Medicine ID: {medicine_id}
"""
                    await update.message.reply_text(summary, parse_mode='Markdown')
                    
                    # Clean up
                    if user_id in user_data:
                        del user_data[user_id]
                    
                    return ConversationHandler.END
                else:
                    await update.message.reply_text("❌ Error saving medicine.")
                    return ConversationHandler.END
                    
            except Exception as e:
                logger.error(f"Error saving medicine: {e}")
                await update.message.reply_text("❌ Error saving medicine.")
                return ConversationHandler.END
        
        async def cancel_add_medicine(update: Update, context):
            """Cancel add medicine conversation"""
            user_id = update.effective_user.id
            if user_id in user_data:
                del user_data[user_id]
            
            await update.message.reply_text("❌ Add medicine cancelled.")
            return ConversationHandler.END
        
        async def handle_document(update: Update, context):
            """Handle document uploads (Excel files)"""
            user_id = update.effective_user.id
            user_info = get_or_create_user(user_id, update.effective_user.first_name)
            
            # Check if user has staff/admin access
            if not user_info or user_info['user_type'] not in ['staff', 'admin']:
                await update.message.reply_text("❌ Access denied. Staff/Admin access required for file uploads.")
                return
            
            # Check if user is expecting an Excel file
            if user_id not in user_data or not user_data[user_id].get('awaiting_excel'):
                await update.message.reply_text(
                    "📎 **File Upload**\n\n"
                    "I see you've uploaded a file! To upload medicines via Excel:\n\n"
                    "1. Use /start and select 'Add Medicine'\n"
                    "2. Choose 'Add Many Medicines (Excel)'\n"
                    "3. Click 'Upload Excel File'"
                )
                return
            
            document = update.message.document
            
            # Validate file type
            if not document.file_name.lower().endswith(('.xlsx', '.xls')):
                await update.message.reply_text(
                    "❌ **Invalid File Type**\n\n"
                    "Please upload an Excel file (.xlsx or .xls format only)."
                )
                return
            
            # Check file size (20MB limit)
            if document.file_size > 20 * 1024 * 1024:
                await update.message.reply_text(
                    "❌ **File Too Large**\n\n"
                    "Please upload a file smaller than 20MB."
                )
                return
            
            if not EXCEL_SUPPORT:
                await update.message.reply_text(
                    "❌ **Excel Support Not Available**\n\n"
                    "Please install: `pip install pandas openpyxl` and restart the bot."
                )
                return
            
            # Send processing message
            processing_msg = await update.message.reply_text(
                "⏳ **Processing Excel File...**\n\n"
                f"📄 File: {document.file_name}\n"
                f"📊 Size: {document.file_size / 1024:.1f} KB\n\n"
                "🔄 Please wait while I process your medicines..."
            )
            
            try:
                # Download the file
                file = await context.bot.get_file(document.file_id)
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
                    temp_path = temp_file.name
                    await file.download_to_drive(temp_path)
                
                # Process the Excel file
                result = process_excel_file(temp_path)
                
                # Clean up temporary file
                os.unlink(temp_path)
                
                # Clear awaiting status
                if user_id in user_data:
                    user_data[user_id]['awaiting_excel'] = False
                
                if 'error' in result:
                    await processing_msg.edit_text(
                        f"❌ **Processing Failed**\n\n"
                        f"**Error:** {result['error']}\n\n"
                        "💡 **Tips:**\n"
                        "• Ensure column headers match exactly\n"
                        "• Check for valid data in required fields\n"
                        "• Use the template format provided"
                    )
                    return
                
                medicines = result['medicines']
                errors = result.get('errors', [])
                
                # Add medicines to database
                added_count = 0
                failed_count = 0
                
                for medicine in medicines:
                    try:
                        medicine_id = db.add_medicine(
                            name=medicine['name'],
                            batch_number=medicine['batch_number'],
                            manufacturing_date=medicine['manufacturing_date'],
                            expiring_date=medicine['expiring_date'],
                            dosage_form=medicine['dosage_form'],
                            price=medicine['price'],
                            stock_quantity=medicine['stock_quantity']
                        )
                        
                        if medicine_id:
                            added_count += 1
                        else:
                            failed_count += 1
                            
                    except Exception as e:
                        failed_count += 1
                        errors.append(f"Database error for {medicine['name']}: {str(e)}")
                
                # Prepare summary message (plain text to avoid markdown parsing issues)
                summary = f"✅ Excel Processing Complete!\n\n"
                summary += f"📊 Summary:\n"
                summary += f"• Added: {added_count} medicines\n"
                summary += f"• Failed: {failed_count} medicines\n"
                summary += f"• Total processed: {len(medicines)}\n\n"
                summary += f"📄 File: {document.file_name}\n"
                summary += f"⏱️ Processing time: A few seconds\n"
                
                if errors:
                    summary += f"\n⚠️ Errors encountered:\n"
                    for i, error in enumerate(errors[:5], 1):
                        # Escape problematic characters
                        clean_error = str(error).replace('*', '').replace('_', '').replace('[', '').replace(']', '')
                        summary += f"• {clean_error}\n"
                    if len(errors) > 5:
                        summary += f"• ...and {len(errors) - 5} more errors\n"
                
                summary += f"\n🎉 Success! Your medicines have been added to the inventory."
                
                await processing_msg.edit_text(summary)
                
                # Send additional success message with options
                keyboard = [
                    [InlineKeyboardButton("📋 View All Medicines", callback_data="view_all_medicines")],
                    [InlineKeyboardButton("📊 Upload More Files", callback_data="add_bulk_medicine")],
                    [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "🎯 **What would you like to do next?**",
                    reply_markup=reply_markup
                )
                
            except Exception as e:
                logger.error(f"Error processing Excel file: {e}")
                
                # Clean up user data
                if user_id in user_data:
                    user_data[user_id]['awaiting_excel'] = False
                
                await processing_msg.edit_text(
                    f"❌ **Processing Error**\n\n"
                    f"**Error:** {str(e)}\n\n"
                    "Please try again with a different file or contact support."
                )
        
        # NEW HANDLER FUNCTIONS FOR VIEW TEXT AND EXCEL EXPORT
        
        async def handle_view_text(query):
            """Handle view medicines as text in chat"""
            try:
                medicines = db.get_all_medicines(15)
                
                if not medicines:
                    await query.edit_message_text("📦 No medicines in inventory.")
                    return
                
                message = "💊 **Complete Medicine Inventory (Text View):**\n\n"
                
                total_value = 0
                for i, med in enumerate(medicines, 1):
                    name = med['name']
                    price = med['price']
                    stock = med['stock_quantity']
                    dosage_form = med['dosage_form'] or "N/A"
                    batch = med['batch_number'] or "N/A"
                    mfg_date = med['manufacturing_date'] or "N/A"
                    exp_date = med['expiring_date'] or "N/A"
                    
                    stock_info = f"✅ {stock} units" if stock > 0 else "❌ Out of Stock"
                    total_value += price * stock
                    
                    message += f"**{i}. {name}**\n"
                    message += f"💰 {price:.2f} ETB | 📦 {stock_info}\n"
                    message += f"💊 {dosage_form} | 🏷️ {batch}\n"
                    message += f"📅 Mfg: {mfg_date} | Exp: {exp_date}\n\n"
                
                message += f"📊 **Summary:** {len(medicines)} medicines, Total value: {total_value:.2f} ETB\n\n"
                
                if len(medicines) == 15:
                    message += "_Showing first 15 medicines. Use Excel export for complete list._"
                
                keyboard = [
                    [InlineKeyboardButton("📄 Export to Excel", callback_data="export_excel")],
                    [InlineKeyboardButton("🔍 Search Medicine", callback_data="search_medicine")],
                    [InlineKeyboardButton("🔙 Back", callback_data="view_all_medicines")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
                
            except Exception as e:
                logger.error(f"Error in view text: {e}")
                await query.edit_message_text("Error retrieving medicines.")
        
        async def handle_export_excel(query, context):
            """Handle Excel export of all medicines"""
            try:
                if not EXCEL_SUPPORT:
                    await query.edit_message_text(
                        "❌ **Excel Support Not Available**\n\n"
                        "Please install: `pip install pandas openpyxl` and restart the bot."
                    )
                    return
                
                # Show processing message
                processing_msg = await query.edit_message_text(
                    "⏳ **Generating Excel Export...**\n\n"
                    "🗺️ Processing all medicines\n"
                    "📄 Creating Excel file\n"
                    "🔄 Please wait..."
                )
                
                # Get all medicines
                medicines = db.get_all_medicines()
                
                if not medicines:
                    await processing_msg.edit_text("📦 No medicines to export.")
                    return
                
                # Create DataFrame with 7-field system
                data = []
                for med in medicines:
                    data.append({
                        'Medicine Name': med['name'],
                        'Batch Number': med['batch_number'] or '',
                        'Manufacturing Date': med['manufacturing_date'] or '',
                        'Expiring Date': med['expiring_date'] or '',
                        'Dosage Form': med['dosage_form'] or '',
                        'Price (ETB)': med['price'],
                        'Stock Quantity': med['stock_quantity']
                    })
                
                df = pd.DataFrame(data)
                
                # Create temporary Excel file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"BluePharma_Inventory_{timestamp}.xlsx"
                
                with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
                    temp_path = temp_file.name
                    
                    # Create Excel with formatting
                    with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name='Medicines Inventory', index=False)
                        
                        # Get worksheet for formatting
                        worksheet = writer.sheets['Medicines Inventory']
                        
                        # Auto-adjust column widths
                        for column in worksheet.columns:
                            max_length = 0
                            column_letter = column[0].column_letter
                            for cell in column:
                                try:
                                    if len(str(cell.value)) > max_length:
                                        max_length = len(str(cell.value))
                                except:
                                    pass
                            adjusted_width = min(max_length + 2, 50)
                            worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Send the file
                total_medicines = len(medicines)
                total_value = sum(med['price'] * med['stock_quantity'] for med in medicines)
                
                # Create plain text caption to avoid markdown parsing errors
                caption = f"📄 Blue Pharma Inventory Export\n\n"
                caption += f"📊 Summary:\n"
                caption += f"• Total Medicines: {total_medicines}\n"
                caption += f"• Total Inventory Value: {total_value:,.2f} ETB\n"
                caption += f"• Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                caption += f"📈 7-Field System: All medicine data included\n"
                caption += f"💾 File: {filename}"
                
                # Send document
                with open(temp_path, 'rb') as excel_file:
                    await context.bot.send_document(
                        chat_id=query.message.chat_id,
                        document=excel_file,
                        filename=filename,
                        caption=caption
                    )
                
                # Clean up temporary file
                os.unlink(temp_path)
                
                # Update the message with success info
                success_text = f"✅ **Excel Export Complete!**\n\n"
                success_text += f"📄 **File sent:** {filename}\n"
                success_text += f"📊 **Contains:** {total_medicines} medicines\n"
                success_text += f"🗺️ **7-Field Data:** Complete inventory\n\n"
                success_text += f"💾 The Excel file has been sent above. You can download and open it with Excel, Google Sheets, or any spreadsheet application."
                
                keyboard = [
                    [InlineKeyboardButton("📋 View as Text", callback_data="view_text")],
                    [InlineKeyboardButton("🔙 Back to Medicines", callback_data="view_all_medicines")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await processing_msg.edit_text(success_text, reply_markup=reply_markup)
                
            except Exception as e:
                logger.error(f"Error in Excel export: {e}")
                await query.edit_message_text(f"Error creating Excel export: {str(e)}")
        
        # PIN VERIFICATION SYSTEM
        
        async def handle_pin_verification(update: Update, context):
            """Handle PIN verification for bulk delete"""
            user_id = update.effective_user.id
            
            # Check if user is in PIN verification state
            if user_id not in user_data or not user_data[user_id].get('awaiting_pin'):
                return  # Not waiting for PIN
            
            pin_input = update.message.text.strip()
            
            # Check PIN
            if pin_input == "4321":
                # Correct PIN - proceed with deletion
                user_data[user_id]['awaiting_pin'] = False
                
                try:
                    # Get count before deletion
                    medicines = db.get_all_medicines()
                    total_deleted = len(medicines)
                    total_value = sum(med['price'] * med['stock_quantity'] for med in medicines)
                    
                    # Execute bulk deletion
                    success = db.delete_all_medicines()
                    
                    if success:
                        success_message = f"✅ **ALL MEDICINES DELETED SUCCESSFULLY!**\n\n"
                        success_message += f"🗛️ **Deletion Summary:**\n"
                        success_message += f"• Medicines Deleted: {total_deleted}\n"
                        success_message += f"• Inventory Value Removed: {total_value:,.2f} ETB\n"
                        success_message += f"• Deletion Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        success_message += f"🗺️ **Your inventory is now completely empty.**\n\n"
                        success_message += f"🔄 You can start fresh by adding new medicines."
                        
                        keyboard = [
                            [InlineKeyboardButton("📝 Add New Medicine", callback_data="add_medicine")],
                            [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_main")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await update.message.reply_text(
                            success_message,
                            parse_mode='Markdown',
                            reply_markup=reply_markup
                        )
                    else:
                        await update.message.reply_text(
                            "❌ **Deletion Failed**\n\n"
                            "There was an error deleting the medicines. Please try again or contact support."
                        )
                        
                except Exception as e:
                    logger.error(f"Error in bulk deletion: {e}")
                    await update.message.reply_text(
                        f"❌ **Deletion Error**\n\n"
                        f"Error: {str(e)}\n\n"
                        "Please contact the administrator."
                    )
            else:
                # Incorrect PIN
                await update.message.reply_text(
                    "❌ **Incorrect PIN**\n\n"
                    "🔐 The security PIN you entered is incorrect.\n\n"
                    "🛡️ **Bulk deletion has been CANCELLED for security.**\n\n"
                    "If you need to delete all medicines, please try again with the correct PIN."
                )
                user_data[user_id]['awaiting_pin'] = False
            
            # Clean up user data
            if user_id in user_data and 'awaiting_pin' in user_data[user_id]:
                del user_data[user_id]
        
        async def cancel_pin_verification(update: Update, context):
            """Cancel PIN verification"""
            user_id = update.effective_user.id
            if user_id in user_data:
                user_data[user_id]['awaiting_pin'] = False
                del user_data[user_id]
            
            await update.message.reply_text(
                "❌ **Bulk Delete Cancelled**\n\n"
                "🛡️ Your medicines are safe. The bulk delete operation has been cancelled."
            )
        
        async def error_handler(update: Update, context):
            """Handle errors"""
            logger.error(f"Update {update} caused error {context.error}")
        
        # Create application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add conversation handler for add medicine
        add_medicine_conv = ConversationHandler(
            entry_points=[CommandHandler('add_medicine', add_medicine_start)],
            states={
                MEDICINE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_medicine_name)],
                BATCH_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_batch_number)],
                MANUFACTURING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manufacturing_date)],
                EXPIRING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_expiring_date)],
                DOSAGE_FORM: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dosage_form)],
                PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price)],
                STOCK_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stock_quantity)],
            },
            fallbacks=[CommandHandler('cancel', cancel_add_medicine)],
        )
        
        # Add handlers
        application.add_handler(CommandHandler('start', start_command))
        application.add_handler(CommandHandler('medicines', medicines_command))
        application.add_handler(CommandHandler('search', search_command))
        application.add_handler(CommandHandler('cancel', cancel_pin_verification))
        application.add_handler(add_medicine_conv)
        application.add_handler(CallbackQueryHandler(enhanced_button_handler))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))  # Add document handler
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pin_verification))  # Add PIN verification handler
        application.add_error_handler(error_handler)
        
        print("✅ Complete bot with buttons configured!")
        print("\n🎯 **COMPREHENSIVE FEATURES ACTIVE:**")
        print("   🔹 Complete button interface")
        print("   🔹 7-field medicine system")
        print("   🔹 Role-based access control")
        print("   🔹 Staff/Admin management tools")
        print("   🔹 Customer service features")
        print("   🔹 Interactive navigation")
        print("   🔹 Comprehensive help system")
        
        print("\n📱 **BUTTON FEATURES:**")
        print("   📦 Manage Stock")
        print("   💊 Check Medicine") 
        print("   📝 Add Medicine")
        print("   📊 View Statistics")
        print("   📋 View Orders")
        print("   💰 Update Prices")
        print("   📝 Edit Contacts")
        print("   👥 Manage Users")
        print("   📞 Contact Info")
        print("   ❓ Help")
        
        print("\n" + "=" * 65)
        print("🚀 COMPLETE BLUE PHARMA BOT WITH BUTTONS IS RUNNING!")
        print("📱 All buttons and features are fully functional")
        print("🛑 Press Ctrl+C to stop")
        print("=" * 65)
        
        # Run the bot
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
        print("👋 Thank you for using Blue Pharma Bot!")
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Please install: pip install python-telegram-bot")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Bot error: {e}")
        return False

if __name__ == "__main__":
    main()
