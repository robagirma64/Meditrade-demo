-- Blue Pharma Trading PLC - Database Schema (2-Tier System)
-- Two-tier user system: Customers and Staff/Admin
-- Includes shopping cart and multi-order functionality

-- Users Table (2-tier system)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT NOT NULL,
    last_name TEXT,
    phone_number TEXT,
    email TEXT,
    user_type TEXT NOT NULL DEFAULT 'customer' CHECK(user_type IN ('customer', 'staff', 'admin')),
    registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Staff-specific information (extends users table for staff)
CREATE TABLE IF NOT EXISTS staff_info (
    user_id INTEGER PRIMARY KEY,
    employee_id TEXT UNIQUE,
    department TEXT,
    position TEXT,
    permissions TEXT, -- JSON string of permissions
    hire_date DATE,
    is_admin BOOLEAN DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Medicines Table (Enhanced with therapeutic category)
CREATE TABLE IF NOT EXISTS medicines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    batch_number TEXT,
    manufacturing_date DATE,
    expiring_date DATE,
    dosage_form TEXT, -- tablet, capsule, syrup, injection, etc.
    therapeutic_category TEXT, -- antibiotics, analgesics, cardiovascular, etc.
    price REAL NOT NULL DEFAULT 0.0,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Shopping Cart Table (multi-order functionality)
CREATE TABLE IF NOT EXISTS shopping_cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    medicine_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price REAL NOT NULL,
    total_price REAL NOT NULL,
    date_added DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
    UNIQUE(user_id, medicine_id) -- One entry per medicine per user
);

-- Orders Table
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    total_amount REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'confirmed', 'processing', 'ready', 'completed', 'cancelled')),
    payment_method TEXT,
    payment_status TEXT DEFAULT 'unpaid' CHECK(payment_status IN ('unpaid', 'paid', 'refunded')),
    delivery_method TEXT DEFAULT 'pickup' CHECK(delivery_method IN ('pickup', 'delivery')),
    delivery_address TEXT,
    delivery_fee REAL DEFAULT 0.0,
    notes TEXT,
    order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    estimated_completion DATETIME,
    completion_date DATETIME,
    created_by INTEGER, -- staff who created/processed the order
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Order Items Table
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    medicine_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    total_price REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE
);

-- Order Status History Table
CREATE TABLE IF NOT EXISTS order_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    changed_by INTEGER, -- user who made the change
    change_reason TEXT,
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'info' CHECK(type IN ('info', 'warning', 'error', 'success')),
    related_order_id INTEGER,
    is_read BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (related_order_id) REFERENCES orders(id) ON DELETE SET NULL
);

-- Audit Log Table (for tracking changes and staff actions)
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id INTEGER,
    old_values TEXT, -- JSON string
    new_values TEXT, -- JSON string
    ip_address TEXT,
    user_agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- System Settings Table
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT UNIQUE NOT NULL,
    setting_value TEXT,
    description TEXT,
    category TEXT DEFAULT 'general',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Customer Feedback Table
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    order_id INTEGER,
    rating INTEGER CHECK(rating BETWEEN 1 AND 5),
    feedback_text TEXT,
    feedback_type TEXT DEFAULT 'general' CHECK(feedback_type IN ('general', 'order', 'medicine', 'service')),
    is_anonymous BOOLEAN DEFAULT 0,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'reviewed', 'resolved')),
    staff_response TEXT,
    responded_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL,
    FOREIGN KEY (responded_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Contact Information Table
CREATE TABLE IF NOT EXISTS contact_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    address TEXT,
    working_hours TEXT,
    emergency_contact TEXT,
    website TEXT,
    social_media TEXT, -- JSON string
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Prescription Requirements Table
CREATE TABLE IF NOT EXISTS prescription_requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    medicine_id INTEGER NOT NULL,
    prescription_image_path TEXT,
    prescription_verified BOOLEAN DEFAULT 0,
    verified_by INTEGER,
    verification_date DATETIME,
    verification_notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
    FOREIGN KEY (verified_by) REFERENCES users(id) ON DELETE SET NULL
);

-- User Sessions Table (for conversation state management)
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_data TEXT, -- JSON string to store conversation state
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Sales Tracking Table (for statistics and reporting)
CREATE TABLE IF NOT EXISTS sales_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    medicine_id INTEGER NOT NULL,
    medicine_name TEXT NOT NULL,
    therapeutic_category TEXT,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    total_price REAL NOT NULL,
    sale_date DATE NOT NULL,
    sale_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    customer_id INTEGER NOT NULL,
    staff_id INTEGER,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE SET NULL,
    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (staff_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Daily Sales Summary Table (for quick daily statistics)
CREATE TABLE IF NOT EXISTS daily_sales_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_date DATE UNIQUE NOT NULL,
    total_orders INTEGER DEFAULT 0,
    total_items_sold INTEGER DEFAULT 0,
    total_revenue REAL DEFAULT 0.0,
    total_customers INTEGER DEFAULT 0,
    avg_order_value REAL DEFAULT 0.0,
    top_category TEXT,
    top_medicine TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Weekly Sales Summary Table (for weekly comparisons)
CREATE TABLE IF NOT EXISTS weekly_sales_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start_date DATE NOT NULL,
    week_end_date DATE NOT NULL,
    week_number INTEGER NOT NULL,
    year INTEGER NOT NULL,
    total_orders INTEGER DEFAULT 0,
    total_items_sold INTEGER DEFAULT 0,
    total_revenue REAL DEFAULT 0.0,
    total_customers INTEGER DEFAULT 0,
    avg_daily_revenue REAL DEFAULT 0.0,
    growth_percentage REAL DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(week_number, year)
);

-- Database Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_type ON users(user_type);
CREATE INDEX IF NOT EXISTS idx_medicines_active ON medicines(is_active);
CREATE INDEX IF NOT EXISTS idx_medicines_name ON medicines(name);
CREATE INDEX IF NOT EXISTS idx_medicines_category ON medicines(therapeutic_category);
CREATE INDEX IF NOT EXISTS idx_shopping_cart_user ON shopping_cart(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_date ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_sales_records_date ON sales_records(sale_date);
CREATE INDEX IF NOT EXISTS idx_sales_records_category ON sales_records(therapeutic_category);
CREATE INDEX IF NOT EXISTS idx_daily_sales_date ON daily_sales_summary(sale_date);
CREATE INDEX IF NOT EXISTS idx_weekly_sales_year ON weekly_sales_summary(year, week_number);

-- Views for Common Queries

-- Active medicines with stock info (New 6-field structure)
CREATE VIEW IF NOT EXISTS active_medicines AS
SELECT 
    id, name, batch_number, manufacturing_date, expiring_date,
    dosage_form, price, stock_quantity,
    CASE WHEN stock_quantity <= 10 THEN 1 ELSE 0 END as low_stock
FROM medicines 
WHERE is_active = 1;

-- Customer order summary
CREATE VIEW IF NOT EXISTS customer_orders AS
SELECT 
    o.id, o.order_number, o.total_amount, o.status,
    o.payment_status, o.delivery_method, o.order_date,
    u.first_name, u.last_name, u.phone_number,
    COUNT(oi.id) as item_count
FROM orders o
JOIN users u ON o.user_id = u.id
LEFT JOIN order_items oi ON o.id = oi.order_id
WHERE u.user_type = 'customer'
GROUP BY o.id;

-- Staff performance view
CREATE VIEW IF NOT EXISTS staff_performance AS
SELECT 
    u.id, u.first_name, u.last_name, si.department, si.position,
    COUNT(o.id) as orders_processed,
    SUM(o.total_amount) as total_sales,
    AVG(o.total_amount) as avg_order_value
FROM users u
JOIN staff_info si ON u.id = si.user_id
LEFT JOIN orders o ON u.id = o.created_by
WHERE u.user_type = 'staff'
GROUP BY u.id;

-- Low stock alerts (New 6-field structure)
CREATE VIEW IF NOT EXISTS low_stock_alerts AS
SELECT 
    id, name, batch_number, stock_quantity,
    (10 - stock_quantity) as stock_deficit
FROM medicines 
WHERE is_active = 1 AND stock_quantity <= 10
ORDER BY stock_deficit DESC;

-- Insert default settings
INSERT OR IGNORE INTO settings (setting_key, setting_value, description, category) VALUES
('pharmacy_name', 'Blue Pharma Trading PLC', 'Name of the pharmacy', 'general'),
('working_hours', '08:00-22:00', 'Daily working hours', 'general'),
('delivery_fee', '5.00', 'Standard delivery fee', 'delivery'),
('min_order_delivery', '50.00', 'Minimum order for free delivery', 'delivery'),
('prescription_required_categories', 'Antibiotics,Controlled Substances', 'Categories requiring prescription', 'medical'),
('max_cart_items', '50', 'Maximum items in shopping cart', 'orders'),
('order_timeout_hours', '24', 'Hours before pending orders timeout', 'orders'),
('notification_retention_days', '30', 'Days to keep notifications', 'system'),
('audit_retention_days', '365', 'Days to keep audit logs', 'system'),
('backup_frequency_hours', '24', 'Hours between database backups', 'system');

-- Insert default contact information
INSERT OR IGNORE INTO contact_info (name, phone, email, address, working_hours, emergency_contact, website) VALUES
('Blue Pharma Trading PLC', '+251-11-xxx-xxxx', 'info@bluepharma.et', 'Addis Ababa, Ethiopia', '08:00-22:00 Daily', '+251-91-xxx-xxxx', 'www.bluepharma.et');

-- Create triggers for automatic timestamp updates
CREATE TRIGGER IF NOT EXISTS update_users_timestamp 
    AFTER UPDATE ON users
    FOR EACH ROW
    BEGIN
        UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_medicines_timestamp 
    AFTER UPDATE ON medicines
    FOR EACH ROW
    BEGIN
        UPDATE medicines SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_shopping_cart_timestamp 
    AFTER UPDATE ON shopping_cart
    FOR EACH ROW
    BEGIN
        UPDATE shopping_cart SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_orders_timestamp 
    AFTER UPDATE ON orders
    FOR EACH ROW
    BEGIN
        UPDATE orders SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Trigger to automatically create order status history
CREATE TRIGGER IF NOT EXISTS order_status_change
    AFTER UPDATE OF status ON orders
    FOR EACH ROW
    WHEN NEW.status != OLD.status
    BEGIN
        INSERT INTO order_status_history (order_id, old_status, new_status, changed_at)
        VALUES (NEW.id, OLD.status, NEW.status, CURRENT_TIMESTAMP);
    END;

-- Trigger to clean up expired user sessions
CREATE TRIGGER IF NOT EXISTS cleanup_expired_sessions
    AFTER INSERT ON user_sessions
    FOR EACH ROW
    BEGIN
        DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP;
    END;
