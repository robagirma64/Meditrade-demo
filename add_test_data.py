#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add Test Data for Blue Pharma Bot Analytics Testing
This script adds 3 weeks of sample order data for testing Excel analytics features.
"""

import sqlite3
import random
from datetime import datetime, timedelta

# Database connection
DB_NAME = "blue_pharma_v2.db"

def get_connection():
    """Creates and returns a database connection."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def add_test_orders():
    """Add test orders for exactly 3 weeks for weekly comparison testing."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get existing medicines and users
        cursor.execute("SELECT id, name, price FROM medicines WHERE is_active = 1 LIMIT 20")
        medicines = cursor.fetchall()
        
        cursor.execute("SELECT id, first_name, last_name FROM users LIMIT 10")
        users = cursor.fetchall()
        
        if not medicines:
            print("❌ No medicines found in database. Please add medicines first.")
            return 0
        
        if not users:
            print("❌ No users found in database. Please register users first.")
            return 0
        
        # Customer data pools
        customer_names = [
            "Ahmed Hassan", "Fatima Mohamed", "Yusuf Ibrahim", 
            "Aisha Ali", "Omar Farah", "Zeinab Osman",
            "Abdi Rahman", "Maryam Said", "Hassan Noor", "Amina Yusuf",
            "Mohammed Ali", "Sara Ahmed", "Ibrahim Yusuf", "Khadija Omar"
        ]
        customer_phones = [
            "+251912345678", "+251923456789", "+251934567890",
            "+251945678901", "+251956789012", "+251967890123",
            "0912345678", "0923456789", "0934567890", "0945678901",
            "+251987654321", "0976543210", "+251965432109", "0954321098"
        ]
        
        orders_added = 0
        
        # WEEK 1 (3 weeks ago) - Lower activity: 15-20 orders total
        week1_start = datetime.now() - timedelta(weeks=3)
        # Ensure week 1 starts on Monday
        week1_start = week1_start - timedelta(days=week1_start.weekday())
        
        print(f"📅 Week 1: {week1_start.strftime('%Y-%m-%d')} to {(week1_start + timedelta(days=6)).strftime('%Y-%m-%d')}")
        
        for day in range(7):
            current_date = week1_start + timedelta(days=day)
            
            # 2-3 orders per day in week 1
            num_orders = random.randint(2, 3)
            
            for order_num in range(num_orders):
                # Add some hours to spread orders throughout the day
                order_time = current_date + timedelta(hours=random.randint(9, 20), minutes=random.randint(0, 59))
                date_str = order_time.strftime('%Y-%m-%d %H:%M:%S')
                
                user = random.choice(users)
                order_number = f"ORD{int(order_time.timestamp())}{order_num:02d}"
                customer_name = random.choice(customer_names)
                customer_phone = random.choice(customer_phones)
                
                # 1-3 medicines per order in week 1
                num_items = random.randint(1, 3)
                order_total = 0.0
                order_medicines = random.sample(medicines, min(num_items, len(medicines)))
                
                for med in order_medicines:
                    quantity = random.randint(1, 4)  # Lower quantities in week 1
                    order_total += med[2] * quantity
                
                cursor.execute("""
                    INSERT INTO orders (order_number, user_id, total_amount, status, 
                    delivery_method, customer_name, customer_phone, order_date)
                    VALUES (?, ?, ?, ?, 'pickup', ?, ?, ?)
                """, (order_number, user[0], order_total, 
                      random.choice(['pending', 'completed']), 
                      customer_name, customer_phone, date_str))
                
                order_id = cursor.lastrowid
                
                # Insert order items
                for med in order_medicines:
                    quantity = random.randint(1, 4)
                    unit_price = med[2]
                    total_price = unit_price * quantity
                    
                    cursor.execute("""
                        INSERT INTO order_items (order_id, medicine_id, quantity, unit_price, total_price)
                        VALUES (?, ?, ?, ?, ?)
                    """, (order_id, med[0], quantity, unit_price, total_price))
                
                orders_added += 1
        
        # WEEK 2 (2 weeks ago) - Medium activity: 25-30 orders total
        week2_start = datetime.now() - timedelta(weeks=2)
        # Ensure week 2 starts on Monday
        week2_start = week2_start - timedelta(days=week2_start.weekday())
        
        print(f"📅 Week 2: {week2_start.strftime('%Y-%m-%d')} to {(week2_start + timedelta(days=6)).strftime('%Y-%m-%d')}")
        
        for day in range(7):
            current_date = week2_start + timedelta(days=day)
            
            # 3-5 orders per day in week 2
            num_orders = random.randint(3, 5)
            
            for order_num in range(num_orders):
                order_time = current_date + timedelta(hours=random.randint(8, 21), minutes=random.randint(0, 59))
                date_str = order_time.strftime('%Y-%m-%d %H:%M:%S')
                
                user = random.choice(users)
                order_number = f"ORD{int(order_time.timestamp())}{order_num:02d}"
                customer_name = random.choice(customer_names)
                customer_phone = random.choice(customer_phones)
                
                # 1-4 medicines per order in week 2
                num_items = random.randint(1, 4)
                order_total = 0.0
                order_medicines = random.sample(medicines, min(num_items, len(medicines)))
                
                for med in order_medicines:
                    quantity = random.randint(1, 6)  # Medium quantities
                    order_total += med[2] * quantity
                
                cursor.execute("""
                    INSERT INTO orders (order_number, user_id, total_amount, status, 
                    delivery_method, customer_name, customer_phone, order_date)
                    VALUES (?, ?, ?, ?, 'pickup', ?, ?, ?)
                """, (order_number, user[0], order_total, 
                      random.choice(['pending', 'completed']), 
                      customer_name, customer_phone, date_str))
                
                order_id = cursor.lastrowid
                
                for med in order_medicines:
                    quantity = random.randint(1, 6)
                    unit_price = med[2]
                    total_price = unit_price * quantity
                    
                    cursor.execute("""
                        INSERT INTO order_items (order_id, medicine_id, quantity, unit_price, total_price)
                        VALUES (?, ?, ?, ?, ?)
                    """, (order_id, med[0], quantity, unit_price, total_price))
                
                orders_added += 1
        
        # WEEK 3 (1 week ago) - Higher activity: 35-42 orders total
        week3_start = datetime.now() - timedelta(weeks=1)
        # Ensure week 3 starts on Monday
        week3_start = week3_start - timedelta(days=week3_start.weekday())
        
        print(f"📅 Week 3: {week3_start.strftime('%Y-%m-%d')} to {(week3_start + timedelta(days=6)).strftime('%Y-%m-%d')}")
        
        for day in range(7):
            current_date = week3_start + timedelta(days=day)
            
            # 5-6 orders per day in week 3
            num_orders = random.randint(5, 6)
            
            for order_num in range(num_orders):
                order_time = current_date + timedelta(hours=random.randint(8, 22), minutes=random.randint(0, 59))
                date_str = order_time.strftime('%Y-%m-%d %H:%M:%S')
                
                user = random.choice(users)
                order_number = f"ORD{int(order_time.timestamp())}{order_num:02d}"
                customer_name = random.choice(customer_names)
                customer_phone = random.choice(customer_phones)
                
                # 2-5 medicines per order in week 3 (larger orders)
                num_items = random.randint(2, 5)
                order_total = 0.0
                order_medicines = random.sample(medicines, min(num_items, len(medicines)))
                
                for med in order_medicines:
                    quantity = random.randint(2, 8)  # Higher quantities
                    order_total += med[2] * quantity
                
                cursor.execute("""
                    INSERT INTO orders (order_number, user_id, total_amount, status, 
                    delivery_method, customer_name, customer_phone, order_date)
                    VALUES (?, ?, ?, ?, 'pickup', ?, ?, ?)
                """, (order_number, user[0], order_total, 
                      random.choice(['pending', 'completed']), 
                      customer_name, customer_phone, date_str))
                
                order_id = cursor.lastrowid
                
                for med in order_medicines:
                    quantity = random.randint(2, 8)
                    unit_price = med[2]
                    total_price = unit_price * quantity
                    
                    cursor.execute("""
                        INSERT INTO order_items (order_id, medicine_id, quantity, unit_price, total_price)
                        VALUES (?, ?, ?, ?, ?)
                    """, (order_id, med[0], quantity, unit_price, total_price))
                
                orders_added += 1
        
        # Also add some user activity data if the table exists
        try:
            # Check if user_activity table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_activity'")
            if cursor.fetchone():
                # Add user activity data for the same time period
                for weeks_ago in range(3, 0, -1):
                    for day in range(7):
                        activity_date = (datetime.now() - timedelta(weeks=weeks_ago, days=day)).strftime('%Y-%m-%d')
                        
                        # Add activity for random users
                        for user in random.sample(users, min(random.randint(3, 8), len(users))):
                            message_count = random.randint(5, 25)
                            order_count = random.randint(0, 3)
                            
                            cursor.execute("""
                                INSERT OR REPLACE INTO user_activity 
                                (user_id, activity_date, message_count, order_count, last_activity)
                                VALUES (?, ?, ?, ?, ?)
                            """, (user[0], activity_date, message_count, order_count, 
                                  f"{activity_date} {random.randint(9, 21):02d}:{random.randint(0, 59):02d}:00"))
                
                print("✅ User activity data added successfully!")
        except Exception as e:
            print(f"⚠️ Could not add user activity data: {e}")
        
        conn.commit()
        print(f"✅ Successfully added {orders_added} test orders across 3 weeks!")
        
        # Show summary of added data
        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(total_amount) FROM orders")
        total_revenue = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
        pending_orders = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
        completed_orders = cursor.fetchone()[0]
        
        print(f"\n📊 Database Summary:")
        print(f"   📋 Total Orders: {total_orders}")
        print(f"   💰 Total Revenue: {total_revenue:.2f} ETB")
        print(f"   ⏳ Pending Orders: {pending_orders}")
        print(f"   ✅ Completed Orders: {completed_orders}")
        print(f"   📅 Test Data Added: {orders_added} orders")
        
        return orders_added
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error adding test data: {e}")
        return 0
    finally:
        conn.close()

def remove_test_data():
    """Remove test orders (orders from the last 3 weeks)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Calculate date 3 weeks ago
        three_weeks_ago = (datetime.now() - timedelta(weeks=3)).strftime('%Y-%m-%d')
        
        # Count orders to be removed
        cursor.execute("SELECT COUNT(*) FROM orders WHERE order_date >= ?", (three_weeks_ago,))
        orders_to_remove = cursor.fetchone()[0]
        
        if orders_to_remove == 0:
            print("❌ No test orders found to remove.")
            return 0
        
        print(f"🗑️ Found {orders_to_remove} orders from the last 3 weeks to remove...")
        
        # Remove order items first (foreign key constraint)
        cursor.execute("""
            DELETE FROM order_items 
            WHERE order_id IN (
                SELECT id FROM orders WHERE order_date >= ?
            )
        """, (three_weeks_ago,))
        
        # Remove orders
        cursor.execute("DELETE FROM orders WHERE order_date >= ?", (three_weeks_ago,))
        
        # Remove user activity data from the same period if table exists
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_activity'")
            if cursor.fetchone():
                cursor.execute("DELETE FROM user_activity WHERE activity_date >= ?", (three_weeks_ago,))
                print("✅ User activity data removed!")
        except Exception as e:
            print(f"⚠️ Could not remove user activity data: {e}")
        
        conn.commit()
        print(f"✅ Successfully removed {orders_to_remove} test orders!")
        
        return orders_to_remove
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error removing test data: {e}")
        return 0
    finally:
        conn.close()

def main():
    """Main function to add or remove test data."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'remove':
        print("🗑️ Removing test data...")
        removed_count = remove_test_data()
        if removed_count > 0:
            print(f"🎉 Test data cleanup complete! Removed {removed_count} orders.")
        else:
            print("❌ No test data was removed.")
    else:
        print("📊 Adding test data for 3 weeks of orders...")
        added_count = add_test_orders()
        if added_count > 0:
            print(f"🎉 Test data setup complete! Added {added_count} orders.")
            print(f"\n💡 To remove this test data later, run:")
            print(f"   python add_test_data.py remove")
        else:
            print("❌ No test data was added.")

if __name__ == '__main__':
    main()
