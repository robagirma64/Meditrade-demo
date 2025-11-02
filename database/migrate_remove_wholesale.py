"""
Migration script to remove wholesale functionality from Blue Pharma Database
- Removes wholesale-related tables and columns
- Converts to single price and stock system
- Updates currency to Ethiopian Birr (ETB)
"""

import sqlite3
import os
from datetime import datetime

class RemoveWholesaleMigration:
    def __init__(self, db_path='database/bluepharma.db'):
        self.db_path = db_path
        self.backup_path = f'database/backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}_bluepharma.db'
        
    def backup_database(self):
        """Create a backup of the current database"""
        try:
            import shutil
            shutil.copy2(self.db_path, self.backup_path)
            print(f"✅ Database backed up to: {self.backup_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to backup database: {e}")
            return False
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path, timeout=30)
    
    def migrate_medicines_table(self):
        """Update medicines table: remove wholesale columns, rename retail to single price/stock"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("🔄 Migrating medicines table...")
            
            # Create new medicines table with single price/stock
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS medicines_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    manufacturing_date DATE,
                    expire_date DATE,
                    batch_number TEXT,
                    manufacturing_country TEXT,
                    generic_name TEXT,
                    brand TEXT,
                    category TEXT,
                    description TEXT,
                    type TEXT DEFAULT 'tablet',
                    price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                    stock INTEGER NOT NULL DEFAULT 0,
                    min_stock_alert INTEGER DEFAULT 10,
                    requires_prescription BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    CONSTRAINT type_check CHECK (type IN ('tablet', 'capsule', 'syrup', 'injection', 'cream', 'ointment', 'drops', 'inhaler', 'other'))
                )
            ''')
            
            # Migrate data - use retail_price as price, combine retail+wholesale stock
            cursor.execute('''
                INSERT INTO medicines_new (
                    id, name, manufacturing_date, expire_date, batch_number, manufacturing_country,
                    generic_name, brand, category, description, type, price, stock, 
                    min_stock_alert, requires_prescription, created_at, updated_at, is_active
                )
                SELECT 
                    id, name, NULL as manufacturing_date, expiry_date as expire_date, 
                    NULL as batch_number, NULL as manufacturing_country,
                    generic_name, brand, category, description, type, 
                    retail_price as price, 
                    (retail_stock + wholesale_stock) as stock, 
                    min_stock_alert, requires_prescription, created_at, updated_at, is_active
                FROM medicines
            ''')
            
            # Drop old table and rename new one
            cursor.execute('DROP TABLE medicines')
            cursor.execute('ALTER TABLE medicines_new RENAME TO medicines')
            
            print("✅ Medicines table migrated successfully")
            conn.commit()
            
        except sqlite3.Error as e:
            print(f"❌ Error migrating medicines table: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
        
        return True
    
    def migrate_orders_table(self):
        """Update orders table to remove wholesale order types and use single price"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("🔄 Migrating orders table...")
            
            # Create new orders table without wholesale
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    medicine_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price DECIMAL(10,2) NOT NULL,
                    total_amount DECIMAL(10,2) NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    delivery_address TEXT,
                    phone_number TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (medicine_id) REFERENCES medicines (id),
                    CONSTRAINT status_check CHECK (status IN ('pending', 'confirmed', 'processing', 'ready', 'delivered', 'cancelled'))
                )
            ''')
            
            # Migrate existing orders (keep all orders but remove order_type column)
            cursor.execute('''
                INSERT INTO orders_new (
                    id, user_id, medicine_id, quantity, unit_price, total_amount, status,
                    notes, created_at, updated_at, delivery_address, phone_number
                )
                SELECT 
                    id, user_id, medicine_id, quantity, unit_price, total_amount, status,
                    notes, created_at, updated_at, delivery_address, phone_number
                FROM orders
            ''')
            
            # Drop old table and rename new one
            cursor.execute('DROP TABLE orders')
            cursor.execute('ALTER TABLE orders_new RENAME TO orders')
            
            print("✅ Orders table migrated successfully")
            conn.commit()
            
        except sqlite3.Error as e:
            print(f"❌ Error migrating orders table: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
        
        return True
    
    def update_user_roles(self):
        """Remove wholesale role, convert wholesale users to customers"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("🔄 Updating user roles...")
            
            # Convert wholesale users to customers
            cursor.execute("UPDATE users SET role = 'customer' WHERE role = 'wholesale'")
            wholesale_converted = cursor.rowcount
            
            # Update role constraint to remove wholesale
            # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    role TEXT NOT NULL DEFAULT 'customer',
                    company_name TEXT,
                    phone TEXT,
                    email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    CONSTRAINT role_check CHECK (role IN ('customer', 'staff', 'admin'))
                )
            ''')
            
            # Migrate user data
            cursor.execute('''
                INSERT INTO users_new (
                    id, telegram_id, username, first_name, last_name, role,
                    company_name, phone, email, created_at, last_active, is_active
                )
                SELECT 
                    id, telegram_id, username, first_name, last_name, role,
                    company_name, phone, email, created_at, last_active, is_active
                FROM users
            ''')
            
            # Drop old table and rename new one
            cursor.execute('DROP TABLE users')
            cursor.execute('ALTER TABLE users_new RENAME TO users')
            
            print(f"✅ User roles updated - {wholesale_converted} wholesale users converted to customers")
            conn.commit()
            
        except sqlite3.Error as e:
            print(f"❌ Error updating user roles: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
        
        return True
    
    def remove_wholesale_tables(self):
        """Drop wholesale-specific tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("🔄 Removing wholesale-specific tables...")
            
            # Drop wholesale tables
            tables_to_drop = [
                'wholesale_cart',
                'wholesale_order_items',
                'wholesale_orders'
            ]
            
            for table in tables_to_drop:
                try:
                    cursor.execute(f'DROP TABLE IF EXISTS {table}')
                    print(f"  ✅ Dropped table: {table}")
                except sqlite3.Error as e:
                    print(f"  ⚠️ Could not drop {table}: {e}")
            
            conn.commit()
            print("✅ Wholesale tables removed successfully")
            
        except sqlite3.Error as e:
            print(f"❌ Error removing wholesale tables: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
        
        return True
    
    def update_analytics_tables(self):
        """Update analytics tables to remove wholesale columns"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("🔄 Updating analytics tables...")
            
            # Update daily_analytics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_analytics_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL UNIQUE,
                    total_orders INTEGER DEFAULT 0,
                    total_revenue DECIMAL(10,2) DEFAULT 0.00,
                    new_customers INTEGER DEFAULT 0,
                    top_medicine_id INTEGER,
                    top_medicine_sales INTEGER DEFAULT 0,
                    low_stock_alerts INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (top_medicine_id) REFERENCES medicines (id)
                )
            ''')
            
            # Migrate daily analytics data (combine retail and wholesale)
            cursor.execute('''
                INSERT INTO daily_analytics_new (
                    id, date, total_orders, total_revenue, new_customers,
                    top_medicine_id, top_medicine_sales, low_stock_alerts, created_at
                )
                SELECT 
                    id, date, total_orders, (retail_revenue + wholesale_revenue) as total_revenue, 
                    new_customers, top_medicine_id, top_medicine_sales, low_stock_alerts, created_at
                FROM daily_analytics
            ''')
            
            # Drop old and rename
            cursor.execute('DROP TABLE daily_analytics')
            cursor.execute('ALTER TABLE daily_analytics_new RENAME TO daily_analytics')
            
            # Update weekly_analytics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS weekly_analytics_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    week_start DATE NOT NULL,
                    week_end DATE NOT NULL,
                    total_orders INTEGER DEFAULT 0,
                    total_revenue DECIMAL(10,2) DEFAULT 0.00,
                    new_customers INTEGER DEFAULT 0,
                    avg_order_value DECIMAL(10,2) DEFAULT 0.00,
                    top_medicine_id INTEGER,
                    top_medicine_sales INTEGER DEFAULT 0,
                    total_medicines_sold INTEGER DEFAULT 0,
                    unique_customers INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (top_medicine_id) REFERENCES medicines (id)
                )
            ''')
            
            # Migrate weekly analytics data (combine retail and wholesale)
            cursor.execute('''
                INSERT INTO weekly_analytics_new (
                    id, week_start, week_end, total_orders, total_revenue, new_customers,
                    avg_order_value, top_medicine_id, top_medicine_sales, 
                    total_medicines_sold, unique_customers, created_at
                )
                SELECT 
                    id, week_start, week_end, total_orders, 
                    (retail_revenue + wholesale_revenue) as total_revenue, new_customers,
                    avg_order_value, top_medicine_id, top_medicine_sales, 
                    total_medicines_sold, unique_customers, created_at
                FROM weekly_analytics
            ''')
            
            # Drop old and rename
            cursor.execute('DROP TABLE weekly_analytics')
            cursor.execute('ALTER TABLE weekly_analytics_new RENAME TO weekly_analytics')
            
            print("✅ Analytics tables updated successfully")
            conn.commit()
            
        except sqlite3.Error as e:
            print(f"❌ Error updating analytics tables: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
        
        return True
    
    def update_business_settings_currency(self):
        """Update business settings to use Ethiopian Birr"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("🔄 Updating business settings for Ethiopian Birr...")
            
            # Add currency setting
            cursor.execute('''
                INSERT OR REPLACE INTO business_settings (setting_key, setting_value, updated_by) 
                SELECT 'currency_symbol', 'ETB', id FROM users WHERE role = 'admin' LIMIT 1
            ''')
            
            cursor.execute('''
                INSERT OR REPLACE INTO business_settings (setting_key, setting_value, updated_by) 
                SELECT 'currency_name', 'Ethiopian Birr', id FROM users WHERE role = 'admin' LIMIT 1
            ''')
            
            # Update business name and address for Ethiopian context if needed
            cursor.execute('''
                UPDATE business_settings 
                SET setting_value = 'Blue Pharma Trading PLC - Ethiopia' 
                WHERE setting_key = 'business_name'
            ''')
            
            print("✅ Business settings updated for Ethiopian Birr")
            conn.commit()
            
        except sqlite3.Error as e:
            print(f"❌ Error updating business settings: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
        
        return True
    
    def clean_audit_logs(self):
        """Clean up audit logs related to wholesale functionality"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("🔄 Cleaning up audit logs...")
            
            # Remove wholesale-related audit entries
            cursor.execute('''
                DELETE FROM audit_logs 
                WHERE action LIKE '%wholesale%' 
                   OR table_affected IN ('wholesale_orders', 'wholesale_order_items', 'wholesale_cart')
            ''')
            
            cleaned_entries = cursor.rowcount
            print(f"✅ Cleaned {cleaned_entries} wholesale-related audit log entries")
            conn.commit()
            
        except sqlite3.Error as e:
            print(f"❌ Error cleaning audit logs: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
        
        return True
    
    def run_migration(self):
        """Run the complete migration"""
        print("🚀 Starting wholesale removal migration...")
        print(f"📍 Database: {self.db_path}")
        
        # Create backup
        if not self.backup_database():
            print("❌ Migration aborted - could not create backup")
            return False
        
        success = True
        
        # Run migration steps
        steps = [
            ("Migrating medicines table", self.migrate_medicines_table),
            ("Migrating orders table", self.migrate_orders_table),
            ("Updating user roles", self.update_user_roles),
            ("Removing wholesale tables", self.remove_wholesale_tables),
            ("Updating analytics tables", self.update_analytics_tables),
            ("Updating currency settings", self.update_business_settings_currency),
            ("Cleaning audit logs", self.clean_audit_logs)
        ]
        
        for step_name, step_function in steps:
            print(f"\n📋 {step_name}...")
            if not step_function():
                print(f"❌ Migration failed at: {step_name}")
                success = False
                break
        
        if success:
            print(f"\n🎉 Migration completed successfully!")
            print(f"📁 Original database backed up to: {self.backup_path}")
            print("\n✅ Changes applied:")
            print("  • Removed wholesale functionality")
            print("  • Combined retail and wholesale stock into single stock")
            print("  • Updated prices to single price system")
            print("  • Converted wholesale users to customers")
            print("  • Updated currency to Ethiopian Birr (ETB)")
            print("  • Cleaned up related data")
        else:
            print(f"\n❌ Migration failed!")
            print(f"💡 Restore from backup if needed: {self.backup_path}")
        
        return success

def main():
    """Run the migration"""
    migration = RemoveWholesaleMigration()
    return migration.run_migration()

if __name__ == "__main__":
    main()
