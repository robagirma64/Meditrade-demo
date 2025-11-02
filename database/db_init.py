"""
Database initialization script for Blue Pharma Trading PLC Telegram Bot
Creates and manages the SQLite database with all necessary tables
"""

# -*- coding: utf-8 -*-
import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path='database/bluepharma.db'):
        self.db_path = db_path
        self.ensure_database_directory()
        self.init_database()
    
    def ensure_database_directory(self):
        """Ensure the database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
    
    def get_connection(self):
        """Get database connection with foreign key support"""
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn
    
    def init_database(self):
        """Initialize database with all required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Users table - stores user information and roles
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
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
                    CONSTRAINT role_check CHECK (role IN ('customer', 'wholesale', 'staff', 'admin'))
                )
            ''')
            
            # Medicines table - simplified 6-field structure
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS medicines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    batch_number TEXT NOT NULL,
                    manufacturing_date DATE NOT NULL,
                    expiring_date DATE NOT NULL,
                    dosage_form TEXT NOT NULL,
                    price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                    stock_quantity INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    CONSTRAINT dosage_form_check CHECK (dosage_form IN ('tablet', 'capsule', 'syrup', 'injection', 'cream', 'ointment', 'drops', 'inhaler', 'powder', 'gel', 'patch', 'spray', 'other'))
                )
            ''')
            
            # Orders table - tracks all orders (retail and wholesale)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    medicine_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price DECIMAL(10,2) NOT NULL,
                    total_amount DECIMAL(10,2) NOT NULL,
                    customer_name TEXT,
                    phone_number TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (medicine_id) REFERENCES medicines (id),
                    CONSTRAINT status_check CHECK (status IN ('pending', 'confirmed', 'processing', 'ready', 'delivered', 'cancelled'))
                )
            ''')
            
            # Inquiries table - logs customer interactions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inquiries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    inquiry_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    response TEXT,
                    handled_by INTEGER,
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (handled_by) REFERENCES users (id),
                    CONSTRAINT inquiry_type_check CHECK (inquiry_type IN ('general', 'product', 'order', 'complaint', 'prescription')),
                    CONSTRAINT inquiry_status_check CHECK (status IN ('open', 'pending', 'resolved', 'closed'))
                )
            ''')
            
            # Wholesale Orders table - multi-item orders
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS wholesale_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    total DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                    status TEXT NOT NULL DEFAULT 'pending',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    CONSTRAINT wholesale_status_check CHECK (status IN ('pending', 'confirmed', 'processing', 'ready', 'delivered', 'cancelled'))
                )
            ''')
            
            # Wholesale Order Items table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS wholesale_order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    medicine_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price DECIMAL(10,2) NOT NULL,
                    subtotal DECIMAL(10,2) NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES wholesale_orders (id) ON DELETE CASCADE,
                    FOREIGN KEY (medicine_id) REFERENCES medicines (id)
                )
            ''')
            
            # Wholesale Cart table - temporary storage for user selections
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS wholesale_cart (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    medicine_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price DECIMAL(10,2) NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (medicine_id) REFERENCES medicines (id),
                    UNIQUE(user_id, medicine_id)
                )
            ''')
            
            # Business Settings table - stores editable business information
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS business_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT NOT NULL UNIQUE,
                    setting_value TEXT NOT NULL,
                    updated_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (updated_by) REFERENCES users (id)
                )
            ''')
            
            # We'll insert business settings after the admin user is created
            # This is done in add_sample_data() to avoid foreign key issues
            
            # Daily Analytics table - stores daily performance metrics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL UNIQUE,
                    total_orders INTEGER DEFAULT 0,
                    retail_orders INTEGER DEFAULT 0,
                    wholesale_orders INTEGER DEFAULT 0,
                    total_revenue DECIMAL(10,2) DEFAULT 0.00,
                    retail_revenue DECIMAL(10,2) DEFAULT 0.00,
                    wholesale_revenue DECIMAL(10,2) DEFAULT 0.00,
                    new_customers INTEGER DEFAULT 0,
                    top_medicine_id INTEGER,
                    top_medicine_sales INTEGER DEFAULT 0,
                    low_stock_alerts INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (top_medicine_id) REFERENCES medicines (id)
                )
            ''')
            
            # Weekly Analytics table - stores weekly summaries
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS weekly_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    week_start DATE NOT NULL,
                    week_end DATE NOT NULL,
                    total_orders INTEGER DEFAULT 0,
                    retail_orders INTEGER DEFAULT 0,
                    wholesale_orders INTEGER DEFAULT 0,
                    total_revenue DECIMAL(10,2) DEFAULT 0.00,
                    retail_revenue DECIMAL(10,2) DEFAULT 0.00,
                    wholesale_revenue DECIMAL(10,2) DEFAULT 0.00,
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
            
            # Audit log table - tracks all important actions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    table_affected TEXT,
                    record_id INTEGER,
                    old_values TEXT,
                    new_values TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
            print("✅ Database tables created successfully!")
            
        except sqlite3.Error as e:
            print(f"❌ Error creating database: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def add_sample_data(self):
        """Add sample data for testing"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Sample medicines
            sample_medicines = [
                ('Paracetamol 500mg', 'Paracetamol', 'Generic', 'Analgesic', 'Pain relief and fever reducer', 5.00, 3.50, 100, 500, 20, 0),
                ('Amoxicillin 250mg', 'Amoxicillin', 'Generic', 'Antibiotic', 'Bacterial infection treatment', 15.00, 10.00, 50, 200, 15, 1),
                ('Ibuprofen 400mg', 'Ibuprofen', 'Advil', 'Anti-inflammatory', 'Pain and inflammation relief', 8.00, 5.50, 75, 300, 25, 0),
                ('Omeprazole 20mg', 'Omeprazole', 'Generic', 'Proton Pump Inhibitor', 'Acid reflux treatment', 12.00, 8.00, 60, 250, 20, 0),
                ('Metformin 500mg', 'Metformin', 'Generic', 'Antidiabetic', 'Diabetes management', 10.00, 7.00, 80, 400, 30, 1),
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO medicines 
                (name, generic_name, brand, category, description, retail_price, wholesale_price, 
                retail_stock, wholesale_stock, min_stock_alert, requires_prescription)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', sample_medicines)
            
            # Admin user with correct telegram_id from config
            cursor.execute('''
                INSERT OR IGNORE INTO users 
                (telegram_id, username, first_name, role, company_name)
                VALUES (7264670729, 'admin', 'System Admin', 'admin', 'Blue Pharma Trading PLC')
            ''')
            
            # Get the admin user ID for business settings
            cursor.execute("SELECT id FROM users WHERE telegram_id = 7264670729")
            admin_user_id = cursor.fetchone()[0]
            
            # Insert default business settings with correct admin user ID
            cursor.execute('''
                INSERT OR IGNORE INTO business_settings (setting_key, setting_value, updated_by) VALUES
                ('business_name', 'Blue Pharma Trading PLC', ?),
                ('contact_phone', '+1-234-567-8900', ?),
                ('contact_email', 'info@bluepharma.com', ?),
                ('address', '123 Pharmacy Street, Medical District, City, State 12345', ?),
                ('business_hours', 'Monday-Friday: 9:00 AM - 6:00 PM, Saturday: 9:00 AM - 2:00 PM', ?)
            ''', (admin_user_id, admin_user_id, admin_user_id, admin_user_id, admin_user_id))
            
            conn.commit()
            print("✅ Sample data added successfully!")
            
        except sqlite3.Error as e:
            print(f"❌ Error adding sample data: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_user_role(self, telegram_id):
        """Get user role by telegram ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT role FROM users WHERE telegram_id = ?", (telegram_id,))
            result = cursor.fetchone()
            return result[0] if result else 'customer'
        except sqlite3.Error:
            return 'customer'
    
    def get_business_setting(self, setting_key: str) -> str:
        """Get a business setting value by key"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT setting_value FROM business_settings WHERE setting_key = ?", (setting_key,))
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"Error getting business setting {setting_key}: {e}")
            return None
        finally:
            conn.close()
    
    def update_business_setting(self, setting_key: str, setting_value: str, updated_by: int) -> bool:
        """Update a business setting value"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get old value for audit log
            cursor.execute("SELECT setting_value FROM business_settings WHERE setting_key = ?", (setting_key,))
            old_result = cursor.fetchone()
            old_value = old_result[0] if old_result else None
            
            # Update the setting
            cursor.execute(
                "UPDATE business_settings SET setting_value = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP WHERE setting_key = ?",
                (setting_value, updated_by, setting_key)
            )
            
            # Log the change
            self.log_audit(
                updated_by, 
                f"Business setting updated: {setting_key}", 
                "business_settings", 
                None, 
                old_value, 
                setting_value
            )
            
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating business setting {setting_key}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_all_business_settings(self) -> dict:
        """Get all business settings as a dictionary"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT setting_key, setting_value FROM business_settings")
            return dict(cursor.fetchall())
        except sqlite3.Error as e:
            print(f"Error getting all business settings: {e}")
            return {}
        finally:
            conn.close()
    
    def create_user(self, telegram_id, username=None, first_name=None, last_name=None, role='customer'):
        """Create a new user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (telegram_id, username, first_name, last_name, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (telegram_id, username, first_name, last_name, role))
            
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error creating user: {e}")
            return None
        finally:
            conn.close()
    
    def log_audit(self, user_id, action, table_affected=None, record_id=None, old_values=None, new_values=None):
        """Log an audit entry"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO audit_logs 
                (user_id, action, table_affected, record_id, old_values, new_values)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, action, table_affected, record_id, old_values, new_values))
            
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error logging audit: {e}")
        finally:
            conn.close()
    
    def calculate_daily_analytics(self, target_date=None):
        """Calculate and store daily analytics for a specific date"""
        from datetime import date, timedelta
        
        if target_date is None:
            target_date = date.today()
        elif isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get daily order statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_orders,
                    COUNT(*) as retail_orders,
                    0 as wholesale_orders,
                    SUM(total_amount) as total_revenue,
                    SUM(total_amount) as retail_revenue,
                    0 as wholesale_revenue
                FROM orders 
                WHERE date(created_at) = ? AND status != 'cancelled'
            """, (target_date,))
            
            order_stats = cursor.fetchone()
            total_orders, retail_orders, wholesale_orders, total_revenue, retail_revenue, wholesale_revenue = order_stats
            
            # Get new customers count for the day
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE date(created_at) = ?
            """, (target_date,))
            new_customers = cursor.fetchone()[0]
            
            # Get top selling medicine for the day
            cursor.execute("""
                SELECT medicine_id, SUM(quantity) as total_sold
                FROM orders 
                WHERE date(created_at) = ? AND status != 'cancelled'
                GROUP BY medicine_id 
                ORDER BY total_sold DESC 
                LIMIT 1
            """, (target_date,))
            
            top_medicine_result = cursor.fetchone()
            top_medicine_id, top_medicine_sales = top_medicine_result if top_medicine_result else (None, 0)
            
            # Get low stock alerts count
            cursor.execute("""
                SELECT COUNT(*) FROM medicines 
                WHERE (retail_stock + wholesale_stock) <= min_stock_alert AND is_active = 1
            """)
            low_stock_alerts = cursor.fetchone()[0]
            
            # Insert or update daily analytics
            cursor.execute("""
                INSERT OR REPLACE INTO daily_analytics 
                (date, total_orders, retail_orders, wholesale_orders, total_revenue, 
                 retail_revenue, wholesale_revenue, new_customers, top_medicine_id, 
                 top_medicine_sales, low_stock_alerts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (target_date, total_orders or 0, retail_orders or 0, wholesale_orders or 0,
                  total_revenue or 0.0, retail_revenue or 0.0, wholesale_revenue or 0.0,
                  new_customers, top_medicine_id, top_medicine_sales or 0, low_stock_alerts))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"Error calculating daily analytics: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def calculate_weekly_analytics(self, week_start_date=None):
        """Calculate and store weekly analytics"""
        from datetime import date, timedelta
        
        if week_start_date is None:
            # Get current week start (Monday)
            today = date.today()
            week_start_date = today - timedelta(days=today.weekday())
        elif isinstance(week_start_date, str):
            week_start_date = datetime.strptime(week_start_date, '%Y-%m-%d').date()
        
        week_end_date = week_start_date + timedelta(days=6)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get weekly order statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_orders,
                    COUNT(*) as retail_orders,
                    0 as wholesale_orders,
                    SUM(total_amount) as total_revenue,
                    SUM(total_amount) as retail_revenue,
                    0 as wholesale_revenue,
                    SUM(quantity) as total_medicines_sold,
                    AVG(total_amount) as avg_order_value,
                    COUNT(DISTINCT user_id) as unique_customers
                FROM orders 
                WHERE date(created_at) BETWEEN ? AND ? AND status != 'cancelled'
            """, (week_start_date, week_end_date))
            
            weekly_stats = cursor.fetchone()
            (total_orders, retail_orders, wholesale_orders, total_revenue, retail_revenue, 
             wholesale_revenue, total_medicines_sold, avg_order_value, unique_customers) = weekly_stats
            
            # Get new customers for the week
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE date(created_at) BETWEEN ? AND ?
            """, (week_start_date, week_end_date))
            new_customers = cursor.fetchone()[0]
            
            # Get top selling medicine for the week
            cursor.execute("""
                SELECT medicine_id, SUM(quantity) as total_sold
                FROM orders 
                WHERE date(created_at) BETWEEN ? AND ? AND status != 'cancelled'
                GROUP BY medicine_id 
                ORDER BY total_sold DESC 
                LIMIT 1
            """, (week_start_date, week_end_date))
            
            top_medicine_result = cursor.fetchone()
            top_medicine_id, top_medicine_sales = top_medicine_result if top_medicine_result else (None, 0)
            
            # Insert or update weekly analytics
            cursor.execute("""
                INSERT OR REPLACE INTO weekly_analytics 
                (week_start, week_end, total_orders, retail_orders, wholesale_orders, 
                 total_revenue, retail_revenue, wholesale_revenue, new_customers, 
                 avg_order_value, top_medicine_id, top_medicine_sales, 
                 total_medicines_sold, unique_customers)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (week_start_date, week_end_date, total_orders or 0, retail_orders or 0, 
                  wholesale_orders or 0, total_revenue or 0.0, retail_revenue or 0.0, 
                  wholesale_revenue or 0.0, new_customers, avg_order_value or 0.0,
                  top_medicine_id, top_medicine_sales or 0, total_medicines_sold or 0, 
                  unique_customers or 0))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"Error calculating weekly analytics: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_daily_analytics(self, target_date=None):
        """Get daily analytics data"""
        from datetime import date
        
        if target_date is None:
            target_date = date.today()
        elif isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT da.*, m.name as top_medicine_name
                FROM daily_analytics da
                LEFT JOIN medicines m ON da.top_medicine_id = m.id
                WHERE da.date = ?
            """, (target_date,))
            
            result = cursor.fetchone()
            if result:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, result))
            return None
            
        except sqlite3.Error as e:
            print(f"Error getting daily analytics: {e}")
            return None
        finally:
            conn.close()
    
    def get_weekly_analytics(self, week_start_date=None):
        """Get weekly analytics data"""
        from datetime import date, timedelta
        
        if week_start_date is None:
            today = date.today()
            week_start_date = today - timedelta(days=today.weekday())
        elif isinstance(week_start_date, str):
            week_start_date = datetime.strptime(week_start_date, '%Y-%m-%d').date()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT wa.*, m.name as top_medicine_name
                FROM weekly_analytics wa
                LEFT JOIN medicines m ON wa.top_medicine_id = m.id
                WHERE wa.week_start = ?
            """, (week_start_date,))
            
            result = cursor.fetchone()
            if result:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, result))
            return None
            
        except sqlite3.Error as e:
            print(f"Error getting weekly analytics: {e}")
            return None
        finally:
            conn.close()
    
    def cleanup_old_analytics(self, days_to_keep=30):
        """Clean up old analytics data"""
        from datetime import date, timedelta
        
        cutoff_date = date.today() - timedelta(days=days_to_keep)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Clean up old daily analytics
            cursor.execute("DELETE FROM daily_analytics WHERE date < ?", (cutoff_date,))
            daily_deleted = cursor.rowcount
            
            # Clean up old weekly analytics (keep last 8 weeks)
            cutoff_week = date.today() - timedelta(weeks=8)
            cursor.execute("DELETE FROM weekly_analytics WHERE week_start < ?", (cutoff_week,))
            weekly_deleted = cursor.rowcount
            
            conn.commit()
            return daily_deleted, weekly_deleted
            
        except sqlite3.Error as e:
            print(f"Error cleaning up analytics: {e}")
            conn.rollback()
            return 0, 0
        finally:
            conn.close()

if __name__ == "__main__":
    # Initialize database
    print("🔧 Initializing Blue Pharma Trading PLC Database...")
    db_manager = DatabaseManager()
    
    # Add sample data
    print("📦 Adding sample data...")
    db_manager.add_sample_data()
    
    print("🎉 Database setup complete!")
    print("📍 Database location: database/bluepharma.db")
