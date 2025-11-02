#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blue Pharma Trading PLC - Complete Bot with All Buttons
Includes a comprehensive button interface with a new 7-field medicine system.
"""

import sys
import logging
import asyncio
import os
import tempfile
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
# Keep the bot alive on Render without a paid worker
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

keep_alive()


load_dotenv()

# Try to import pandas, make it optional
try:
    import pandas as pd
    PANDAS_SUPPORT = True
except ImportError:
    PANDAS_SUPPORT = False
    pd = None
    print("⚠️ Pandas not available. Excel export features will be disabled.")

# Telegram imports
try:
    from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes
    )
    TELEGRAM_SUPPORT = True
except ImportError:
    TELEGRAM_SUPPORT = False
    print("⚠️ Telegram support not available. Install with: pip install python-telegram-bot")

# Fuzzy matching imports
try:
    from difflib import SequenceMatcher
    FUZZY_SUPPORT = True
except ImportError:
    FUZZY_SUPPORT = False
    print("⚠️ Fuzzy matching not available.")

# Excel processing imports
try:
    import openpyxl
    EXCEL_SUPPORT = PANDAS_SUPPORT and True  # Only enable if pandas is also available
except ImportError:
    EXCEL_SUPPORT = False
    print("⚠️ Excel support not available. Install with: pip install pandas openpyxl")

# Import enhanced Excel analytics
try:
    from excel_analytics import generate_enhanced_weekly_report, generate_enhanced_comparison_report
    ENHANCED_EXCEL_SUPPORT = True
except ImportError:
    ENHANCED_EXCEL_SUPPORT = False
    print("⚠️ Enhanced Excel analytics not available. Check excel_analytics.py file.")

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

# --- Database Manager Class ---
class DatabaseManager:
    """Manages the SQLite database for the bot."""
    
    def __init__(self, db_name):
        self.db_name = db_name
        self.create_tables()

    def get_connection(self):
        """Creates and returns a database connection."""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def create_tables(self):
        """Creates database tables if they don't exist."""
        # Note: Tables already exist in the database with different schema
        # This method is kept for compatibility but doesn't create new tables
        pass

    def add_user(self, telegram_id, first_name, last_name, username, user_type):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (telegram_id, first_name, last_name, username, user_type)
            VALUES (?, ?, ?, ?, ?)
        """, (telegram_id, first_name, last_name, username, user_type))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id
    
    def get_user(self, telegram_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ? AND is_active = 1", (telegram_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            # Return user dict directly since user_type column exists
            user_dict = dict(user)
            return user_dict
        return None

    def update_user_type(self, telegram_id, new_type):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET user_type = ? WHERE telegram_id = ?", (new_type, telegram_id))
        conn.commit()
        conn.close()
    
    # --- Users management helpers ---
    def get_all_users(self, limit=20):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT id, telegram_id, first_name, last_name, username, user_type, is_active
                FROM users
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def set_user_active(self, user_id, is_active):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (1 if is_active else 0, user_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def update_user_type_by_id(self, user_id, new_type):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET user_type = ? WHERE id = ?", (new_type, user_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def add_medicine(self, name, category, mfg_date, exp_date, form, price, quantity):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO medicines (name, therapeutic_category, manufacturing_date, expiring_date, 
            dosage_form, price, stock_quantity, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (name, category, mfg_date, exp_date, form, price, quantity))
        conn.commit()
        conn.close()
    
    def get_medicine_by_name(self, name):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # First try exact LIKE search
        cursor.execute("SELECT * FROM medicines WHERE name LIKE ? COLLATE NOCASE AND is_active = 1", (f'%{name}%',))
        medicines = cursor.fetchall()
        
        # If no results and search term contains spaces, try with underscores
        if not medicines and ' ' in name:
            name_with_underscores = name.replace(' ', '_')
            cursor.execute("SELECT * FROM medicines WHERE name LIKE ? COLLATE NOCASE AND is_active = 1", (f'%{name_with_underscores}%',))
            medicines = cursor.fetchall()
        
        # If no results and search term contains underscores, try with spaces
        elif not medicines and '_' in name:
            name_with_spaces = name.replace('_', ' ')
            cursor.execute("SELECT * FROM medicines WHERE name LIKE ? COLLATE NOCASE AND is_active = 1", (f'%{name_with_spaces}%',))
            medicines = cursor.fetchall()
        
        conn.close()
        return [dict(med) for med in medicines]
        
    def get_medicine_by_id(self, med_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medicines WHERE id = ?", (med_id,))
        medicine = cursor.fetchone()
        conn.close()
        return dict(medicine) if medicine else None

    def get_all_medicines(self, limit=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM medicines WHERE is_active = 1 ORDER BY name"
        if limit:
            query += f" LIMIT {limit}"
        cursor.execute(query)
        medicines = cursor.fetchall()
        conn.close()
        return [dict(med) for med in medicines]
    
    def check_duplicate(self, name):
        """Check if medicine with similar name already exists (case-insensitive)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT id, name, manufacturing_date, expiring_date, dosage_form, price, stock_quantity
                FROM medicines 
                WHERE LOWER(name) = LOWER(?) AND is_active = 1
            """, (name.strip(),))
            
            row = cursor.fetchone()
            return dict(row) if row else None
            
        except sqlite3.Error as e:
            logger.error(f"Error checking duplicate medicine: {e}")
            return None
        finally:
            conn.close()
    
    def get_medicine_categories(self):
        """Get unique therapeutic categories that have active medicines."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT therapeutic_category FROM medicines WHERE therapeutic_category IS NOT NULL AND is_active = 1 ORDER BY therapeutic_category")
        categories = cursor.fetchall()
        conn.close()
        return [row[0] for row in categories]
    
    def get_medicines_by_category(self, category):
        """Get all medicines in a specific category."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medicines WHERE therapeutic_category = ? AND is_active = 1 ORDER BY name", (category,))
        medicines = cursor.fetchall()
        conn.close()
        return [dict(med) for med in medicines]

    def get_low_stock_medicines(self, threshold=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medicines WHERE stock_quantity <= ? ORDER BY stock_quantity", (threshold,))
        medicines = cursor.fetchall()
        conn.close()
        return [dict(med) for med in medicines]
        
    def get_stock_overview(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM medicines")
        total_medicines = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(stock_quantity) FROM medicines")
        total_stock = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM medicines WHERE stock_quantity <= 10")
        low_stock = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM medicines WHERE stock_quantity = 0")
        out_of_stock = cursor.fetchone()[0]
        
        conn.close()
        return {
            'total_medicines': total_medicines,
            'total_stock': total_stock,
            'low_stock': low_stock,
            'out_of_stock': out_of_stock
        }

    def get_daily_sales_summary(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Count orders from today
        cursor.execute("SELECT COUNT(*) FROM orders WHERE order_date LIKE ? || '%'", (today,))
        total_orders = cursor.fetchone()[0]
        
        # Get total items sold and revenue from order_items
        cursor.execute("""
            SELECT SUM(oi.quantity), SUM(o.total_amount)
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            WHERE o.order_date LIKE ? || '%'
        """, (today,))
        result = cursor.fetchone()
        total_items_sold, total_revenue = result if result else (0, 0.0)
        
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM orders WHERE order_date LIKE ? || '%'", (today,))
        total_customers = cursor.fetchone()[0]
        
        # Get top medicine
        cursor.execute("""
            SELECT m.name, SUM(oi.quantity) AS total_sold
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN medicines m ON oi.medicine_id = m.id
            WHERE o.order_date LIKE ? || '%'
            GROUP BY m.name
            ORDER BY total_sold DESC
            LIMIT 1
        """, (today,))
        top_medicine = cursor.fetchone()
        
        # Get top category
        cursor.execute("""
            SELECT m.therapeutic_category, SUM(oi.quantity) AS total_sold
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN medicines m ON oi.medicine_id = m.id
            WHERE o.order_date LIKE ? || '%'
            GROUP BY m.therapeutic_category
            ORDER BY total_sold DESC
            LIMIT 1
        """, (today,))
        top_category = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_orders': total_orders,
            'total_items_sold': total_items_sold or 0,
            'total_revenue': total_revenue or 0.0,
            'total_customers': total_customers,
            'avg_order_value': (total_revenue / total_orders) if total_orders > 0 else 0,
            'top_medicine': top_medicine[0] if top_medicine else 'N/A',
            'top_category': top_category[0] if top_category else 'N/A'
        }

    def get_weekly_sales_data(self, num_weeks=4):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = f"""
            SELECT
                strftime('%Y-%W', order_date) as week,
                SUM(total_amount) as total_revenue,
                COUNT(id) as total_orders
            FROM orders
            GROUP BY week
            ORDER BY week DESC
            LIMIT {num_weeks}
        """
        cursor.execute(query)
        data = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in data]
    
    def cleanup_old_orders(self):
        """Remove orders older than 2 weeks"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Calculate date 2 weeks ago
        from datetime import datetime, timedelta
        two_weeks_ago = (datetime.now() - timedelta(weeks=2)).strftime('%Y-%m-%d')
        
        try:
            # First, get the orders that will be deleted for logging
            cursor.execute("SELECT COUNT(*) FROM orders WHERE order_date < ?", (two_weeks_ago,))
            old_orders_count = cursor.fetchone()[0]
            
            # Delete order items first (foreign key constraint)
            cursor.execute("""
                DELETE FROM order_items 
                WHERE order_id IN (
                    SELECT id FROM orders WHERE order_date < ?
                )
            """, (two_weeks_ago,))
            
            # Then delete the orders
            cursor.execute("DELETE FROM orders WHERE order_date < ?", (two_weeks_ago,))
            
            conn.commit()
            logger.info(f"Database cleanup: Removed {old_orders_count} orders older than {two_weeks_ago}")
            return old_orders_count
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error during database cleanup: {e}", exc_info=True)
            return 0
        finally:
            conn.close()
    
    def get_weekly_comparison_data(self):
        """Get weekly sales data for comparison analysis"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT
                strftime('%Y-%W', order_date) as week_number,
                strftime('%Y-%m-%d', MIN(order_date)) as week_start,
                strftime('%Y-%m-%d', MAX(order_date)) as week_end,
                SUM(total_amount) as total_revenue,
                COUNT(id) as total_orders,
                COUNT(DISTINCT user_id) as unique_customers,
                AVG(total_amount) as avg_order_value
            FROM orders
            WHERE order_date >= date('now', '-8 weeks')
            GROUP BY week_number
            ORDER BY week_number DESC
        """
        cursor.execute(query)
        data = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in data]
    
    def place_order(self, user_id, customer_name, customer_phone, cart):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Calculate total order amount
            order_total = 0.0
            valid_items = []
            
            # Validate all items and calculate total
            for item in cart:
                med = self.get_medicine_by_id(item['medicine_id'])
                if not med:
                    logger.warning(f"Medicine {item['medicine_id']} not found")
                    continue
                if med['stock_quantity'] < item['quantity']:
                    logger.warning(f"Insufficient stock for medicine {med['name']}")
                    continue
                    
                item_total = med['price'] * item['quantity']
                order_total += item_total
                valid_items.append({
                    'medicine_id': item['medicine_id'],
                    'quantity': item['quantity'],
                    'unit_price': med['price'],
                    'total_price': item_total,
                    'medicine': med
                })
            
            if not valid_items:
                logger.error("No valid items in cart")
                return None
            
            # Generate order number (timestamp-based for uniqueness)
            order_number = f"ORD{int(datetime.now().timestamp())}"
            
            # Create main order record (order_id will be consecutive)
            cursor.execute("""
                INSERT INTO orders (user_id, order_number, total_amount, status, 
                delivery_method, customer_name, customer_phone)
                VALUES (?, ?, ?, 'pending', 'pickup', ?, ?)
            """, (user_id, order_number, order_total, customer_name, customer_phone))
            
            order_id = cursor.lastrowid
            
            # Generate clean consecutive order number for display
            clean_order_id = f"{order_id:02d}"
            
            # Create order items
            for item in valid_items:
                cursor.execute("""
                    INSERT INTO order_items (order_id, medicine_id, quantity, unit_price, total_price)
                    VALUES (?, ?, ?, ?, ?)
                """, (order_id, item['medicine_id'], item['quantity'], 
                      item['unit_price'], item['total_price']))
                
                # Update stock
                new_stock = item['medicine']['stock_quantity'] - item['quantity']
                cursor.execute("UPDATE medicines SET stock_quantity = ? WHERE id = ?", 
                              (new_stock, item['medicine_id']))
            
            conn.commit()
            logger.info(f"Order {order_id} placed successfully with {len(valid_items)} items")
            return order_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to place order: {e}", exc_info=True)
            return None
        finally:
            conn.close()
    
    def get_user_orders(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT o.id, o.order_date, o.status, o.total_amount,
                   COUNT(oi.id) as total_items
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.user_id = ?
            GROUP BY o.id
            ORDER BY o.order_date DESC
            LIMIT 10
        """, (user_id,))
        orders = cursor.fetchall()
        conn.close()
        return [dict(order) for order in orders]
    
    def get_all_orders(self, limit=50):
        """Get all orders in the system (for admin/staff view)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT o.id, o.order_number, o.order_date, o.status, o.total_amount,
                   o.customer_name, o.customer_phone, o.delivery_method,
                   u.first_name, u.last_name, u.telegram_id,
                   COUNT(oi.id) as total_items
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            LEFT JOIN order_items oi ON o.id = oi.order_id
            GROUP BY o.id
            ORDER BY o.order_date DESC
            LIMIT ?
        """, (limit,))
        orders = cursor.fetchall()
        conn.close()
        return [dict(order) for order in orders]
    
    def get_pending_orders(self, limit=50):
        """Get all pending orders (for admin/staff view)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT o.id, o.order_number, o.order_date, o.status, o.total_amount,
                   o.customer_name, o.customer_phone, o.delivery_method,
                   u.first_name, u.last_name, u.telegram_id,
                   COUNT(oi.id) as total_items
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.status = 'pending'
            GROUP BY o.id
            ORDER BY o.order_date DESC
            LIMIT ?
        """, (limit,))
        orders = cursor.fetchall()
        conn.close()
        return [dict(order) for order in orders]
    
    def get_completed_orders(self, limit=50):
        """Get all completed orders (for admin/staff view)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT o.id, o.order_number, o.order_date, o.status, o.total_amount,
                   o.customer_name, o.customer_phone, o.delivery_method,
                   u.first_name, u.last_name, u.telegram_id,
                   COUNT(oi.id) as total_items
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.status = 'completed'
            GROUP BY o.id
            ORDER BY o.order_date DESC
            LIMIT ?
        """, (limit,))
        orders = cursor.fetchall()
        conn.close()
        return [dict(order) for order in orders]
    
    def get_order_details(self, order_id):
        """Get detailed information about a specific order including items."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get order information
        cursor.execute("""
            SELECT o.*, u.first_name, u.last_name, u.telegram_id
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            WHERE o.id = ?
        """, (order_id,))
        order = cursor.fetchone()
        
        if not order:
            conn.close()
            return None
        
        # Get order items
        cursor.execute("""
            SELECT oi.*, m.name as medicine_name, m.therapeutic_category
            FROM order_items oi
            JOIN medicines m ON oi.medicine_id = m.id
            WHERE oi.order_id = ?
            ORDER BY m.name
        """, (order_id,))
        items = cursor.fetchall()
        
        conn.close()
        
        order_dict = dict(order)
        order_dict['items'] = [dict(item) for item in items]
        
        return order_dict
    
    def remove_medicine(self, medicine_id):
        """Remove a specific medicine by setting is_active to 0"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE medicines SET is_active = 0 WHERE id = ?", (medicine_id,))
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected > 0
    
    def remove_all_medicines(self):
        """Remove all medicines by setting is_active to 0"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE medicines SET is_active = 0 WHERE is_active = 1")
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected
    
    def update_medicine_stock(self, medicine_id, new_quantity, reason=None):
        """Update stock quantity for a specific medicine"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get current stock
        cursor.execute("SELECT stock_quantity, name FROM medicines WHERE id = ?", (medicine_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "Medicine not found"
        
        old_quantity, medicine_name = result
        
        # Update stock
        cursor.execute("UPDATE medicines SET stock_quantity = ? WHERE id = ?", (new_quantity, medicine_id))
        
        # Log the stock change (optional - could add a stock_history table)
        logger.info(f"Stock updated for {medicine_name}: {old_quantity} -> {new_quantity}. Reason: {reason or 'Not specified'}")
        
        conn.commit()
        conn.close()
        return True, f"Stock updated from {old_quantity} to {new_quantity}"
    
    def update_medicine_price(self, medicine_id, new_price):
        """Update price for a specific medicine"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get current price
        cursor.execute("SELECT price, name FROM medicines WHERE id = ?", (medicine_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "Medicine not found"
        
        old_price, medicine_name = result
        
        # Update price
        cursor.execute("UPDATE medicines SET price = ? WHERE id = ?", (new_price, medicine_id))
        
        logger.info(f"Price updated for {medicine_name}: {old_price} -> {new_price}")
        
        conn.commit()
        conn.close()
        return True, f"Price updated from {old_price:.2f} ETB to {new_price:.2f} ETB"
    
    def bulk_update_prices_by_percentage(self, percentage, category=None):
        """Update prices by percentage for all medicines or specific category"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if category:
            cursor.execute("SELECT id, name, price FROM medicines WHERE therapeutic_category = ? AND is_active = 1", (category,))
        else:
            cursor.execute("SELECT id, name, price FROM medicines WHERE is_active = 1")
        
        medicines = cursor.fetchall()
        updated_count = 0
        
        for medicine in medicines:
            med_id, name, old_price = medicine
            new_price = old_price * (1 + percentage / 100)
            cursor.execute("UPDATE medicines SET price = ? WHERE id = ?", (new_price, med_id))
            updated_count += 1
            logger.info(f"Price updated for {name}: {old_price:.2f} -> {new_price:.2f} ETB ({percentage:+.1f}%)")
        
        conn.commit()
        conn.close()
        return updated_count
    
    def bulk_update_prices_by_amount(self, amount, category=None):
        """Update prices by fixed amount for all medicines or specific category"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if category:
            cursor.execute("SELECT id, name, price FROM medicines WHERE therapeutic_category = ? AND is_active = 1", (category,))
        else:
            cursor.execute("SELECT id, name, price FROM medicines WHERE is_active = 1")
        
        medicines = cursor.fetchall()
        updated_count = 0
        
        for medicine in medicines:
            med_id, name, old_price = medicine
            new_price = max(0.01, old_price + amount)  # Ensure price doesn't go below 0.01
            cursor.execute("UPDATE medicines SET price = ? WHERE id = ?", (new_price, med_id))
            updated_count += 1
            logger.info(f"Price updated for {name}: {old_price:.2f} -> {new_price:.2f} ETB ({amount:+.2f} ETB)")
        
        conn.commit()
        conn.close()
        return updated_count
    
    def get_monthly_sales_summary(self, num_months=6):
        """Get monthly sales summary for the specified number of months"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = f"""
            SELECT
                strftime('%Y-%m', order_date) as month,
                SUM(total_amount) as total_revenue,
                COUNT(id) as total_orders,
                COUNT(DISTINCT user_id) as unique_customers
            FROM orders
            GROUP BY month
            ORDER BY month DESC
            LIMIT {num_months}
        """
        cursor.execute(query)
        data = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in data]
    
    def get_category_sales_breakdown(self):
        """Get sales breakdown by therapeutic category"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                m.therapeutic_category,
                SUM(oi.quantity) as total_quantity_sold,
                SUM(oi.total_price) as total_revenue,
                COUNT(DISTINCT o.id) as orders_containing_category
            FROM order_items oi
            JOIN medicines m ON oi.medicine_id = m.id
            JOIN orders o ON oi.order_id = o.id
            GROUP BY m.therapeutic_category
            ORDER BY total_revenue DESC
        """
        cursor.execute(query)
        data = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in data]
    
    def update_existing_medicine(self, medicine_id, name, category, mfg_date, exp_date, form, price, quantity, update_mode='add_stock'):
        """Update an existing medicine record.
        
        Args:
            medicine_id: ID of the medicine to update
            name, category, mfg_date, exp_date, form, price, quantity: New medicine data
            update_mode: 'add_stock' to add to existing stock, 'overwrite' to replace all fields
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if update_mode == 'add_stock':
                # Get current stock and add to it
                cursor.execute("SELECT stock_quantity FROM medicines WHERE id = ?", (medicine_id,))
                result = cursor.fetchone()
                if result:
                    current_stock = result[0]
                    new_stock = current_stock + quantity
                    cursor.execute("UPDATE medicines SET stock_quantity = ? WHERE id = ?", (new_stock, medicine_id))
                    conn.commit()
                    conn.close()
                    return True, f"Stock updated: {current_stock} + {quantity} = {new_stock} units"
                else:
                    conn.close()
                    return False, "Medicine not found"
            
            elif update_mode == 'overwrite':
                # Update all fields with new data
                cursor.execute("""
                    UPDATE medicines 
                    SET name = ?, therapeutic_category = ?, manufacturing_date = ?, 
                        expiring_date = ?, dosage_form = ?, price = ?, stock_quantity = ?
                    WHERE id = ?
                """, (name, category, mfg_date, exp_date, form, price, quantity, medicine_id))
                conn.commit()
                conn.close()
                return True, "Medicine record completely updated"
            
            else:
                conn.close()
                return False, "Invalid update mode"
                
        except Exception as e:
            conn.rollback()
            conn.close()
            logger.error(f"Error updating existing medicine: {e}", exc_info=True)
            return False, f"Update failed: {str(e)}"
    
    def batch_update_medicines(self, updates_list, update_mode='add_stock'):
        """Batch update multiple medicines for Excel processing.
        
        Args:
            updates_list: List of tuples (medicine_id, medicine_data)
            update_mode: 'add_stock' to add to existing stock, 'overwrite' to replace all fields
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        updated_count = 0
        failed_count = 0
        
        try:
            for medicine_id, medicine_data in updates_list:
                try:
                    if update_mode == 'add_stock':
                        # Get current stock and add to it
                        cursor.execute("SELECT stock_quantity FROM medicines WHERE id = ?", (medicine_id,))
                        result = cursor.fetchone()
                        if result:
                            current_stock = result[0]
                            new_stock = current_stock + medicine_data['stock_quantity']
                            cursor.execute("UPDATE medicines SET stock_quantity = ? WHERE id = ?", (new_stock, medicine_id))
                            updated_count += 1
                            logger.info(f"Stock updated for medicine ID {medicine_id}: {current_stock} + {medicine_data['stock_quantity']} = {new_stock}")
                        else:
                            failed_count += 1
                            logger.error(f"Medicine ID {medicine_id} not found for stock update")
                    
                    elif update_mode == 'overwrite':
                        # Update all fields with new data
                        cursor.execute("""
                            UPDATE medicines 
                            SET name = ?, therapeutic_category = ?, manufacturing_date = ?, 
                                expiring_date = ?, dosage_form = ?, price = ?, stock_quantity = ?
                            WHERE id = ?
                        """, (
                            medicine_data['name'],
                            medicine_data['therapeutic_category'],
                            medicine_data['manufacturing_date'],
                            medicine_data['expiring_date'],
                            medicine_data['dosage_form'],
                            medicine_data['price'],
                            medicine_data['stock_quantity'],
                            medicine_id
                        ))
                        updated_count += 1
                        logger.info(f"Medicine ID {medicine_id} completely updated with new data")
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to update medicine ID {medicine_id}: {e}")
            
            conn.commit()
            conn.close()
            return updated_count, failed_count
            
        except Exception as e:
            conn.rollback()
            conn.close()
            logger.error(f"Error in batch update: {e}", exc_info=True)
            return 0, len(updates_list)
    
    def update_order_status(self, order_id, new_status):
        """Update the status of an order."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get current order details
            cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            order = cursor.fetchone()
            
            if not order:
                conn.close()
                return False, "Order not found"
            
            old_status = order['status']
            
            # Update order status
            cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Order {order_id} status updated from '{old_status}' to '{new_status}'")
            return True, f"Order status updated from '{old_status}' to '{new_status}'"
            
        except Exception as e:
            conn.rollback()
            conn.close()
            logger.error(f"Error updating order status: {e}", exc_info=True)
            return False, f"Failed to update status: {str(e)}"
    
    def find_order_by_number(self, order_number):
        """Find an order by its order number."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT o.*, u.first_name, u.last_name, u.telegram_id
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            WHERE o.order_number = ?
        """, (order_number,))
        order = cursor.fetchone()
        conn.close()
        
        return dict(order) if order else None
    
    def create_user_activity_table(self):
        """Create user activity tracking table if it doesn't exist."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    activity_date DATE,
                    message_count INTEGER DEFAULT 0,
                    order_count INTEGER DEFAULT 0,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_activity_date 
                ON user_activity(user_id, activity_date)
            """)
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error creating user activity table: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def track_user_activity(self, telegram_id, activity_type='message'):
        """Track user activity for analytics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get user ID
            cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            user_result = cursor.fetchone()
            if not user_result:
                conn.close()
                return
            
            user_id = user_result[0]
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Check if activity record exists for today
            cursor.execute(
                "SELECT id, message_count, order_count FROM user_activity WHERE user_id = ? AND activity_date = ?",
                (user_id, today)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                activity_id, msg_count, order_count = existing
                if activity_type == 'message':
                    msg_count += 1
                elif activity_type == 'order':
                    order_count += 1
                
                cursor.execute(
                    "UPDATE user_activity SET message_count = ?, order_count = ?, last_activity = CURRENT_TIMESTAMP WHERE id = ?",
                    (msg_count, order_count, activity_id)
                )
            else:
                # Create new record
                msg_count = 1 if activity_type == 'message' else 0
                order_count = 1 if activity_type == 'order' else 0
                
                cursor.execute(
                    "INSERT INTO user_activity (user_id, activity_date, message_count, order_count) VALUES (?, ?, ?, ?)",
                    (user_id, today, msg_count, order_count)
                )
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error tracking user activity: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_weekly_analytics_data(self, num_weeks=8):
        """Get comprehensive weekly analytics data for bot usage."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Create the user activity table if it doesn't exist
            self.create_user_activity_table()
            
            # Get weekly data for the specified number of weeks
            query = """
                WITH weekly_stats AS (
                    SELECT 
                        strftime('%Y-%W', activity_date) as week_number,
                        MIN(activity_date) as week_start,
                        MAX(activity_date) as week_end,
                        COUNT(DISTINCT user_id) as active_users,
                        SUM(message_count) as total_messages,
                        SUM(order_count) as total_orders
                    FROM user_activity 
                    WHERE activity_date >= date('now', '-' || ? || ' weeks')
                    GROUP BY week_number
                ),
                new_users_weekly AS (
                    SELECT 
                        strftime('%Y-%W', created_at) as week_number,
                        COUNT(*) as new_users
                    FROM users 
                    WHERE created_at >= date('now', '-' || ? || ' weeks')
                    GROUP BY week_number
                ),
                revenue_weekly AS (
                    SELECT 
                        strftime('%Y-%W', order_date) as week_number,
                        SUM(total_amount) as revenue,
                        COUNT(*) as order_requests
                    FROM orders 
                    WHERE order_date >= date('now', '-' || ? || ' weeks')
                    GROUP BY week_number
                ),
                top_users_weekly AS (
                    SELECT 
                        strftime('%Y-%W', ua.activity_date) as week_number,
                        u.first_name || ' ' || COALESCE(u.last_name, '') as top_user,
                        SUM(ua.message_count + ua.order_count) as total_activity
                    FROM user_activity ua
                    JOIN users u ON ua.user_id = u.id
                    WHERE ua.activity_date >= date('now', '-' || ? || ' weeks')
                    GROUP BY week_number, ua.user_id
                )
                SELECT 
                    ws.week_number,
                    ws.week_start,
                    ws.week_end,
                    COALESCE(nuw.new_users, 0) as new_users,
                    ws.active_users,
                    ws.total_messages,
                    COALESCE(rw.order_requests, 0) as orders_requests,
                    COALESCE(rw.revenue, 0) as revenue,
                    (
                        SELECT tuw.top_user 
                        FROM top_users_weekly tuw 
                        WHERE tuw.week_number = ws.week_number 
                        ORDER BY tuw.total_activity DESC 
                        LIMIT 1
                    ) as top_user
                FROM weekly_stats ws
                LEFT JOIN new_users_weekly nuw ON ws.week_number = nuw.week_number
                LEFT JOIN revenue_weekly rw ON ws.week_number = rw.week_number
                ORDER BY ws.week_number DESC
                LIMIT ?
            """
            
            cursor.execute(query, (num_weeks, num_weeks, num_weeks, num_weeks, num_weeks))
            data = cursor.fetchall()
            conn.close()
            
            # Convert to list of dictionaries and add notes
            weekly_data = []
            for row in data:
                row_dict = dict(row)
                
                # Add contextual notes based on performance
                notes = []
                if row_dict['new_users'] > 10:
                    notes.append("High user acquisition")
                elif row_dict['new_users'] == 0:
                    notes.append("No new users")
                
                if row_dict['revenue'] > 1000:
                    notes.append("Strong revenue week")
                elif row_dict['revenue'] == 0:
                    notes.append("No sales recorded")
                
                if row_dict['total_messages'] > 100:
                    notes.append("High engagement")
                elif row_dict['total_messages'] < 10:
                    notes.append("Low activity")
                
                row_dict['notes'] = "; ".join(notes) if notes else "Normal activity"
                weekly_data.append(row_dict)
            
            return weekly_data
            
        except Exception as e:
            logger.error(f"Error getting weekly analytics data: {e}", exc_info=True)
            conn.close()
            return []
    
    def get_weekly_comparison_metrics(self):
        """Get current week vs previous week comparison metrics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Create the user activity table if it doesn't exist
            self.create_user_activity_table()
            
            # Get current week and previous week data
            current_week = datetime.now().strftime('%Y-%W')
            
            # Calculate previous week
            from datetime import timedelta
            prev_week_date = datetime.now() - timedelta(weeks=1)
            previous_week = prev_week_date.strftime('%Y-%W')
            
            metrics = {
                'new_users': {'current': 0, 'previous': 0},
                'active_users': {'current': 0, 'previous': 0},
                'total_messages': {'current': 0, 'previous': 0},
                'orders_requests': {'current': 0, 'previous': 0},
                'revenue': {'current': 0.0, 'previous': 0.0}
            }
            
            # Get new users for both weeks
            cursor.execute("""
                SELECT 
                    strftime('%Y-%W', created_at) as week_number,
                    COUNT(*) as new_users
                FROM users 
                WHERE strftime('%Y-%W', created_at) IN (?, ?)
                GROUP BY week_number
            """, (current_week, previous_week))
            
            new_users_data = cursor.fetchall()
            for week_data in new_users_data:
                week, count = week_data
                if week == current_week:
                    metrics['new_users']['current'] = count
                elif week == previous_week:
                    metrics['new_users']['previous'] = count
            
            # Get user activity data for both weeks
            cursor.execute("""
                SELECT 
                    strftime('%Y-%W', activity_date) as week_number,
                    COUNT(DISTINCT user_id) as active_users,
                    SUM(message_count) as total_messages,
                    SUM(order_count) as total_orders
                FROM user_activity 
                WHERE strftime('%Y-%W', activity_date) IN (?, ?)
                GROUP BY week_number
            """, (current_week, previous_week))
            
            activity_data = cursor.fetchall()
            for week_data in activity_data:
                week, active, messages, orders = week_data
                if week == current_week:
                    metrics['active_users']['current'] = active or 0
                    metrics['total_messages']['current'] = messages or 0
                    metrics['orders_requests']['current'] = orders or 0
                elif week == previous_week:
                    metrics['active_users']['previous'] = active or 0
                    metrics['total_messages']['previous'] = messages or 0
                    metrics['orders_requests']['previous'] = orders or 0
            
            # Get revenue data for both weeks
            cursor.execute("""
                SELECT 
                    strftime('%Y-%W', order_date) as week_number,
                    SUM(total_amount) as revenue
                FROM orders 
                WHERE strftime('%Y-%W', order_date) IN (?, ?)
                GROUP BY week_number
            """, (current_week, previous_week))
            
            revenue_data = cursor.fetchall()
            for week_data in revenue_data:
                week, revenue = week_data
                if week == current_week:
                    metrics['revenue']['current'] = revenue or 0.0
                elif week == previous_week:
                    metrics['revenue']['previous'] = revenue or 0.0
            
            conn.close()
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting weekly comparison metrics: {e}", exc_info=True)
            conn.close()
            return {}
    
    def create_contact_settings_table(self):
        """Create contact settings table if it doesn't exist."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contact_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Initialize default values if they don't exist
            default_values = [
                ('phone', '+251-11-555-0123'),
                ('email', 'contact@bluepharma.et'),
                ('address', '123 Pharmacy Street, Addis Ababa, Ethiopia'),
                ('hours', '08:00-22:00 Daily')
            ]
            
            for key, value in default_values:
                cursor.execute("""
                    INSERT OR IGNORE INTO contact_settings (setting_key, setting_value)
                    VALUES (?, ?)
                """, (key, value))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error creating contact settings table: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_contact_setting(self, key):
        """Get a contact setting value."""
        # Ensure table exists
        self.create_contact_settings_table()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT setting_value FROM contact_settings WHERE setting_key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting contact setting {key}: {e}")
            return None
        finally:
            conn.close()
    
    def update_contact_setting(self, key, value):
        """Update a contact setting value."""
        # Ensure table exists
        self.create_contact_settings_table()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO contact_settings (setting_key, setting_value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
            conn.commit()
            logger.info(f"Updated contact setting {key}: {value}")
            return True
        except Exception as e:
            logger.error(f"Error updating contact setting {key}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_all_contact_settings(self):
        """Get all contact settings."""
        # Ensure table exists
        self.create_contact_settings_table()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT setting_key, setting_value FROM contact_settings")
            results = cursor.fetchall()
            return {row[0]: row[1] for row in results}
        except Exception as e:
            logger.error(f"Error getting all contact settings: {e}")
            return {}
        finally:
            conn.close()
    
    def get_users_by_type(self, user_types):
        """Get users by user type(s)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if isinstance(user_types, str):
                # Single user type
                cursor.execute("""
                    SELECT * FROM users 
                    WHERE user_type = ?
                    ORDER BY created_at DESC
                """, (user_types,))
            else:
                # Multiple user types
                placeholders = ','.join('?' * len(user_types))
                cursor.execute(f"""
                    SELECT * FROM users 
                    WHERE user_type IN ({placeholders})
                    ORDER BY created_at DESC
                """, user_types)
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Error getting users by type: {e}")
            return []
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
        finally:
            conn.close()
    
    def set_user_active(self, user_id, is_active):
        """Set user active status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE users SET is_active = ? WHERE id = ?
            """, (is_active, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error setting user active status: {e}")
            return False
        finally:
            conn.close()
    
    def remove_all_medicines(self):
        """Remove all medicines from inventory"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM medicines")
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing all medicines: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_all_users(self, limit=50):
        """Get all users with optional limit"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM users 
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
        finally:
            conn.close()
    
    def format_order_id(self, order_id):
        """Format order ID as a clean consecutive string (e.g., '01', '02', '03')"""
        return f"{order_id:02d}"
    
    def get_order_display_id(self, order_id):
        """Get clean display ID for an order"""
        return self.format_order_id(order_id)

# Conversation states
(
    MEDICINE_NAME, THERAPEUTIC_CATEGORY, MANUFACTURING_DATE, EXPIRING_DATE,
    DOSAGE_FORM, PRICE, STOCK_QUANTITY
) = range(7)
(
    DUPLICATE_CONFIRMATION, DUPLICATE_ACTION_CHOICE, DUPLICATE_NEW_NAME
) = range(10, 13)
(
    UPDATE_STOCK_SEARCH, UPDATE_STOCK_QUANTITY
) = range(15, 17)
(
    EDIT_CONTACT_FIELD, EDIT_CONTACT_VALUE, EDIT_PHONE, EDIT_EMAIL, EDIT_ADDRESS
) = range(20, 25)
(
    WAITING_FOR_EXCEL_FILE, EXCEL_DUPLICATE_CHOICE, EXCEL_BATCH_CHOICE
) = range(30, 33)
(
    PIN_VERIFICATION
) = 40
(
    REMOVE_SELECTION, REMOVE_CONFIRMATION, REMOVE_PIN_VERIFICATION
) = range(50, 53)
(
    REMOVE_ALL_PIN_VERIFICATION
) = 55
(
    CUSTOMER_NAME, CUSTOMER_PHONE
) = range(60, 62)
(
    PRICE_UPDATE_METHOD, PRICE_UPDATE_VALUE, PRICE_MEDICINE_SELECTION
) = range(70, 73)
(
    STOCK_UPDATE_SEARCH, STOCK_UPDATE_QUANTITY, STOCK_UPDATE_REASON
) = range(80, 83)
(
    ORDER_STATUS_UPDATE_INPUT
) = 90
(
    ORDER_ID_SEARCH
) = 95
(
    CUSTOM_QUANTITY_INPUT
) = 100
(
    CHANGE_PIN_INPUT
) = 105

# User roles
USER_ROLES = {
    'customer': 'Customer',
    'staff': 'Staff',
    'admin': 'Administrator'
}

# User data storage for conversations and carts
user_data = {}

# Admin user ID
ADMIN_USER_ID = 7264670729

# --- Helper Functions ---
def get_or_create_user(db: DatabaseManager, telegram_id: int, first_name: str, last_name: Optional[str] = None, username: Optional[str] = None) -> Optional[Dict]:
    """Get or create user with automatic admin assignment."""
    try:
        user = db.get_user(telegram_id)
        if user:
            if telegram_id == ADMIN_USER_ID and user['user_type'] != 'admin':
                db.update_user_type(telegram_id, 'admin')
                user['user_type'] = 'admin'
                logger.info(f"Updated user {telegram_id} to admin role")
            return user
        
        user_type = 'admin' if telegram_id == ADMIN_USER_ID else 'customer'
        user_id = db.add_user(telegram_id, first_name, last_name, username, user_type)
        if user_type == 'admin':
            logger.info(f"Created new admin user: {telegram_id} ({first_name})")
        
        return {
            'id': user_id,
            'first_name': first_name,
            'user_type': user_type
        }
    except Exception as e:
        logger.error(f"User management error: {e}", exc_info=True)
        return None

def get_user_keyboard(user_type: str) -> List[List[InlineKeyboardButton]]:
    """Get role-based inline keyboard."""
    keyboard = []
    if user_type in ['staff', 'admin']:
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
            InlineKeyboardButton("📊 Update Stock", callback_data="update_stock")
        ])
        # Staff: only Edit Contacts; Admin: Edit Contacts + Manage Users + Change PIN
        if user_type == 'admin':
            keyboard.append([
                InlineKeyboardButton("📝 Edit Contacts", callback_data="edit_contact"),
                InlineKeyboardButton("👥 Manage Users", callback_data="manage_users")
            ])
            keyboard.append([
                InlineKeyboardButton("🔑 Change PIN", callback_data="change_pin")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("📝 Edit Contacts", callback_data="edit_contact")
            ])
    else:
        keyboard.append([
            InlineKeyboardButton("💊 Check Medicine", callback_data="check_medicine"),
            InlineKeyboardButton("🛒 Place Order", callback_data="place_order")
        ])
        keyboard.append([
            InlineKeyboardButton("📦 My Orders", callback_data="my_orders")
        ])
    
    keyboard.append([
        InlineKeyboardButton("📞 Contact Info", callback_data="contact_info"),
        InlineKeyboardButton("❓ Help", callback_data="help")
    ])
    return keyboard

def get_user_cart(user_id):
    """Get user's shopping cart."""
    if user_id not in user_data:
        user_data[user_id] = {}
    if 'cart' not in user_data[user_id]:
        user_data[user_id]['cart'] = []
    return user_data[user_id]['cart']

def add_to_cart_local(user_id, medicine_id, quantity=1):
    """Add item to cart or update quantity."""
    cart = get_user_cart(user_id)
    for item in cart:
        if item['medicine_id'] == medicine_id:
            item['quantity'] += quantity
            return
    cart.append({'medicine_id': medicine_id, 'quantity': quantity})

def remove_from_cart_local(user_id, medicine_id):
    """Remove item from cart."""
    cart = get_user_cart(user_id)
    user_data[user_id]['cart'] = [item for item in cart if item['medicine_id'] != medicine_id]

def clear_cart_local(user_id):
    """Clear user's cart."""
    if user_id in user_data and 'cart' in user_data[user_id]:
        user_data[user_id]['cart'] = []

def calculate_cart_total(db, user_id):
    """Calculate total price of items in cart."""
    cart = get_user_cart(user_id)
    total = 0.0
    for item in cart:
        medicine = db.get_medicine_by_id(item['medicine_id'])
        if medicine:
            total += medicine['price'] * item['quantity']
    return total

def calculate_similarity(a, b):
    """Calculate similarity ratio between two strings with enhanced matching."""
    if not FUZZY_SUPPORT:
        return 0.0
    
    # Normalize strings: lowercase, replace underscores with spaces, remove extra spaces
    a_norm = ' '.join(a.lower().replace('_', ' ').split())
    b_norm = ' '.join(b.lower().replace('_', ' ').split())
    
    # Primary similarity using SequenceMatcher
    primary_similarity = SequenceMatcher(None, a_norm, b_norm).ratio()
    
    # Secondary check: exact word matching (for cases like "med 99" vs "med_99")
    a_words = set(a_norm.split())
    b_words = set(b_norm.split())
    
    if a_words and b_words:
        # Calculate word overlap ratio
        common_words = a_words.intersection(b_words)
        word_similarity = len(common_words) / max(len(a_words), len(b_words))
        
        # Enhanced matching for partial matches like "med" in "med 99"
        if word_similarity >= 0.5 and primary_similarity < 0.6:
            primary_similarity = max(primary_similarity, word_similarity * 0.85)
        
        # Special boost for numeric patterns (like "99" in "med 99" vs "med_99")
        for word in a_words:
            if word.isdigit():
                for b_word in b_words:
                    if word == b_word:
                        primary_similarity = max(primary_similarity, 0.8)
    
    # Tertiary check: substring matching (one contains the other)
    if a_norm in b_norm or b_norm in a_norm:
        substring_similarity = min(len(a_norm), len(b_norm)) / max(len(a_norm), len(b_norm))
        primary_similarity = max(primary_similarity, substring_similarity * 0.75)
    
    # Special handling for common patterns like "med" + numbers
    if 'med' in a_norm and 'med' in b_norm:
        # Extract numbers from both strings
        import re
        a_nums = re.findall(r'\d+', a_norm)
        b_nums = re.findall(r'\d+', b_norm)
        if a_nums and b_nums and any(num in b_nums for num in a_nums):
            primary_similarity = max(primary_similarity, 0.7)
    
    return primary_similarity

def detect_medicine_duplicates(db, medicine_name, threshold=0.8):
    """Detect potential duplicate medicines by name with high similarity threshold."""
    all_medicines = db.get_all_medicines()
    duplicates = []
    
    # Normalize the input name
    name_norm = ' '.join(medicine_name.lower().replace('_', ' ').split())
    
    for medicine in all_medicines:
        similarity = calculate_similarity(medicine_name, medicine['name'])
        
        # Also check for exact case-insensitive match
        med_name_norm = ' '.join(medicine['name'].lower().replace('_', ' ').split())
        if name_norm == med_name_norm:
            similarity = 1.0
        
        if similarity >= threshold:
            medicine['similarity_score'] = similarity
            duplicates.append(medicine)
    
    # Sort by similarity score (highest first)
    duplicates.sort(key=lambda x: x['similarity_score'], reverse=True)
    return duplicates

def detect_excel_duplicates(db, excel_medicines, threshold=0.8):
    """Detect duplicates in Excel data against existing database."""
    existing_medicines = db.get_all_medicines()
    duplicates = []
    
    for i, excel_med in enumerate(excel_medicines):
        excel_name = str(excel_med.get('name', '')).strip()
        if not excel_name:
            continue
            
        # Check against existing medicines
        for existing_med in existing_medicines:
            similarity = calculate_similarity(excel_name, existing_med['name'])
            
            # Also check for exact case-insensitive match
            excel_name_norm = ' '.join(excel_name.lower().replace('_', ' ').split())
            existing_name_norm = ' '.join(existing_med['name'].lower().replace('_', ' ').split())
            if excel_name_norm == existing_name_norm:
                similarity = 1.0
            
            if similarity >= threshold:
                duplicate_info = {
                    'excel_index': i,
                    'excel_medicine': excel_med,
                    'existing_medicine': existing_med,
                    'similarity_score': similarity
                }
                duplicates.append(duplicate_info)
                break  # Only find the first duplicate for each Excel medicine
    
    return duplicates

async def present_duplicate_options(update, context, duplicate_medicines, medicine_name):
    """Present options to user when duplicates are detected for single medicine addition."""
    if not duplicate_medicines:
        return False
    
    # Store duplicate info in context
    context.user_data['duplicate_medicines'] = duplicate_medicines
    context.user_data['original_medicine_name'] = medicine_name
    
    duplicate_text = f"⚠️ **Potential Duplicate Medicine Detected!**\n\n"
    duplicate_text += f"🔍 **You're trying to add:** {medicine_name}\n\n"
    duplicate_text += f"📋 **Similar medicine(s) already exist:**\n\n"
    
    for i, medicine in enumerate(duplicate_medicines[:3], 1):  # Show top 3 matches
        similarity_percentage = int(medicine['similarity_score'] * 100)
        duplicate_text += f"{i}. **{medicine['name']}** ({similarity_percentage}% match)\n"
        duplicate_text += f"   📦 Current Stock: {medicine['stock_quantity']} units\n"
        duplicate_text += f"   💰 Current Price: {medicine['price']:.2f} ETB\n"
        duplicate_text += f"   🏷️ Category: {medicine['therapeutic_category'] or 'N/A'}\n\n"
    
    duplicate_text += f"🤔 **What would you like to do?**"
    
    keyboard = [
        [InlineKeyboardButton("📝 Continue with Original Name", callback_data="continue_original_name")],
        [InlineKeyboardButton("🔄 Update Existing Medicine", callback_data="update_existing_medicine")],
        [InlineKeyboardButton("📝 Enter New Name", callback_data="enter_new_name")],
        [InlineKeyboardButton("❌ Cancel Addition", callback_data="cancel_add")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(duplicate_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(duplicate_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    return True

async def present_excel_duplicate_options(update, context, duplicates):
    """Present options to user when duplicates are detected in Excel upload."""
    if not duplicates:
        return False
    
    # Store duplicate info in context
    context.user_data['excel_duplicates'] = duplicates
    
    duplicate_text = f"⚠️ **Duplicate Medicines Detected in Excel File!**\n\n"
    duplicate_text += f"📊 **Found {len(duplicates)} potential duplicate(s)**\n\n"
    
    # Show first few duplicates as examples
    for i, dup in enumerate(duplicates[:3], 1):
        excel_name = dup['excel_medicine'].get('name', 'Unknown')
        existing_name = dup['existing_medicine']['name']
        similarity_percentage = int(dup['similarity_score'] * 100)
        
        duplicate_text += f"{i}. Excel: **{excel_name}** ↔️ Existing: **{existing_name}** ({similarity_percentage}% match)\n"
    
    if len(duplicates) > 3:
        duplicate_text += f"\n... and {len(duplicates) - 3} more duplicates.\n"
    
    duplicate_text += f"\n🤔 **How would you like to handle duplicates?**"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Update Existing Records", callback_data="excel_update_existing")],
        [InlineKeyboardButton("➕ Add as New Medicines", callback_data="excel_add_as_new")],
        [InlineKeyboardButton("⚖️ Review Each Duplicate", callback_data="excel_review_each")],
        [InlineKeyboardButton("❌ Skip All Duplicates", callback_data="excel_skip_duplicates")],
        [InlineKeyboardButton("❌ Cancel Upload", callback_data="cancel_excel_upload")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(duplicate_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(duplicate_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    return True

def find_similar_medicines(db, search_term, threshold=0.35, max_results=5):
    """Find medicines with similar names using enhanced fuzzy matching."""
    if not FUZZY_SUPPORT:
        return []
    
    all_medicines = db.get_all_medicines()
    similar_medicines = []
    
    # Normalize search term
    search_norm = ' '.join(search_term.lower().replace('_', ' ').split())
    
    for medicine in all_medicines:
        similarity = calculate_similarity(search_term, medicine['name'])
        
        # Additional boost for very close matches
        med_name_norm = ' '.join(medicine['name'].lower().replace('_', ' ').split())
        
        # Extra boost for cases where search term is a subset of medicine name
        if search_norm in med_name_norm:
            similarity = max(similarity, 0.8)
        
        # Extra boost for exact word matches
        search_words = set(search_norm.split())
        med_words = set(med_name_norm.split())
        if search_words and med_words and search_words.issubset(med_words):
            similarity = max(similarity, 0.9)
        
        if similarity >= threshold:
            medicine['similarity_score'] = similarity
            similar_medicines.append(medicine)
    
    # Sort by similarity score (highest first) and return top results
    similar_medicines.sort(key=lambda x: x['similarity_score'], reverse=True)
    return similar_medicines[:max_results]

async def cleanup_old_reports(db):
    """Clean up old reports from database (remove reports older than 2 weeks)."""
    try:
        removed_count = db.cleanup_old_orders()
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old orders from database")
    except Exception as e:
        logger.error(f"Error during database cleanup: {e}", exc_info=True)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced start command with comprehensive button interface."""
    user = update.effective_user
    db = context.bot_data['db']
    telegram_user = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if not telegram_user:
        if update.message:
            await update.message.reply_text("Sorry, there was an error. Please try again.")
        return

    # Clear any ongoing conversation state
    user_id = user.id
    if user_id in user_data:
        user_data[user_id].clear()
    context.user_data.clear()
    
    user_type = telegram_user['user_type']
    role_display = USER_ROLES.get(user_type, user_type.title())
    
    welcome_text = f"""
🏥 **Welcome to Blue Pharma Trading PLC!**

Hello {telegram_user['first_name']}! I'm your comprehensive pharmacy management bot.

👤 **Your Access Level:** {role_display}

💊 **Our Enhanced 7-Field Medicine System:**
1. Medicine Name
2. Therapeutic Category
3. Manufacturing Date
4. Expiring Date
5. Dosage Form
6. Price (ETB)
7. Stock Quantity

🎯 **What would you like to do today?**
Choose from the options below:
"""
    keyboard = get_user_keyboard(user_type)
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all inline button presses."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db = context.bot_data['db']
    user_info = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if not user_info:
        await query.edit_message_text("Error accessing user information. Please try /start")
        return
        
    user_type = user_info['user_type']
    data = query.data
    
    # --- Button Routing Logic ---
    if data == "manage_stock":
        await handle_manage_stock(query, user_type, db)
    elif data == "check_medicine":
        await handle_check_medicine(query)
    elif data == "add_medicine":
        await handle_add_medicine_button(query, user_type)
    elif data == "view_stats":
        await handle_view_stats(query, user_type, db)
    elif data == "view_orders":
        await handle_view_orders(query, user_type)
    elif data == "update_prices":
        await handle_update_prices(query, user_type)
    elif data == "edit_contact":
        await handle_edit_contact(query, user_type)
    elif data == "edit_phone":
        await handle_edit_phone(query, user_type, context)
    elif data == "edit_email":
        await handle_edit_email(query, user_type, context)
    elif data == "edit_address":
        await handle_edit_address(query, user_type, context)
    elif data == "manage_users":
        await handle_manage_users(query, user_type)
    elif data == "manage_customers":
        await handle_manage_customers(query, user_type, db)
    elif data == "manage_staff":
        await handle_manage_staff(query, user_type, db)
    elif data == "view_customers":
        await handle_view_customers(query, user_type, db)
    elif data == "toggle_customers":
        await handle_toggle_customers(query, user_type, db)
    elif data == "edit_customer_roles":
        await handle_edit_customer_roles(query, user_type, db)
    elif data == "view_staff":
        await handle_view_staff(query, user_type, db)
    elif data == "toggle_staff":
        await handle_toggle_staff(query, user_type, db)
    elif data == "edit_staff_roles":
        await handle_edit_staff_roles(query, user_type, db)
    elif data == "change_pin":
        await handle_change_pin(update, context)
    elif data == "view_all_users":
        await handle_view_all_users(query, user_type, db)
    elif data == "activate_deactivate_users":
        await handle_activate_deactivate_users(query, user_type, db)
    elif data.startswith("toggle_user_"):
        await handle_toggle_user_active(query, db)
    elif data == "edit_user_roles":
        await handle_edit_user_roles_main(query, user_type, db)
    elif data.startswith("edit_role_"):
        await handle_choose_user_role(query, db)
    elif data.startswith("set_role_"):
        await handle_set_user_role(query, db)
    elif data == "contact_info":
        await handle_contact_info(query, context)
    elif data == "help":
        await handle_help(query, user_type)
    elif data == "place_order":
        await handle_place_order(query, context)
    elif data == "my_orders":
        await handle_my_orders(query, user_type, db)
    elif data == "request_wholesale":
        await handle_request_wholesale(query)
    elif data == "update_stock":
        await handle_update_stock(update, context)
    elif data == "enhanced_stats":
        await handle_enhanced_stats(query, user_type, db)
    elif data == "add_single_medicine":
        await handle_add_single_medicine(query, user_type)
    elif data == "add_bulk_medicine":
        await handle_add_bulk_medicine(query, user_type)
    elif data == "low_stock_alert":
        await handle_low_stock_alert(query, user_type, db)
    elif data == "remove_medicine":
        await handle_remove_medicine(query, user_type)
    elif data == "remove_all_medicines":
        await handle_remove_all_medicines(query, user_type)
    # Remove medicine with PIN and Remove all with PIN are handled by ConversationHandler
    elif data.startswith("confirm_remove_med_"):
        await handle_confirm_remove_single_medicine(query, db, context)
    elif data == "confirm_remove_all_final":
        await handle_confirm_remove_all_final(query, db, context)
    elif data.startswith("add_to_cart_"):
        await handle_add_to_cart(query, db)
    elif data.startswith("quantity_"):
        await handle_quantity_selection(query, db)
    elif data == "view_order_cart":
        await handle_view_cart(query, db)
    elif data == "edit_order_cart":
        await handle_edit_cart(query, db)
    elif data == "clear_order_cart":
        await handle_clear_cart(query)
    elif data == "confirm_clear_cart":
        await handle_confirm_clear_cart(query)
    elif data.startswith("remove_cart_item_"):
        await handle_remove_cart_item(query)
    elif data == "proceed_checkout":
        await handle_proceed_checkout(update, context)
    elif data == "collect_customer_info":
        await handle_collect_customer_info(query, context)
    elif data == "confirm_final_order":
        await handle_confirm_final_order(update, context)
    elif data == "category_breakdown":
        await handle_category_breakdown(query, user_type, db)
    elif data == "weekly_comparison":
        await handle_weekly_comparison(query, user_type, db)
    elif data == "back_to_main":
        await handle_back_to_main(query, user_type)
    elif data == "view_all_medicines":
        await handle_view_all_medicines(query, user_type, db)
    elif data == "medicines_quick_view":
        await handle_medicines_quick_view(query, user_type, db)
    elif data == "medicines_excel_export":
        await handle_medicines_excel_export(query, user_type, db, context)
    elif data == "start_single_add":
        await handle_start_single_add(query, context)
    elif data.startswith("toggle_medicine_"):
        await handle_toggle_medicine_selection(query)
    elif data == "confirm_remove_medicines":
        context.user_data['user_type'] = user_type
        await handle_confirm_remove_medicines(update, context)
    elif data == "cancel_remove_medicines":
        context.user_data['user_type'] = user_type
        await handle_cancel_remove_medicines(update, context)
    elif data.startswith("category_"):
        await handle_category_selection(query, db, context)
    elif data.startswith("add_medicine_"):
        await handle_add_medicine_to_cart(query, db)
    elif data.startswith("set_quantity_"):
        await handle_set_quantity(query, db)
    elif data.startswith("confirm_add_quantity_"):
        await handle_confirm_add_quantity(query, db)
    elif data == "back_to_categories":
        await handle_place_order(query, context)
    elif data.startswith("back_to_category_"):
        category = data.replace("back_to_category_", "")
        await show_medicines_in_category(query, db, category, context)
    elif data == "start_stock_update":
        await handle_start_stock_update(update, context)
    elif data.startswith("update_stock_medicine_"):
        await handle_select_medicine_for_stock_update(update, context)
    elif data.startswith("price_update_percentage"):
        await handle_price_update_percentage(update, context)
    elif data.startswith("price_update_amount"):
        await handle_price_update_amount(update, context)
    elif data == "monthly_stats":
        await handle_monthly_stats(query, user_type, db)
    elif data == "category_stats":
        await handle_category_stats(query, user_type, db)
    elif data == "apply_percentage_all":
        await handle_apply_percentage_all(query, db, context)
    elif data == "choose_category_percentage":
        await handle_choose_category_percentage(query, db, context)
    elif data.startswith("apply_percentage_category_"):
        await handle_apply_percentage_category(query, db, context)
    elif data == "apply_amount_all":
        await handle_apply_amount_all(query, db, context)
    elif data == "choose_category_amount":
        await handle_choose_category_amount(query, db, context)
    elif data.startswith("apply_amount_category_"):
        await handle_apply_amount_category(query, db, context)
    elif data.startswith("price_update_med_"):
        await handle_select_medicine_for_price_update(update, context)
    elif data.startswith("search_suggestion_"):
        await handle_search_suggestion(query, db)
    elif data == "daily_summary_text":
        await handle_daily_summary_text(query, user_type, db)
    elif data == "weekly_excel_report":
        await handle_weekly_excel_report(query, user_type, db, context)
    elif data == "weekly_comparison_excel":
        await handle_weekly_comparison_excel(query, user_type, db)
    # Duplicate handling actions for single medicine addition
    elif data == "continue_original_name":
        await handle_continue_original_name(update, context)
    elif data == "update_existing_medicine":
        await handle_update_existing_medicine(update, context)
    elif data == "enter_new_name":
        await handle_enter_new_name(update, context)
    elif data == "cancel_add":
        await handle_cancel_add(update, context)
    # Duplicate handling actions for Excel upload
    elif data == "excel_update_existing":
        await handle_excel_update_existing(update, context)
    elif data == "excel_add_as_new":
        await handle_excel_add_as_new(update, context)
    elif data == "excel_review_each":
        await handle_excel_review_each(update, context)
    elif data == "excel_skip_duplicates":
        await handle_excel_skip_duplicates(update, context)
    elif data == "cancel_excel_upload":
        await handle_cancel_excel_upload(update, context)
    # Order filter handlers
    elif data == "all_orders":
        await handle_all_orders(query, user_type, db)
    elif data == "pending_orders":
        await handle_pending_orders(query, user_type, db)
    elif data == "completed_orders":
        await handle_completed_orders(query, user_type, db)
    # Order Excel export handlers
    elif data == "export_all_orders_excel":
        await handle_export_all_orders_excel(query, user_type, db, context)
    elif data == "export_pending_orders_excel":
        await handle_export_pending_orders_excel(query, user_type, db, context)
    elif data == "export_completed_orders_excel":
        await handle_export_completed_orders_excel(query, user_type, db, context)
    # Order status update handlers
    elif data.startswith("mark_completed_"):
        await handle_mark_order_completed(query, user_type, db)
    elif data.startswith("mark_pending_"):
        await handle_mark_order_pending(query, user_type, db)
    # Order details expansion handlers (must come before general view_order_details)
    elif data.startswith("view_order_details_expand_"):
        await handle_view_order_details_expand(query, user_type, db)
    elif data.startswith("hide_order_details_"):
        await handle_hide_order_details(query, user_type, db)
    elif data.startswith("view_order_details_"):
        await handle_view_order_details(query, user_type, db)
    # Order status update by number handlers
    elif data.startswith("update_status_"):
        await handle_update_order_status_by_number(update, context)
    # Order Details search handler
    elif data == "order_details_search":
        await handle_order_details_search(update, context)
    # Custom quantity handler
    elif data.startswith("custom_quantity_"):
        await handle_custom_quantity(update, context)
    else:
        await query.edit_message_text("Feature coming soon! 🚀")

# --- Conversation handlers for adding medicine ---
async def handle_start_single_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the conversation to add a single medicine."""
    user_type = get_or_create_user(context.bot_data['db'], update.effective_user.id, update.effective_user.first_name)['user_type']
    if user_type not in ['staff', 'admin']:
        await update.callback_query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return ConversationHandler.END

    await update.callback_query.edit_message_text("📝 **Step 1/7: Medicine Name**\n\nWhat is the name of the medicine? (e.g., *Paracetamol*)")
    return MEDICINE_NAME

async def add_medicine_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collects medicine name and checks for duplicates."""
    med_name = update.message.text.strip()
    db = context.bot_data['db']
    
    # Check for potential duplicates using enhanced detection
    duplicates = detect_medicine_duplicates(db, med_name, threshold=0.8)
    
    if duplicates:
        # Store medicine name for potential continuation
        context.user_data['medicine_name'] = med_name
        
        # Present duplicate options to user
        await present_duplicate_options(update, context, duplicates, med_name)
        return DUPLICATE_CONFIRMATION
    
    # No duplicates found, proceed normally
    context.user_data['medicine_name'] = med_name
    await update.message.reply_text("📝 **Step 2/7: Therapeutic Category**\n\nWhat is its therapeutic category? (e.g., *Analgesic*)")
    return THERAPEUTIC_CATEGORY

async def add_therapeutic_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collects therapeutic category and prompts for manufacturing date."""
    context.user_data['therapeutic_category'] = update.message.text.strip()
    await update.message.reply_text("📝 **Step 3/7: Manufacturing Date**\n\nPlease enter the manufacturing date in `YYYY-MM-DD` format. (e.g., *2023-05-15*)")
    return MANUFACTURING_DATE

async def add_manufacturing_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collects manufacturing date and prompts for expiry date."""
    try:
        date_str = update.message.text.strip()
        datetime.strptime(date_str, '%Y-%m-%d')
        context.user_data['manufacturing_date'] = date_str
        await update.message.reply_text("📝 **Step 4/7: Expiring Date**\n\nPlease enter the expiring date in `YYYY-MM-DD` format. (e.g., *2025-05-15*)")
        return EXPIRING_DATE
    except ValueError:
        await update.message.reply_text("❌ Invalid date format. Please use `YYYY-MM-DD`.")
        return MANUFACTURING_DATE

async def add_expiring_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collects expiring date and prompts for dosage form."""
    try:
        date_str = update.message.text.strip()
        datetime.strptime(date_str, '%Y-%m-%d')
        context.user_data['expiring_date'] = date_str
        await update.message.reply_text("📝 **Step 5/7: Dosage Form**\n\nWhat is the dosage form? (e.g., *Tablet*, *Capsule*, *Syrup*)")
        return DOSAGE_FORM
    except ValueError:
        await update.message.reply_text("❌ Invalid date format. Please use `YYYY-MM-DD`.")
        return EXPIRING_DATE

async def add_dosage_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collects dosage form and prompts for price."""
    context.user_data['dosage_form'] = update.message.text.strip()
    await update.message.reply_text("📝 **Step 6/7: Price**\n\nWhat is the price per unit in ETB? (e.g., *25.50*)")
    return PRICE

async def add_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collects price and prompts for stock quantity."""
    try:
        price = float(update.message.text.strip())
        if price <= 0:
            raise ValueError
        context.user_data['price'] = price
        await update.message.reply_text("📝 **Step 7/7: Stock Quantity**\n\nHow many units are you adding to stock? (e.g., *100*)")
        return STOCK_QUANTITY
    except ValueError:
        await update.message.reply_text("❌ Invalid price. Please enter a positive number.")
        return PRICE

async def add_stock_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collects stock quantity and adds the medicine to the database."""
    try:
        quantity = int(update.message.text.strip())
        if quantity < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Invalid quantity. Please enter a non-negative integer.")
        return STOCK_QUANTITY

    db = context.bot_data['db']
    med_info = context.user_data
    try:
        db.add_medicine(
            med_info['medicine_name'],
            med_info['therapeutic_category'],
            med_info['manufacturing_date'],
            med_info['expiring_date'],
            med_info['dosage_form'],
            med_info['price'],
            quantity
        )
        await update.message.reply_text("✅ **Medicine Added Successfully!**\n\n"
                                        f"**Name:** {med_info['medicine_name']}\n"
                                        f"**Category:** {med_info['therapeutic_category']}\n"
                                        f"**Price:** {med_info['price']:.2f} ETB\n"
                                        f"**Stock:** {quantity}\n\n"
                                        "Use /start to go back to the main menu.")
    except Exception as e:
        logger.error(f"Error adding medicine: {e}", exc_info=True)
        await update.message.reply_text("❌ An error occurred while adding the medicine. Please try again.")

    context.user_data.clear()
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the current conversation and returns to the main menu."""
    user_id = update.effective_user.id
    
    # Clear all user state data
    if user_id in user_data:
        user_data[user_id].clear()
    context.user_data.clear()
    
    # Get user info for welcome message
    db = context.bot_data['db']
    telegram_user = get_or_create_user(db, user_id, update.effective_user.first_name, update.effective_user.last_name, update.effective_user.username)
    
    if telegram_user:
        user_type = telegram_user['user_type']
        role_display = USER_ROLES.get(user_type, user_type.title())
        
        welcome_text = f"""
❌ **Operation Cancelled**

🏥 **Welcome back to Blue Pharma Trading PLC!**

Hello {telegram_user['first_name']}! Your Access Level: {role_display}

🎯 **What would you like to do today?**
Choose from the options below:
"""
        keyboard = get_user_keyboard(user_type)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("❌ Operation cancelled. Use /start to go back to the main menu.")
    
    return ConversationHandler.END

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle standalone /search command to search medicines in database."""
    if not context.args:
        await update.message.reply_text(
            "🔍 **Medicine Search**\n\n"
            "Usage: `/search [medicine name]`\n\n"
            "📝 **Examples:**\n"
            "• `/search Paracetamol`\n"
            "• `/search Para`\n"
            "• `/search Aspirin`\n\n"
            "💡 **Tip:** You can search with partial names!",
            parse_mode='Markdown'
        )
        return
    
    search_term = ' '.join(context.args)
    db = context.bot_data['db']
    
    try:
        medicines = db.get_medicine_by_name(search_term)
        
        if not medicines:
            # Try fuzzy search to find similar medicines
            similar_medicines = find_similar_medicines(db, search_term, threshold=0.35, max_results=5)
            
            if similar_medicines:
                # Found similar medicines - show suggestions
                suggestions_text = f"❌ **No exact matches found for '{search_term}'**\n\n"
                suggestions_text += f"🤖 **Search Assistant - Did you mean?**\n\n"
                suggestions_text += f"💡 Here are some similar medicines:\n\n"
                
                keyboard = []
                for i, medicine in enumerate(similar_medicines, 1):
                    similarity_percentage = int(medicine['similarity_score'] * 100)
                    stock_emoji = "✅" if medicine['stock_quantity'] > 0 else "❌"
                    suggestions_text += f"{i}. {stock_emoji} **{medicine['name']}** ({similarity_percentage}% match)\n"
                    suggestions_text += f"   💰 {medicine['price']:.2f} ETB | 📦 {medicine['stock_quantity']} units\n"
                    if medicine['therapeutic_category']:
                        suggestions_text += f"   🏷️ {medicine['therapeutic_category']}\n"
                    suggestions_text += "\n"
                    
                    # Add button to search for this medicine
                    keyboard.append([
                        InlineKeyboardButton(
                            f"🔍 Search {medicine['name']}", 
                            callback_data=f"search_suggestion_{medicine['id']}"
                        )
                    ])
                
                suggestions_text += f"🔍 **Tip:** Click a button above to see full details of a suggested medicine."
                
                keyboard.append([InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(suggestions_text, parse_mode='Markdown', reply_markup=reply_markup)
            else:
                # No similar medicines found either
                await update.message.reply_text(
                    f"❌ **Medicine not found: '{search_term}'**\n\n"
                    "🔍 **Search Tips:**\n"
                    "• Check spelling\n"
                    "• Try shorter search terms\n"
                    "• Use generic names\n"
                    "• Try common abbreviations\n\n"
                    "💡 Use `/search` without parameters for usage help."
                )
            return
        
        if len(medicines) == 1:
            # Single medicine found - show detailed info
            medicine = medicines[0]
            
            # Calculate expiry status
            try:
                exp_date = datetime.strptime(medicine['expiring_date'], '%Y-%m-%d')
                days_to_expiry = (exp_date - datetime.now()).days
                if days_to_expiry < 0:
                    expiry_status = "⚠️ EXPIRED"
                elif days_to_expiry <= 30:
                    expiry_status = f"⚠️ Expires in {days_to_expiry} days"
                else:
                    expiry_status = "✅ Valid"
            except:
                expiry_status = "❓ Unknown"
            
            stock_status = "✅ In Stock" if medicine['stock_quantity'] > 0 else "❌ Out of Stock"
            
            medicine_text = f"💊 **Medicine Details**\n\n"
            medicine_text += f"**Name:** {medicine['name']}\n"
            medicine_text += f"**Category:** {medicine['therapeutic_category'] or 'N/A'}\n"
            medicine_text += f"**Form:** {medicine['dosage_form'] or 'N/A'}\n"
            medicine_text += f"**Price:** {medicine['price']:.2f} ETB\n"
            medicine_text += f"**Stock:** {medicine['stock_quantity']} units ({stock_status})\n"
            medicine_text += f"**Mfg Date:** {medicine['manufacturing_date']}\n"
            medicine_text += f"**Exp Date:** {medicine['expiring_date']} ({expiry_status})\n\n"
            
            if medicine['stock_quantity'] > 0:
                medicine_text += "🛒 **Available for ordering!**"
            else:
                medicine_text += "❌ **Currently out of stock**"
            
            keyboard = []
            # Add action buttons based on user type
            user = get_or_create_user(db, update.effective_user.id, update.effective_user.first_name)
            if user and user['user_type'] == 'customer' and medicine['stock_quantity'] > 0:
                keyboard.append([InlineKeyboardButton("🛒 Add to Cart", callback_data=f"add_medicine_{medicine['id']}")])
            
            keyboard.append([InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")])
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            await update.message.reply_text(medicine_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        else:
            # Multiple medicines found - show list
            search_text = f"🔍 **Search Results for '{search_term}'**\n\n"
            search_text += f"📋 **Found {len(medicines)} medicines:**\n\n"
            
            for i, medicine in enumerate(medicines[:15], 1):  # Limit to 15 results
                stock_emoji = "✅" if medicine['stock_quantity'] > 0 else "❌"
                search_text += f"{i}. {stock_emoji} **{medicine['name']}**\n"
                search_text += f"   💰 {medicine['price']:.2f} ETB | 📦 {medicine['stock_quantity']} units\n"
                if medicine['therapeutic_category']:
                    search_text += f"   🏷️ {medicine['therapeutic_category']}\n"
                search_text += "\n"
            
            if len(medicines) > 15:
                search_text += f"... and {len(medicines) - 15} more results.\n\n"
                search_text += f"💡 **Tip:** Use a more specific search term to narrow results.\n"
            
            search_text += f"\n🔍 **To see details of a specific medicine, search with its exact name.**"
            
            await update.message.reply_text(search_text, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error in search command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while searching. Please try again."
        )

# --- Order Checkout Conversation ---
async def handle_collect_customer_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the conversation to collect customer info for an order."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📝 **Final Step: Your Information**\n\nPlease enter your full name:")
    return CUSTOMER_NAME

async def get_customer_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collects customer name and prompts for Ethiopian phone."""
    context.user_data['customer_name'] = update.message.text.strip()
    await update.message.reply_text("📱 Please enter your Ethiopian phone number (e.g., +251912345678 or 0912345678):")
    return CUSTOMER_PHONE

async def get_customer_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collects Ethiopian phone number and finalizes order with admin notification."""
    phone_number = update.message.text.strip()
    
    # Validate Ethiopian phone number format
    import re
    eth_phone_pattern = r'^(\+251|0)[79]\d{8}$'
    if not re.match(eth_phone_pattern, phone_number):
        await update.message.reply_text(
            "❌ **Invalid Ethiopian phone number format!**\n\n"
            "Please enter a valid Ethiopian phone number:\n"
            "• Format: +251912345678 or 0912345678\n"
            "• Must start with +251 or 0\n"
            "• Must be followed by 9 or 7\n"
            "• Must have exactly 9 digits after the prefix"
        )
        return CUSTOMER_PHONE
    
    context.user_data['customer_phone'] = phone_number
    db = context.bot_data['db']
    user_id = update.effective_user.id
    cart = get_user_cart(user_id)
    
    # Calculate total before placing order
    total = calculate_cart_total(db, user_id)
    
    # Place the order
    order_id = db.place_order(
        user_id,
        context.user_data['customer_name'],
        context.user_data['customer_phone'],
        cart
    )
    
    if order_id:
        # Get clean display ID
        clean_id = db.format_order_id(order_id)
        
        # Prepare order details for notifications
        order_details = ""
        for item in cart:
            medicine = db.get_medicine_by_id(item['medicine_id'])
            if medicine:
                order_details += f"• {medicine['name']} x{item['quantity']} = {medicine['price'] * item['quantity']:.2f} ETB\n"
        
        # Send confirmation to customer
        await update.message.reply_text(
            "✅ **ORDER CONFIRMED!**\n\n"
            f"**Order ID:** {clean_id}\n"
            f"**Customer:** {context.user_data['customer_name']}\n"
            f"**Phone:** {context.user_data['customer_phone']}\n"
            f"**Total Amount:** {total:.2f} ETB\n\n"
            "📞 **Our staff will contact you shortly to confirm and process your order.**\n\n"
            "Thank you for choosing Blue Pharma Trading PLC! 🏥"
        )
        
        # Send notification to admin
        try:
            admin_notification = (
                f"🔔 **NEW ORDER RECEIVED!**\n\n"
                f"**Order ID:** {clean_id}\n"
                f"**Customer:** {context.user_data['customer_name']}\n"
                f"**Phone:** {context.user_data['customer_phone']}\n"
                f"**Customer Telegram:** @{update.effective_user.username or 'No username'}\n"
                f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"**Order Details:**\n{order_details}\n"
                f"**Total Amount:** {total:.2f} ETB\n\n"
                f"👤 **Customer ID:** {user_id}\n"
                f"📱 **Please contact the customer to confirm this order.**"
            )
            
            await context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=admin_notification,
                parse_mode='Markdown'
            )
            logger.info(f"Admin notification sent for order {order_id}")
        except Exception as e:
            logger.error(f"Failed to send admin notification for order {order_id}: {e}")
        
        clear_cart_local(user_id)
    else:
        await update.message.reply_text("❌ There was an error placing your order. Please try again.")

    context.user_data.clear()
    return ConversationHandler.END

async def handle_excel_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles an incoming Excel file for bulk medicine upload with duplicate detection."""
    if not EXCEL_SUPPORT:
        await update.message.reply_text("❌ Excel processing libraries are not installed. Please install pandas and openpyxl.")
        return ConversationHandler.END
        
    if not update.message.document:
        await update.message.reply_text("Please upload an Excel file (`.xlsx`).")
        return WAITING_FOR_EXCEL_FILE
    
    document = update.message.document
    if not document.file_name.endswith('.xlsx'):
        await update.message.reply_text("❌ The uploaded file is not an Excel file. Please try again.")
        return WAITING_FOR_EXCEL_FILE

    user_info = get_or_create_user(context.bot_data['db'], update.effective_user.id, update.effective_user.first_name)
    if user_info['user_type'] not in ['staff', 'admin']:
        await update.message.reply_text("❌ Access denied. Staff/Admin access required.")
        return ConversationHandler.END

    try:
        file_id = document.file_id
        file_path = await context.bot.get_file(file_id)
        
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
            await file_path.download_to_drive(temp_file.name)
            temp_file_path = temp_file.name
        
        df = pd.read_excel(temp_file_path)
        os.remove(temp_file_path)

        required_cols = [
            'name', 'therapeutic_category', 'manufacturing_date',
            'expiring_date', 'dosage_form', 'price', 'stock_quantity'
        ]
        if not all(col in df.columns for col in required_cols):
            await update.message.reply_text(f"❌ Missing required columns. Please ensure your file has these columns: {', '.join(required_cols)}")
            return WAITING_FOR_EXCEL_FILE

        db = context.bot_data['db']
        
        # Convert DataFrame to list of dictionaries for duplicate detection
        excel_medicines = []
        for index, row in df.iterrows():
            try:
                # Process dates
                mfg_date = row['manufacturing_date']
                exp_date = row['expiring_date']
                
                # Handle different date formats
                if pd.isna(mfg_date) or pd.isna(exp_date):
                    logger.error(f"Row {index}: Missing date values")
                    continue
                    
                # Convert to string if it's a Timestamp or datetime
                if hasattr(mfg_date, 'strftime'):
                    mfg_date_str = mfg_date.strftime('%Y-%m-%d')
                elif isinstance(mfg_date, str):
                    mfg_date_str = mfg_date
                else:
                    mfg_date_str = str(mfg_date)
                    
                if hasattr(exp_date, 'strftime'):
                    exp_date_str = exp_date.strftime('%Y-%m-%d')
                elif isinstance(exp_date, str):
                    exp_date_str = exp_date
                else:
                    exp_date_str = str(exp_date)
                
                # Validate other required fields
                if pd.isna(row['name']) or pd.isna(row['price']) or pd.isna(row['stock_quantity']):
                    logger.error(f"Row {index}: Missing required fields")
                    continue
                
                excel_medicine = {
                    'name': str(row['name']).strip(),
                    'therapeutic_category': str(row['therapeutic_category']).strip() if not pd.isna(row['therapeutic_category']) else 'General',
                    'manufacturing_date': mfg_date_str,
                    'expiring_date': exp_date_str,
                    'dosage_form': str(row['dosage_form']).strip() if not pd.isna(row['dosage_form']) else 'Unknown',
                    'price': float(row['price']),
                    'stock_quantity': int(row['stock_quantity'])
                }
                
                excel_medicines.append(excel_medicine)
                
            except Exception as e:
                logger.error(f"Failed to process Excel row {index}: {e}")
                continue
        
        if not excel_medicines:
            await update.message.reply_text("❌ No valid medicines found in the Excel file. Please check the data and try again.")
            return ConversationHandler.END
        
        # Store Excel data in context for later use
        context.user_data['excel_data'] = excel_medicines
        
        # Check for duplicates
        duplicates = detect_excel_duplicates(db, excel_medicines, threshold=0.8)
        
        if duplicates:
            # Found duplicates - present options to user
            await present_excel_duplicate_options(update, context, duplicates)
            return EXCEL_DUPLICATE_CHOICE
        else:
            # No duplicates found - proceed with adding all medicines
            added_count = 0
            failed_count = 0
            
            for excel_med in excel_medicines:
                try:
                    db.add_medicine(
                        excel_med['name'],
                        excel_med['therapeutic_category'],
                        excel_med['manufacturing_date'],
                        excel_med['expiring_date'],
                        excel_med['dosage_form'],
                        excel_med['price'],
                        excel_med['stock_quantity']
                    )
                    added_count += 1
                except Exception as e:
                    logger.error(f"Failed to add medicine from Excel: {e}")
                    failed_count += 1
            
            # Clear Excel data from context
            context.user_data.pop('excel_data', None)
            
            result_text = f"✅ **Excel Upload Complete!**\n\n"
            result_text += f"➕ **New medicines added:** {added_count}\n"
            
            if failed_count > 0:
                result_text += f"❌ **Failed to add:** {failed_count}\n\n"
                result_text += "Check logs for details on failed operations."
            else:
                result_text += "\n🎉 **All medicines added successfully!**\n"
                result_text += "No duplicates were detected."
            
            await update.message.reply_text(
                result_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📝 Add More Medicines", callback_data="add_medicine")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            
            return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error processing Excel file: {e}", exc_info=True)
        await update.message.reply_text("❌ An error occurred while processing the file. Please check the format and try again.")
    
    return ConversationHandler.END

async def handle_manage_stock(query, user_type, db):
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    try:
        overview = db.get_stock_overview()
        stock_text = f"""
📦 **Stock Management Overview**

📊 **Current Status:**
• Total Medicines: {overview.get('total_medicines', 0)}
• Total Stock Units: {overview.get('total_stock', 0):,}
• Low Stock Items: {overview.get('low_stock', 0)}
• Out of Stock: {overview.get('out_of_stock', 0)}

🔧 **Quick Actions:**
"""
        keyboard = [
            [InlineKeyboardButton("📝 Add Medicine", callback_data="add_medicine")],
            [InlineKeyboardButton("📊 View All Medicines", callback_data="view_all_medicines")],
            [InlineKeyboardButton("⚠️ Low Stock Alert", callback_data="low_stock_alert")],
            [InlineKeyboardButton("🗑️ Remove Medicine", callback_data="remove_medicine_with_pin"),
             InlineKeyboardButton("🗑️ Remove All", callback_data="remove_all_with_pin")],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(stock_text, parse_mode='Markdown', reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in stock management: {e}", exc_info=True)
        await query.edit_message_text("Error retrieving stock information.")

async def handle_check_medicine(query):
    check_text = """
💊 **Check Medicine Information**

To check medicine details, use `/search [medicine name]` or choose an option below.

📋 **Available options:**
"""
    keyboard = [
        [InlineKeyboardButton("📋 View All Medicines", callback_data="view_all_medicines")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(check_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_remove_medicine(query, user_type):
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    remove_text = """
🗑️ **Remove Medicine - Choose Method**

⚠️ **Choose how you want to remove medicines:**

**Method 1: Remove Single Medicine**
• Select and remove individual medicines with PIN verification

**Method 2: Remove All Medicines** (Admin Only)
• Remove all medicines from inventory (requires admin PIN)

🔐 **Security Note:** All removal operations require PIN verification for security.
"""
    
    keyboard = []
    # Single medicine removal for staff and admin
    keyboard.append([InlineKeyboardButton("🗑️ Remove Single Medicine", callback_data="remove_medicine_with_pin")])
    
    # Remove all option only for admin
    if user_type == 'admin':
        keyboard.append([InlineKeyboardButton("⚠️ Remove All Medicines", callback_data="remove_all_with_pin")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Stock Management", callback_data="manage_stock")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(remove_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_remove_all_medicines(query, user_type):
    """Handle remove all medicines button - redirects to PIN-protected version."""
    if user_type != 'admin':
        await query.edit_message_text("❌ Access denied. Administrator access required.")
        return
    
    # Redirect to the PIN-protected version
    remove_all_text = """
⚠️ **Remove All Medicines**

🔐 **PIN Verification Required**

This action will remove ALL medicines from the inventory. This operation requires admin PIN verification for security.

Click "Proceed with PIN" to continue with PIN verification.
"""
    keyboard = [
        [InlineKeyboardButton("🔐 Proceed with PIN", callback_data="remove_all_with_pin")],
        [InlineKeyboardButton("❌ Cancel", callback_data="manage_stock")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(remove_all_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_add_medicine_button(query, user_type):
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    add_text = """
📝 **Add Medicine - Choose Method**

🎯 **Choose how you want to add medicines:**

**Method 1: Single Medicine**
• Add one medicine using our 7-question flow

**Method 2: Bulk Addition (Excel)**
• Upload Excel file with multiple medicines
"""
    keyboard = [
        [InlineKeyboardButton("📝 Add Single Medicine", callback_data="start_single_add")],
        [InlineKeyboardButton("📊 Add Many Medicines (Excel)", callback_data="add_bulk_medicine")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(add_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_add_bulk_medicine(query, user_type):
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    bulk_text = """
📊 **Bulk Medicine Addition (Excel)**

📋 **Required Excel Columns:**
• `name` - Medicine name (required)
• `therapeutic_category` - Category (e.g., Analgesic, Antibiotic)
• `manufacturing_date` - Format: YYYY-MM-DD (e.g., 2024-01-15)
• `expiring_date` - Format: YYYY-MM-DD (e.g., 2026-01-15)
• `dosage_form` - Form (e.g., Tablet, Capsule, Syrup)
• `price` - Price in ETB (numeric only)
• `stock_quantity` - Number of units (whole numbers)

📎 **Upload your Excel file (.xlsx) as a document to proceed.**

💡 **Tips:**
- Save as .xlsx format (not .xls or .csv)
- Use proper date format (YYYY-MM-DD)
- No currency symbols in price field
- All required columns must be present
"""
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Add Medicine", callback_data="add_medicine")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(bulk_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_view_stats(query, user_type, db):
    """Show analytics menu with three options: Daily Summary, Weekly Excel, Weekly Comparison Excel."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        # Clean up old reports first
        await cleanup_old_reports(db)
        
        stats_text = "📊 **Analytics Dashboard**\n\n"
        stats_text += "📈 **Choose the type of analytics report:**\n\n"
        stats_text += "📅 **Daily Summary** - Today's sales overview (text)\n"
        stats_text += "📄 **Weekly Report** - Export weekly data to Excel\n"
        stats_text += "📊 **Weekly Comparison** - Compare weeks in Excel format\n"
        
        keyboard = [
            [InlineKeyboardButton("📅 Daily Summary", callback_data="daily_summary_text")],
            [InlineKeyboardButton("📄 Weekly Report (Excel)", callback_data="weekly_excel_report")],
            [InlineKeyboardButton("📊 Weekly Comparison (Excel)", callback_data="weekly_comparison_excel")],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(stats_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in view stats: {e}", exc_info=True)
        await query.edit_message_text("Error retrieving sales statistics.")

async def handle_view_orders(query, user_type):
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    orders_text = """
📋 **Order Management**

Choose the type of orders you want to view:

📦 **All Orders** - View all orders in the system
⏳ **Pending Orders** - View orders awaiting confirmation
✅ **Completed Orders** - View fulfilled orders

🔍 **Search Orders:**
📋 **Order Details** - Search and view detailed order information by order ID

🔄 **Quick Status Updates:**
📝 **Update by Order Number** - Mark orders completed or pending by entering order number
"""
    keyboard = [
        [InlineKeyboardButton("📦 All Orders", callback_data="all_orders")],
        [InlineKeyboardButton("⏳ Pending Orders", callback_data="pending_orders")],
        [InlineKeyboardButton("✅ Completed Orders", callback_data="completed_orders")],
        [InlineKeyboardButton("🔍 Order Details", callback_data="order_details_search")],
        [InlineKeyboardButton("✅ Mark Order Completed", callback_data="update_status_completed"),
         InlineKeyboardButton("⏳ Mark Order Pending", callback_data="update_status_pending")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(orders_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_update_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the simplified price update conversation."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db = context.bot_data['db']
    user_info = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if not user_info or user_info['user_type'] not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return ConversationHandler.END
    
    await query.edit_message_text(
        "💰 **Update Medicine Price**\n\n"
        "🔍 **Step 1: Search Medicine**\n\n"
        "Please enter the name of the medicine you want to update (or part of the name):\n\n"
        "📝 **Examples:**\n"
        "• Paracetamol\n"
        "• Para\n"
        "• Aspirin"
    )
    
    return PRICE_UPDATE_VALUE

async def handle_price_medicine_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle medicine search for individual price update."""
    search_term = update.message.text.strip()
    db = context.bot_data['db']
    
    medicines = db.get_medicine_by_name(search_term)
    
    if not medicines:
        # Try fuzzy search to find similar medicines
        similar_medicines = find_similar_medicines(db, search_term, threshold=0.35, max_results=5)
        
        if similar_medicines:
            # Found similar medicines - show suggestions for price update
            suggestions_text = f"❌ **No exact matches found for '{search_term}'**\n\n"
            suggestions_text += f"🤖 **Price Update Assistant - Did you mean?**\n\n"
            suggestions_text += f"💡 Here are some similar medicines:\n\n"
            
            keyboard = []
            for i, medicine in enumerate(similar_medicines, 1):
                similarity_percentage = int(medicine['similarity_score'] * 100)
                stock_emoji = "✅" if medicine['stock_quantity'] > 0 else "❌"
                suggestions_text += f"{i}. {stock_emoji} **{medicine['name']}** ({similarity_percentage}% match)\n"
                suggestions_text += f"   💰 Current Price: {medicine['price']:.2f} ETB\n"
                suggestions_text += f"   📦 Stock: {medicine['stock_quantity']} units\n"
                if medicine['therapeutic_category']:
                    suggestions_text += f"   🏷️ {medicine['therapeutic_category']}\n"
                suggestions_text += "\n"
                
                # Add button to select this medicine for price update
                keyboard.append([
                    InlineKeyboardButton(
                        f"💰 Update Price: {medicine['name']}", 
                        callback_data=f"price_update_med_{medicine['id']}"
                    )
                ])
            
            suggestions_text += f"💰 **Tip:** Click a button above to update price for a suggested medicine."
            
            keyboard.append([InlineKeyboardButton("🔍 Try Different Search", callback_data="update_prices")])
            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="back_to_main")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(suggestions_text, parse_mode='Markdown', reply_markup=reply_markup)
            return ConversationHandler.END
        else:
            # No similar medicines found either
            await update.message.reply_text(
                f"❌ **Medicine not found: '{search_term}'**\n\n"
                "🔍 **Search Tips:**\n"
                "• Check spelling\n"
                "• Try shorter search terms\n"
                "• Use generic names\n"
                "• Try common abbreviations\n\n"
                "Please try again with a different search term:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Try Again", callback_data="update_prices")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="back_to_main")]
                ])
            )
        return PRICE_UPDATE_VALUE
    
    if len(medicines) == 1:
        # Only one medicine found, proceed directly to price input
        medicine = medicines[0]
        context.user_data['selected_medicine_for_price'] = medicine['id']
        
        await update.message.reply_text(
            f"💊 **Medicine Found:** {medicine['name']}\n"
            f"💰 **Current Price:** {medicine['price']:.2f} ETB\n"
            f"📦 **Stock:** {medicine['stock_quantity']} units\n\n"
            "💰 **Enter new price in ETB:**\n\n"
            "Examples: 25.50, 100, 15.75"
        )
        return PRICE_MEDICINE_SELECTION
    else:
        # Multiple medicines found, let user choose
        search_text = f"🔍 **Search Results for '{search_term}'**\n\n"
        search_text += "📋 **Multiple medicines found. Select one to update price:**\n\n"
        
        keyboard = []
        for i, medicine in enumerate(medicines[:10]):  # Limit to 10 results
            search_text += f"{i+1}. **{medicine['name']}** - Current: {medicine['price']:.2f} ETB\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"💰 Update {medicine['name']}", 
                    callback_data=f"price_update_med_{medicine['id']}"
                )
            ])
        
        if len(medicines) > 10:
            search_text += f"\n... and {len(medicines) - 10} more results.\n"
            search_text += "Please refine your search term.\n"
        
        keyboard.append([InlineKeyboardButton("🔍 New Search", callback_data="update_prices")])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="back_to_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(search_text, parse_mode='Markdown', reply_markup=reply_markup)
        return ConversationHandler.END

async def handle_select_medicine_for_price_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle selection of a specific medicine for price update."""
    query = update.callback_query
    await query.answer()
    
    db = context.bot_data['db']
    medicine_id = int(query.data.replace("price_update_med_", ""))
    medicine = db.get_medicine_by_id(medicine_id)
    
    if not medicine:
        await query.edit_message_text("❌ Medicine not found. Please try again.")
        return
    
    context.user_data['selected_medicine_for_price'] = medicine_id
    
    await query.edit_message_text(
        f"💊 **Selected Medicine:** {medicine['name']}\n"
        f"💰 **Current Price:** {medicine['price']:.2f} ETB\n"
        f"📦 **Stock:** {medicine['stock_quantity']} units\n\n"
        "💰 **Enter new price in ETB:**\n\n"
        "Reply with the new price (any positive number).\n\n"
        "Examples: 25.50, 100, 15.75"
    )
    
    return PRICE_MEDICINE_SELECTION

async def handle_price_value_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new price input for individual medicine."""
    try:
        new_price = float(update.message.text.strip())
        if new_price <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid price. Please enter a positive number:\n\n"
            "Examples: 25.50, 100, 15.75"
        )
        return PRICE_MEDICINE_SELECTION
    
    db = context.bot_data['db']
    medicine_id = context.user_data['selected_medicine_for_price']
    
    # Get medicine details for confirmation
    medicine = db.get_medicine_by_id(medicine_id)
    old_price = medicine['price']
    
    # Update the price
    success, message = db.update_medicine_price(medicine_id, new_price)
    
    if success:
        price_change = new_price - old_price
        percentage_change = ((new_price - old_price) / old_price) * 100 if old_price > 0 else 0
        
        await update.message.reply_text(
            f"✅ **Price Updated Successfully!**\n\n"
            f"💊 **Medicine:** {medicine['name']}\n"
            f"💰 **Previous Price:** {old_price:.2f} ETB\n"
            f"💰 **New Price:** {new_price:.2f} ETB\n"
            f"📈 **Change:** {price_change:+.2f} ETB ({percentage_change:+.1f}%)\n\n"
            "Use /start to return to the main menu.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Update Another Price", callback_data="update_prices")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
    else:
        await update.message.reply_text(
            f"❌ **Failed to update price:** {message}\n\n"
            "Please try again."
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def handle_edit_contact(query, user_type):
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    contact_text = """
📝 **Edit Contact Information**

To update contact details, choose a field to edit:

📞 **Phone Number** - Update business phone number
📧 **Email Address** - Update business email address
🏢 **Office Address** - Update business office address
"""
    keyboard = [
        [InlineKeyboardButton("📞 Edit Phone Number", callback_data="edit_phone")],
        [InlineKeyboardButton("📧 Edit Email Address", callback_data="edit_email")],
        [InlineKeyboardButton("🏢 Edit Office Address", callback_data="edit_address")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(contact_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone number editing."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db = context.bot_data['db']
    user_info = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if not user_info or user_info['user_type'] not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return ConversationHandler.END
    
    current_phone = db.get_contact_setting('phone') or '+251-11-555-0123'
    
    await query.edit_message_text(
        f"📞 **Edit Phone Number**\n\n"
        f"**Current Phone:** {current_phone}\n\n"
        f"💬 **Please enter the new phone number:**\n\n"
        f"Format examples:\n"
        f"• +251-11-123-4567\n"
        f"• +1-555-123-4567\n"
        f"• 0911-123456\n\n"
        f"Type your response below:"
    )
    
    context.user_data['edit_field'] = 'phone'
    return EDIT_PHONE

async def handle_edit_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle email address editing."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db = context.bot_data['db']
    user_info = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if not user_info or user_info['user_type'] not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return ConversationHandler.END
    
    current_email = db.get_contact_setting('email') or 'contact@bluepharma.et'
    
    await query.edit_message_text(
        f"📧 **Edit Email Address**\n\n"
        f"**Current Email:** {current_email}\n\n"
        f"💬 **Please enter the new email address:**\n\n"
        f"Format examples:\n"
        f"• info@yourcompany.com\n"
        f"• contact@bluepharma.et\n"
        f"• support@pharmacy.com\n\n"
        f"Type your response below:"
    )
    
    context.user_data['edit_field'] = 'email'
    return EDIT_EMAIL

async def handle_edit_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle office address editing."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db = context.bot_data['db']
    user_info = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if not user_info or user_info['user_type'] not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return ConversationHandler.END
    
    current_address = db.get_contact_setting('address') or '123 Pharmacy Street, Addis Ababa, Ethiopia'
    
    await query.edit_message_text(
        f"🏢 **Edit Office Address**\n\n"
        f"**Current Address:** {current_address}\n\n"
        f"💬 **Please enter the new office address:**\n\n"
        f"Format examples:\n"
        f"• 123 Main Street, City, Country\n"
        f"• Building Name, Street, District, City\n"
        f"• P.O. Box 1234, City, Country\n\n"
        f"Type your response below:"
    )
    
    context.user_data['edit_field'] = 'address'
    return EDIT_ADDRESS

async def handle_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone number input."""
    phone_input = update.message.text.strip()
    db = context.bot_data['db']
    
    # Basic phone validation
    if len(phone_input) < 8 or len(phone_input) > 20:
        await update.message.reply_text(
            "❌ **Invalid phone number length.**\n\n"
            "Phone number should be between 8 and 20 characters.\n\n"
            "Please enter a valid phone number:"
        )
        return EDIT_PHONE
    
    # Update the phone number
    success = db.update_contact_setting('phone', phone_input)
    
    if success:
        await update.message.reply_text(
            f"✅ **Phone Number Updated Successfully!**\n\n"
            f"📞 **New Phone:** {phone_input}\n\n"
            "Use /start to return to the main menu.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Edit More Contacts", callback_data="edit_contact")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
    else:
        await update.message.reply_text(
            "❌ **Failed to update phone number.**\n\n"
            "Please try again."
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def handle_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle email address input."""
    email_input = update.message.text.strip()
    db = context.bot_data['db']
    
    # Basic email validation
    if '@' not in email_input or '.' not in email_input.split('@')[1]:
        await update.message.reply_text(
            "❌ **Invalid email format.**\n\n"
            "Please enter a valid email address (e.g., contact@example.com):"
        )
        return EDIT_EMAIL
    
    # Update the email address
    success = db.update_contact_setting('email', email_input)
    
    if success:
        await update.message.reply_text(
            f"✅ **Email Address Updated Successfully!**\n\n"
            f"📧 **New Email:** {email_input}\n\n"
            "Use /start to return to the main menu.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Edit More Contacts", callback_data="edit_contact")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
    else:
        await update.message.reply_text(
            "❌ **Failed to update email address.**\n\n"
            "Please try again."
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def handle_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle office address input."""
    address_input = update.message.text.strip()
    db = context.bot_data['db']
    
    # Basic address validation
    if len(address_input) < 10 or len(address_input) > 500:
        await update.message.reply_text(
            "❌ **Invalid address length.**\n\n"
            "Address should be between 10 and 500 characters.\n\n"
            "Please enter a valid office address:"
        )
        return EDIT_ADDRESS
    
    # Update the office address
    success = db.update_contact_setting('address', address_input)
    
    if success:
        await update.message.reply_text(
            f"✅ **Office Address Updated Successfully!**\n\n"
            f"🏢 **New Address:** {address_input}\n\n"
            "Use /start to return to the main menu.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Edit More Contacts", callback_data="edit_contact")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
    else:
        await update.message.reply_text(
            "❌ **Failed to update office address.**\n\n"
            "Please try again."
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def handle_change_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db = context.bot_data['db']
    user_info = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if not user_info:
        await query.edit_message_text("Error accessing user information. Please try /start")
        return ConversationHandler.END
        
    user_type = user_info['user_type']
    
    if user_type != 'admin':
        await query.edit_message_text("❌ Access denied. Administrator access required.")
        return ConversationHandler.END
    
    current_pin = db.get_contact_setting('admin_pin') if hasattr(db, 'get_contact_setting') else None
    masked = '****' if current_pin else '(default: 4321)'
    text = (
        "🔑 **Change Admin PIN**\n\n"
        f"Current PIN: {masked}\n\n"
        "Enter a new PIN (4-8 digits)."
    )
    await query.edit_message_text(text, parse_mode='Markdown')
    return CHANGE_PIN_INPUT

async def handle_change_pin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_pin = update.message.text.strip()
    if not new_pin.isdigit() or not (4 <= len(new_pin) <= 8):
        await update.message.reply_text(
            "❌ Invalid PIN. Enter 4-8 digits only:"
        )
        return CHANGE_PIN_INPUT
    db = context.bot_data['db']
    ok = db.update_contact_setting('admin_pin', new_pin) if hasattr(db, 'update_contact_setting') else False
    if ok:
        await update.message.reply_text(
            "✅ PIN updated successfully.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]])
        )
    else:
        await update.message.reply_text("❌ Failed to update PIN. Please try again.")
        return CHANGE_PIN_INPUT
    return ConversationHandler.END

async def handle_manage_users(query, user_type):
    if user_type != 'admin':
        await query.edit_message_text("❌ Access denied. Administrator access required.")
        return
    
    users_text = """
👥 **User Management** (Admin Only)

🎯 **Choose user type to manage:**

👥 **Customers** - Manage customer accounts
• View, activate/deactivate customers
• Change customer roles

👨‍💼 **Staff** - Manage staff accounts  
• View, activate/deactivate staff
• Change staff roles and permissions

👀 **All Users** - View everyone at once
"""
    keyboard = [
        [InlineKeyboardButton("👥 Manage Customers", callback_data="manage_customers"),
         InlineKeyboardButton("👨‍💼 Manage Staff", callback_data="manage_staff")],
        [InlineKeyboardButton("👀 View All Users", callback_data="view_all_users")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(users_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_manage_customers(query, user_type, db):
    if user_type != 'admin':
        await query.edit_message_text("❌ Access denied. Administrator access required.")
        return
    
    customers = db.get_users_by_type('customer')
    customer_count = len(customers)
    active_customers = len([u for u in customers if u.get('is_active')])
    inactive_customers = customer_count - active_customers
    
    customers_text = f"""
👥 **Customer Management**

📊 **Customer Statistics:**
• Total Customers: {customer_count}
• Active: {active_customers}
• Inactive: {inactive_customers}

🔧 **Management Options:**
"""
    
    keyboard = [
        [InlineKeyboardButton("👀 View All Customers", callback_data="view_customers")],
        [InlineKeyboardButton("✅/🚫 Toggle Customer Status", callback_data="toggle_customers")],
        [InlineKeyboardButton("🛡️ Change Customer Roles", callback_data="edit_customer_roles")],
        [InlineKeyboardButton("🔙 Back to User Management", callback_data="manage_users")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(customers_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_manage_staff(query, user_type, db):
    if user_type != 'admin':
        await query.edit_message_text("❌ Access denied. Administrator access required.")
        return
    
    staff = db.get_users_by_type(['staff', 'admin'])
    staff_count = len(staff)
    active_staff = len([u for u in staff if u.get('is_active')])
    inactive_staff = staff_count - active_staff
    admins = len([u for u in staff if u.get('user_type') == 'admin'])
    regular_staff = staff_count - admins
    
    staff_text = f"""
👨‍💼 **Staff Management**

📊 **Staff Statistics:**
• Total Staff: {staff_count}
• Active: {active_staff}
• Inactive: {inactive_staff}
• Admins: {admins}
• Regular Staff: {regular_staff}

🔧 **Management Options:**
"""
    
    keyboard = [
        [InlineKeyboardButton("👀 View All Staff", callback_data="view_staff")],
        [InlineKeyboardButton("✅/🚫 Toggle Staff Status", callback_data="toggle_staff")],
        [InlineKeyboardButton("🛡️ Change Staff Roles", callback_data="edit_staff_roles")],
        [InlineKeyboardButton("🔙 Back to User Management", callback_data="manage_users")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(staff_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_view_customers(query, user_type, db):
    if user_type != 'admin':
        await query.edit_message_text("❌ Access denied. Administrator access required.")
        return
    
    customers = db.get_users_by_type('customer')
    if not customers:
        await query.edit_message_text(
            "👥 No customers found.", 
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Customer Management", callback_data="manage_customers")]
            ])
        )
        return
    
    text = f"👥 **All Customers ({len(customers)})**\n\n"
    for u in customers[:20]:  # Show latest 20
        name = u.get('first_name') or ''
        uname = f"@{u['username']}" if u.get('username') else ''
        status = "✅ Active" if u.get('is_active') else "🚫 Inactive"
        text += f"• ID:{u['id']} | {name} {uname} | {status}\n"
    
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Customer Management", callback_data="manage_customers")]
    ])
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_toggle_customers(query, user_type, db):
    if user_type != 'admin':
        await query.edit_message_text("❌ Access denied. Administrator access required.")
        return
    
    customers = db.get_users_by_type('customer')
    if not customers:
        await query.edit_message_text(
            "No customers to manage.", 
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Customer Management", callback_data="manage_customers")]
            ])
        )
        return
    
    text = "✅/🚫 **Toggle Customer Active Status**\n\nTap a customer to toggle active/inactive:\n\n"
    keyboard = []
    for u in customers[:10]:  # Show latest 10
        status = "✅" if u.get('is_active') else "🚫"
        label = f"{status} {u.get('first_name') or ''} (@{u.get('username') or 'No username'}) | id:{u['id']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"toggle_user_{u['id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Customer Management", callback_data="manage_customers")])
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_edit_customer_roles(query, user_type, db):
    if user_type != 'admin':
        await query.edit_message_text("❌ Access denied. Administrator access required.")
        return
    
    customers = db.get_users_by_type('customer')
    if not customers:
        await query.edit_message_text(
            "No customers to manage.", 
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Customer Management", callback_data="manage_customers")]
            ])
        )
        return
    
    text = "🛡️ **Edit Customer Roles**\n\nChoose a customer to change role:\n\n"
    keyboard = []
    for u in customers[:10]:  # Show latest 10
        label = f"{u.get('first_name') or ''} (@{u.get('username') or 'No username'}) | {u['user_type']} | id:{u['id']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"edit_role_{u['id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Customer Management", callback_data="manage_customers")])
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_view_staff(query, user_type, db):
    if user_type != 'admin':
        await query.edit_message_text("❌ Access denied. Administrator access required.")
        return
    
    staff = db.get_users_by_type(['staff', 'admin'])
    if not staff:
        await query.edit_message_text(
            "👨‍💼 No staff members found.", 
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Staff Management", callback_data="manage_staff")]
            ])
        )
        return
    
    text = f"👨‍💼 **All Staff ({len(staff)})**\n\n"
    for u in staff[:20]:  # Show latest 20
        name = u.get('first_name') or ''
        uname = f"@{u['username']}" if u.get('username') else ''
        status = "✅ Active" if u.get('is_active') else "🚫 Inactive"
        role_emoji = "🔑" if u['user_type'] == 'admin' else "👨‍💼"
        text += f"• {role_emoji} ID:{u['id']} | {name} {uname} | {u['user_type'].title()} | {status}\n"
    
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Staff Management", callback_data="manage_staff")]
    ])
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_toggle_staff(query, user_type, db):
    if user_type != 'admin':
        await query.edit_message_text("❌ Access denied. Administrator access required.")
        return
    
    staff = db.get_users_by_type(['staff', 'admin'])
    if not staff:
        await query.edit_message_text(
            "No staff members to manage.", 
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Staff Management", callback_data="manage_staff")]
            ])
        )
        return
    
    text = "✅/🚫 **Toggle Staff Active Status**\n\nTap a staff member to toggle active/inactive:\n\n"
    keyboard = []
    for u in staff[:10]:  # Show latest 10
        status = "✅" if u.get('is_active') else "🚫"
        role_emoji = "🔑" if u['user_type'] == 'admin' else "👨‍💼"
        label = f"{status} {role_emoji} {u.get('first_name') or ''} (@{u.get('username') or 'No username'}) | {u['user_type']} | id:{u['id']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"toggle_user_{u['id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Staff Management", callback_data="manage_staff")])
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_edit_staff_roles(query, user_type, db):
    if user_type != 'admin':
        await query.edit_message_text("❌ Access denied. Administrator access required.")
        return
    
    staff = db.get_users_by_type(['staff', 'admin'])
    if not staff:
        await query.edit_message_text(
            "No staff members to manage.", 
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Staff Management", callback_data="manage_staff")]
            ])
        )
        return
    
    text = "🛡️ **Edit Staff Roles**\n\nChoose a staff member to change role:\n\n"
    keyboard = []
    for u in staff[:10]:  # Show latest 10
        role_emoji = "🔑" if u['user_type'] == 'admin' else "👨‍💼"
        label = f"{role_emoji} {u.get('first_name') or ''} (@{u.get('username') or 'No username'}) | {u['user_type']} | id:{u['id']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"edit_role_{u['id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Staff Management", callback_data="manage_staff")])
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_view_all_users(query, user_type, db):
    if user_type != 'admin':
        await query.edit_message_text("❌ Access denied. Administrator access required.")
        return
    users = db.get_all_users(limit=20)
    if not users:
        await query.edit_message_text("👥 No users found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="manage_users")]]))
        return
    text = "👥 **All Users (latest 20)**\n\n"
    for u in users:
        name = u.get('first_name') or ''
        uname = f"@{u['username']}" if u.get('username') else ''
        status = "✅ Active" if u.get('is_active') else "🚫 Inactive"
        text += f"• ID:{u['id']} | {name} {uname} | {u['user_type'].title()} | {status}\n"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="manage_users")]])
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_activate_deactivate_users(query, user_type, db):
    if user_type != 'admin':
        await query.edit_message_text("❌ Access denied. Administrator access required.")
        return
    users = db.get_all_users(limit=10)
    if not users:
        await query.edit_message_text("No users to manage.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="manage_users")]]))
        return
    text = "✅/🚫 **Toggle User Active Status**\n\nTap a user to toggle active/inactive:\n\n"
    keyboard = []
    for u in users:
        status = "✅" if u.get('is_active') else "🚫"
        label = f"{status} {u.get('first_name') or ''} (@{u.get('username')}) | {u['user_type']} | id:{u['id']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"toggle_user_{u['id']}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="manage_users")])
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_toggle_user_active(query, db):
    await query.answer()
    data = query.data
    try:
        user_id = int(data.replace("toggle_user_", ""))
    except:
        await query.edit_message_text("❌ Invalid user id.")
        return
    user = db.get_user_by_id(user_id)
    if not user:
        await query.edit_message_text("❌ User not found.")
        return
    new_active = 0 if user.get('is_active') else 1
    db.set_user_active(user_id, new_active)
    # Refresh the toggle list
    await handle_activate_deactivate_users(query, 'admin', db)

async def handle_edit_user_roles_main(query, user_type, db):
    if user_type != 'admin':
        await query.edit_message_text("❌ Access denied. Administrator access required.")
        return
    users = db.get_all_users(limit=10)
    if not users:
        await query.edit_message_text("No users to manage.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="manage_users")]]))
        return
    text = "🛡️ **Edit User Roles**\n\nChoose a user to change role:\n\n"
    keyboard = []
    for u in users:
        label = f"{u.get('first_name') or ''} (@{u.get('username')}) | {u['user_type']} | id:{u['id']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"edit_role_{u['id']}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="manage_users")])
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_choose_user_role(query, db):
    await query.answer()
    data = query.data
    try:
        user_id = int(data.replace("edit_role_", ""))
    except:
        await query.edit_message_text("❌ Invalid user id.")
        return
    u = db.get_user_by_id(user_id)
    if not u:
        await query.edit_message_text("❌ User not found.")
        return
    text = f"🛡️ **Set Role for:** {u.get('first_name') or ''} (@{u.get('username')})\nCurrent: {u['user_type'].title()}\n\nChoose new role:"
    keyboard = [
        [InlineKeyboardButton("Customer", callback_data=f"set_role_customer_{user_id}"),
         InlineKeyboardButton("Staff", callback_data=f"set_role_staff_{user_id}"),
         InlineKeyboardButton("Admin", callback_data=f"set_role_admin_{user_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="edit_user_roles")]
    ]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_set_user_role(query, db):
    await query.answer()
    data = query.data
    try:
        # format: set_role_<role>_<id>
        parts = data.split('_')
        role = parts[2]
        user_id = int(parts[3])
    except Exception:
        await query.edit_message_text("❌ Invalid parameters.")
        return
    if role not in ('customer', 'staff', 'admin'):
        await query.edit_message_text("❌ Invalid role.")
        return
    ok = db.update_user_type_by_id(user_id, role)
    if not ok:
        await query.edit_message_text("❌ Failed to update role.")
        return
    # Go back to role list
    await handle_edit_user_roles_main(query, 'admin', db)

async def handle_contact_info(query, context):
    """Show contact information with updated values from database."""
    try:
        # Get database from context
        db = context.bot_data['db']
        
        # Get updated contact settings from database
        phone = db.get_contact_setting('phone') or '+251-11-555-0123'
        email = db.get_contact_setting('email') or 'contact@bluepharma.et'
        address = db.get_contact_setting('address') or '123 Pharmacy Street, Addis Ababa, Ethiopia'
        hours = db.get_contact_setting('hours') or '08:00-22:00 Daily'
        
    except Exception as e:
        # Fallback to default values if any error occurs
        logger.error(f"Error getting contact settings: {e}")
        phone = '+251-11-555-0123'
        email = 'contact@bluepharma.et'
        address = '123 Pharmacy Street, Addis Ababa, Ethiopia'
        hours = '08:00-22:00 Daily'
    
    contact_text = f"""
📞 **Contact Blue Pharma Trading PLC**

🏥 **Business Information:**
📍 Address: {address}
📱 Phone: {phone}
📧 Email: {email}
🕐 Hours: {hours}
"""
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(contact_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_help(query, user_type):
    help_text = f"""
❓ **Help & Information**

👤 **Your Access Level:** {USER_ROLES.get(user_type, user_type.title())}

To use this bot, simply click on the buttons to perform actions like checking medicines, placing orders, and managing stock.

For any issues, contact support.
"""
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_place_order(query, context):
    """Show medicine categories for ordering."""
    db = context.bot_data['db']
    categories = db.get_medicine_categories()
    
    if not categories:
        await query.edit_message_text(
            "❌ No medicine categories available. Please contact admin to add medicines.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
        return
    
    order_text = "🛒 **Place Order - Select Category**\n\n💊 **Choose a therapeutic category to browse medicines:**\n\n"
    
    keyboard = []
    # Add category buttons in rows of 2
    for i in range(0, len(categories), 2):
        row = []
        for j in range(i, min(i + 2, len(categories))):
            category = categories[j]
            # Use emoji based on category name
            emoji = get_category_emoji(category)
            row.append(InlineKeyboardButton(f"{emoji} {category}", callback_data=f"category_{category}"))
        keyboard.append(row)
    
    # Add cart and navigation buttons
    keyboard.append([InlineKeyboardButton("🛒 View Cart", callback_data="view_order_cart")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(order_text, parse_mode='Markdown', reply_markup=reply_markup)

def get_category_emoji(category):
    """Get appropriate emoji for medicine category."""
    category_lower = category.lower()
    if 'analgesic' in category_lower or 'pain' in category_lower:
        return "💊"
    elif 'antibiotic' in category_lower:
        return "🦠"
    elif 'antidepressant' in category_lower or 'depression' in category_lower:
        return "🧠"
    elif 'antifungal' in category_lower or 'fungal' in category_lower:
        return "🍄"
    elif 'antihypertensive' in category_lower or 'hypertension' in category_lower or 'blood pressure' in category_lower:
        return "❤️"
    elif 'antipyretic' in category_lower or 'fever' in category_lower:
        return "🌡️"
    elif 'antiviral' in category_lower or 'viral' in category_lower:
        return "🛡️"
    elif 'respiratory' in category_lower or 'lung' in category_lower:
        return "🫁"
    elif 'vitamin' in category_lower:
        return "🌟"
    elif 'cardiac' in category_lower or 'heart' in category_lower:
        return "❤️"
    elif 'digestive' in category_lower or 'gastro' in category_lower:
        return "🍽️"
    elif 'neurological' in category_lower or 'neuro' in category_lower:
        return "🧠"
    elif 'dermatological' in category_lower or 'skin' in category_lower:
        return "🧴"
    else:
        return "💉"

async def handle_my_orders(query, user_type, db):
    user_id = query.from_user.id
    orders = db.get_user_orders(user_id)
    if not orders:
        await query.edit_message_text("📦 You have no past orders.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]]))
        return
    order_text = "📦 **My Recent Orders**\n\n"
    for order in orders:
        order_text += f"**Order #{db.format_order_id(order['id'])}** | Status: {order['status'].capitalize()}\n"
        order_text += f"Total: {order['total_amount']:.2f} ETB\n"
        order_text += f"Date: {order['order_date']}\n\n"
    await query.edit_message_text(order_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]]))

async def handle_request_wholesale(query):
    wholesale_text = "🏢 **Wholesale Request**\n\nContact our team for wholesale inquiries."
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(wholesale_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_all_orders(query, user_type, db):
    """Display all orders in the system for admin/staff with comprehensive details."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        orders = db.get_all_orders(20)  # Limit to 20 orders for readability
        
        if not orders:
            await query.edit_message_text(
                "📋 All Orders\n\n❌ No orders found in the system.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return
        
        orders_text = f"📋 All Orders ({len(orders)} shown)\n\n"
        
        # Show comprehensive details for each order
        for i, order in enumerate(orders, 1):
            # Get detailed order information
            order_details = db.get_order_details(order['id'])
            
            if not order_details:
                continue
            
            # Format order status with emoji
            status_emoji = "⏳" if order['status'] == 'pending' else "✅" if order['status'] == 'completed' else "📦"
            order_date = order['order_date'][:10] if order['order_date'] else 'N/A'
            order_time = order['order_date'][11:16] if len(order['order_date']) > 10 else ''
            
            # Calculate urgency for pending orders
            urgency_info = ""
            if order['status'] == 'pending':
                try:
                    order_date_obj = datetime.strptime(order_date, '%Y-%m-%d')
                    days_pending = (datetime.now() - order_date_obj).days
                    if days_pending > 3:
                        urgency_info = f" 🚨 {days_pending}d"
                    elif days_pending > 1:
                        urgency_info = f" ⚠️ {days_pending}d"
                    else:
                        urgency_info = f" {days_pending}d"
                except:
                    pass
            
            # Main order header
            orders_text += f"{i}. {status_emoji} #{db.format_order_id(order['id'])}{urgency_info}\n"
            orders_text += f"📅 Date: {order_date} {order_time} | 💰 Total: {order['total_amount']:.2f} ETB\n"
            orders_text += f"👤 Customer: {order['customer_name']} | 📱 {order['customer_phone']}\n"
            
            # Show ordered items
            items_text = "📦 Items: "
            items_list = []
            for item in order_details.get('items', []):
                items_list.append(f"{item['medicine_name']} x{item['quantity']} ({item['total_price']:.2f} ETB)")
            
            if len(items_list) <= 2:
                items_text += "; ".join(items_list)
            else:
                items_text += f"{items_list[0]}; {items_list[1]}; +{len(items_list)-2} more"
            
            orders_text += items_text + "\n"
            
            # Add status-specific action buttons inline
            if order['status'] == 'pending':
                orders_text += f"⚡ Actions: Mark Complete | Update Status\n"
            elif order['status'] == 'completed':
                orders_text += f"⚡ Actions: Reopen | View History\n"
            
            orders_text += "\n"
        
        # Add navigation buttons at the bottom
        keyboard = [
            [InlineKeyboardButton("📄 Export to Excel", callback_data="export_all_orders_excel")],
            [InlineKeyboardButton("🔍 Search Order Details", callback_data="order_details_search")],
            [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
        ]
        
        # Truncate if message is too long
        if len(orders_text) > 3800:
            orders_text = orders_text[:3800] + "\n\n... List truncated. Use Excel export for complete data or search for specific orders."
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(orders_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in handle_all_orders: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error retrieving orders. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")]
            ])
        )

async def handle_pending_orders(query, user_type, db):
    """Display pending orders for admin/staff with comprehensive details."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        orders = db.get_pending_orders(15)  # Limit to 15 orders for readability
        
        if not orders:
            await query.edit_message_text(
                "⏳ Pending Orders\n\n✅ No pending orders found. All orders have been processed!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 View All Orders", callback_data="all_orders")],
                    [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return
        
        orders_text = f"⏳ Pending Orders ({len(orders)} shown)\n\n"
        
        keyboard = []
        
        # Show comprehensive details for each pending order
        for i, order in enumerate(orders, 1):
            # Get detailed order information
            order_details = db.get_order_details(order['id'])
            
            if not order_details:
                continue
            
            order_date = order['order_date'][:10] if order['order_date'] else 'N/A'
            order_time = order['order_date'][11:16] if len(order['order_date']) > 10 else ''
            
            # Calculate days pending for urgency indicator
            urgency_indicator = "⏳"
            days_pending = 0
            try:
                order_date_obj = datetime.strptime(order_date, '%Y-%m-%d')
                days_pending = (datetime.now() - order_date_obj).days
                if days_pending > 3:
                    urgency_indicator = "🚨 URGENT"  # Very urgent
                elif days_pending > 1:
                    urgency_indicator = "⚠️ PRIORITY"  # Urgent
                else:
                    urgency_indicator = "⏳ NORMAL"  # Normal
            except:
                urgency_indicator = "⏳ NORMAL"
            
            # Main order header with urgency
            orders_text += f"{i}. 🔥 #{db.format_order_id(order['id'])} ({urgency_indicator})\n"
            orders_text += f"📅 Date: {order_date} {order_time} | ⏰ Pending: {days_pending} days\n"
            orders_text += f"👤 Customer: {order['customer_name']} | 📱 {order['customer_phone']}\n"
            orders_text += f"💰 Total: {order['total_amount']:.2f} ETB | 📦 Items: {order['total_items']} units\n"
            
            # Show ordered medicines with details
            orders_text += "🛒 Medicines: "
            items_list = []
            for item in order_details.get('items', []):
                items_list.append(f"{item['medicine_name']} x{item['quantity']} ({item['total_price']:.2f} ETB)")
            
            if len(items_list) <= 2:
                orders_text += "; ".join(items_list)
            else:
                orders_text += f"{items_list[0]}; {items_list[1]}; +{len(items_list)-2} more"
            
            orders_text += "\n"
            
            # Telegram user info if available
            if order_details.get('first_name'):
                orders_text += f"👨‍💼 Telegram: @{order_details.get('first_name')} {order_details.get('last_name', '')} (ID: {order_details.get('telegram_id')})\n"
            
            # Add action buttons for each order
            keyboard.append([
                InlineKeyboardButton(f"✅ Complete #{db.format_order_id(order['id'])}", 
                                   callback_data=f"mark_completed_{order['id']}"),
                InlineKeyboardButton(f"📋 Full Details #{db.format_order_id(order['id'])}", 
                                   callback_data=f"view_order_details_{order['id']}")
            ])
            
            orders_text += "\n"
        
        # Add navigation buttons at the bottom
        keyboard.append([InlineKeyboardButton("📄 Export Pending Orders", callback_data="export_pending_orders_excel")])
        keyboard.append([InlineKeyboardButton("✅ View Completed Orders", callback_data="completed_orders")])
        keyboard.append([InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")])
        keyboard.append([InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")])
        
        # Truncate if message is too long
        if len(orders_text) > 3800:
            orders_text = orders_text[:3800] + "\n\n... List truncated. Use Excel export for complete data."
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(orders_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in handle_pending_orders: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error retrieving pending orders. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")]
            ])
        )

async def handle_completed_orders(query, user_type, db):
    """Display completed orders for admin/staff with comprehensive details."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        orders = db.get_completed_orders(15)  # Limit to 15 orders for readability
        
        if not orders:
            await query.edit_message_text(
                "✅ Completed Orders\n\n📋 No completed orders found in the system.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏳ View Pending Orders", callback_data="pending_orders")],
                    [InlineKeyboardButton("📦 View All Orders", callback_data="all_orders")],
                    [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return
        
        orders_text = f"✅ Completed Orders ({len(orders)} shown)\n\n"
        
        keyboard = []
        
        # Show comprehensive details for each completed order
        for i, order in enumerate(orders, 1):
            # Get detailed order information
            order_details = db.get_order_details(order['id'])
            
            if not order_details:
                continue
            
            order_date = order['order_date'][:10] if order['order_date'] else 'N/A'
            order_time = order['order_date'][11:16] if len(order['order_date']) > 10 else ''
            
            # Calculate completion timeframe
            completion_info = ""
            try:
                order_date_obj = datetime.strptime(order_date, '%Y-%m-%d')
                days_ago = (datetime.now() - order_date_obj).days
                if days_ago == 0:
                    completion_info = " (Today)"
                elif days_ago == 1:
                    completion_info = " (Yesterday)"
                elif days_ago <= 7:
                    completion_info = f" ({days_ago}d ago)"
                else:
                    completion_info = f" ({days_ago}d ago)"
            except:
                pass
            
            # Main order header
            orders_text += f"{i}. ✅ #{db.format_order_id(order['id'])}{completion_info}\n"
            orders_text += f"📅 Date: {order_date} {order_time} | 💰 Total: {order['total_amount']:.2f} ETB\n"
            orders_text += f"👤 Customer: {order['customer_name']} | 📱 {order['customer_phone']}\n"
            
            # Show delivery method and total items
            orders_text += f"🚚 Delivery: {order['delivery_method'].title()} | 📦 Items: {order['total_items']} units\n"
            
            # Show ordered medicines with details
            orders_text += "🛒 Medicines: "
            items_list = []
            for item in order_details.get('items', []):
                items_list.append(f"{item['medicine_name']} x{item['quantity']} ({item['total_price']:.2f} ETB)")
            
            if len(items_list) <= 2:
                orders_text += "; ".join(items_list)
            else:
                orders_text += f"{items_list[0]}; {items_list[1]}; +{len(items_list)-2} more"
            
            orders_text += "\n"
            
            # Telegram user info if available
            if order_details.get('first_name'):
                orders_text += f"👨‍💼 Telegram: @{order_details.get('first_name')} {order_details.get('last_name', '')}\n"
            
            # Add action buttons for each order
            keyboard.append([
                InlineKeyboardButton(f"⏳ Reopen #{db.format_order_id(order['id'])}", 
                                   callback_data=f"mark_pending_{order['id']}"),
                InlineKeyboardButton(f"📋 Full Details #{db.format_order_id(order['id'])}", 
                                   callback_data=f"view_order_details_{order['id']}")
            ])
            
            orders_text += "\n"
        
        # Add navigation buttons at the bottom
        keyboard.append([InlineKeyboardButton("📄 Export Completed Orders", callback_data="export_completed_orders_excel")])
        keyboard.append([InlineKeyboardButton("⏳ View Pending Orders", callback_data="pending_orders")])
        keyboard.append([InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")])
        keyboard.append([InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")])
        
        # Truncate if message is too long
        if len(orders_text) > 3800:
            orders_text = orders_text[:3800] + "\n\n... List truncated. Use Excel export for complete data."
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(orders_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in handle_pending_orders: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error retrieving pending orders. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")]
            ])
        )

async def handle_back_to_main(query, user_type):
    user = query.from_user
    role_display = USER_ROLES.get(user_type, user_type.title())
    welcome_text = f"Hello {user.first_name}! Your Access Level: {role_display}\n\nWhat would you like to do today?"
    keyboard = get_user_keyboard(user_type)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_view_all_medicines(query, user_type, db):
    """Show options for viewing all medicines - Quick View or Excel Export."""
    try:
        medicines = db.get_all_medicines()
        if not medicines:
            await query.edit_message_text(
                "There are no medicines in stock.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return

        view_text = f"📋 **View All Medicines ({len(medicines)} total)**\n\n"
        view_text += "📊 **Choose how you want to view the medicine list:**\n\n"
        view_text += "👁️ **Quick View** - Display medicines in chat\n"
        view_text += "📄 **Excel Export** - Download complete list as Excel file\n"
        
        keyboard = [
            [InlineKeyboardButton("👁️ Quick View", callback_data="medicines_quick_view")],
            [InlineKeyboardButton("📄 Excel Export", callback_data="medicines_excel_export")],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(view_text, parse_mode='Markdown', reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in view all medicines options: {e}", exc_info=True)
        await query.edit_message_text("Error retrieving medicine information.")

async def handle_add_to_cart(query, db):
    medicine_id = int(query.data.split('_')[-1])
    user_id = query.from_user.id
    
    medicine = db.get_medicine_by_id(medicine_id)
    if not medicine or medicine['stock_quantity'] <= 0:
        await query.edit_message_text("❌ This medicine is currently out of stock.")
        return
    
    add_to_cart_local(user_id, medicine_id)
    await query.edit_message_text(
        f"✅ **{medicine['name']}** has been added to your cart!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 View Cart", callback_data="view_order_cart")],
            [InlineKeyboardButton("➕ Add More Medicines", callback_data="place_order")],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
        ])
    )

async def handle_view_cart(query, db):
    """Handle viewing the shopping cart with robust error handling."""
    try:
        user_id = query.from_user.id
        cart = get_user_cart(user_id)
        
        if not cart:
            await query.edit_message_text(
                "🛒 **Your cart is empty!**\n\n"
                "💡 **Add some medicines to get started:**\n"
                "• Browse by therapeutic category\n"
                "• Search for specific medicines\n"
                "• Check available stock",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 Browse Categories", callback_data="place_order")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return
        
        cart_text = "🛒 **Your Shopping Cart**\n\n"
        total_price = 0.0
        valid_items = []
        invalid_items = []
        stock_warnings = []
        
        # Process each cart item with validation
        for item in cart:
            try:
                medicine = db.get_medicine_by_id(item['medicine_id'])
                
                if not medicine:
                    # Medicine not found - add to invalid items
                    invalid_items.append({
                        'medicine_id': item['medicine_id'],
                        'quantity': item['quantity'],
                        'issue': 'Medicine not found'
                    })
                    continue
                
                if not medicine.get('is_active', True):
                    # Medicine deactivated
                    invalid_items.append({
                        'medicine_id': item['medicine_id'],
                        'quantity': item['quantity'],
                        'name': medicine['name'],
                        'issue': 'Medicine no longer available'
                    })
                    continue
                
                # Check stock availability
                if item['quantity'] > medicine['stock_quantity']:
                    # Insufficient stock - add to stock warnings
                    stock_warnings.append({
                        'medicine_id': item['medicine_id'],
                        'quantity': item['quantity'],
                        'name': medicine['name'],
                        'available_stock': medicine['stock_quantity'],
                        'price': medicine['price']
                    })
                else:
                    # Valid item
                    valid_items.append({
                        'medicine_id': item['medicine_id'],
                        'quantity': item['quantity'],
                        'name': medicine['name'],
                        'price': medicine['price'],
                        'category': medicine.get('therapeutic_category'),
                        'form': medicine.get('dosage_form')
                    })
            except Exception as item_error:
                # Handle errors processing individual cart items
                logger.error(f"Error processing cart item {item.get('medicine_id', 'Unknown')}: {item_error}")
                invalid_items.append({
                    'medicine_id': item.get('medicine_id', 'Unknown'),
                    'quantity': item.get('quantity', 0),
                    'issue': 'Error processing item'
                })
        
        # Display valid items
        if valid_items:
            cart_text += "✅ **Available Items:**\n\n"
            
            for i, item in enumerate(valid_items, 1):
                item_total = item['price'] * item['quantity']
                total_price += item_total
                
                cart_text += f"{i}. **{item['name']}**\n"
                cart_text += f"   🔢 Quantity: {item['quantity']} units\n"
                cart_text += f"   💰 Unit Price: {item['price']:.2f} ETB\n"
                cart_text += f"   💰 Subtotal: {item_total:.2f} ETB\n"
                
                if item.get('category'):
                    category_emoji = get_category_emoji(item['category'])
                    cart_text += f"   🏷️ Category: {category_emoji} {item['category']}\n"
                
                if item.get('form'):
                    cart_text += f"   💊 Form: {item['form']}\n"
                
                cart_text += "\n"
        
        # Display stock warnings
        if stock_warnings:
            cart_text += "⚠️ **Stock Issues:**\n\n"
            
            for warning in stock_warnings:
                cart_text += f"⚠️ **{warning['name']}**\n"
                cart_text += f"   🔢 Requested: {warning['quantity']} units\n"
                cart_text += f"   📦 Available: {warning['available_stock']} units\n"
                cart_text += f"   ❌ **Insufficient stock!**\n\n"
        
        # Display invalid items
        if invalid_items:
            cart_text += "❌ **Unavailable Items:**\n\n"
            
            for invalid in invalid_items:
                name = invalid.get('name', f"Medicine ID {invalid['medicine_id']}")
                cart_text += f"❌ **{name}** - {invalid['issue']}\n"
        
        # Cart summary
        cart_text += "\n" + "="*30 + "\n"
        cart_text += f"🛒 **Cart Summary:**\n"
        cart_text += f"• Valid Items: {len(valid_items)} types\n"
        cart_text += f"• Total Valid Quantity: {sum(item['quantity'] for item in valid_items)} units\n"
        cart_text += f"• **Total Price: {total_price:.2f} ETB**\n"
        
        if stock_warnings:
            cart_text += f"• ⚠️ Stock Issues: {len(stock_warnings)}\n"
        if invalid_items:
            cart_text += f"• ❌ Unavailable: {len(invalid_items)}\n"
        
        # Create action buttons based on cart state
        keyboard = []
        
        if valid_items:
            # Cart has valid items - show full options
            keyboard.append([InlineKeyboardButton("📝 Edit Cart", callback_data="edit_order_cart")])
            
            if not stock_warnings:
                # No stock issues - allow checkout
                keyboard.append([InlineKeyboardButton("✅ Proceed to Checkout", callback_data="proceed_checkout")])
            else:
                # Stock issues - suggest fixing first
                keyboard.append([InlineKeyboardButton("⚠️ Fix Stock Issues First", callback_data="edit_order_cart")])
        
        # Always show these options
        keyboard.append([InlineKeyboardButton("🛒 Continue Shopping", callback_data="place_order")])
        
        if cart:  # If cart has any items (valid or invalid)
            keyboard.append([InlineKeyboardButton("🗑️ Clear Cart", callback_data="clear_order_cart")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(cart_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        # Clean up invalid items from cart automatically
        if invalid_items:
            for invalid in invalid_items:
                remove_from_cart_local(user_id, invalid['medicine_id'])
            logger.info(f"Cleaned up {len(invalid_items)} invalid items from user {user_id}'s cart")
        
    except Exception as e:
        logger.error(f"Error in handle_view_cart: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error loading cart. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Try Again", callback_data="view_order_cart")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )

async def handle_edit_cart(query, db):
    user_id = query.from_user.id
    cart = get_user_cart(user_id)
    
    if not cart:
        await query.edit_message_text("Your cart is empty. Nothing to edit.")
        return
    
    edit_text = "📝 **Edit Your Cart**\n\nSelect an item to remove it:"
    keyboard = []
    for item in cart:
        medicine = db.get_medicine_by_id(item['medicine_id'])
        if medicine:
            keyboard.append([InlineKeyboardButton(f"❌ Remove {medicine['name']}", callback_data=f"remove_cart_item_{item['medicine_id']}")])
            
    keyboard.append([InlineKeyboardButton("🔙 Back to Cart", callback_data="view_order_cart")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(edit_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_remove_cart_item(query):
    medicine_id = int(query.data.split('_')[-1])
    user_id = query.from_user.id
    
    remove_from_cart_local(user_id, medicine_id)
    await query.edit_message_text("✅ Item removed from cart. Use `/cart` to view updated cart.")

async def handle_clear_cart(query):
    await query.edit_message_text(
        "⚠️ Are you sure you want to clear your entire cart? This action cannot be undone.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Clear My Cart", callback_data="confirm_clear_cart")],
            [InlineKeyboardButton("❌ No, Go Back", callback_data="view_order_cart")]
        ])
    )

async def handle_confirm_clear_cart(query):
    user_id = query.from_user.id
    clear_cart_local(user_id)
    await query.edit_message_text("✅ Your cart has been cleared. Use `/start` to return to the main menu.")

async def handle_proceed_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    cart = get_user_cart(user_id)
    if not cart:
        await query.edit_message_text("❌ Your cart is empty. Cannot proceed to checkout.")
        return
    await query.edit_message_text(
        "📦 **Checkout**\n\n"
        "To finalize your order, we need a few details. You will be prompted for your name and phone number."
        "This information is essential for our staff to contact you about your order."
        "\n\n**Do you want to proceed?**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Proceed", callback_data="collect_customer_info")],
            [InlineKeyboardButton("❌ Cancel", callback_data="view_order_cart")]
        ])
    )

async def handle_confirm_final_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    db = context.bot_data['db']
    user_id = query.from_user.id
    cart = get_user_cart(user_id)
    order_id = db.place_order(
        user_id,
        user_data[user_id]['customer_name'],
        user_data[user_id]['customer_phone'],
        cart
    )
    if order_id:
        total = calculate_cart_total(db, user_id)
        await query.edit_message_text(
            f"✅ **Order Placed Successfully!**\n\n"
            f"**Order ID:** {order_id}\n"
            f"**Total:** {total:.2f} ETB\n"
            "Our staff will contact you shortly to confirm and process your order."
        )
        clear_cart_local(user_id)
    else:
        await query.edit_message_text("❌ There was an error placing your order. Please try again.")

# --- Analytics and Reporting ---
async def handle_medicines_quick_view(query, user_type, db):
    """Show quick view of all medicines in chat message."""
    try:
        medicines = db.get_all_medicines()
        if not medicines:
            await query.edit_message_text(
                "There are no medicines in stock.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return

        # Group medicines by therapeutic category for better organization
        medicines_by_category = {}
        for medicine in medicines:
            category = medicine['therapeutic_category'] or "Uncategorized"
            if category not in medicines_by_category:
                medicines_by_category[category] = []
            medicines_by_category[category].append(medicine)
        
        # Create a formatted message with all medicines grouped by category
        medicines_text = "📋 **All Medicines in Stock**\n\n"
        
        # Add count information
        medicines_text += f"**Total Medicines:** {len(medicines)}\n\n"
        
        # Add medicines grouped by category
        for category, category_medicines in sorted(medicines_by_category.items()):
            emoji = get_category_emoji(category)
            # Escape special characters in category name for Markdown
            safe_category = category.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.')
            medicines_text += f"**{emoji} {safe_category} ({len(category_medicines)}):**\n"
            
            # Sort medicines within category alphabetically
            for medicine in sorted(category_medicines, key=lambda x: x['name']):
                stock_status = "✅" if medicine['stock_quantity'] > 0 else "❌"
                # Escape special characters in medicine name for Markdown
                safe_name = medicine['name'].replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.')
                medicines_text += f"{stock_status} **{safe_name}** - {medicine['stock_quantity']} in stock - {medicine['price']:.2f} ETB\n"
            
            medicines_text += "\n"
        
        # Split the message if it's too long (Telegram has a 4096 character limit)
        if len(medicines_text) > 4000:
            # Create a shorter version that won't exceed the limit
            shortened_text = medicines_text[:3900] + "\n\n... *Message truncated due to length*\n\n"
            shortened_text += "*Use Excel Export for complete list*"
            medicines_text = shortened_text
        
        keyboard = [
            [InlineKeyboardButton("📄 Export to Excel", callback_data="medicines_excel_export")],
            [InlineKeyboardButton("🔙 Back to View Options", callback_data="view_all_medicines")],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(medicines_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in medicines quick view: {e}", exc_info=True)
        await query.edit_message_text("Error retrieving medicine information.")

async def handle_medicines_excel_export(query, user_type, db, context):
    """Export all medicines to Excel file."""
    try:
        medicines = db.get_all_medicines()
        if not medicines:
            await query.edit_message_text(
                "There are no medicines in stock to export.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return

        # Create a pandas DataFrame from the medicines list
        df = pd.DataFrame(medicines)
        
        # Reorder and select columns for better display
        columns = [
            'name', 'therapeutic_category', 'price', 'stock_quantity', 
            'dosage_form', 'manufacturing_date', 'expiring_date'
        ]
        
        # Filter to only include columns that exist in the DataFrame
        columns = [col for col in columns if col in df.columns]
        
        # Select and reorder columns
        df = df[columns]
        
        # Rename columns for better readability in Excel
        column_names = {
            'name': 'Medicine Name',
            'therapeutic_category': 'Category',
            'price': 'Price (ETB)',
            'stock_quantity': 'Stock',
            'dosage_form': 'Form',
            'manufacturing_date': 'Mfg Date',
            'expiring_date': 'Exp Date'
        }
        df = df.rename(columns={k: v for k, v in column_names.items() if k in df.columns})
        
        # Create a temporary Excel file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
            df.to_excel(temp_file.name, index=False, sheet_name='Medicines')
            temp_file_path = temp_file.name
        
        # Format the date/time for the filename
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Send the Excel file to the user
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=temp_file_path,
            filename=f"Blue_Pharma_Medicines_{current_date}.xlsx",
            caption="📄 **Complete Medicine List**\n\nThis Excel file contains all medicines currently in the system."
        )
        
        # Remove the temporary file
        os.remove(temp_file_path)
        
        # Update the message
        await query.edit_message_text(
            "✅ **Excel Export Successful!**\n\nThe Excel file has been sent to you.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to View Options", callback_data="view_all_medicines")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error exporting medicines to Excel: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error creating Excel export. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to View Options", callback_data="view_all_medicines")]
            ])
        )


async def handle_category_breakdown(query, user_type, db):
    await query.edit_message_text("📊 Feature coming soon: Category breakdown chart.")

async def handle_search_suggestion(query, db):
    """Handle when user clicks on a search suggestion to see medicine details."""
    await query.answer()
    
    try:
        medicine_id = int(query.data.replace("search_suggestion_", ""))
        medicine = db.get_medicine_by_id(medicine_id)
        
        if not medicine:
            await query.edit_message_text(
                "❌ Medicine not found or no longer available.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return
        
        # Calculate expiry status
        try:
            exp_date = datetime.strptime(medicine['expiring_date'], '%Y-%m-%d')
            days_to_expiry = (exp_date - datetime.now()).days
            if days_to_expiry < 0:
                expiry_status = "⚠️ EXPIRED"
            elif days_to_expiry <= 30:
                expiry_status = f"⚠️ Expires in {days_to_expiry} days"
            else:
                expiry_status = "✅ Valid"
        except:
            expiry_status = "❓ Unknown"
        
        stock_status = "✅ In Stock" if medicine['stock_quantity'] > 0 else "❌ Out of Stock"
        
        medicine_text = f"💊 **Medicine Details**\n\n"
        medicine_text += f"**Name:** {medicine['name']}\n"
        medicine_text += f"**Category:** {medicine['therapeutic_category'] or 'N/A'}\n"
        medicine_text += f"**Form:** {medicine['dosage_form'] or 'N/A'}\n"
        medicine_text += f"**Price:** {medicine['price']:.2f} ETB\n"
        medicine_text += f"**Stock:** {medicine['stock_quantity']} units ({stock_status})\n"
        medicine_text += f"**Mfg Date:** {medicine['manufacturing_date']}\n"
        medicine_text += f"**Exp Date:** {medicine['expiring_date']} ({expiry_status})\n\n"
        
        if medicine['stock_quantity'] > 0:
            medicine_text += "🛒 **Available for ordering!**"
        else:
            medicine_text += "❌ **Currently out of stock**"
        
        keyboard = []
        # Add action buttons based on user availability and stock
        user = get_or_create_user(db, query.from_user.id, query.from_user.first_name)
        if user and user['user_type'] == 'customer' and medicine['stock_quantity'] > 0:
            keyboard.append([InlineKeyboardButton("🛒 Add to Cart", callback_data=f"add_medicine_{medicine['id']}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(medicine_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in handle_search_suggestion: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error retrieving medicine details. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )

async def handle_weekly_comparison_excel(query, user_type, db):
    """Generate and send enhanced weekly comparison report as Excel file."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        # Run cleanup first
        await cleanup_old_reports(db)
        
        # Check if enhanced Excel analytics is available
        if not ENHANCED_EXCEL_SUPPORT:
            # Fallback to basic weekly comparison report
            await handle_basic_weekly_comparison_excel(query, user_type, db)
            return
        
        # Track analytics usage activity
        db.track_user_activity(query.from_user.id, 'message')
        
        # Generate the enhanced comparison report
        temp_file_path, filename = generate_enhanced_comparison_report(db)
        
        if not temp_file_path:
            await query.edit_message_text(
                f"❌ Error generating enhanced comparison report: {filename}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Analytics", callback_data="view_stats")]
                ])
            )
            return
        
        # Send the Excel file
        await query.bot.send_document(
            chat_id=query.message.chat_id,
            document=temp_file_path,
            filename=filename,
            caption=f"📊 **Enhanced Weekly Comparison Report**\n\n"
                   f"📅 **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                   f"📈 **Features:**\n"
                   f"• Professional formatting with conditional colors\n"
                   f"• Week-over-week growth analysis\n"
                   f"• Performance trends and insights\n"
                   f"• Visual indicators for performance changes"
        )
        
        # Remove the temporary file
        os.remove(temp_file_path)
        
        # Update the message
        await query.edit_message_text(
            "✅ **Enhanced Weekly Comparison Report Generated!**\n\n"
            "📊 The enhanced Excel report has been sent with:\n"
            "• 📈 Professional week-over-week comparison\n"
            "• 🎨 Conditional formatting for performance trends\n"
            "• 📊 Growth percentages and change indicators\n"
            "• 💡 Key insights and recommendations\n"
            "• 🎯 Performance summary dashboard",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📅 Daily Summary", callback_data="daily_summary_text")],
                [InlineKeyboardButton("📄 Weekly Report (Excel)", callback_data="weekly_excel_report")],
                [InlineKeyboardButton("🔙 Back to Analytics", callback_data="view_stats")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error generating enhanced weekly comparison Excel: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error generating enhanced weekly comparison report. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Analytics", callback_data="view_stats")]
            ])
        )

async def handle_basic_weekly_comparison_excel(query, user_type, db):
    """Generate and send basic weekly comparison report as Excel file (fallback)."""
    try:
        comparison_data = db.get_weekly_comparison_data()
        
        if not comparison_data or len(comparison_data) < 2:
            await query.edit_message_text(
                "📊 Insufficient data for weekly comparison. Need at least 2 weeks of sales data.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Analytics", callback_data="view_stats")]
                ])
            )
            return
        
        # Create DataFrame
        df = pd.DataFrame(comparison_data)
        
        # Rename columns for better readability
        df = df.rename(columns={
            'week_number': 'Week Number',
            'week_start': 'Week Start Date',
            'week_end': 'Week End Date',
            'total_revenue': 'Revenue (ETB)',
            'total_orders': 'Total Orders',
            'unique_customers': 'Unique Customers',
            'avg_order_value': 'Avg Order Value (ETB)'
        })
        
        # Round numerical columns
        df['Revenue (ETB)'] = df['Revenue (ETB)'].fillna(0).round(2)
        df['Avg Order Value (ETB)'] = df['Avg Order Value (ETB)'].fillna(0).round(2)
        
        # Add week-over-week comparison calculations
        df_sorted = df.sort_values('Week Number', ascending=False).reset_index(drop=True)
        
        # Calculate week-over-week changes
        df_sorted['Revenue Change (%)'] = df_sorted['Revenue (ETB)'].pct_change(-1).fillna(0) * 100
        df_sorted['Orders Change (%)'] = df_sorted['Total Orders'].pct_change(-1).fillna(0) * 100
        df_sorted['Customers Change (%)'] = df_sorted['Unique Customers'].pct_change(-1).fillna(0) * 100
        
        # Round percentage changes
        df_sorted['Revenue Change (%)'] = df_sorted['Revenue Change (%)'].round(1)
        df_sorted['Orders Change (%)'] = df_sorted['Orders Change (%)'].round(1)
        df_sorted['Customers Change (%)'] = df_sorted['Customers Change (%)'].round(1)
        
        # Create a temporary Excel file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
            with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
                # Write main comparison data
                df_sorted.to_excel(writer, sheet_name='Weekly Comparison', index=False)
                
                # Create summary insights sheet
                if len(df_sorted) >= 2:
                    latest_week = df_sorted.iloc[0]
                    previous_week = df_sorted.iloc[1]
                    
                    insights = {
                        'Insight': [
                            'Current Week Revenue (ETB)',
                            'Previous Week Revenue (ETB)',
                            'Revenue Change (ETB)',
                            'Revenue Change (%)',
                            'Current Week Orders',
                            'Previous Week Orders',
                            'Orders Change',
                            'Best Week Revenue (ETB)',
                            'Worst Week Revenue (ETB)',
                            'Average Weekly Revenue (ETB)',
                            'Average Weekly Orders'
                        ],
                        'Value': [
                            latest_week['Revenue (ETB)'],
                            previous_week['Revenue (ETB)'],
                            latest_week['Revenue (ETB)'] - previous_week['Revenue (ETB)'],
                            latest_week['Revenue Change (%)'],
                            latest_week['Total Orders'],
                            previous_week['Total Orders'],
                            latest_week['Total Orders'] - previous_week['Total Orders'],
                            df_sorted['Revenue (ETB)'].max(),
                            df_sorted['Revenue (ETB)'].min(),
                            df_sorted['Revenue (ETB)'].mean().round(2),
                            df_sorted['Total Orders'].mean().round(1)
                        ]
                    }
                    insights_df = pd.DataFrame(insights)
                    insights_df.to_excel(writer, sheet_name='Key Insights', index=False)
            
            temp_file_path = temp_file.name
        
        # Format the date/time for the filename
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Calculate comparison summary for caption
        latest_revenue = df_sorted.iloc[0]['Revenue (ETB)']
        revenue_change = df_sorted.iloc[0]['Revenue Change (%)']
        
        # Send the Excel file
        await query.bot.send_document(
            chat_id=query.message.chat_id,
            document=temp_file_path,
            filename=f"Blue_Pharma_Weekly_Comparison_{current_date}.xlsx",
            caption=f"📊 **Weekly Comparison Report**\n\n"
                   f"📅 **Generated:** {current_date}\n"
                   f"📈 **Data Period:** Last {len(comparison_data)} weeks\n"
                   f"💰 **Latest Week Revenue:** {latest_revenue:.2f} ETB\n"
                   f"📊 **Week-over-Week Change:** {revenue_change:+.1f}%"
        )
        
        # Remove the temporary file
        os.remove(temp_file_path)
        
        # Update the message
        await query.edit_message_text(
            "✅ **Weekly Comparison Excel Generated!**\n\n"
            "📊 The Excel report has been sent with:\n"
            "• Week-by-week comparison data\n"
            "• Growth percentages\n"
            "• Key insights and trends",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📅 Daily Summary", callback_data="daily_summary_text")],
                [InlineKeyboardButton("📄 Weekly Report (Excel)", callback_data="weekly_excel_report")],
                [InlineKeyboardButton("🔙 Back to Analytics", callback_data="view_stats")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error generating basic weekly comparison Excel: {e}", exc_info=True)
        raise

async def handle_low_stock_alert(query, user_type, db):
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    low_stock_medicines = db.get_low_stock_medicines()
    if not low_stock_medicines:
        await query.edit_message_text("✅ All medicines are well-stocked. No low stock alerts at this time.")
        return
    
    alert_text = "⚠️ **Low Stock Alert!**\n\nThe following medicines are running low (stock <= 10):\n\n"
    for med in low_stock_medicines:
        alert_text += f"- **{med['name']}**: {med['stock_quantity']} units left\n"
        
    await query.edit_message_text(alert_text, parse_mode='Markdown')

async def handle_remove_medicine_with_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle remove medicine with PIN verification."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db = context.bot_data['db']
    user_info = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if not user_info:
        await query.edit_message_text("Error accessing user information. Please try /start")
        return ConversationHandler.END
    
    user_type = user_info['user_type']
    
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return ConversationHandler.END
    
    await query.edit_message_text(
        "🔐 **PIN Verification Required**\n\n"
        "To remove medicines, please enter the admin PIN:\n"
        "\n"
        "Reply with the PIN to continue.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="manage_stock")]
        ])
    )
    
    # Store the intended action in context
    context.user_data['pin_action'] = 'remove_medicine'
    
    # Return the PIN verification state
    return PIN_VERIFICATION

async def handle_remove_all_with_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle remove all medicines with PIN verification."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db = context.bot_data['db']
    user_info = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if not user_info:
        await query.edit_message_text("Error accessing user information. Please try /start")
        return ConversationHandler.END
    
    user_type = user_info['user_type']
    
    if user_type != 'admin':
        await query.edit_message_text("❌ Access denied. Administrator access required.")
        return ConversationHandler.END
    
    await query.edit_message_text(
        "🔐 **PIN Verification Required**\n\n"
        "⚠️ **CAUTION: You are about to remove ALL medicines!**\n\n"
        "To proceed, please enter the admin PIN:\n"
        "\n"
        "Reply with the PIN to continue.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="manage_stock")]
        ])
    )
    
    # Store the intended action in context
    context.user_data['pin_action'] = 'remove_all_medicines'
    
    # Return the PIN verification state
    return PIN_VERIFICATION

async def handle_toggle_medicine_selection(query):
    await query.edit_message_text("This feature is under development.")

async def handle_confirm_remove_medicines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_type = context.user_data.get('user_type', None)
    db = context.bot_data['db']
    
    if user_type != 'admin':
        await query.edit_message_text("❌ Access denied. Administrator access required.")
        return
    
    try:
        # Get all medicines count before removal
        medicines = db.get_all_medicines()
        medicine_count = len(medicines)
        
        if medicine_count == 0:
            await query.edit_message_text(
                "⚠️ **No Medicines to Remove**\n\n"
                "The inventory is already empty.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Stock Management", callback_data="manage_stock")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return
        
        # Remove all medicines from database
        success = db.remove_all_medicines()
        
        if success:
            await query.edit_message_text(
                f"✅ **All Medicines Removed Successfully!**\n\n"
                f"🗑️ **Removed:** {medicine_count} medicines\n"
                f"📊 **Inventory Status:** Empty\n\n"
                "All medicines have been permanently removed from the inventory.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📝 Add New Medicines", callback_data="add_medicine")],
                    [InlineKeyboardButton("🔙 Back to Stock Management", callback_data="manage_stock")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
        else:
            await query.edit_message_text(
                "❌ **Failed to Remove Medicines**\n\n"
                "An error occurred while removing medicines. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Try Again", callback_data="remove_all_with_pin")],
                    [InlineKeyboardButton("🔙 Back to Stock Management", callback_data="manage_stock")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
        
    except Exception as e:
        logger.error(f"Error removing all medicines: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ **Error Occurred**\n\n"
            "An unexpected error occurred while removing medicines. Please contact support.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Stock Management", callback_data="manage_stock")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )

async def handle_cancel_remove_medicines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("❌ Remove operation cancelled.")

async def handle_category_selection(query, db, context):
    """
    Handle when user selects a category to browse medicines.
    """
    category = query.data.replace("category_", "")
    await show_medicines_in_category(query, db, category, context)

async def show_medicines_in_category(query, db, category, context):
    """
    Show all medicines in the selected category with add to cart options.
    """
    try:
        medicines = db.get_medicines_by_category(category)
        
        if not medicines:
            await query.edit_message_text(
                f"❌ No medicines found in category '{category}'.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="back_to_categories")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return
        
        # Create message header with category info
        emoji = get_category_emoji(category)
        medicines_text = f"{emoji} **{category} Medicines**\n\n"
        medicines_text += f"📋 **Available medicines in this category:**\n\n"
        
        keyboard = []
        
        # Show each medicine with details and add to cart button
        for medicine in medicines:
            stock_status = "✅" if medicine['stock_quantity'] > 0 else "❌"
            medicines_text += f"{stock_status} **{medicine['name']}**\n"
            medicines_text += f"   💰 Price: {medicine['price']:.2f} ETB\n"
            medicines_text += f"   📦 Stock: {medicine['stock_quantity']} units\n"
            
            if medicine['dosage_form']:
                medicines_text += f"   💊 Form: {medicine['dosage_form']}\n"
            
            medicines_text += "\n"
            
            # Add "Add to Cart" button if medicine is in stock
            if medicine['stock_quantity'] > 0:
                keyboard.append([
                    InlineKeyboardButton(
                        f"🛒 Add {medicine['name']}", 
                        callback_data=f"add_medicine_{medicine['id']}"
                    )
                ])
        
        # Add navigation buttons
        keyboard.append([InlineKeyboardButton("🛒 View Cart", callback_data="view_order_cart")])
        keyboard.append([
            InlineKeyboardButton("🔙 Back to Categories", callback_data="back_to_categories"),
            InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(medicines_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error showing medicines in category {category}: {e}", exc_info=True)
        await query.edit_message_text("Error retrieving medicines. Please try again.")

async def handle_add_medicine_to_cart(query, db):
    """
    Handle adding a specific medicine to cart with quantity selection.
    """
    try:
        # Extract medicine ID from callback data
        callback_parts = query.data.split('_')
        if len(callback_parts) < 3:
            logger.error(f"Invalid callback data format: {query.data}")
            await query.edit_message_text(
                "❌ Invalid request format. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")]
                ])
            )
            return
        
        try:
            medicine_id = int(callback_parts[-1])
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse medicine ID from callback data {query.data}: {e}")
            await query.edit_message_text(
                "❌ Invalid medicine selection. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")]
                ])
            )
            return
        
        # Get medicine details with error handling
        medicine = db.get_medicine_by_id(medicine_id)
        
        if not medicine:
            await query.edit_message_text(
                "❌ Medicine not found. It may have been removed or is no longer available.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return
        
        # Check if medicine is active and has stock
        if not medicine.get('is_active', True):
            await query.edit_message_text(
                "❌ This medicine is no longer available.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Category", callback_data=f"back_to_category_{medicine.get('therapeutic_category', 'Unknown')}")],
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")]
                ])
            )
            return
        
        if medicine['stock_quantity'] <= 0:
            await query.edit_message_text(
                f"❌ **{medicine['name']} is currently out of stock.**\n\n"
                f"📦 **Available Stock:** 0 units\n"
                f"💰 **Price:** {medicine['price']:.2f} ETB\n\n"
                f"🔄 **Please check back later or choose a different medicine.**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Category", callback_data=f"back_to_category_{medicine.get('therapeutic_category', 'Unknown')}")],
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")]
                ])
            )
            return
        
        # Show quantity selection interface
        quantity_text = f"🛒 **Adding to Cart**\n\n"
        quantity_text += f"💊 **Medicine:** {medicine['name']}\n"
        quantity_text += f"💰 **Price:** {medicine['price']:.2f} ETB per unit\n"
        quantity_text += f"📦 **Available Stock:** {medicine['stock_quantity']} units\n"
        
        # Add category and form info if available
        if medicine.get('therapeutic_category'):
            category_emoji = get_category_emoji(medicine['therapeutic_category'])
            quantity_text += f"🏷️ **Category:** {category_emoji} {medicine['therapeutic_category']}\n"
        
        if medicine.get('dosage_form'):
            quantity_text += f"💊 **Form:** {medicine['dosage_form']}\n"
        
        quantity_text += f"\n🔢 **Select quantity to add to cart:**"
        
        # Create quantity selection buttons (1-10, or max available)
        max_selectable = min(medicine['stock_quantity'], 10)
        keyboard = []
        
        # Add quantity buttons in rows of 5
        for i in range(1, max_selectable + 1, 5):
            row = []
            for j in range(i, min(i + 5, max_selectable + 1)):
                row.append(InlineKeyboardButton(f"{j}", callback_data=f"set_quantity_{medicine_id}_{j}"))
            keyboard.append(row)
        
        # Add "More" option if stock is higher than 10
        if medicine['stock_quantity'] > 10:
            keyboard.append([InlineKeyboardButton("➡️ More (Custom)", callback_data=f"custom_quantity_{medicine_id}")])
        
        # Add back navigation with proper category handling
        category = medicine.get('therapeutic_category', 'Unknown')
        keyboard.append([
            InlineKeyboardButton("🔙 Back to Category", callback_data=f"back_to_category_{category}"),
            InlineKeyboardButton("🛒 View Cart", callback_data="view_order_cart")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(quantity_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in handle_add_medicine_to_cart: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ An error occurred while processing your request. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )

async def handle_set_quantity(query, db):
    """
    Handle quantity selection and add to cart with robust error handling.
    """
    try:
        # Parse the callback data: set_quantity_medicineId_quantity
        parts = query.data.split('_')
        
        if len(parts) < 4:
            logger.error(f"Invalid callback data format for set_quantity: {query.data}")
            await query.edit_message_text(
                "❌ Invalid request format. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return
        
        try:
            medicine_id = int(parts[2])
            quantity = int(parts[3])
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse medicine ID or quantity from callback data {query.data}: {e}")
            await query.edit_message_text(
                "❌ Invalid medicine or quantity selection. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return
        
        # Validate quantity is positive
        if quantity <= 0:
            logger.error(f"Invalid quantity selected: {quantity}")
            await query.edit_message_text(
                "❌ Invalid quantity selected. Please choose a positive number.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Try Again", callback_data=f"add_medicine_{medicine_id}")],
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")]
                ])
            )
            return
        
        user_id = query.from_user.id
        
        # Get medicine details with error handling
        medicine = db.get_medicine_by_id(medicine_id)
        
        if not medicine:
            await query.edit_message_text(
                "❌ Medicine not found. It may have been removed or is no longer available.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return
        
        # Check if medicine is active
        if not medicine.get('is_active', True):
            await query.edit_message_text(
                f"❌ **{medicine['name']} is no longer available.**\n\n"
                "This medicine has been deactivated and cannot be ordered.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Category", callback_data=f"back_to_category_{medicine.get('therapeutic_category', 'Unknown')}")],
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")]
                ])
            )
            return
        
        # Check stock availability
        if medicine['stock_quantity'] < quantity:
            await query.edit_message_text(
                f"❌ **Insufficient Stock!**\n\n"
                f"💊 **Medicine:** {medicine['name']}\n"
                f"🔢 **Requested Quantity:** {quantity} units\n"
                f"📦 **Available Stock:** {medicine['stock_quantity']} units\n\n"
                f"❌ **We don't have enough stock to fulfill this request.**\n\n"
                f"💡 **Please select a smaller quantity or try again later.**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Choose Different Quantity", callback_data=f"add_medicine_{medicine_id}")],
                    [InlineKeyboardButton("🔙 Back to Category", callback_data=f"back_to_category_{medicine.get('therapeutic_category', 'Unknown')}")],
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")]
                ])
            )
            return
        
        # Check for duplicate items in cart and handle accordingly
        cart = get_user_cart(user_id)
        existing_item = None
        for item in cart:
            if item['medicine_id'] == medicine_id:
                existing_item = item
                break
        
        if existing_item:
            # Check if adding this quantity would exceed stock
            total_quantity = existing_item['quantity'] + quantity
            if total_quantity > medicine['stock_quantity']:
                await query.edit_message_text(
                    f"❌ **Cannot Add - Stock Limit Exceeded!**\n\n"
                    f"💊 **Medicine:** {medicine['name']}\n"
                    f"🛒 **Currently in Cart:** {existing_item['quantity']} units\n"
                    f"➕ **Trying to Add:** {quantity} units\n"
                    f"📊 **Total Requested:** {total_quantity} units\n"
                    f"📦 **Available Stock:** {medicine['stock_quantity']} units\n\n"
                    f"❌ **Adding {quantity} units would exceed available stock.**\n\n"
                    f"💡 **Options:**\n"
                    f"• Choose a smaller quantity\n"
                    f"• Remove the item from cart first\n"
                    f"• Check available stock",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🛒 View Cart", callback_data="view_order_cart")],
                        [InlineKeyboardButton("🔙 Choose Different Quantity", callback_data=f"add_medicine_{medicine_id}")],
                        [InlineKeyboardButton("🔙 Back to Category", callback_data=f"back_to_category_{medicine.get('therapeutic_category', 'Unknown')}")]
                    ])
                )
                return
        
        # Add to cart with error handling
        try:
            add_to_cart_local(user_id, medicine_id, quantity)
        except Exception as cart_error:
            logger.error(f"Error adding to cart: {cart_error}", exc_info=True)
            await query.edit_message_text(
                "❌ Error adding item to cart. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Try Again", callback_data=f"add_medicine_{medicine_id}")],
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")]
                ])
            )
            return
        
        # Calculate totals for confirmation
        try:
            item_total = medicine['price'] * quantity
            cart_total = calculate_cart_total(db, user_id)
        except Exception as calc_error:
            logger.error(f"Error calculating totals: {calc_error}", exc_info=True)
            item_total = 0.0
            cart_total = 0.0
        
        # Get updated cart info for display
        updated_cart = get_user_cart(user_id)
        cart_item_count = len(updated_cart)
        cart_total_items = sum(item['quantity'] for item in updated_cart)
        
        confirmation_text = f"✅ **Added to Cart Successfully!**\n\n"
        confirmation_text += f"💊 **Medicine:** {medicine['name']}\n"
        confirmation_text += f"🔢 **Quantity Added:** {quantity} units\n"
        confirmation_text += f"💰 **Item Total:** {item_total:.2f} ETB\n\n"
        confirmation_text += f"🛒 **Updated Cart Summary:**\n"
        confirmation_text += f"• Total Items: {cart_total_items} units\n"
        confirmation_text += f"• Different Medicines: {cart_item_count}\n"
        confirmation_text += f"• Cart Total: {cart_total:.2f} ETB\n\n"
        
        # Add information about remaining stock
        remaining_stock = medicine['stock_quantity'] - quantity
        if existing_item:
            # Account for previous quantity in cart
            total_in_cart = existing_item['quantity'] + quantity
            remaining_stock = medicine['stock_quantity'] - total_in_cart
            confirmation_text += f"📦 **Total {medicine['name']} in cart:** {total_in_cart} units\n"
        
        confirmation_text += f"📦 **Remaining stock:** {remaining_stock} units"
        
        # Create action buttons with safe category handling
        keyboard = [
            [InlineKeyboardButton("🛒 View Full Cart", callback_data="view_order_cart")],
            [InlineKeyboardButton("✅ Proceed to Checkout", callback_data="proceed_checkout")]
        ]
        
        # Add category navigation if category is available
        category = medicine.get('therapeutic_category')
        if category:
            keyboard.append([
                InlineKeyboardButton(f"➡️ Continue in {category}", callback_data=f"back_to_category_{category}"),
                InlineKeyboardButton("🔙 All Categories", callback_data="place_order")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(confirmation_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in handle_set_quantity: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ An error occurred while adding item to cart. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )

async def handle_confirm_add_quantity(query, db):
    """
    Handle confirmation of adding item with quantity to cart.
    """
    # This would be used for custom quantity input
    # For now, we'll implement a simple version
    await query.edit_message_text("Custom quantity selection coming soon!")

# --- PIN Verification and Medicine Removal Functions ---
async def verify_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PIN verification for protected operations."""
    pin_input = update.message.text.strip()
    db = context.bot_data['db']
    stored_pin = db.get_contact_setting('admin_pin') if hasattr(db, 'get_contact_setting') else None
    correct_pin = stored_pin or "4321"
    
    if pin_input == correct_pin:
        # PIN is correct, proceed with the intended action
        action = context.user_data.get('pin_action', None)
        
        if action == 'remove_medicine':
            await show_medicines_for_removal(update, context)
            return REMOVE_SELECTION
        elif action == 'remove_all_medicines':
            await show_remove_all_confirmation(update, context)
            return REMOVE_ALL_PIN_VERIFICATION
        else:
            await update.message.reply_text("❌ Invalid action. Please start over.")
            return ConversationHandler.END
    else:
        # Incorrect PIN
        await update.message.reply_text(
            "❌ **Incorrect PIN!**\n\n"
            "Access denied. Please try again or cancel.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="manage_stock")]
            ])
        )
        return PIN_VERIFICATION

async def show_medicines_for_removal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of medicines that can be removed."""
    db = context.bot_data['db']
    medicines = db.get_all_medicines()
    
    if not medicines:
        await update.message.reply_text(
            "❌ No medicines available to remove.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Stock Management", callback_data="manage_stock")]
            ])
        )
        return ConversationHandler.END
    
    removal_text = "🗑️ **Select Medicine to Remove**\n\n"
    removal_text += "⚠️ **Warning:** This action will deactivate the selected medicine.\n\n"
    removal_text += "📋 **Available medicines:**\n\n"
    
    keyboard = []
    
    # Show up to 10 medicines to avoid message length issues
    for i, medicine in enumerate(medicines[:10]):
        removal_text += f"{i+1}. **{medicine['name']}** - Stock: {medicine['stock_quantity']}\n"
        keyboard.append([
            InlineKeyboardButton(
                f"🗑️ Remove {medicine['name']}", 
                callback_data=f"confirm_remove_med_{medicine['id']}"
            )
        ])
    
    if len(medicines) > 10:
        removal_text += f"\n... and {len(medicines) - 10} more medicines.\n"
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="manage_stock")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(removal_text, parse_mode='Markdown', reply_markup=reply_markup)

async def show_remove_all_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show final confirmation for removing all medicines."""
    db = context.bot_data['db']
    medicines_count = len(db.get_all_medicines())
    
    confirmation_text = f"⚠️ **FINAL CONFIRMATION**\n\n"
    confirmation_text += f"🚨 **You are about to remove ALL {medicines_count} medicines!**\n\n"
    confirmation_text += f"This action will:\n"
    confirmation_text += f"• Deactivate all {medicines_count} medicine records\n"
    confirmation_text += f"• Make them unavailable for ordering\n"
    confirmation_text += f"• Cannot be easily undone\n\n"
    confirmation_text += f"**Are you absolutely sure you want to proceed?**"
    
    keyboard = [
        [InlineKeyboardButton("✅ Yes, Remove All Medicines", callback_data="confirm_remove_all_final")],
        [InlineKeyboardButton("❌ No, Cancel", callback_data="manage_stock")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(confirmation_text, parse_mode='Markdown', reply_markup=reply_markup)

async def wrapper_handle_manage_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper function for handle_manage_stock to use in conversation handlers."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db = context.bot_data['db']
    user_info = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if not user_info:
        await query.edit_message_text("Error accessing user information. Please try /start")
        return ConversationHandler.END
    
    user_type = user_info['user_type']
    
    # Call the original handle_manage_stock with correct parameters
    await handle_manage_stock(query, user_type, db)
    
    # End the conversation and return to normal button handling
    return ConversationHandler.END

async def handle_confirm_remove_single_medicine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confirmation and removal of a single medicine."""
    query = update.callback_query
    await query.answer()
    db = context.bot_data['db']
    
    try:
        # Extract medicine ID from callback data
        medicine_id = int(query.data.replace("confirm_remove_med_", ""))
        
        # Get medicine details before removal
        medicine = db.get_medicine_by_id(medicine_id)
        
        if not medicine:
            await query.edit_message_text(
                "❌ Medicine not found. It may have already been removed.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Stock Management", callback_data="manage_stock")]
                ])
            )
            return
        
        # Remove the medicine
        success = db.remove_medicine(medicine_id)
        
        if success:
            await query.edit_message_text(
                f"✅ **Medicine Removed Successfully!**\n\n"
                f"**Medicine:** {medicine['name']}\n"
                f"**Category:** {medicine['therapeutic_category']}\n"
                f"**Stock Removed:** {medicine['stock_quantity']} units\n\n"
                "The medicine has been deactivated and is no longer available for ordering.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Stock Management", callback_data="manage_stock")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            logger.info(f"Medicine {medicine['name']} (ID: {medicine_id}) removed by user {query.from_user.id}")
        else:
            await query.edit_message_text(
                "❌ Failed to remove medicine. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Stock Management", callback_data="manage_stock")]
                ])
            )
    
    except Exception as e:
        logger.error(f"Error removing single medicine: {e}", exc_info=True)
        await query.edit_message_text("❌ An error occurred while removing the medicine.")

async def handle_confirm_remove_all_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle final confirmation and removal of all medicines."""
    query = update.callback_query
    await query.answer()
    db = context.bot_data['db']
    
    try:
        # Remove all medicines
        removed_count = db.remove_all_medicines()
        
        if removed_count > 0:
            await query.edit_message_text(
                f"✅ **All Medicines Removed Successfully!**\n\n"
                f"**Total medicines deactivated:** {removed_count}\n\n"
                "All medicine records have been deactivated and are no longer available for ordering.\n\n"
                "⚠️ **Note:** You can still view historical data, but no medicines are available for new orders.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Stock Management", callback_data="manage_stock")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            logger.warning(f"ALL MEDICINES REMOVED by user {query.from_user.id} - {removed_count} medicines deactivated")
        else:
            await query.edit_message_text(
                "❌ No medicines were found to remove or an error occurred.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Stock Management", callback_data="manage_stock")]
                ])
            )
    
    except Exception as e:
        logger.error(f"Error removing all medicines: {e}", exc_info=True)
        await query.edit_message_text("❌ An error occurred while removing medicines.")

# --- New Functionality Handlers ---
async def handle_update_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the simplified stock update conversation."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db = context.bot_data['db']
    user_info = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if not user_info or user_info['user_type'] not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return ConversationHandler.END
    
    await query.edit_message_text(
        "📊 **Update Medicine Stock**\n\n"
        "🔍 **Step 1: Search Medicine**\n\n"
        "Please enter the name of the medicine you want to update stock for (or part of the name):\n\n"
        "📝 **Examples:**\n"
        "• Paracetamol\n"
        "• Para\n"
        "• Aspirin"
    )
    
    return STOCK_UPDATE_SEARCH

async def handle_enhanced_stats(query, user_type, db):
    """Handle Enhanced Statistics main menu."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    stats_text = """
📈 **Enhanced Statistics Dashboard**

📊 **Choose the type of report you want to view:**

1️⃣ **Daily Summary** - Today's sales overview
2️⃣ **Monthly Analysis** - Multi-month sales trends
3️⃣ **Category Breakdown** - Sales by therapeutic category
4️⃣ **Weekly Comparison** - Week-over-week analysis
"""
    keyboard = [
        [InlineKeyboardButton("📅 Daily Summary", callback_data="view_stats")],
        [InlineKeyboardButton("📆 Monthly Analysis", callback_data="monthly_stats")],
        [InlineKeyboardButton("📊 Category Breakdown", callback_data="category_stats")],
        [InlineKeyboardButton("📈 Weekly Comparison", callback_data="weekly_comparison")],
        [InlineKeyboardButton("📄 Export Weekly Excel", callback_data="weekly_sales_excel")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(stats_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_start_stock_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the stock update conversation."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db = context.bot_data['db']
    user_info = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if not user_info or user_info['user_type'] not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return ConversationHandler.END
    
    await query.edit_message_text(
        "🔍 **Stock Update - Search Medicine**\n\n"
        "Please enter the name of the medicine you want to update (or part of the name):\n\n"
        "Example: *Paracetamol* or *Para*"
    )
    
    return STOCK_UPDATE_SEARCH

async def handle_stock_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle medicine search for stock update."""
    search_term = update.message.text.strip()
    db = context.bot_data['db']
    
    medicines = db.get_medicine_by_name(search_term)
    
    if not medicines:
        # Try fuzzy search to find similar medicines
        similar_medicines = find_similar_medicines(db, search_term, threshold=0.35, max_results=5)
        
        if similar_medicines:
            # Found similar medicines - show suggestions for stock update
            suggestions_text = f"❌ **No exact matches found for '{search_term}'**\n\n"
            suggestions_text += f"🤖 **Stock Update Assistant - Did you mean?**\n\n"
            suggestions_text += f"💡 Here are some similar medicines:\n\n"
            
            keyboard = []
            for i, medicine in enumerate(similar_medicines, 1):
                similarity_percentage = int(medicine['similarity_score'] * 100)
                stock_emoji = "✅" if medicine['stock_quantity'] > 0 else "❌"
                suggestions_text += f"{i}. {stock_emoji} **{medicine['name']}** ({similarity_percentage}% match)\n"
                suggestions_text += f"   📦 Current Stock: {medicine['stock_quantity']} units\n"
                suggestions_text += f"   💰 Price: {medicine['price']:.2f} ETB\n"
                if medicine['therapeutic_category']:
                    suggestions_text += f"   🏷️ {medicine['therapeutic_category']}\n"
                suggestions_text += "\n"
                
                # Add button to select this medicine for stock update
                keyboard.append([
                    InlineKeyboardButton(
                        f"📦 Update Stock: {medicine['name']}", 
                        callback_data=f"update_stock_medicine_{medicine['id']}"
                    )
                ])
            
            suggestions_text += f"🔍 **Tip:** Click a button above to update stock for a suggested medicine."
            
            keyboard.append([InlineKeyboardButton("🔍 Try Different Search", callback_data="start_stock_update")])
            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="update_stock")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(suggestions_text, parse_mode='Markdown', reply_markup=reply_markup)
            return ConversationHandler.END
        else:
            # No similar medicines found either
            await update.message.reply_text(
                f"❌ **Medicine not found: '{search_term}'**\n\n"
                "🔍 **Search Tips:**\n"
                "• Check spelling\n"
                "• Try shorter search terms\n"
                "• Use generic names\n"
                "• Try common abbreviations\n\n"
                "Please try again with a different search term:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Try Again", callback_data="start_stock_update")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="update_stock")]
                ])
            )
        return STOCK_UPDATE_SEARCH
    
    if len(medicines) == 1:
        # Only one medicine found, proceed directly
        medicine = medicines[0]
        context.user_data['selected_medicine_id'] = medicine['id']
        
        await update.message.reply_text(
            f"💊 **Medicine Found:** {medicine['name']}\n"
            f"📦 **Current Stock:** {medicine['stock_quantity']} units\n"
            f"💰 **Price:** {medicine['price']:.2f} ETB\n\n"
            "📝 **Enter new stock quantity:**\n\n"
            "You can enter any non-negative number."
        )
        return STOCK_UPDATE_QUANTITY
    else:
        # Multiple medicines found, let user choose
        search_text = f"🔍 **Search Results for '{search_term}'**\n\n"
        search_text += "📋 **Multiple medicines found. Select one to update:**\n\n"
        
        keyboard = []
        for i, medicine in enumerate(medicines[:10]):  # Limit to 10 results
            search_text += f"{i+1}. **{medicine['name']}** - Stock: {medicine['stock_quantity']}\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"📦 Update {medicine['name']}", 
                    callback_data=f"update_stock_medicine_{medicine['id']}"
                )
            ])
        
        if len(medicines) > 10:
            search_text += f"\n... and {len(medicines) - 10} more results.\n"
            search_text += "Please refine your search term.\n"
        
        keyboard.append([InlineKeyboardButton("🔍 New Search", callback_data="start_stock_update")])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="update_stock")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(search_text, parse_mode='Markdown', reply_markup=reply_markup)
        return ConversationHandler.END

async def handle_select_medicine_for_stock_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle selection of a specific medicine for stock update."""
    query = update.callback_query
    await query.answer()
    
    db = context.bot_data['db']
    medicine_id = int(query.data.replace("update_stock_medicine_", ""))
    medicine = db.get_medicine_by_id(medicine_id)
    
    if not medicine:
        await query.edit_message_text("❌ Medicine not found. Please try again.")
        return
    
    context.user_data['selected_medicine_id'] = medicine_id
    
    await query.edit_message_text(
        f"💊 **Selected Medicine:** {medicine['name']}\n"
        f"📦 **Current Stock:** {medicine['stock_quantity']} units\n"
        f"💰 **Price:** {medicine['price']:.2f} ETB\n\n"
        "📝 **Enter new stock quantity:**\n\n"
        "Reply with the new quantity (any non-negative number)."
    )
    
    return STOCK_UPDATE_QUANTITY

async def handle_stock_quantity_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new stock quantity input."""
    try:
        new_quantity = int(update.message.text.strip())
        if new_quantity < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid quantity. Please enter a non-negative integer:\n\n"
            "Examples: 0, 50, 100, 500"
        )
        return STOCK_UPDATE_QUANTITY
    
    context.user_data['new_stock_quantity'] = new_quantity
    
    await update.message.reply_text(
        "📝 **Optional: Update Reason**\n\n"
        "Please provide a reason for this stock update (optional):\n\n"
        "Examples:\n"
        "• New shipment received\n"
        "• Stock correction\n"
        "• Damaged goods removed\n"
        "• Inventory adjustment\n\n"
        "Or type 'skip' to proceed without a reason."
    )
    
    return STOCK_UPDATE_REASON

async def handle_stock_update_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle stock update reason and complete the update."""
    reason = update.message.text.strip()
    if reason.lower() == 'skip':
        reason = None
    
    db = context.bot_data['db']
    medicine_id = context.user_data['selected_medicine_id']
    new_quantity = context.user_data['new_stock_quantity']
    
    # Get medicine details for confirmation
    medicine = db.get_medicine_by_id(medicine_id)
    old_quantity = medicine['stock_quantity']
    
    # Update the stock
    success, message = db.update_medicine_stock(medicine_id, new_quantity, reason)
    
    if success:
        await update.message.reply_text(
            f"✅ **Stock Updated Successfully!**\n\n"
            f"💊 **Medicine:** {medicine['name']}\n"
            f"📦 **Previous Stock:** {old_quantity} units\n"
            f"📦 **New Stock:** {new_quantity} units\n"
            f"📈 **Change:** {new_quantity - old_quantity:+d} units\n"
            f"📝 **Reason:** {reason or 'Not specified'}\n\n"
            "Use /start to return to the main menu.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Update Another Medicine", callback_data="start_stock_update")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
    else:
        await update.message.reply_text(
            f"❌ **Failed to update stock:** {message}\n\n"
            "Please try again."
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def handle_monthly_stats(query, user_type, db):
    """Show monthly sales statistics."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        monthly_data = db.get_monthly_sales_summary(6)
        
        if not monthly_data:
            await query.edit_message_text(
                "📊 No sales data available for monthly analysis.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Enhanced Stats", callback_data="enhanced_stats")]
                ])
            )
            return
        
        stats_text = "📆 **Monthly Sales Analysis**\n\n"
        
        total_revenue = 0
        total_orders = 0
        
        for month_data in monthly_data:
            month = month_data['month']
            revenue = month_data['total_revenue'] or 0
            orders = month_data['total_orders'] or 0
            customers = month_data['unique_customers'] or 0
            
            total_revenue += revenue
            total_orders += orders
            
            stats_text += f"**{month}**\n"
            stats_text += f"• Revenue: {revenue:.2f} ETB\n"
            stats_text += f"• Orders: {orders}\n"
            stats_text += f"• Customers: {customers}\n"
            stats_text += f"• Avg Order: {(revenue/orders):.2f} ETB\n\n" if orders > 0 else "• Avg Order: 0.00 ETB\n\n"
        
        stats_text += f"📊 **Summary ({len(monthly_data)} months):**\n"
        stats_text += f"• Total Revenue: {total_revenue:.2f} ETB\n"
        stats_text += f"• Total Orders: {total_orders}\n"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Enhanced Stats", callback_data="enhanced_stats")],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(stats_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in monthly stats: {e}", exc_info=True)
        await query.edit_message_text("Error retrieving monthly statistics.")

async def handle_category_stats(query, user_type, db):
    """Show category breakdown statistics."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        category_data = db.get_category_sales_breakdown()
        
        if not category_data:
            await query.edit_message_text(
                "📊 No sales data available for category analysis.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Enhanced Stats", callback_data="enhanced_stats")]
                ])
            )
            return
        
        stats_text = "📊 **Sales by Therapeutic Category**\n\n"
        
        total_revenue = sum(cat['total_revenue'] or 0 for cat in category_data)
        
        for i, category in enumerate(category_data[:10], 1):  # Top 10 categories
            cat_name = category['therapeutic_category'] or 'Unknown'
            revenue = category['total_revenue'] or 0
            quantity = category['total_quantity_sold'] or 0
            orders = category['orders_containing_category'] or 0
            percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0
            
            emoji = get_category_emoji(cat_name)
            stats_text += f"**{i}. {emoji} {cat_name}**\n"
            stats_text += f"• Revenue: {revenue:.2f} ETB ({percentage:.1f}%)\n"
            stats_text += f"• Quantity Sold: {quantity} units\n"
            stats_text += f"• Orders: {orders}\n\n"
        
        if len(category_data) > 10:
            stats_text += f"... and {len(category_data) - 10} more categories.\n\n"
        
        stats_text += f"💰 **Total Revenue:** {total_revenue:.2f} ETB"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Enhanced Stats", callback_data="enhanced_stats")],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(stats_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in category stats: {e}", exc_info=True)
        await query.edit_message_text("Error retrieving category statistics.")

async def handle_price_update_percentage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle percentage-based price updates."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db = context.bot_data['db']
    user_info = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if not user_info or user_info['user_type'] not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return ConversationHandler.END
    
    context.user_data['price_update_method'] = 'percentage'
    
    await query.edit_message_text(
        "📊 **Price Update by Percentage**\n\n"
        "Enter the percentage change for prices:\n\n"
        "📈 **Examples:**\n"
        "• +15 (increase prices by 15%)\n"
        "• -10 (decrease prices by 10%)\n"
        "• +5.5 (increase prices by 5.5%)\n\n"
        "⚠️ **Note:** This will affect ALL medicines or selected category.\n\n"
        "📝 **Enter percentage (with + or - sign):**"
    )
    
    return PRICE_UPDATE_VALUE

async def handle_price_percentage_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle percentage input for price updates."""
    try:
        percentage_str = update.message.text.strip()
        
        # Parse percentage with optional + or - sign
        if percentage_str.startswith('+'):
            percentage = float(percentage_str[1:])
        elif percentage_str.startswith('-'):
            percentage = -float(percentage_str[1:])
        else:
            percentage = float(percentage_str)
        
        # Validate reasonable percentage range
        if percentage < -99 or percentage > 1000:
            await update.message.reply_text(
                "❌ Invalid percentage range.\n\n"
                "⚠️ Please enter a percentage between -99% and +1000%:\n\n"
                "Examples: +15, -10, +5.5"
            )
            return PRICE_UPDATE_VALUE
        
        context.user_data['percentage'] = percentage
        
        # Show category selection or apply to all
        db = context.bot_data['db']
        categories = db.get_medicine_categories()
        
        category_text = f"🎯 **Price Update: {percentage:+.1f}%**\n\n"
        category_text += f"📈 **Choose scope for price update:**\n\n"
        category_text += f"📊 All prices will be {'increased' if percentage > 0 else 'decreased'} by {abs(percentage):.1f}%\n\n"
        category_text += f"📅 **Options:**\n"
        category_text += f"• Apply to ALL medicines\n"
        category_text += f"• Apply to specific category only\n"
        
        keyboard = [
            [InlineKeyboardButton(f"🔄 Update ALL Medicines ({percentage:+.1f}%)", callback_data="apply_percentage_all")]
        ]
        
        # Add category options
        if categories:
            keyboard.append([InlineKeyboardButton("📂 Choose Specific Category", callback_data="choose_category_percentage")])
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="update_prices")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(category_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        return PRICE_MEDICINE_SELECTION
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid percentage format.\n\n"
            "📈 Please enter a valid percentage:\n\n"
            "Examples:\n"
            "• +15 (increase by 15%)\n"
            "• -10 (decrease by 10%)\n"
            "• 5.5 (increase by 5.5%)\n"
            "• -2.3 (decrease by 2.3%)"
        )
        return PRICE_UPDATE_VALUE

async def handle_apply_percentage_all(query, db, context):
    """Apply percentage price update to all medicines."""
    await query.answer()
    
    percentage = context.user_data.get('percentage', 0)
    
    try:
        updated_count = db.bulk_update_prices_by_percentage(percentage)
        
        await query.edit_message_text(
            f"✅ **Price Update Complete!**\n\n"
            f"📈 **Percentage Applied:** {percentage:+.1f}%\n"
            f"📊 **Medicines Updated:** {updated_count}\n"
            f"📅 **Scope:** All active medicines\n\n"
            f"All medicine prices have been {'increased' if percentage > 0 else 'decreased'} by {abs(percentage):.1f}%.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Update More Prices", callback_data="update_prices")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
        
        logger.info(f"Bulk price update applied: {percentage:+.1f}% to {updated_count} medicines by user {query.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error applying percentage price update: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error updating prices. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Price Updates", callback_data="update_prices")]
            ])
        )

async def handle_choose_category_percentage(query, db, context):
    """Show category selection for percentage price update."""
    await query.answer()
    
    categories = db.get_medicine_categories()
    percentage = context.user_data.get('percentage', 0)
    
    if not categories:
        await query.edit_message_text(
            "❌ No categories available for price update.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Price Updates", callback_data="update_prices")]
            ])
        )
        return
    
    category_text = f"📂 **Select Category for {percentage:+.1f}% Price Update**\n\n"
    category_text += f"📊 Choose a therapeutic category to update:\n\n"
    
    keyboard = []
    
    # Add category buttons
    for category in categories:
        emoji = get_category_emoji(category)
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {category}", 
                callback_data=f"apply_percentage_category_{category}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="update_prices")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(category_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_apply_percentage_category(query, db, context):
    """Apply percentage price update to specific category."""
    await query.answer()
    
    category = query.data.replace("apply_percentage_category_", "")
    percentage = context.user_data.get('percentage', 0)
    
    try:
        updated_count = db.bulk_update_prices_by_percentage(percentage, category)
        
        emoji = get_category_emoji(category)
        await query.edit_message_text(
            f"✅ **Category Price Update Complete!**\n\n"
            f"📂 **Category:** {emoji} {category}\n"
            f"📈 **Percentage Applied:** {percentage:+.1f}%\n"
            f"📊 **Medicines Updated:** {updated_count}\n\n"
            f"All medicines in the '{category}' category have been {'increased' if percentage > 0 else 'decreased'} by {abs(percentage):.1f}%.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Update More Prices", callback_data="update_prices")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
        
        logger.info(f"Category price update applied: {percentage:+.1f}% to {updated_count} medicines in '{category}' by user {query.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error applying category percentage price update: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error updating prices. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Price Updates", callback_data="update_prices")]
            ])
        )

async def handle_price_update_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle fixed amount-based price updates."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db = context.bot_data['db']
    user_info = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if not user_info or user_info['user_type'] not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return ConversationHandler.END
    
    context.user_data['price_update_method'] = 'amount'
    
    await query.edit_message_text(
        "💰 **Price Update by Fixed Amount**\n\n"
        "Enter the amount to add or subtract from prices:\n\n"
        "📈 **Examples:**\n"
        "• +10 (increase all prices by 10 ETB)\n"
        "• -5 (decrease all prices by 5 ETB)\n"
        "• +2.50 (increase all prices by 2.50 ETB)\n\n"
        "⚠️ **Note:** This will affect ALL medicines or selected category.\n"
        "⚠️ Prices will not go below 0.01 ETB.\n\n"
        "📝 **Enter amount in ETB (with + or - sign):**"
    )
    
    return PRICE_UPDATE_VALUE

async def handle_price_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle amount input for price updates."""
    try:
        amount_str = update.message.text.strip()
        
        # Parse amount with optional + or - sign
        if amount_str.startswith('+'):
            amount = float(amount_str[1:])
        elif amount_str.startswith('-'):
            amount = -float(amount_str[1:])
        else:
            amount = float(amount_str)
        
        # Validate reasonable amount range
        if amount < -1000 or amount > 1000:
            await update.message.reply_text(
                "❌ Invalid amount range.\n\n"
                "⚠️ Please enter an amount between -1000 and +1000 ETB:\n\n"
                "Examples: +10, -5, +2.50"
            )
            return PRICE_UPDATE_VALUE
        
        context.user_data['amount'] = amount
        
        # Show category selection or apply to all
        db = context.bot_data['db']
        categories = db.get_medicine_categories()
        
        category_text = f"🎯 **Price Update: {amount:+.2f} ETB**\n\n"
        category_text += f"📈 **Choose scope for price update:**\n\n"
        category_text += f"💰 All prices will be {'increased' if amount > 0 else 'decreased'} by {abs(amount):.2f} ETB\n\n"
        category_text += f"📅 **Options:**\n"
        category_text += f"• Apply to ALL medicines\n"
        category_text += f"• Apply to specific category only\n"
        
        keyboard = [
            [InlineKeyboardButton(f"🔄 Update ALL Medicines ({amount:+.2f} ETB)", callback_data="apply_amount_all")]
        ]
        
        # Add category options
        if categories:
            keyboard.append([InlineKeyboardButton("📂 Choose Specific Category", callback_data="choose_category_amount")])
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="update_prices")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(category_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        return PRICE_MEDICINE_SELECTION
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount format.\n\n"
            "💰 Please enter a valid amount in ETB:\n\n"
            "Examples:\n"
            "• +10 (increase by 10 ETB)\n"
            "• -5 (decrease by 5 ETB)\n"
            "• 2.50 (increase by 2.50 ETB)\n"
            "• -1.75 (decrease by 1.75 ETB)"
        )
        return PRICE_UPDATE_VALUE

async def handle_apply_amount_all(query, db, context):
    """Apply fixed amount price update to all medicines."""
    await query.answer()
    
    amount = context.user_data.get('amount', 0)
    
    try:
        updated_count = db.bulk_update_prices_by_amount(amount)
        
        await query.edit_message_text(
            f"✅ **Price Update Complete!**\n\n"
            f"💰 **Amount Applied:** {amount:+.2f} ETB\n"
            f"📊 **Medicines Updated:** {updated_count}\n"
            f"📅 **Scope:** All active medicines\n\n"
            f"All medicine prices have been {'increased' if amount > 0 else 'decreased'} by {abs(amount):.2f} ETB.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Update More Prices", callback_data="update_prices")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
        
        logger.info(f"Bulk price update applied: {amount:+.2f} ETB to {updated_count} medicines by user {query.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error applying amount price update: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error updating prices. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Price Updates", callback_data="update_prices")]
            ])
        )

async def handle_choose_category_amount(query, db, context):
    """Show category selection for amount price update."""
    await query.answer()
    
    categories = db.get_medicine_categories()
    amount = context.user_data.get('amount', 0)
    
    if not categories:
        await query.edit_message_text(
            "❌ No categories available for price update.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Price Updates", callback_data="update_prices")]
            ])
        )
        return
    
    category_text = f"📂 **Select Category for {amount:+.2f} ETB Price Update**\n\n"
    category_text += f"📊 Choose a therapeutic category to update:\n\n"
    
    keyboard = []
    
    # Add category buttons
    for category in categories:
        emoji = get_category_emoji(category)
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {category}", 
                callback_data=f"apply_amount_category_{category}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="update_prices")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(category_text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_apply_amount_category(query, db, context):
    """Apply fixed amount price update to specific category."""
    await query.answer()
    
    category = query.data.replace("apply_amount_category_", "")
    amount = context.user_data.get('amount', 0)
    
    try:
        updated_count = db.bulk_update_prices_by_amount(amount, category)
        
        emoji = get_category_emoji(category)
        await query.edit_message_text(
            f"✅ **Category Price Update Complete!**\n\n"
            f"📂 **Category:** {emoji} {category}\n"
            f"💰 **Amount Applied:** {amount:+.2f} ETB\n"
            f"📊 **Medicines Updated:** {updated_count}\n\n"
            f"All medicines in the '{category}' category have been {'increased' if amount > 0 else 'decreased'} by {abs(amount):.2f} ETB.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Update More Prices", callback_data="update_prices")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
        
        logger.info(f"Category price update applied: {amount:+.2f} ETB to {updated_count} medicines in '{category}' by user {query.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error applying category amount price update: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error updating prices. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Price Updates", callback_data="update_prices")]
            ])
        )

# --- New Analytics Handlers ---
async def handle_daily_summary_text(query, user_type, db):
    """Handle daily summary text analytics."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        # Run cleanup first
        await cleanup_old_reports(db)
        
        daily_summary = db.get_daily_sales_summary()
        current_date = datetime.now().strftime('%B %d, %Y')
        
        summary_text = f"📅 **Daily Sales Summary**\n"
        summary_text += f"📆 **Date:** {current_date}\n\n"
        
        summary_text += f"📊 **Today's Performance:**\n"
        summary_text += f"• 📋 Total Orders: {daily_summary['total_orders']}\n"
        summary_text += f"• 📦 Items Sold: {daily_summary['total_items_sold']}\n"
        summary_text += f"• 💰 Revenue: {daily_summary['total_revenue']:.2f} ETB\n"
        summary_text += f"• 👥 Customers Served: {daily_summary['total_customers']}\n"
        summary_text += f"• 📈 Avg Order Value: {daily_summary['avg_order_value']:.2f} ETB\n\n"
        
        summary_text += f"🏆 **Top Performers:**\n"
        summary_text += f"• 💊 Best Medicine: {daily_summary['top_medicine']}\n"
        summary_text += f"• 🏷️ Top Category: {daily_summary['top_category']}\n\n"
        
        if daily_summary['total_orders'] == 0:
            summary_text += "📝 **Note:** No orders recorded today."
        else:
            summary_text += f"📝 **Performance:** {'Excellent' if daily_summary['total_orders'] > 10 else 'Good' if daily_summary['total_orders'] > 5 else 'Slow'} sales day."
        
        keyboard = [
            [InlineKeyboardButton("📄 Weekly Report (Excel)", callback_data="weekly_excel_report")],
            [InlineKeyboardButton("📊 Weekly Comparison (Excel)", callback_data="weekly_comparison_excel")],
            [InlineKeyboardButton("🔙 Back to Analytics", callback_data="view_stats")],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(summary_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in daily summary: {e}", exc_info=True)
        await query.edit_message_text("Error retrieving daily summary.")

async def handle_weekly_excel_report(query, user_type, db, context):
    """Generate and send enhanced weekly analytics report as Excel file."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        # Run cleanup first
        await cleanup_old_reports(db)
        
        # Check if enhanced Excel analytics is available
        if not ENHANCED_EXCEL_SUPPORT:
            # Fallback to basic Excel report
            await handle_basic_weekly_excel_report(query, user_type, db, context)
            return
        
        # Track analytics usage activity
        db.track_user_activity(query.from_user.id, 'message')
        
        # Generate the enhanced report
        temp_file_path, filename = generate_enhanced_weekly_report(db)
        
        if not temp_file_path:
            await query.edit_message_text(
                f"❌ Error generating enhanced weekly report: {filename}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Analytics", callback_data="view_stats")]
                ])
            )
            return
        
        # Send the Excel file
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=temp_file_path,
            filename=filename,
            caption=f"📄 **Enhanced Weekly Analytics Report**\n\n"
                   f"📅 **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                   f"📊 **Features:**\n"
                   f"• Professional formatting with charts\n"
                   f"• Dashboard with KPIs and visualizations\n"
                   f"• Performance summary and insights\n"
                   f"• Trend analysis and recommendations"
        )
        
        # Remove the temporary file
        os.remove(temp_file_path)
        
        # Update the message
        await query.edit_message_text(
            "✅ **Enhanced Weekly Analytics Report Generated!**\n\n"
            "📄 The enhanced Excel report has been sent with:\n"
            "• 📊 Professional formatting and tables\n"
            "• 📈 Interactive charts and visualizations\n"
            "• 🎯 Dashboard with key performance indicators\n"
            "• 💡 Performance insights and recommendations\n"
            "• 📋 Detailed weekly breakdown with trends",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Weekly Comparison (Excel)", callback_data="weekly_comparison_excel")],
                [InlineKeyboardButton("🔙 Back to Analytics", callback_data="view_stats")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error generating enhanced weekly Excel report: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error generating enhanced weekly report. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Analytics", callback_data="view_stats")]
            ])
        )

async def handle_basic_weekly_excel_report(query, user_type, db, context):
    """Generate and send basic weekly sales report as Excel file (fallback)."""
    try:
        weekly_data = db.get_weekly_sales_data(8)  # Get 8 weeks of data
        
        if not weekly_data:
            await query.edit_message_text(
                "📊 No weekly sales data available for report generation.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Analytics", callback_data="view_stats")]
                ])
            )
            return
        
        # Create DataFrame
        df = pd.DataFrame(weekly_data)
        
        # Rename columns for better readability
        df = df.rename(columns={
            'week': 'Week (Year-Week)',
            'total_revenue': 'Revenue (ETB)',
            'total_orders': 'Total Orders'
        })
        
        # Add calculated columns
        df['Average Order Value (ETB)'] = df['Revenue (ETB)'] / df['Total Orders']
        df['Average Order Value (ETB)'] = df['Average Order Value (ETB)'].fillna(0).round(2)
        
        # Create a temporary Excel file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
            # Create Excel writer with multiple sheets
            with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
                # Write weekly summary
                df.to_excel(writer, sheet_name='Weekly Summary', index=False)
                
                # Add summary statistics sheet
                summary_stats = {
                    'Metric': [
                        'Total Revenue (ETB)',
                        'Total Orders',
                        'Average Weekly Revenue (ETB)',
                        'Average Weekly Orders',
                        'Highest Weekly Revenue (ETB)',
                        'Most Orders in a Week'
                    ],
                    'Value': [
                        df['Revenue (ETB)'].sum(),
                        df['Total Orders'].sum(),
                        df['Revenue (ETB)'].mean().round(2),
                        df['Total Orders'].mean().round(1),
                        df['Revenue (ETB)'].max(),
                        df['Total Orders'].max()
                    ]
                }
                summary_df = pd.DataFrame(summary_stats)
                summary_df.to_excel(writer, sheet_name='Summary Statistics', index=False)
            
            temp_file_path = temp_file.name
        
        # Format the date/time for the filename
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Send the Excel file
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=temp_file_path,
            filename=f"Blue_Pharma_Weekly_Report_{current_date}.xlsx",
            caption=f"📄 **Weekly Sales Report (Basic)**\n\n"
                   f"📅 **Generated:** {current_date}\n"
                   f"📊 **Data Period:** Last {len(weekly_data)} weeks\n"
                   f"💰 **Total Revenue:** {df['Revenue (ETB)'].sum():.2f} ETB"
        )
        
        # Remove the temporary file
        os.remove(temp_file_path)
        
    except Exception as e:
        logger.error(f"Error generating basic weekly Excel report: {e}", exc_info=True)
        raise

async def handle_weekly_comparison_excel(query, user_type, db):
    """Generate and send weekly comparison report as Excel file."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        # Run cleanup first
        await cleanup_old_reports(db)
        
        comparison_data = db.get_weekly_comparison_data()
        
        if not comparison_data or len(comparison_data) < 2:
            await query.edit_message_text(
                "📊 Insufficient data for weekly comparison. Need at least 2 weeks of sales data.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Analytics", callback_data="view_stats")]
                ])
            )
            return
        
        # Create DataFrame
        df = pd.DataFrame(comparison_data)
        
        # Rename columns for better readability
        df = df.rename(columns={
            'week_number': 'Week Number',
            'week_start': 'Week Start Date',
            'week_end': 'Week End Date',
            'total_revenue': 'Revenue (ETB)',
            'total_orders': 'Total Orders',
            'unique_customers': 'Unique Customers',
            'avg_order_value': 'Avg Order Value (ETB)'
        })
        
        # Round numerical columns
        df['Revenue (ETB)'] = df['Revenue (ETB)'].fillna(0).round(2)
        df['Avg Order Value (ETB)'] = df['Avg Order Value (ETB)'].fillna(0).round(2)
        
        # Add week-over-week comparison calculations
        df_sorted = df.sort_values('Week Number', ascending=False).reset_index(drop=True)
        
        # Calculate week-over-week changes
        df_sorted['Revenue Change (%)'] = df_sorted['Revenue (ETB)'].pct_change(-1).fillna(0) * 100
        df_sorted['Orders Change (%)'] = df_sorted['Total Orders'].pct_change(-1).fillna(0) * 100
        df_sorted['Customers Change (%)'] = df_sorted['Unique Customers'].pct_change(-1).fillna(0) * 100
        
        # Round percentage changes
        df_sorted['Revenue Change (%)'] = df_sorted['Revenue Change (%)'].round(1)
        df_sorted['Orders Change (%)'] = df_sorted['Orders Change (%)'].round(1)
        df_sorted['Customers Change (%)'] = df_sorted['Customers Change (%)'].round(1)
        
        # Create a temporary Excel file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
            with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
                # Write main comparison data
                df_sorted.to_excel(writer, sheet_name='Weekly Comparison', index=False)
                
                # Create summary insights sheet
                if len(df_sorted) >= 2:
                    latest_week = df_sorted.iloc[0]
                    previous_week = df_sorted.iloc[1]
                    
                    insights = {
                        'Insight': [
                            'Current Week Revenue (ETB)',
                            'Previous Week Revenue (ETB)',
                            'Revenue Change (ETB)',
                            'Revenue Change (%)',
                            'Current Week Orders',
                            'Previous Week Orders',
                            'Orders Change',
                            'Best Week Revenue (ETB)',
                            'Worst Week Revenue (ETB)',
                            'Average Weekly Revenue (ETB)',
                            'Average Weekly Orders'
                        ],
                        'Value': [
                            latest_week['Revenue (ETB)'],
                            previous_week['Revenue (ETB)'],
                            latest_week['Revenue (ETB)'] - previous_week['Revenue (ETB)'],
                            latest_week['Revenue Change (%)'],
                            latest_week['Total Orders'],
                            previous_week['Total Orders'],
                            latest_week['Total Orders'] - previous_week['Total Orders'],
                            df_sorted['Revenue (ETB)'].max(),
                            df_sorted['Revenue (ETB)'].min(),
                            df_sorted['Revenue (ETB)'].mean().round(2),
                            df_sorted['Total Orders'].mean().round(1)
                        ]
                    }
                    insights_df = pd.DataFrame(insights)
                    insights_df.to_excel(writer, sheet_name='Key Insights', index=False)
            
            temp_file_path = temp_file.name
        
        # Format the date/time for the filename
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Calculate comparison summary for caption
        latest_revenue = df_sorted.iloc[0]['Revenue (ETB)']
        revenue_change = df_sorted.iloc[0]['Revenue Change (%)']
        
        # Send the Excel file
        await query.bot.send_document(
            chat_id=query.message.chat_id,
            document=temp_file_path,
            filename=f"Blue_Pharma_Weekly_Comparison_{current_date}.xlsx",
            caption=f"📊 **Weekly Comparison Report**\n\n"
                   f"📅 **Generated:** {current_date}\n"
                   f"📈 **Data Period:** Last {len(comparison_data)} weeks\n"
                   f"💰 **Latest Week Revenue:** {latest_revenue:.2f} ETB\n"
                   f"📊 **Week-over-Week Change:** {revenue_change:+.1f}%"
        )
        
        # Remove the temporary file
        os.remove(temp_file_path)
        
        # Update the message
        await query.edit_message_text(
            "✅ **Weekly Comparison Excel Generated!**\n\n"
            "📊 The Excel report has been sent with:\n"
            "• Week-by-week comparison data\n"
            "• Growth percentages\n"
            "• Key insights and trends",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📅 Daily Summary", callback_data="daily_summary_text")],
                [InlineKeyboardButton("📄 Weekly Report (Excel)", callback_data="weekly_excel_report")],
                [InlineKeyboardButton("🔙 Back to Analytics", callback_data="view_stats")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error generating weekly comparison Excel: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error generating weekly comparison report. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Analytics", callback_data="view_stats")]
            ])
        )

# --- Duplicate Handling Functions ---

# Single Medicine Addition Duplicate Handlers
async def handle_continue_original_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle continuing with original medicine name despite duplicates."""
    query = update.callback_query
    await query.answer()
    
    # Get the original medicine name from context
    medicine_name = context.user_data.get('original_medicine_name', 'Unknown')
    
    # Clear duplicate data and proceed with normal flow
    context.user_data.pop('duplicate_medicines', None)
    context.user_data.pop('original_medicine_name', None)
    
    # Store the medicine name and proceed to therapeutic category
    context.user_data['medicine_name'] = medicine_name
    
    await query.edit_message_text(
        f"✅ **Proceeding with original name:** {medicine_name}\n\n"
        "📝 **Step 2/7: Therapeutic Category**\n\n"
        "What is its therapeutic category? (e.g., *Analgesic*)"
    )
    
    return THERAPEUTIC_CATEGORY

async def handle_update_existing_medicine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle updating existing medicine with new stock/data."""
    query = update.callback_query
    await query.answer()
    
    duplicates = context.user_data.get('duplicate_medicines', [])
    
    if not duplicates:
        await query.edit_message_text("❌ No duplicate medicines found. Please try again.")
        return ConversationHandler.END
    
    # Show selection of duplicates to update
    update_text = "🔄 **Update Existing Medicine**\n\n"
    update_text += "📋 **Select which medicine to update:**\n\n"
    
    keyboard = []
    
    for i, medicine in enumerate(duplicates[:5], 1):  # Show top 5 matches
        similarity_percentage = int(medicine['similarity_score'] * 100)
        update_text += f"{i}. **{medicine['name']}** ({similarity_percentage}% match)\n"
        update_text += f"   📦 Current Stock: {medicine['stock_quantity']} units\n"
        update_text += f"   💰 Current Price: {medicine['price']:.2f} ETB\n\n"
        
        # Add buttons for different update options
        keyboard.append([
            InlineKeyboardButton(
                f"📦 Add Stock to {medicine['name']}", 
                callback_data=f"update_stock_for_{medicine['id']}"
            )
        ])
        keyboard.append([
            InlineKeyboardButton(
                f"🔄 Overwrite {medicine['name']}", 
                callback_data=f"overwrite_medicine_{medicine['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_add")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(update_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    return DUPLICATE_CONFIRMATION

async def handle_enter_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle entering a new medicine name to avoid duplicates."""
    query = update.callback_query
    await query.answer()
    
    # Clear duplicate data
    context.user_data.pop('duplicate_medicines', None)
    context.user_data.pop('original_medicine_name', None)
    
    await query.edit_message_text(
        "📝 **Enter New Medicine Name**\n\n"
        "Please enter a different name for the medicine to avoid duplicates:\n\n"
        "💡 **Tip:** Try being more specific or using a brand name."
    )
    
    return MEDICINE_NAME

async def handle_cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancelling the medicine addition process."""
    query = update.callback_query
    await query.answer()
    
    # Clear all user data
    context.user_data.clear()
    
    # Get user info for returning to main menu
    user = query.from_user
    db = context.bot_data['db']
    user_info = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if user_info:
        user_type = user_info['user_type']
        role_display = USER_ROLES.get(user_type, user_type.title())
        
        welcome_text = f"""
❌ **Medicine Addition Cancelled**

🏥 **Welcome back to Blue Pharma Trading PLC!**

Hello {user_info['first_name']}! Your Access Level: {role_display}

🎯 **What would you like to do today?**
Choose from the options below:
"""
        keyboard = get_user_keyboard(user_type)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text("❌ Medicine addition cancelled. Use /start to go back to the main menu.")
    
    return ConversationHandler.END

# Excel Upload Duplicate Handlers
async def handle_excel_update_existing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle updating existing medicines from Excel duplicates."""
    query = update.callback_query
    await query.answer()
    
    duplicates = context.user_data.get('excel_duplicates', [])
    excel_data = context.user_data.get('excel_data', [])
    
    if not duplicates or not excel_data:
        await query.edit_message_text("❌ No duplicate data found. Please upload the Excel file again.")
        return ConversationHandler.END
    
    db = context.bot_data['db']
    
    # Prepare list of updates for batch processing
    updates_list = []
    
    for duplicate in duplicates:
        medicine_id = duplicate['existing_medicine']['id']
        excel_medicine = duplicate['excel_medicine']
        
        # Convert Excel data to proper format
        medicine_data = {
            'name': str(excel_medicine.get('name', '')).strip(),
            'therapeutic_category': str(excel_medicine.get('therapeutic_category', '')).strip(),
            'manufacturing_date': excel_medicine.get('manufacturing_date'),
            'expiring_date': excel_medicine.get('expiring_date'),
            'dosage_form': str(excel_medicine.get('dosage_form', '')).strip(),
            'price': float(excel_medicine.get('price', 0)),
            'stock_quantity': int(excel_medicine.get('stock_quantity', 0))
        }
        
        updates_list.append((medicine_id, medicine_data))
    
    # Perform batch update (add stock mode)
    updated_count, failed_count = db.batch_update_medicines(updates_list, update_mode='add_stock')
    
    # Process remaining non-duplicate medicines
    remaining_medicines = []
    duplicate_indices = {dup['excel_index'] for dup in duplicates}
    
    for i, excel_med in enumerate(excel_data):
        if i not in duplicate_indices:
            remaining_medicines.append(excel_med)
    
    # Add remaining medicines as new
    added_count = 0
    failed_new_count = 0
    
    for excel_med in remaining_medicines:
        try:
            # Process dates
            mfg_date = excel_med.get('manufacturing_date')
            exp_date = excel_med.get('expiring_date')
            
            if pd.isna(mfg_date) or pd.isna(exp_date):
                failed_new_count += 1
                continue
            
            if hasattr(mfg_date, 'strftime'):
                mfg_date_str = mfg_date.strftime('%Y-%m-%d')
            else:
                mfg_date_str = str(mfg_date)
                
            if hasattr(exp_date, 'strftime'):
                exp_date_str = exp_date.strftime('%Y-%m-%d')
            else:
                exp_date_str = str(exp_date)
            
            if pd.isna(excel_med.get('name')) or pd.isna(excel_med.get('price')) or pd.isna(excel_med.get('stock_quantity')):
                failed_new_count += 1
                continue
            
            db.add_medicine(
                str(excel_med.get('name')).strip(),
                str(excel_med.get('therapeutic_category', 'General')).strip(),
                mfg_date_str,
                exp_date_str,
                str(excel_med.get('dosage_form', 'Unknown')).strip(),
                float(excel_med.get('price')),
                int(excel_med.get('stock_quantity'))
            )
            added_count += 1
            
        except Exception as e:
            logger.error(f"Failed to add new medicine from Excel: {e}")
            failed_new_count += 1
    
    # Clear Excel data from context
    context.user_data.pop('excel_duplicates', None)
    context.user_data.pop('excel_data', None)
    
    result_text = f"✅ **Excel Upload Complete!**\n\n"
    result_text += f"🔄 **Existing medicines updated:** {updated_count}\n"
    result_text += f"➕ **New medicines added:** {added_count}\n"
    
    if failed_count > 0 or failed_new_count > 0:
        result_text += f"❌ **Failed operations:** {failed_count + failed_new_count}\n\n"
        result_text += "Check logs for details on failed operations."
    else:
        result_text += "\n🎉 **All operations completed successfully!**"
    
    await query.edit_message_text(
        result_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Add More Medicines", callback_data="add_medicine")],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
        ])
    )
    
    return ConversationHandler.END

async def handle_excel_add_as_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle adding all Excel medicines as new, ignoring duplicates."""
    query = update.callback_query
    await query.answer()
    
    excel_data = context.user_data.get('excel_data', [])
    
    if not excel_data:
        await query.edit_message_text("❌ No Excel data found. Please upload the Excel file again.")
        return ConversationHandler.END
    
    db = context.bot_data['db']
    
    # Add all medicines from Excel as new records
    added_count = 0
    failed_count = 0
    
    for excel_med in excel_data:
        try:
            # Process dates
            mfg_date = excel_med.get('manufacturing_date')
            exp_date = excel_med.get('expiring_date')
            
            if pd.isna(mfg_date) or pd.isna(exp_date):
                failed_count += 1
                continue
            
            if hasattr(mfg_date, 'strftime'):
                mfg_date_str = mfg_date.strftime('%Y-%m-%d')
            else:
                mfg_date_str = str(mfg_date)
                
            if hasattr(exp_date, 'strftime'):
                exp_date_str = exp_date.strftime('%Y-%m-%d')
            else:
                exp_date_str = str(exp_date)
            
            if pd.isna(excel_med.get('name')) or pd.isna(excel_med.get('price')) or pd.isna(excel_med.get('stock_quantity')):
                failed_count += 1
                continue
            
            db.add_medicine(
                str(excel_med.get('name')).strip(),
                str(excel_med.get('therapeutic_category', 'General')).strip(),
                mfg_date_str,
                exp_date_str,
                str(excel_med.get('dosage_form', 'Unknown')).strip(),
                float(excel_med.get('price')),
                int(excel_med.get('stock_quantity'))
            )
            added_count += 1
            
        except Exception as e:
            logger.error(f"Failed to add medicine from Excel: {e}")
            failed_count += 1
    
    # Clear Excel data from context
    context.user_data.pop('excel_duplicates', None)
    context.user_data.pop('excel_data', None)
    
    result_text = f"✅ **Excel Upload Complete!**\n\n"
    result_text += f"➕ **New medicines added:** {added_count}\n"
    
    if failed_count > 0:
        result_text += f"❌ **Failed to add:** {failed_count}\n\n"
        result_text += "Note: Duplicates were added as separate records."
    else:
        result_text += "\n🎉 **All medicines added successfully!**\n"
        result_text += "Note: Duplicates were added as separate records."
    
    await query.edit_message_text(
        result_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Add More Medicines", callback_data="add_medicine")],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
        ])
    )
    
    return ConversationHandler.END

async def handle_excel_review_each(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle reviewing each duplicate individually (not implemented yet)."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "⚖️ **Individual Review Feature**\n\n"
        "🚧 This feature is under development.\n\n"
        "For now, please choose one of these options:\n"
        "• Update all existing records\n"
        "• Add all as new medicines\n"
        "• Skip duplicates\n"
        "• Cancel upload",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Update Existing Records", callback_data="excel_update_existing")],
            [InlineKeyboardButton("➕ Add as New Medicines", callback_data="excel_add_as_new")],
            [InlineKeyboardButton("❌ Skip All Duplicates", callback_data="excel_skip_duplicates")],
            [InlineKeyboardButton("❌ Cancel Upload", callback_data="cancel_excel_upload")]
        ])
    )
    
    return EXCEL_DUPLICATE_CHOICE

async def handle_excel_skip_duplicates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle skipping all duplicates and only adding new medicines."""
    query = update.callback_query
    await query.answer()
    
    duplicates = context.user_data.get('excel_duplicates', [])
    excel_data = context.user_data.get('excel_data', [])
    
    if not excel_data:
        await query.edit_message_text("❌ No Excel data found. Please upload the Excel file again.")
        return ConversationHandler.END
    
    db = context.bot_data['db']
    
    # Get indices of duplicate medicines to skip
    duplicate_indices = {dup['excel_index'] for dup in duplicates}
    
    # Process only non-duplicate medicines
    added_count = 0
    failed_count = 0
    skipped_count = len(duplicates)
    
    for i, excel_med in enumerate(excel_data):
        if i in duplicate_indices:
            continue  # Skip this duplicate
        
        try:
            # Process dates
            mfg_date = excel_med.get('manufacturing_date')
            exp_date = excel_med.get('expiring_date')
            
            if pd.isna(mfg_date) or pd.isna(exp_date):
                failed_count += 1
                continue
            
            if hasattr(mfg_date, 'strftime'):
                mfg_date_str = mfg_date.strftime('%Y-%m-%d')
            else:
                mfg_date_str = str(mfg_date)
                
            if hasattr(exp_date, 'strftime'):
                exp_date_str = exp_date.strftime('%Y-%m-%d')
            else:
                exp_date_str = str(exp_date)
            
            if pd.isna(excel_med.get('name')) or pd.isna(excel_med.get('price')) or pd.isna(excel_med.get('stock_quantity')):
                failed_count += 1
                continue
            
            db.add_medicine(
                str(excel_med.get('name')).strip(),
                str(excel_med.get('therapeutic_category', 'General')).strip(),
                mfg_date_str,
                exp_date_str,
                str(excel_med.get('dosage_form', 'Unknown')).strip(),
                float(excel_med.get('price')),
                int(excel_med.get('stock_quantity'))
            )
            added_count += 1
            
        except Exception as e:
            logger.error(f"Failed to add medicine from Excel: {e}")
            failed_count += 1
    
    # Clear Excel data from context
    context.user_data.pop('excel_duplicates', None)
    context.user_data.pop('excel_data', None)
    
    result_text = f"✅ **Excel Upload Complete!**\n\n"
    result_text += f"➕ **New medicines added:** {added_count}\n"
    result_text += f"⏩ **Duplicates skipped:** {skipped_count}\n"
    
    if failed_count > 0:
        result_text += f"❌ **Failed to add:** {failed_count}\n\n"
        result_text += "Duplicates were skipped to avoid data conflicts."
    else:
        result_text += "\n🎉 **All valid medicines added successfully!**\n"
        result_text += "Duplicates were skipped to avoid data conflicts."
    
    await query.edit_message_text(
        result_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Add More Medicines", callback_data="add_medicine")],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
        ])
    )
    
    return ConversationHandler.END

async def handle_cancel_excel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancelling the Excel upload process."""
    query = update.callback_query
    await query.answer()
    
    # Clear all Excel data
    context.user_data.pop('excel_duplicates', None)
    context.user_data.pop('excel_data', None)
    
    # Get user info for returning to main menu
    user = query.from_user
    db = context.bot_data['db']
    user_info = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if user_info:
        user_type = user_info['user_type']
        role_display = USER_ROLES.get(user_type, user_type.title())
        
        welcome_text = f"""
❌ **Excel Upload Cancelled**

🏥 **Welcome back to Blue Pharma Trading PLC!**

Hello {user_info['first_name']}! Your Access Level: {role_display}

🎯 **What would you like to do today?**
Choose from the options below:
"""
        keyboard = get_user_keyboard(user_type)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text("❌ Excel upload cancelled. Use /start to go back to the main menu.")
    
    return ConversationHandler.END

# --- Order Excel Export Functions ---
async def handle_export_all_orders_excel(query, user_type, db, context):
    """Export all orders to Excel file."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        orders = db.get_all_orders(1000)  # Get up to 1000 orders
        
        if not orders:
            await query.edit_message_text(
                "📋 **All Orders Export**\n\n❌ No orders found in the system to export.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return
        
        # Prepare data for Excel export
        export_data = []
        for order in orders:
            export_data.append({
                'Order Number': db.format_order_id(order['id']),
                'Order Date': order['order_date'][:10] if order['order_date'] else '',
                'Customer Name': order['customer_name'],
                'Customer Phone': order['customer_phone'],
                'Status': order['status'].capitalize(),
                'Total Items': order['total_items'],
                'Total Amount (ETB)': order['total_amount'],
                'Delivery Method': order['delivery_method'],
                'User First Name': order['first_name'] or '',
                'User Last Name': order['last_name'] or '',
                'Telegram ID': order['telegram_id'] or ''
            })
        
        # Create DataFrame
        df = pd.DataFrame(export_data)
        
        # Create a temporary Excel file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
            df.to_excel(temp_file.name, index=False, sheet_name='All Orders')
            temp_file_path = temp_file.name
        
        # Format the date/time for the filename
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Calculate summary statistics
        total_revenue = sum(order['total_amount'] for order in orders)
        pending_count = sum(1 for order in orders if order['status'] == 'pending')
        completed_count = sum(1 for order in orders if order['status'] == 'completed')
        
        # Send the Excel file
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=temp_file_path,
            filename=f"Blue_Pharma_All_Orders_{current_date}.xlsx",
            caption=f"📋 **All Orders Export**\n\n"
                   f"📅 **Generated:** {current_date}\n"
                   f"📊 **Total Orders:** {len(orders)}\n"
                   f"⏳ **Pending:** {pending_count}\n"
                   f"✅ **Completed:** {completed_count}\n"
                   f"💰 **Total Revenue:** {total_revenue:.2f} ETB"
        )
        
        # Remove the temporary file
        os.remove(temp_file_path)
        
        # Update the message
        await query.edit_message_text(
            "✅ **All Orders Excel Export Complete!**\n\n"
            f"📊 Exported {len(orders)} orders to Excel file.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏳ Export Pending Orders", callback_data="export_pending_orders_excel")],
                [InlineKeyboardButton("✅ Export Completed Orders", callback_data="export_completed_orders_excel")],
                [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error exporting all orders to Excel: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error creating all orders Excel export. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")]
            ])
        )

async def handle_export_pending_orders_excel(query, user_type, db, context):
    """Export pending orders to Excel file."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        orders = db.get_pending_orders(1000)  # Get up to 1000 pending orders
        
        if not orders:
            await query.edit_message_text(
                "⏳ **Pending Orders Export**\n\n✅ No pending orders found. All orders have been processed!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 Export All Orders", callback_data="export_all_orders_excel")],
                    [InlineKeyboardButton("✅ Export Completed Orders", callback_data="export_completed_orders_excel")],
                    [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return
        
        # Prepare data for Excel export
        export_data = []
        for order in orders:
            # Calculate days pending
            try:
                order_date = datetime.strptime(order['order_date'][:10], '%Y-%m-%d')
                days_pending = (datetime.now() - order_date).days
            except:
                days_pending = 0
            
            export_data.append({
                'Order Number': db.format_order_id(order['id']),
                'Order Date': order['order_date'][:10] if order['order_date'] else '',
                'Days Pending': days_pending,
                'Customer Name': order['customer_name'],
                'Customer Phone': order['customer_phone'],
                'Status': order['status'].capitalize(),
                'Total Items': order['total_items'],
                'Total Amount (ETB)': order['total_amount'],
                'Delivery Method': order['delivery_method'],
                'User First Name': order['first_name'] or '',
                'User Last Name': order['last_name'] or '',
                'Telegram ID': order['telegram_id'] or '',
                'Priority': 'High' if days_pending > 3 else 'Medium' if days_pending > 1 else 'Normal'
            })
        
        # Create DataFrame
        df = pd.DataFrame(export_data)
        
        # Sort by days pending (most urgent first)
        df = df.sort_values('Days Pending', ascending=False)
        
        # Create a temporary Excel file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
            with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
                # Write main data
                df.to_excel(writer, sheet_name='Pending Orders', index=False)
                
                # Add summary sheet
                summary_stats = {
                    'Metric': [
                        'Total Pending Orders',
                        'Total Pending Revenue (ETB)',
                        'Average Order Value (ETB)',
                        'Orders Pending > 3 Days',
                        'Orders Pending > 1 Day',
                        'Oldest Pending Order (Days)',
                        'Total Items Pending'
                    ],
                    'Value': [
                        len(orders),
                        df['Total Amount (ETB)'].sum(),
                        df['Total Amount (ETB)'].mean().round(2),
                        len(df[df['Days Pending'] > 3]),
                        len(df[df['Days Pending'] > 1]),
                        df['Days Pending'].max(),
                        df['Total Items'].sum()
                    ]
                }
                summary_df = pd.DataFrame(summary_stats)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            temp_file_path = temp_file.name
        
        # Format the date/time for the filename
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Calculate statistics for caption
        total_revenue = sum(order['total_amount'] for order in orders)
        urgent_orders = len([o for o in orders if (datetime.now() - datetime.strptime(o['order_date'][:10], '%Y-%m-%d')).days > 3])
        
        # Send the Excel file
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=temp_file_path,
            filename=f"Blue_Pharma_Pending_Orders_{current_date}.xlsx",
            caption=f"⏳ **Pending Orders Export**\n\n"
                   f"📅 **Generated:** {current_date}\n"
                   f"📊 **Pending Orders:** {len(orders)}\n"
                   f"⚠️ **Urgent (>3 days):** {urgent_orders}\n"
                   f"💰 **Pending Revenue:** {total_revenue:.2f} ETB"
        )
        
        # Remove the temporary file
        os.remove(temp_file_path)
        
        # Update the message
        await query.edit_message_text(
            "✅ **Pending Orders Excel Export Complete!**\n\n"
            f"📊 Exported {len(orders)} pending orders with priority analysis.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 Export All Orders", callback_data="export_all_orders_excel")],
                [InlineKeyboardButton("✅ Export Completed Orders", callback_data="export_completed_orders_excel")],
                [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error exporting pending orders to Excel: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error creating pending orders Excel export. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")]
            ])
        )

async def handle_export_completed_orders_excel(query, user_type, db, context):
    """Export completed orders to Excel file."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        orders = db.get_completed_orders(1000)  # Get up to 1000 completed orders
        
        if not orders:
            await query.edit_message_text(
                "✅ **Completed Orders Export**\n\n📋 No completed orders found in the system to export.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 Export All Orders", callback_data="export_all_orders_excel")],
                    [InlineKeyboardButton("⏳ Export Pending Orders", callback_data="export_pending_orders_excel")],
                    [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return
        
        # Prepare data for Excel export
        export_data = []
        for order in orders:
            export_data.append({
                'Order Number': db.format_order_id(order['id']),
                'Order Date': order['order_date'][:10] if order['order_date'] else '',
                'Completion Date': order['order_date'][:10] if order['order_date'] else '',  # Assuming order_date is completion for completed orders
                'Customer Name': order['customer_name'],
                'Customer Phone': order['customer_phone'],
                'Status': order['status'].capitalize(),
                'Total Items': order['total_items'],
                'Total Amount (ETB)': order['total_amount'],
                'Delivery Method': order['delivery_method'],
                'User First Name': order['first_name'] or '',
                'User Last Name': order['last_name'] or '',
                'Telegram ID': order['telegram_id'] or ''
            })
        
        # Create DataFrame
        df = pd.DataFrame(export_data)
        
        # Sort by order date (most recent first)
        df = df.sort_values('Order Date', ascending=False)
        
        # Create a temporary Excel file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
            with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
                # Write main data
                df.to_excel(writer, sheet_name='Completed Orders', index=False)
                
                # Add summary sheet
                summary_stats = {
                    'Metric': [
                        'Total Completed Orders',
                        'Total Revenue (ETB)',
                        'Average Order Value (ETB)',
                        'Total Items Sold',
                        'Average Items per Order',
                        'Unique Customers',
                        'Highest Order Value (ETB)',
                        'Lowest Order Value (ETB)'
                    ],
                    'Value': [
                        len(orders),
                        df['Total Amount (ETB)'].sum(),
                        df['Total Amount (ETB)'].mean().round(2),
                        df['Total Items'].sum(),
                        df['Total Items'].mean().round(1),
                        len(df['Customer Name'].unique()),
                        df['Total Amount (ETB)'].max(),
                        df['Total Amount (ETB)'].min()
                    ]
                }
                summary_df = pd.DataFrame(summary_stats)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            temp_file_path = temp_file.name
        
        # Format the date/time for the filename
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Calculate statistics for caption
        total_revenue = sum(order['total_amount'] for order in orders)
        unique_customers = len(set(order['customer_name'] for order in orders))
        
        # Send the Excel file
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=temp_file_path,
            filename=f"Blue_Pharma_Completed_Orders_{current_date}.xlsx",
            caption=f"✅ **Completed Orders Export**\n\n"
                   f"📅 **Generated:** {current_date}\n"
                   f"📊 **Completed Orders:** {len(orders)}\n"
                   f"👥 **Unique Customers:** {unique_customers}\n"
                   f"💰 **Total Revenue:** {total_revenue:.2f} ETB"
        )
        
        # Remove the temporary file
        os.remove(temp_file_path)
        
        # Update the message
        await query.edit_message_text(
            "✅ **Completed Orders Excel Export Complete!**\n\n"
            f"📊 Exported {len(orders)} completed orders with summary statistics.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 Export All Orders", callback_data="export_all_orders_excel")],
                [InlineKeyboardButton("⏳ Export Pending Orders", callback_data="export_pending_orders_excel")],
                [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error exporting completed orders to Excel: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error creating completed orders Excel export. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")]
            ])
        )

# --- Order Status Update Conversation Handlers ---
async def handle_update_order_status_by_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start conversation to update order status by order number."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db = context.bot_data['db']
    user_info = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if not user_info or user_info['user_type'] not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return ConversationHandler.END
    
    # Store the target status in context
    target_status = query.data.replace("update_status_", "")
    context.user_data['target_status'] = target_status
    
    status_emoji = "✅" if target_status == "completed" else "⏳" if target_status == "pending" else "📦"
    status_display = target_status.capitalize()
    
    await query.edit_message_text(
        f"{status_emoji} **Mark Order as {status_display}**\n\n"
        f"📋 **Step 1: Enter Order Number**\n\n"
        f"Please enter the order number you want to mark as {status_display.lower()}:\n\n"
        f"📝 **Examples:**\n"
        f"• ORD1234567890\n"
        f"• ORD1703123456\n\n"
        f"💡 **Tip:** You can find order numbers in the order list or customer communications."
    )
    
    return ORDER_STATUS_UPDATE_INPUT

async def handle_order_number_input_for_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle order number input and update status."""
    order_number = update.message.text.strip().upper()  # Convert to uppercase and strip whitespace
    db = context.bot_data['db']
    target_status = context.user_data.get('target_status', 'pending')
    
    # Clean and normalize the order number
    # Remove any extra characters and ensure it starts with ORD
    if not order_number.startswith('ORD'):
        # If user entered just numbers, try to find order with ORD prefix
        if order_number.isdigit():
            order_number = f"ORD{order_number}"
        else:
            await update.message.reply_text(
                f"❌ **Invalid order number format: {order_number}**\n\n"
                f"🔍 **Please enter a valid order number:**\n"
                f"• Should start with 'ORD' followed by numbers\n"
                f"• Example: ORD1756389094\n"
                f"• Or just the numbers: 1756389094\n\n"
                f"📝 **Try again:**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="view_orders")]
                ])
            )
            return ORDER_STATUS_UPDATE_INPUT
    
    # Find the order by order number
    order = db.find_order_by_number(order_number)
    
    if not order:
        # Try alternative search methods
        # 1. Try without ORD prefix
        if order_number.startswith('ORD'):
            number_only = order_number[3:]
            order = db.find_order_by_number(number_only)
        
        # 2. Try with different case variations
        if not order:
            order = db.find_order_by_number(order_number.lower())
        
        if not order:
            await update.message.reply_text(
                f"❌ **Order not found: {order_number}**\n\n"
                f"🔍 **Please check:**\n"
                f"• Order number spelling and format\n"
                f"• Order number exists in the system\n"
                f"• No extra spaces or characters\n\n"
                f"📝 **Example valid formats:**\n"
                f"• ORD1756389094\n"
                f"• 1756389094\n\n"
                f"📝 **Try again with a different order number:**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="view_orders")]
                ])
            )
            return ORDER_STATUS_UPDATE_INPUT
    
    # Check if status change is needed
    current_status = order['status']
    if current_status == target_status:
        status_emoji = "✅" if target_status == "completed" else "⏳" if target_status == "pending" else "📦"
        await update.message.reply_text(
            f"ℹ️ **Order Already {target_status.capitalize()}**\n\n"
            f"📋 **Order:** #{db.format_order_id(order['id'])}\n"
            f"👤 **Customer:** {order['customer_name']}\n"
            f"📱 **Phone:** {order['customer_phone']}\n"
            f"💰 **Amount:** {order['total_amount']:.2f} ETB\n"
            f"📋 **Current Status:** {status_emoji} {current_status.capitalize()}\n\n"
            f"✅ **No change needed - order is already {target_status}.**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 View Order Details", callback_data=f"view_order_details_{order['id']}")],
                [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Update the order status
    success, message = db.update_order_status(order['id'], target_status)
    
    if success:
        old_status_emoji = "✅" if current_status == "completed" else "⏳" if current_status == "pending" else "📦"
        new_status_emoji = "✅" if target_status == "completed" else "⏳" if target_status == "pending" else "📦"
        
        await update.message.reply_text(
            f"✅ **Order Status Updated Successfully!**\n\n"
            f"📋 **Order:** #{db.format_order_id(order['id'])}\n"
            f"👤 **Customer:** {order['customer_name']}\n"
            f"📱 **Phone:** {order['customer_phone']}\n"
            f"💰 **Amount:** {order['total_amount']:.2f} ETB\n\n"
            f"📋 **Status Change:**\n"
            f"• From: {old_status_emoji} {current_status.capitalize()}\n"
            f"• To: {new_status_emoji} {target_status.capitalize()}\n\n"
            f"🎉 **The order has been successfully marked as {target_status}!**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 View Order Details", callback_data=f"view_order_details_{order['id']}")],
                [InlineKeyboardButton(f"🔄 Update Another Order", callback_data=f"update_status_{target_status}")],
                [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
        
        # Notify admin if order is completed and user is not admin
        if target_status == 'completed' and update.effective_user.id != ADMIN_USER_ID:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_USER_ID,
                    text=f"✅ **Order Completed**\n\n"
                         f"📋 **Order:** #{db.format_order_id(order['id'])}\n"
                         f"👤 **Customer:** {order['customer_name']}\n"
                         f"💰 **Amount:** {order['total_amount']:.2f} ETB\n"
                         f"👨‍💼 **Completed by:** {update.effective_user.first_name}\n"
                         f"📅 **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            except Exception as e:
                logger.error(f"Failed to send completion notification to admin: {e}")
    else:
        await update.message.reply_text(
            f"❌ **Failed to update order status:** {message}\n\n"
            f"Please try again or contact support if the issue persists.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Try Again", callback_data=f"update_status_{target_status}")],
                [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
    
    context.user_data.clear()
    return ConversationHandler.END

# --- Order Details Expansion Handlers ---
async def handle_view_order_details_expand(query, user_type, db):
    """Handle expanding order details in the order list view."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        order_id = int(query.data.replace("view_order_details_expand_", ""))
        user_id = query.from_user.id
        
        # Initialize user_data structure if it doesn't exist
        if user_id not in user_data:
            user_data[user_id] = {}
        if 'expanded_orders' not in user_data[user_id]:
            user_data[user_id]['expanded_orders'] = []
        
        # Add this order to the expanded list
        if order_id not in user_data[user_id]['expanded_orders']:
            user_data[user_id]['expanded_orders'].append(order_id)
        
        # Determine which view to refresh based on the current context
        # We'll refresh the current view by calling the appropriate handler
        
        # Get order details to determine status and refresh appropriate view
        order_details = db.get_order_details(order_id)
        if order_details:
            if order_details['status'] == 'pending':
                await handle_pending_orders(query, user_type, db)
            elif order_details['status'] == 'completed':
                await handle_completed_orders(query, user_type, db)
            else:
                await handle_all_orders(query, user_type, db)
        else:
            await query.edit_message_text(
                "❌ Order not found.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Orders", callback_data="view_orders")]
                ])
            )
    
    except Exception as e:
        logger.error(f"Error expanding order details: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error expanding order details. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Orders", callback_data="view_orders")]
            ])
        )

async def handle_hide_order_details(query, user_type, db):
    """Handle hiding order details in the order list view."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        order_id = int(query.data.replace("hide_order_details_", ""))
        user_id = query.from_user.id
        
        # Initialize user_data structure if it doesn't exist
        if user_id not in user_data:
            user_data[user_id] = {}
        if 'expanded_orders' not in user_data[user_id]:
            user_data[user_id]['expanded_orders'] = []
        
        # Remove this order from the expanded list
        if order_id in user_data[user_id]['expanded_orders']:
            user_data[user_id]['expanded_orders'].remove(order_id)
        
        # Determine which view to refresh based on the current context
        # Get order details to determine status and refresh appropriate view
        order_details = db.get_order_details(order_id)
        if order_details:
            if order_details['status'] == 'pending':
                await handle_pending_orders(query, user_type, db)
            elif order_details['status'] == 'completed':
                await handle_completed_orders(query, user_type, db)
            else:
                await handle_all_orders(query, user_type, db)
        else:
            await query.edit_message_text(
                "❌ Order not found.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Orders", callback_data="view_orders")]
                ])
            )
    
    except Exception as e:
        logger.error(f"Error hiding order details: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error hiding order details. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Orders", callback_data="view_orders")]
            ])
        )

# --- Order Status Update Functions ---
async def handle_mark_order_completed(query, user_type, db):
    """Mark an order as completed."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        order_id = int(query.data.replace("mark_completed_", ""))
        
        # Get order details first
        order_details = db.get_order_details(order_id)
        
        if not order_details:
            await query.edit_message_text(
                "❌ Order not found. It may have been removed.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Orders", callback_data="view_orders")]
                ])
            )
            return
        
        # Update order status
        success, message = db.update_order_status(order_id, 'completed')
        
        if success:
            await query.edit_message_text(
                f"✅ **Order Marked as Completed!**\n\n"
                f"📋 **Order:** #{order_details['order_number']}\n"
                f"👤 **Customer:** {order_details['customer_name']}\n"
                f"📱 **Phone:** {order_details['customer_phone']}\n"
                f"💰 **Amount:** {order_details['total_amount']:.2f} ETB\n\n"
                f"🎉 **Status changed to: Completed**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 View Order Details", callback_data=f"view_order_details_{order_id}")],
                    [InlineKeyboardButton("⏳ View Pending Orders", callback_data="pending_orders")],
                    [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
        else:
            await query.edit_message_text(
                f"❌ **Failed to update order status:** {message}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Orders", callback_data="view_orders")]
                ])
            )
    
    except Exception as e:
        logger.error(f"Error marking order as completed: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error updating order status. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Orders", callback_data="view_orders")]
            ])
        )

async def handle_mark_order_pending(query, user_type, db):
    """Mark an order as pending."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        order_id = int(query.data.replace("mark_pending_", ""))
        
        # Get order details first
        order_details = db.get_order_details(order_id)
        
        if not order_details:
            await query.edit_message_text(
                "❌ Order not found. It may have been removed.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Orders", callback_data="view_orders")]
                ])
            )
            return
        
        # Update order status
        success, message = db.update_order_status(order_id, 'pending')
        
        if success:
            await query.edit_message_text(
                f"⏳ **Order Marked as Pending!**\n\n"
                f"📋 **Order:** #{order_details['order_number']}\n"
                f"👤 **Customer:** {order_details['customer_name']}\n"
                f"📱 **Phone:** {order_details['customer_phone']}\n"
                f"💰 **Amount:** {order_details['total_amount']:.2f} ETB\n\n"
                f"⏳ **Status changed to: Pending**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 View Order Details", callback_data=f"view_order_details_{order_id}")],
                    [InlineKeyboardButton("✅ View Completed Orders", callback_data="completed_orders")],
                    [InlineKeyboardButton("🔙 Back to Order Management", callback_data="view_orders")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
        else:
            await query.edit_message_text(
                f"❌ **Failed to update order status:** {message}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Orders", callback_data="view_orders")]
                ])
            )
    
    except Exception as e:
        logger.error(f"Error marking order as pending: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error updating order status. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Orders", callback_data="view_orders")]
            ])
        )

# --- Custom Quantity Handler ---
async def handle_custom_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom quantity selection for adding medicines to cart."""
    query = update.callback_query
    await query.answer()
    
    try:
        # Extract medicine ID from callback data: custom_quantity_medicineId
        callback_parts = query.data.split('_')
        
        if len(callback_parts) < 3:
            logger.error(f"Invalid custom quantity callback data format: {query.data}")
            await query.edit_message_text(
                "❌ Invalid request format. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")]
                ])
            )
            return ConversationHandler.END
        
        try:
            medicine_id = int(callback_parts[-1])
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse medicine ID from custom quantity callback data {query.data}: {e}")
            await query.edit_message_text(
                "❌ Invalid medicine selection. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")]
                ])
            )
            return ConversationHandler.END
        
        # Get medicine details with error handling
        db = context.bot_data['db']
        medicine = db.get_medicine_by_id(medicine_id)
        
        if not medicine:
            await query.edit_message_text(
                "❌ Medicine not found. It may have been removed or is no longer available.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return ConversationHandler.END
        
        # Check if medicine is active and has stock
        if not medicine.get('is_active', True):
            await query.edit_message_text(
                "❌ This medicine is no longer available.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Category", callback_data=f"back_to_category_{medicine.get('therapeutic_category', 'Unknown')}")],
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")]
                ])
            )
            return ConversationHandler.END
        
        if medicine['stock_quantity'] <= 0:
            await query.edit_message_text(
                f"❌ **{medicine['name']} is currently out of stock.**\n\n"
                f"📦 **Available Stock:** 0 units\n"
                f"💰 **Price:** {medicine['price']:.2f} ETB\n\n"
                f"🔄 **Please check back later or choose a different medicine.**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Category", callback_data=f"back_to_category_{medicine.get('therapeutic_category', 'Unknown')}")],
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")]
                ])
            )
            return ConversationHandler.END
        
        # Store medicine ID for the custom quantity conversation
        context.user_data['custom_quantity_medicine_id'] = medicine_id
        
        # Check current cart for this medicine
        user_id = query.from_user.id
        cart = get_user_cart(user_id)
        current_in_cart = 0
        
        for item in cart:
            if item['medicine_id'] == medicine_id:
                current_in_cart = item['quantity']
                break
        
        # Calculate available quantity (total stock minus what's already in cart)
        available_to_add = medicine['stock_quantity'] - current_in_cart
        
        if available_to_add <= 0:
            await query.edit_message_text(
                f"❌ **Cannot add more {medicine['name']}**\n\n"
                f"💊 **Medicine:** {medicine['name']}\n"
                f"📦 **Total Stock:** {medicine['stock_quantity']} units\n"
                f"🛒 **Already in Cart:** {current_in_cart} units\n"
                f"📊 **Available to Add:** 0 units\n\n"
                f"❌ **You already have the maximum available quantity in your cart.**\n\n"
                f"💡 **Options:**\n"
                f"• Remove some from cart first\n"
                f"• Choose a different medicine",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 View Cart", callback_data="view_order_cart")],
                    [InlineKeyboardButton("🔙 Back to Category", callback_data=f"back_to_category_{medicine.get('therapeutic_category', 'Unknown')}")],
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")]
                ])
            )
            return ConversationHandler.END
        
        # Show custom quantity input interface
        custom_text = f"🔢 **Custom Quantity Selection**\n\n"
        custom_text += f"💊 **Medicine:** {medicine['name']}\n"
        custom_text += f"💰 **Price:** {medicine['price']:.2f} ETB per unit\n"
        custom_text += f"📦 **Total Stock:** {medicine['stock_quantity']} units\n"
        
        if current_in_cart > 0:
            custom_text += f"🛒 **Already in Cart:** {current_in_cart} units\n"
        
        custom_text += f"📊 **Available to Add:** {available_to_add} units\n\n"
        
        # Add category and form info if available
        if medicine.get('therapeutic_category'):
            category_emoji = get_category_emoji(medicine['therapeutic_category'])
            custom_text += f"🏷️ **Category:** {category_emoji} {medicine['therapeutic_category']}\n"
        
        if medicine.get('dosage_form'):
            custom_text += f"💊 **Form:** {medicine['dosage_form']}\n"
        
        custom_text += f"\n📝 **Enter the quantity you want to add to cart:**\n\n"
        custom_text += f"🔢 **Valid range:** 1 to {available_to_add} units\n\n"
        custom_text += f"💡 **Example:** If you want to add 25 units, just type `25`"
        
        # Create back navigation buttons
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Quantity Selection", callback_data=f"add_medicine_{medicine_id}")],
            [InlineKeyboardButton("🛒 View Cart", callback_data="view_order_cart")]
        ]
        
        # Add category navigation if available
        category = medicine.get('therapeutic_category')
        if category:
            keyboard.append([
                InlineKeyboardButton("🔙 Back to Category", callback_data=f"back_to_category_{category}"),
                InlineKeyboardButton("🔙 All Categories", callback_data="place_order")
            ])
        else:
            keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")])
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="back_to_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(custom_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        return CUSTOM_QUANTITY_INPUT
        
    except Exception as e:
        logger.error(f"Error in handle_custom_quantity: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ An error occurred while processing your request. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
        return ConversationHandler.END

async def handle_custom_quantity_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom quantity input from user."""
    try:
        # Get the input quantity
        quantity_input = update.message.text.strip()
        
        # Validate that input is a positive integer
        try:
            quantity = int(quantity_input)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except ValueError:
            await update.message.reply_text(
                "❌ **Invalid quantity format!**\n\n"
                "🔢 **Please enter a valid positive number:**\n\n"
                "✅ **Valid examples:** 1, 25, 50, 100\n"
                "❌ **Invalid examples:** 0, -5, abc, 1.5\n\n"
                "📝 **Try again:**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="place_order")]
                ])
            )
            return CUSTOM_QUANTITY_INPUT
        
        # Get medicine and user information
        medicine_id = context.user_data.get('custom_quantity_medicine_id')
        if not medicine_id:
            await update.message.reply_text(
                "❌ Medicine selection expired. Please start over.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 Browse Medicines", callback_data="place_order")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return ConversationHandler.END
        
        db = context.bot_data['db']
        medicine = db.get_medicine_by_id(medicine_id)
        
        if not medicine:
            await update.message.reply_text(
                "❌ Medicine not found. It may have been removed.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 Browse Medicines", callback_data="place_order")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return ConversationHandler.END
        
        # Check if medicine is still active and has stock
        if not medicine.get('is_active', True):
            await update.message.reply_text(
                f"❌ **{medicine['name']} is no longer available.**\n\n"
                "This medicine has been deactivated and cannot be ordered.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return ConversationHandler.END
        
        if medicine['stock_quantity'] <= 0:
            await update.message.reply_text(
                f"❌ **{medicine['name']} is now out of stock.**\n\n"
                f"📦 **Available Stock:** 0 units\n\n"
                f"🔄 **The stock may have changed since you started the order process.**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")],
                    [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
                ])
            )
            return ConversationHandler.END
        
        # Check current cart for this medicine
        user_id = update.effective_user.id
        cart = get_user_cart(user_id)
        current_in_cart = 0
        
        for item in cart:
            if item['medicine_id'] == medicine_id:
                current_in_cart = item['quantity']
                break
        
        # Validate requested quantity against available stock
        available_to_add = medicine['stock_quantity'] - current_in_cart
        
        if quantity > available_to_add:
            await update.message.reply_text(
                f"❌ **Quantity exceeds available stock!**\n\n"
                f"💊 **Medicine:** {medicine['name']}\n"
                f"🔢 **Requested Quantity:** {quantity} units\n"
                f"📦 **Total Stock:** {medicine['stock_quantity']} units\n"
                f"🛒 **Already in Cart:** {current_in_cart} units\n"
                f"📊 **Available to Add:** {available_to_add} units\n\n"
                f"❌ **Cannot add {quantity} units. Maximum available: {available_to_add} units.**\n\n"
                f"📝 **Please enter a quantity between 1 and {available_to_add}:**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="place_order")]
                ])
            )
            return CUSTOM_QUANTITY_INPUT
        
        # Add to cart with error handling
        try:
            add_to_cart_local(user_id, medicine_id, quantity)
        except Exception as cart_error:
            logger.error(f"Error adding custom quantity to cart: {cart_error}", exc_info=True)
            await update.message.reply_text(
                "❌ Error adding item to cart. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Try Again", callback_data=f"custom_quantity_{medicine_id}")],
                    [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")]
                ])
            )
            return ConversationHandler.END
        
        # Calculate totals for confirmation
        try:
            item_total = medicine['price'] * quantity
            cart_total = calculate_cart_total(db, user_id)
        except Exception as calc_error:
            logger.error(f"Error calculating totals for custom quantity: {calc_error}", exc_info=True)
            item_total = 0.0
            cart_total = 0.0
        
        # Get updated cart info for display
        updated_cart = get_user_cart(user_id)
        cart_item_count = len(updated_cart)
        cart_total_items = sum(item['quantity'] for item in updated_cart)
        
        # Calculate new quantity in cart for this medicine
        new_cart_quantity = current_in_cart + quantity
        remaining_stock = medicine['stock_quantity'] - new_cart_quantity
        
        confirmation_text = f"✅ **Custom Quantity Added Successfully!**\n\n"
        confirmation_text += f"💊 **Medicine:** {medicine['name']}\n"
        confirmation_text += f"🔢 **Quantity Added:** {quantity} units\n"
        confirmation_text += f"💰 **Item Total:** {item_total:.2f} ETB\n\n"
        
        if current_in_cart > 0:
            confirmation_text += f"🛒 **Previous in Cart:** {current_in_cart} units\n"
            confirmation_text += f"🛒 **Total {medicine['name']} in Cart:** {new_cart_quantity} units\n\n"
        
        confirmation_text += f"🛒 **Updated Cart Summary:**\n"
        confirmation_text += f"• Total Items: {cart_total_items} units\n"
        confirmation_text += f"• Different Medicines: {cart_item_count}\n"
        confirmation_text += f"• Cart Total: {cart_total:.2f} ETB\n\n"
        
        confirmation_text += f"📦 **Remaining stock:** {remaining_stock} units"
        
        # Create action buttons with safe category handling
        keyboard = [
            [InlineKeyboardButton("🛒 View Full Cart", callback_data="view_order_cart")],
            [InlineKeyboardButton("✅ Proceed to Checkout", callback_data="proceed_checkout")]
        ]
        
        # Add category navigation if category is available
        category = medicine.get('therapeutic_category')
        if category:
            keyboard.append([
                InlineKeyboardButton(f"➡️ Continue in {category}", callback_data=f"back_to_category_{category}"),
                InlineKeyboardButton("🔙 All Categories", callback_data="place_order")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(confirmation_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        # Clear custom quantity context data
        context.user_data.pop('custom_quantity_medicine_id', None)
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in handle_custom_quantity_input: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while processing your custom quantity. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Categories", callback_data="place_order")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
            ])
        )
        return ConversationHandler.END

# --- Order Details Search Conversation ---
async def handle_order_details_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the order details search conversation."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db = context.bot_data['db']
    user_info = get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
    
    if not user_info or user_info['user_type'] not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return ConversationHandler.END
    
    await query.edit_message_text(
        "🔍 **Order Details Search**\n\n"
        "📋 **Enter Order ID or Order Number**\n\n"
        "Please enter the order ID (number) or order number you want to view details for:\n\n"
        "📝 **Examples:**\n"
        "• 123 (Order ID)\n"
        "• ORD1756389094 (Order Number)\n"
        "• 1756389094 (Order Number without ORD)\n\n"
        "💡 **Tip:** You can find order IDs and numbers in the order lists."
    )
    
    return ORDER_ID_SEARCH

async def handle_order_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle order ID/number input and display order details."""
    order_input = update.message.text.strip().upper()  # Convert to uppercase
    db = context.bot_data['db']
    
    order_details = None
    
    # Try different search methods
    try:
        # Method 1: Try as direct order ID (numeric)
        if order_input.isdigit():
            order_id = int(order_input)
            order_details = db.get_order_details(order_id)
        
        # Method 2: Try as order number (with or without ORD prefix)
        if not order_details:
            # Ensure order number starts with ORD
            if not order_input.startswith('ORD'):
                order_number = f"ORD{order_input}"
            else:
                order_number = order_input
            
            # Find order by number and get its details
            order = db.find_order_by_number(order_number)
            if order:
                order_details = db.get_order_details(order['id'])
        
        # Method 3: Try searching just the number part
        if not order_details and order_input.startswith('ORD'):
            number_only = order_input[3:]
            order = db.find_order_by_number(number_only)
            if order:
                order_details = db.get_order_details(order['id'])
    
    except ValueError:
        # Invalid numeric input
        pass
    
    if not order_details:
        await update.message.reply_text(
            f"❌ **Order not found: {order_input}**\n\n"
            f"🔍 **Please check:**\n"
            f"• Order ID or number is correct\n"
            f"• Order exists in the system\n"
            f"• No extra spaces or characters\n\n"
            f"📝 **Valid formats:**\n"
            f"• Order ID: 123\n"
            f"• Order Number: ORD1756389094\n"
            f"• Just Numbers: 1756389094\n\n"
            f"📝 **Try again with a different order ID/number:**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="view_orders")]
            ])
        )
        return ORDER_ID_SEARCH
    
    # Display comprehensive order details
    await display_order_details_response(update, context, order_details)
    
    context.user_data.clear()
    return ConversationHandler.END

async def display_order_details_response(update: Update, context: ContextTypes.DEFAULT_TYPE, order_details):
    """Display comprehensive order details in response format."""
    try:
        # Calculate days since order for pending orders
        days_info = ""
        if order_details['status'] == 'pending':
            try:
                order_date = datetime.strptime(order_details['order_date'][:10], '%Y-%m-%d')
                days_pending = (datetime.now() - order_date).days
                urgency = "🚨 URGENT" if days_pending > 3 else "⚠️ Priority" if days_pending > 1 else "⏳ Normal"
                days_info = f"⏰ Days Pending: {days_pending} days ({urgency})\n"
            except:
                pass
        
        # Format comprehensive order details
        details_text = f"📋 Complete Order Details\n\n"
        details_text += f"🆔 Order ID: {order_details['id']}\n"
        details_text += f"📋 Order Number: #{context.bot_data['db'].format_order_id(order_details['id'])}\n"
        details_text += f"📅 Order Date: {order_details['order_date'][:16] if order_details['order_date'] else 'N/A'}\n"
        details_text += f"📋 Status: {order_details['status'].upper()} {'✅' if order_details['status'] == 'completed' else '⏳' if order_details['status'] == 'pending' else '📦'}\n"
        details_text += days_info
        details_text += f"🚚 Delivery Method: {order_details['delivery_method'].title()}\n\n"
        
        # Customer Information
        details_text += f"👤 Customer Information:\n"
        details_text += f"• Name: {order_details['customer_name']}\n"
        details_text += f"• Phone: {order_details['customer_phone']}\n"
        
        if order_details.get('first_name'):
            details_text += f"• Telegram User: {order_details['first_name']} {order_details['last_name'] or ''}\n"
            details_text += f"• Telegram ID: {order_details['telegram_id']}\n"
        
        details_text += "\n"
        
        # Detailed order items with comprehensive info
        details_text += f"📦 Ordered Medicines:\n\n"
        
        total_items = 0
        total_amount = 0.0
        
        for i, item in enumerate(order_details.get('items', []), 1):
            item_total = item['total_price']
            details_text += f"{i}. {item['medicine_name']}\n"
            details_text += f"   📦 Quantity: {item['quantity']} units\n"
            details_text += f"   💰 Unit Price: {item['unit_price']:.2f} ETB\n"
            details_text += f"   💰 Subtotal: {item_total:.2f} ETB\n"
            
            if item.get('therapeutic_category'):
                details_text += f"   🏷️ Category: {item['therapeutic_category']}\n"
            
            details_text += "\n"
            total_items += item['quantity']
            total_amount += item_total
        
        # Comprehensive order summary
        details_text += f"📊 Order Summary:\n"
        details_text += f"• Total Items: {total_items} units\n"
        details_text += f"• Total Amount: {order_details['total_amount']:.2f} ETB\n"
        details_text += f"• Medicine Types: {len(order_details.get('items', []))} different medicines\n"
        
        if total_items > 0:
            avg_price_per_item = order_details['total_amount'] / total_items
            details_text += f"• Average Price per Item: {avg_price_per_item:.2f} ETB\n"
        
        # Create comprehensive action buttons
        keyboard = []
        order_id = order_details['id']
        
        # Status change buttons
        if order_details['status'] == 'pending':
            keyboard.append([InlineKeyboardButton("✅ Mark as Completed", callback_data=f"mark_completed_{order_id}")])
        elif order_details['status'] == 'completed':
            keyboard.append([InlineKeyboardButton("⏳ Reopen Order (Mark as Pending)", callback_data=f"mark_pending_{order_id}")])
        
        # Quick search and navigation buttons
        keyboard.append([InlineKeyboardButton("🔍 Search Another Order", callback_data="order_details_search")])
        keyboard.append([
            InlineKeyboardButton("📋 All Orders", callback_data="all_orders"),
            InlineKeyboardButton("⏳ Pending Orders", callback_data="pending_orders")
        ])
        keyboard.append([
            InlineKeyboardButton("🔙 Order Management", callback_data="view_orders"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(details_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error displaying order details: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Error displaying order details. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Orders", callback_data="view_orders")]
            ])
        )

async def handle_view_order_details(query, user_type, db):
    """View comprehensive detailed information about a specific order."""
    if user_type not in ['staff', 'admin']:
        await query.edit_message_text("❌ Access denied. Staff/Admin access required.")
        return
    
    try:
        # Handle both regular view_order_details and expand variants
        data = query.data
        if "expand" in data:
            # Skip this function if it's an expand action
            # It should be handled by handle_view_order_details_expand
            return
            
        order_id = int(query.data.replace("view_order_details_", ""))
        
        # Get detailed order information
        order_details = db.get_order_details(order_id)
        
        if not order_details:
            await query.edit_message_text(
                "❌ Order not found. It may have been removed.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Orders", callback_data="view_orders")]
                ])
            )
            return
        
        # Calculate days since order for pending orders
        days_info = ""
        if order_details['status'] == 'pending':
            try:
                order_date = datetime.strptime(order_details['order_date'][:10], '%Y-%m-%d')
                days_pending = (datetime.now() - order_date).days
                urgency = "🚨 URGENT" if days_pending > 3 else "⚠️ Priority" if days_pending > 1 else "⏳ Normal"
                days_info = f"⏰ Days Pending: {days_pending} days ({urgency})\n"
            except:
                pass
        
        # Format comprehensive order details
        details_text = f"📋 Complete Order Details\n\n"
        details_text += f"🆔 Order ID: {order_details['id']}\n"
        details_text += f"📋 Order Number: #{db.format_order_id(order_details['id'])}\n"
        details_text += f"📅 Order Date: {order_details['order_date'][:16] if order_details['order_date'] else 'N/A'}\n"
        details_text += f"📋 Status: {order_details['status'].upper()} {'✅' if order_details['status'] == 'completed' else '⏳' if order_details['status'] == 'pending' else '📦'}\n"
        details_text += days_info
        details_text += f"🚚 Delivery Method: {order_details['delivery_method'].title()}\n\n"
        
        # Customer Information
        details_text += f"👤 Customer Information:\n"
        details_text += f"• Name: {order_details['customer_name']}\n"
        details_text += f"• Phone: {order_details['customer_phone']}\n"
        
        if order_details.get('first_name'):
            details_text += f"• Telegram User: {order_details['first_name']} {order_details['last_name'] or ''}\n"
            details_text += f"• Telegram ID: {order_details['telegram_id']}\n"
        
        details_text += "\n"
        
        # Detailed order items with comprehensive info
        details_text += f"📦 Ordered Medicines:\n\n"
        
        total_items = 0
        total_amount = 0.0
        
        for i, item in enumerate(order_details.get('items', []), 1):
            item_total = item['total_price']
            details_text += f"{i}. {item['medicine_name']}\n"
            details_text += f"   📦 Quantity: {item['quantity']} units\n"
            details_text += f"   💰 Unit Price: {item['unit_price']:.2f} ETB\n"
            details_text += f"   💰 Subtotal: {item_total:.2f} ETB\n"
            
            if item.get('therapeutic_category'):
                details_text += f"   🏷️ Category: {item['therapeutic_category']}\n"
            
            details_text += "\n"
            total_items += item['quantity']
            total_amount += item_total
        
        # Comprehensive order summary
        details_text += f"📊 Order Summary:\n"
        details_text += f"• Total Items: {total_items} units\n"
        details_text += f"• Total Amount: {order_details['total_amount']:.2f} ETB\n"
        details_text += f"• Medicine Types: {len(order_details.get('items', []))} different medicines\n"
        
        if total_items > 0:
            avg_price_per_item = order_details['total_amount'] / total_items
            details_text += f"• Average Price per Item: {avg_price_per_item:.2f} ETB\n"
        
        # Create comprehensive action buttons
        keyboard = []
        
        # Status change buttons
        if order_details['status'] == 'pending':
            keyboard.append([InlineKeyboardButton("✅ Mark as Completed", callback_data=f"mark_completed_{order_id}")])
        elif order_details['status'] == 'completed':
            keyboard.append([InlineKeyboardButton("⏳ Reopen Order (Mark as Pending)", callback_data=f"mark_pending_{order_id}")])
        
        # Navigation buttons
        keyboard.append([
            InlineKeyboardButton("📋 All Orders", callback_data="all_orders"),
            InlineKeyboardButton("⏳ Pending Orders", callback_data="pending_orders")
        ])
        keyboard.append([
            InlineKeyboardButton("✅ Completed Orders", callback_data="completed_orders")
        ])
        keyboard.append([
            InlineKeyboardButton("🔙 Order Management", callback_data="view_orders"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(details_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error viewing order details: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error retrieving order details. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Orders", callback_data="view_orders")]
            ])
        )

# --- Main Function to Run the Bot ---
def main():
    """Main bot function with complete button interface"""
    if not TELEGRAM_SUPPORT:
        print("Please install the required Telegram library.")
        return
    
    print("Blue Pharma Trading PLC - Complete Bot with Buttons")
    print("=" * 65)
    
    try:
        BOT_TOKEN = os.getenv("BOT_TOKEN")
        DB_NAME = os.getenv("DATABASE_PATH")
        
        db = DatabaseManager(DB_NAME)
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Initialize the application
        application.bot_data['db'] = db
        application.bot_data['ADMIN_USER_ID'] = ADMIN_USER_ID
        
        # Add Medicine Conversation
        add_med_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_start_single_add, pattern='^start_single_add$')],
            states={
                MEDICINE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_medicine_name)],
                THERAPEUTIC_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_therapeutic_category)],
                MANUFACTURING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_manufacturing_date)],
                EXPIRING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_expiring_date)],
                DOSAGE_FORM: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_dosage_form)],
                PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_price)],
                STOCK_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_stock_quantity)],
                DUPLICATE_CONFIRMATION: [CallbackQueryHandler(add_therapeutic_category, pattern='^continue_add_'),
                                          CallbackQueryHandler(cancel_conversation, pattern='^cancel_add$')],
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
        )

        # Order Checkout Conversation
        order_checkout_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_collect_customer_info, pattern='^collect_customer_info$')],
            states={
                CUSTOMER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_customer_name)],
                CUSTOMER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_customer_phone)],
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
        )

        # Unified Stock Update Conversation
        stock_update_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(handle_update_stock, pattern='^update_stock$'),
                CallbackQueryHandler(handle_start_stock_update, pattern='^start_stock_update$'),
                CallbackQueryHandler(handle_select_medicine_for_stock_update, pattern='^update_stock_medicine_')
            ],
            states={
                STOCK_UPDATE_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stock_search)],
                STOCK_UPDATE_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stock_quantity_update)],
                STOCK_UPDATE_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stock_update_reason)],
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
        )

        # Unified Price Update Conversation
        price_update_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(handle_update_prices, pattern='^update_prices$'),
                CallbackQueryHandler(handle_price_update_percentage, pattern='^price_update_percentage$'),
                CallbackQueryHandler(handle_price_update_amount, pattern='^price_update_amount$'),
                CallbackQueryHandler(handle_select_medicine_for_price_update, pattern='^price_update_med_')
            ],
            states={
                PRICE_UPDATE_VALUE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_medicine_search),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_percentage_input),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_amount_input)
                ],
                PRICE_MEDICINE_SELECTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_value_input),
                    CallbackQueryHandler(handle_apply_percentage_all, pattern='^apply_percentage_all$'),
                    CallbackQueryHandler(handle_choose_category_percentage, pattern='^choose_category_percentage$'),
                    CallbackQueryHandler(handle_apply_percentage_category, pattern='^apply_percentage_category_'),
                    CallbackQueryHandler(handle_apply_amount_all, pattern='^apply_amount_all$'),
                    CallbackQueryHandler(handle_choose_category_amount, pattern='^choose_category_amount$'),
                    CallbackQueryHandler(handle_apply_amount_category, pattern='^apply_amount_category_')
                ]
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
        )
        
        # PIN Verification Conversation for Medicine Removal
        pin_verification_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(handle_remove_medicine_with_pin, pattern='^remove_medicine_with_pin$'),
                CallbackQueryHandler(handle_remove_all_with_pin, pattern='^remove_all_with_pin$')
            ],
            states={
                PIN_VERIFICATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_pin)],
                REMOVE_SELECTION: [
                    CallbackQueryHandler(handle_confirm_remove_single_medicine, pattern='^confirm_remove_med_'),
                    CallbackQueryHandler(wrapper_handle_manage_stock, pattern='^manage_stock$')
                ],
                REMOVE_ALL_PIN_VERIFICATION: [
                    CallbackQueryHandler(handle_confirm_remove_all_final, pattern='^confirm_remove_all_final$'),
                    CallbackQueryHandler(wrapper_handle_manage_stock, pattern='^manage_stock$')
                ]
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
        )
        
        # Excel Upload with Duplicate Handling Conversation
        excel_upload_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Document.FileExtension("xlsx") & filters.ChatType.PRIVATE, handle_excel_file)],
            states={
                EXCEL_DUPLICATE_CHOICE: [
                    CallbackQueryHandler(handle_excel_update_existing, pattern='^excel_update_existing$'),
                    CallbackQueryHandler(handle_excel_add_as_new, pattern='^excel_add_as_new$'),
                    CallbackQueryHandler(handle_excel_review_each, pattern='^excel_review_each$'),
                    CallbackQueryHandler(handle_excel_skip_duplicates, pattern='^excel_skip_duplicates$'),
                    CallbackQueryHandler(handle_cancel_excel_upload, pattern='^cancel_excel_upload$')
                ]
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
        )
        
        # Order Status Update Conversation
        order_status_update_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_update_order_status_by_number, pattern='^update_status_')],
            states={
                ORDER_STATUS_UPDATE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_order_number_input_for_status)]
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
        )
        
        # Order Details Search Conversation
        order_details_search_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_order_details_search, pattern='^order_details_search$')],
            states={
                ORDER_ID_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_order_id_input)]
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
        )
        
        # Custom Quantity Selection Conversation
        custom_quantity_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_custom_quantity, pattern='^custom_quantity_')],
            states={
                CUSTOM_QUANTITY_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_quantity_input)]
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
        )
        
        # Contact Editing Conversation
        contact_edit_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(handle_edit_phone, pattern='^edit_phone$'),
                CallbackQueryHandler(handle_edit_email, pattern='^edit_email$'),
                CallbackQueryHandler(handle_edit_address, pattern='^edit_address$')
            ],
            states={
                EDIT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone_input)],
                EDIT_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email_input)],
                EDIT_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_address_input)]
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
        )
        
        # Change PIN Conversation (Admin)
        change_pin_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_change_pin, pattern='^change_pin$')],
            states={
                CHANGE_PIN_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_change_pin_input)]
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
        )

        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("search", search_command))
        application.add_handler(CommandHandler("cancel", cancel_conversation))
        
        application.add_handler(add_med_conv)
        application.add_handler(order_checkout_conv)
        application.add_handler(stock_update_conv)
        application.add_handler(price_update_conv)
        application.add_handler(pin_verification_conv)
        application.add_handler(excel_upload_conv)
        application.add_handler(order_status_update_conv)
        application.add_handler(order_details_search_conv)
        application.add_handler(custom_quantity_conv)
        application.add_handler(contact_edit_conv)
        application.add_handler(change_pin_conv)

        application.add_handler(CallbackQueryHandler(button_handler))

        logger.info("Bot is starting...")
        # Initialize the bot before running polling
        asyncio.get_event_loop().run_until_complete(application.initialize())
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Bot has stopped.")

    except Exception as e:
        logger.error(f"Failed to start the bot: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()