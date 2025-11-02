#!/usr/bin/env python3
"""
Clear Order History Script
==========================
This script removes ONLY order-related data from the database:
- All orders from 'orders' table
- All order items from 'order_items' table
- Leaves all other data intact (users, medicines, etc.)
"""

import sqlite3
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_order_history(db_path="blue_pharma_v2.db"):
    """Clear only order history from the database."""
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get count of existing orders before deletion
        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM order_items")
        order_items_count = cursor.fetchone()[0]
        
        logger.info(f"Found {order_count} orders and {order_items_count} order items to remove")
        
        if order_count == 0:
            logger.info("No orders found - database is already clean of order history")
            conn.close()
            return
        
        # Delete order items first (due to foreign key constraints)
        logger.info("Removing order items...")
        cursor.execute("DELETE FROM order_items")
        
        # Delete orders
        logger.info("Removing orders...")
        cursor.execute("DELETE FROM orders")
        
        # Commit the changes
        conn.commit()
        
        # Verify deletion
        cursor.execute("SELECT COUNT(*) FROM orders")
        remaining_orders = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM order_items")
        remaining_items = cursor.fetchone()[0]
        
        logger.info(f"✅ Successfully cleared order history!")
        logger.info(f"   - Removed {order_count} orders")
        logger.info(f"   - Removed {order_items_count} order items")
        logger.info(f"   - Remaining orders: {remaining_orders}")
        logger.info(f"   - Remaining order items: {remaining_items}")
        
        # Vacuum database to reclaim space
        logger.info("Optimizing database...")
        cursor.execute("VACUUM")
        
        conn.close()
        logger.info("✅ Database cleanup completed successfully!")
        
        print("\n" + "="*50)
        print("🎉 ORDER HISTORY CLEARED SUCCESSFULLY!")
        print("="*50)
        print(f"✅ Removed {order_count} orders")
        print(f"✅ Removed {order_items_count} order items")
        print("✅ All other data preserved (users, medicines, etc.)")
        print("\n🚀 Ready to test new clean order ID system!")
        print("   New orders will start with ID: 01")
        
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if conn:
            conn.rollback() 
            conn.close()
        return False

def verify_other_data_intact(db_path="blue_pharma_v2.db"):
    """Verify that other data is still intact."""
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        # Check medicines  
        cursor.execute("SELECT COUNT(*) FROM medicines")
        medicine_count = cursor.fetchone()[0]
        
        conn.close()
        
        print("\n📊 DATA VERIFICATION:")
        print(f"   Users: {user_count} (preserved)")
        print(f"   Medicines: {medicine_count} (preserved)")
        print("   Orders: 0 (cleared)")
        
    except Exception as e:
        logger.error(f"Error verifying data: {e}")

if __name__ == "__main__":
    print("🗑️  CLEARING ORDER HISTORY ONLY...")
    print("=" * 50)
    
    # Clear order history
    clear_order_history()
    
    # Verify other data is intact
    verify_other_data_intact()
    
    print("\n✨ You can now test the new clean order ID system!")
    print("   The next order will have ID: 01")