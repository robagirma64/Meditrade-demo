"""
Migration script to add customer_name field and remove delivery_address from orders table
- Adds customer_name column to orders table
- Removes delivery_address column from orders table
- Preserves phone_number column
"""

import sqlite3
import os
from datetime import datetime

class AddCustomerNameMigration:
    def __init__(self, db_path='database/bluepharma.db'):
        self.db_path = db_path
        self.backup_path = f'database/backup_customer_name_{datetime.now().strftime("%Y%m%d_%H%M%S")}_bluepharma.db'
        
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
    
    def migrate_orders_table(self):
        """Update orders table: add customer_name and remove delivery_address"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("🔄 Migrating orders table...")
            
            # Create new orders table with customer_name instead of delivery_address
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
                    customer_name TEXT,
                    phone_number TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (medicine_id) REFERENCES medicines (id),
                    CONSTRAINT status_check CHECK (status IN ('pending', 'confirmed', 'processing', 'ready', 'delivered', 'cancelled'))
                )
            ''')
            
            # Migrate existing orders (extract name from user data for customer_name)
            cursor.execute('''
                INSERT INTO orders_new (
                    id, user_id, medicine_id, quantity, unit_price, total_amount, status,
                    notes, created_at, updated_at, customer_name, phone_number
                )
                SELECT 
                    o.id, o.user_id, o.medicine_id, o.quantity, o.unit_price, o.total_amount, o.status,
                    o.notes, o.created_at, o.updated_at, 
                    COALESCE(u.first_name, u.username, 'Customer ' || o.user_id) as customer_name,
                    o.phone_number
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.id
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
    
    def run_migration(self):
        """Run the complete migration"""
        print("🚀 Starting customer_name field migration...")
        print(f"📍 Database: {self.db_path}")
        
        # Create backup
        if not self.backup_database():
            print("❌ Migration aborted - could not create backup")
            return False
        
        success = True
        
        # Run migration step
        print(f"\n📋 Migrating orders table...")
        if not self.migrate_orders_table():
            print(f"❌ Migration failed at: orders table")
            success = False
        
        if success:
            print(f"\n🎉 Migration completed successfully!")
            print(f"📁 Original database backed up to: {self.backup_path}")
            print("\n✅ Changes applied:")
            print("  • Added customer_name field to orders table")
            print("  • Removed delivery_address field from orders table") 
            print("  • Preserved phone_number field")
            print("  • Populated customer_name from user data")
        else:
            print(f"\n❌ Migration failed!")
            print(f"💡 Restore from backup if needed: {self.backup_path}")
        
        return success

def main():
    """Run the migration"""
    migration = AddCustomerNameMigration()
    return migration.run_migration()

if __name__ == "__main__":
    main()
