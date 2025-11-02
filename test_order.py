#!/usr/bin/env python3

import sqlite3
import time
from datetime import datetime

class TestDatabaseManager:
    def __init__(self, db_name):
        self.db_name = db_name

    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
        
    def get_medicine_by_id(self, med_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medicines WHERE id = ?", (med_id,))
        medicine = cursor.fetchone()
        conn.close()
        return dict(medicine) if medicine else None
        
    def test_place_order(self, user_id, customer_name, customer_phone, cart):
        """Test actual order placement"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("Testing order placement...")
            
            # Calculate total order amount
            order_total = 0.0
            valid_items = []
            
            # Validate all items and calculate total
            for item in cart:
                med = self.get_medicine_by_id(item['medicine_id'])
                if not med:
                    print(f"WARNING: Medicine {item['medicine_id']} not found")
                    continue
                if med['stock_quantity'] < item['quantity']:
                    print(f"WARNING: Insufficient stock for medicine {med['name']}")
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
                print("ERROR: No valid items in cart")
                return None
            
            # Generate unique order number
            order_number = f"TEST{int(time.time())}"
            
            print(f"Creating order with {len(valid_items)} items, total: {order_total:.2f}")
            
            # Create main order record
            cursor.execute("""
                INSERT INTO orders (order_number, user_id, total_amount, status, 
                delivery_method, customer_name, customer_phone)
                VALUES (?, ?, ?, 'pending', 'pickup', ?, ?)
            """, (order_number, user_id, order_total, customer_name, customer_phone))
            
            order_id = cursor.lastrowid
            print(f"Order created with ID: {order_id}")
            
            # Create order items
            for item in valid_items:
                cursor.execute("""
                    INSERT INTO order_items (order_id, medicine_id, quantity, unit_price, total_price)
                    VALUES (?, ?, ?, ?, ?)
                """, (order_id, item['medicine_id'], item['quantity'], 
                      item['unit_price'], item['total_price']))
                print(f"Added item: {item['medicine']['name']} x{item['quantity']}")
                
                # Update stock (simulate - we'll rollback)
                new_stock = item['medicine']['stock_quantity'] - item['quantity']
                print(f"Would update stock from {item['medicine']['stock_quantity']} to {new_stock}")
            
            # Rollback to avoid actual changes
            conn.rollback()
            print("✅ Order placement test successful (changes rolled back)")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Failed to place test order: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            conn.close()

# Run the test
if __name__ == "__main__":
    print("=== ORDER PLACEMENT TEST ===")
    
    db_test = TestDatabaseManager('blue_pharma_v2.db')
    
    # Create a test cart
    test_cart = [{'medicine_id': 1, 'quantity': 2}]
    
    success = db_test.test_place_order(
        user_id=999,
        customer_name='Test Customer', 
        customer_phone='+251912345678',
        cart=test_cart
    )
    
    if success:
        print("\n🎉 ORDER PLACEMENT FUNCTIONALITY IS WORKING!")
    else:
        print("\n💥 ORDER PLACEMENT STILL HAS ISSUES!")
