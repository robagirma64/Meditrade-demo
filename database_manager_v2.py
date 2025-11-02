# -*- coding: utf-8 -*-
"""
Blue Pharma Trading PLC - Database Manager (2-Tier System)
Enhanced database operations for the new streamlined bot
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Enhanced Database Manager for 2-Tier Blue Pharma Bot"""
    
    def __init__(self, db_path: str = "blue_pharma.db"):
        self.db_path = db_path
        self.connection = None
        logger.info(f"DatabaseManager initialized with path: {db_path}")
        self.initialize_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
        return conn
    
    def initialize_database(self) -> bool:
        """Initialize database with schema"""
        try:
            # Read and execute schema
            schema_path = Path(__file__).parent / "database_schema.sql"
            if schema_path.exists():
                with open(schema_path, 'r', encoding='utf-8') as file:
                    schema_sql = file.read()
                
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.executescript(schema_sql)
                conn.commit()
                conn.close()
                
                logger.info("Database schema initialized successfully")
                return True
            else:
                logger.error("Database schema file not found")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            return False
    
    def log_audit(self, user_id: int, action: str, table_name: str, record_id: int = None, 
                  old_values: str = None, new_values: str = None) -> bool:
        """Log user actions for audit trail"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO audit_log (user_id, action, table_name, record_id, old_values, new_values)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, action, table_name, record_id, old_values, new_values))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error logging audit: {e}")
            return False
        finally:
            conn.close()
    
    # USER MANAGEMENT METHODS
    
    def create_user(self, telegram_id: int, first_name: str, last_name: str = None, 
                   username: str = None, user_type: str = 'customer') -> Optional[int]:
        """Create new user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO users (telegram_id, username, first_name, last_name, user_type)
                VALUES (?, ?, ?, ?, ?)
            """, (telegram_id, username, first_name, last_name, user_type))
            
            user_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"Created user {user_id} ({user_type}): {first_name}")
            return user_id
            
        except sqlite3.IntegrityError:
            logger.warning(f"User with telegram_id {telegram_id} already exists")
            return None
        except sqlite3.Error as e:
            logger.error(f"Error creating user: {e}")
            return None
        finally:
            conn.close()
    
    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user by Telegram ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT u.*, si.employee_id, si.department, si.position, si.is_admin
                FROM users u
                LEFT JOIN staff_info si ON u.id = si.user_id
                WHERE u.telegram_id = ? AND u.is_active = 1
            """, (telegram_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
            
        except sqlite3.Error as e:
            logger.error(f"Error getting user: {e}")
            return None
        finally:
            conn.close()
    
    def update_user_activity(self, user_id: int) -> bool:
        """Update user's last activity timestamp"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE id = ?
            """, (user_id,))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except sqlite3.Error as e:
            logger.error(f"Error updating user activity: {e}")
            return False
        finally:
            conn.close()
    
    def create_staff_member(self, user_id: int, employee_id: str, department: str, 
                          position: str, is_admin: bool = False) -> bool:
        """Create staff information for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO staff_info (user_id, employee_id, department, position, is_admin, hire_date)
                VALUES (?, ?, ?, ?, ?, CURRENT_DATE)
            """, (user_id, employee_id, department, position, is_admin))
            
            # Update user type to staff
            cursor.execute("UPDATE users SET user_type = 'staff' WHERE id = ?", (user_id,))
            
            conn.commit()
            self.log_audit(user_id, "Staff member created", "staff_info", user_id)
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error creating staff member: {e}")
            return False
        finally:
            conn.close()
    
    def get_users_by_type(self, user_types) -> List[Dict]:
        """Get users by user type(s)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if isinstance(user_types, str):
                # Single user type
                cursor.execute("""
                    SELECT * FROM users 
                    WHERE user_type = ? AND is_active = 1
                    ORDER BY created_at DESC
                """, (user_types,))
            else:
                # Multiple user types
                placeholders = ','.join('?' * len(user_types))
                cursor.execute(f"""
                    SELECT * FROM users 
                    WHERE user_type IN ({placeholders}) AND is_active = 1
                    ORDER BY created_at DESC
                """, user_types)
            
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting users by type: {e}")
            return []
        finally:
            conn.close()
    
    def get_all_users(self, limit: int = 50) -> List[Dict]:
        """Get all users with optional limit"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM users 
                WHERE is_active = 1
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting all users: {e}")
            return []
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM users WHERE id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
            
        except sqlite3.Error as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
        finally:
            conn.close()
    
    def set_user_active(self, user_id: int, is_active: int) -> bool:
        """Set user active status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE users SET is_active = ? WHERE id = ?
            """, (is_active, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except sqlite3.Error as e:
            logger.error(f"Error setting user active status: {e}")
            return False
        finally:
            conn.close()
    
    def update_user_type(self, user_id: int, new_user_type: str) -> bool:
        """Update user type"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE users SET user_type = ? WHERE id = ?
            """, (new_user_type, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except sqlite3.Error as e:
            logger.error(f"Error updating user type: {e}")
            return False
        finally:
            conn.close()
    
    # MEDICINE MANAGEMENT METHODS
    
    def check_duplicate_medicine(self, name: str) -> Optional[Dict]:
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
    
    def check_duplicate(self, name: str) -> Optional[Dict]:
        """Alias for check_duplicate_medicine - Check if medicine with similar name already exists"""
        return self.check_duplicate_medicine(name)
    
    def update_medicine(self, medicine_id: int = None, name: str = None, batch_number: str = None,
                       manufacturing_date: str = None, expiring_date: str = None, dosage_form: str = None, 
                       therapeutic_category: str = None, price: float = None, stock_quantity: int = None, 
                       user_id: int = None) -> bool:
        """Update existing medicine with new data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get old values for audit
            cursor.execute("SELECT * FROM medicines WHERE id = ?", (medicine_id,))
            old_record = dict(cursor.fetchone())
            
            # Build update query dynamically
            updates = []
            values = []
            
            if name is not None:
                updates.append("name = ?")
                values.append(name)
            if batch_number is not None:
                updates.append("batch_number = ?")
                values.append(batch_number)
            if manufacturing_date is not None:
                updates.append("manufacturing_date = ?")
                values.append(manufacturing_date)
            if expiring_date is not None:
                updates.append("expiring_date = ?")
                values.append(expiring_date)
            if dosage_form is not None:
                updates.append("dosage_form = ?")
                values.append(dosage_form)
            if therapeutic_category is not None:
                updates.append("therapeutic_category = ?")
                values.append(therapeutic_category)
            if price is not None:
                updates.append("price = ?")
                values.append(price)
            if stock_quantity is not None:
                updates.append("stock_quantity = ?")
                values.append(stock_quantity)
            
            if not updates:
                return False
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(medicine_id)
            
            cursor.execute(f"""
                UPDATE medicines SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            
            if cursor.rowcount > 0:
                conn.commit()
                
                # Log the update
                if user_id:
                    new_values = {k: v for k, v in zip(['name', 'manufacturing_date', 'expiring_date', 'dosage_form', 'price', 'stock_quantity'], 
                                                     [name, manufacturing_date, expiring_date, dosage_form, price, stock_quantity]) if v is not None}
                    self.log_audit(user_id, "Updated medicine", "medicines", medicine_id, 
                                 str(old_record), str(new_values))
                
                logger.info(f"Updated medicine {medicine_id}: {name or old_record['name']}")
                return True
            
            return False
            
        except sqlite3.Error as e:
            logger.error(f"Error updating medicine: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def add_medicine(self, name: str, batch_number: str = None, manufacturing_date: str = None, 
                    expiring_date: str = None, dosage_form: str = None, 
                    therapeutic_category: str = None, price: float = 0.0, 
                    stock_quantity: int = 0, **kwargs) -> Optional[int]:
        """Add new medicine with complete field support including batch number"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print(f"DEBUG: Adding medicine - Name: '{name}', Category: '{therapeutic_category}', Price: {price}, Stock: {stock_quantity}")  # Debug line
            cursor.execute("""
                INSERT INTO medicines (name, batch_number, manufacturing_date, expiring_date, 
                                     dosage_form, therapeutic_category, price, stock_quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, batch_number, manufacturing_date, expiring_date, dosage_form, therapeutic_category, price, stock_quantity))
            
            medicine_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"Added medicine {medicine_id}: {name}")
            print(f"DEBUG: Successfully added medicine {medicine_id}: {name}")  # Debug line
            return medicine_id
            
        except sqlite3.Error as e:
            logger.error(f"Error adding medicine: {e}")
            return None
        finally:
            conn.close()
    
    def get_medicine(self, medicine_id: int) -> Optional[Dict]:
        """Get medicine by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM medicines WHERE id = ? AND is_active = 1", (medicine_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
            
        except sqlite3.Error as e:
            logger.error(f"Error getting medicine: {e}")
            return None
        finally:
            conn.close()
    
    def search_medicines(self, query: str, limit: int = 20) -> List[Dict]:
        """Search medicines by name (new 6-field structure)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM medicines 
                WHERE is_active = 1 AND name LIKE ?
                ORDER BY name ASC LIMIT ?
            """, (f"%{query}%", limit))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error searching medicines: {e}")
            return []
        finally:
            conn.close()
    
    def get_all_medicines(self, limit: int = None) -> List[Dict]:
        """Get all active medicines (new 7-field structure)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if limit:
                cursor.execute("""
                    SELECT * FROM medicines WHERE is_active = 1
                    ORDER BY name ASC LIMIT ?
                """, (limit,))
            else:
                cursor.execute("""
                    SELECT * FROM medicines WHERE is_active = 1
                    ORDER BY name ASC
                """)
            
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting medicines: {e}")
            return []
        finally:
            conn.close()
    
    def update_medicine_stock(self, medicine_id: int, new_stock: int, user_id: int = None) -> bool:
        """Update medicine stock (new 6-field structure)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get current stock for audit log
            cursor.execute("SELECT stock_quantity FROM medicines WHERE id = ?", (medicine_id,))
            row = cursor.fetchone()
            if not row:
                return False
            
            old_stock = row[0]
            
            cursor.execute("""
                UPDATE medicines SET stock_quantity = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_stock, medicine_id))
            
            conn.commit()
            
            if user_id:
                self.log_audit(user_id, "Stock update", "medicines", medicine_id, 
                             f"stock_quantity: {old_stock}", f"stock_quantity: {new_stock}")
            
            return cursor.rowcount > 0
            
        except sqlite3.Error as e:
            logger.error(f"Error updating medicine stock: {e}")
            return False
        finally:
            conn.close()
    
    # SHOPPING CART METHODS
    
    def add_to_cart(self, user_id: int, medicine_id: int, quantity: int) -> bool:
        """Add item to shopping cart"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get medicine price
            cursor.execute("SELECT price FROM medicines WHERE id = ? AND is_active = 1", 
                         (medicine_id,))
            row = cursor.fetchone()
            if not row:
                return False
            
            unit_price = row[0]
            total_price = unit_price * quantity
            
            # Insert or update cart item
            cursor.execute("""
                INSERT OR REPLACE INTO shopping_cart 
                (user_id, medicine_id, quantity, unit_price, total_price)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, medicine_id, quantity, unit_price, total_price))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error adding to cart: {e}")
            return False
        finally:
            conn.close()
    
    def remove_from_cart(self, user_id: int, medicine_id: int) -> bool:
        """Remove item from shopping cart"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM shopping_cart WHERE user_id = ? AND medicine_id = ?
            """, (user_id, medicine_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except sqlite3.Error as e:
            logger.error(f"Error removing from cart: {e}")
            return False
        finally:
            conn.close()
    
    def get_cart_items(self, user_id: int) -> List[Dict]:
        """Get user's cart items with medicine details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT c.*, m.name, m.dosage_form, m.stock_quantity
                FROM shopping_cart c
                JOIN medicines m ON c.medicine_id = m.id
                WHERE c.user_id = ? AND m.is_active = 1
                ORDER BY c.date_added ASC
            """, (user_id,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting cart items: {e}")
            return []
        finally:
            conn.close()
    
    def clear_cart(self, user_id: int) -> bool:
        """Clear user's shopping cart"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM shopping_cart WHERE user_id = ?", (user_id,))
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error clearing cart: {e}")
            return False
        finally:
            conn.close()
    
    def get_cart_summary(self, user_id: int) -> Dict:
        """Get cart summary with totals"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as item_count,
                    SUM(quantity) as total_quantity,
                    SUM(total_price) as total_amount
                FROM shopping_cart
                WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else {'item_count': 0, 'total_quantity': 0, 'total_amount': 0.0}
            
        except sqlite3.Error as e:
            logger.error(f"Error getting cart summary: {e}")
            return {'item_count': 0, 'total_quantity': 0, 'total_amount': 0.0}
        finally:
            conn.close()
    
    # ORDER MANAGEMENT METHODS
    
    def get_next_order_id(self) -> int:
        """Get the next consecutive order ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get the highest order ID from the orders table
            cursor.execute("SELECT MAX(id) FROM orders")
            result = cursor.fetchone()
            
            if result[0] is None:
                # No orders exist yet, start with 1
                return 1
            else:
                # Return next consecutive ID
                return result[0] + 1
                
        except sqlite3.Error as e:
            logger.error(f"Error getting next order ID: {e}")
            # Fallback to a reasonable default
            return 1
        finally:
            conn.close()
    
    def format_order_id(self, order_id: int) -> str:
        """Format order ID as a clean consecutive string (e.g., '01', '02', '03')"""
        return f"{order_id:02d}"
    
    def create_order(self, user_id: int, delivery_method: str = 'pickup', 
                    delivery_address: str = None, notes: str = None) -> Optional[Tuple[int, str]]:
        """Create order from shopping cart. Returns (order_id, formatted_order_id)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get cart items
            cursor.execute("""
                SELECT medicine_id, quantity, unit_price, total_price
                FROM shopping_cart WHERE user_id = ?
            """, (user_id,))
            
            cart_items = cursor.fetchall()
            if not cart_items:
                return None
            
            # Calculate totals
            total_amount = sum(item[3] for item in cart_items)  # total_price column
            
            # Generate clean order number (keep BP prefix for compatibility but use clean display ID)
            order_number = f"BP{datetime.now().strftime('%Y%m%d%H%M%S')}{user_id:04d}"
            
            # Create order
            cursor.execute("""
                INSERT INTO orders (order_number, user_id, total_amount, delivery_method, 
                                  delivery_address, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (order_number, user_id, total_amount, delivery_method, delivery_address, notes))
            
            order_id = cursor.lastrowid
            
            # Create order items
            for medicine_id, quantity, unit_price, total_price in cart_items:
                cursor.execute("""
                    INSERT INTO order_items (order_id, medicine_id, quantity, unit_price, total_price)
                    VALUES (?, ?, ?, ?, ?)
                """, (order_id, medicine_id, quantity, unit_price, total_price))
            
            # Clear cart
            cursor.execute("DELETE FROM shopping_cart WHERE user_id = ?", (user_id,))
            
            conn.commit()
            
            # Return both internal order_id and formatted display ID
            formatted_id = self.format_order_id(order_id)
            logger.info(f"Created order {order_id} (display: {formatted_id}) for user {user_id}")
            return (order_id, formatted_id)
            
        except sqlite3.Error as e:
            logger.error(f"Error creating order: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_order(self, order_number: str) -> Optional[Dict]:
        """Get order details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT o.*, u.first_name, u.last_name, u.phone_number
                FROM orders o
                JOIN users u ON o.user_id = u.id
                WHERE o.order_number = ?
            """, (order_number,))
            
            order = cursor.fetchone()
            if not order:
                return None
            
            order_dict = dict(order)
            
            # Get order items
            cursor.execute("""
                SELECT oi.*, m.name, m.dosage_form
                FROM order_items oi
                JOIN medicines m ON oi.medicine_id = m.id
                WHERE oi.order_id = ?
            """, (order_dict['id'],))
            
            order_dict['items'] = [dict(row) for row in cursor.fetchall()]
            
            return order_dict
            
        except sqlite3.Error as e:
            logger.error(f"Error getting order: {e}")
            return None
        finally:
            conn.close()
    
    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        """Get order details by order ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT o.*, u.first_name, u.last_name, u.phone_number
                FROM orders o
                JOIN users u ON o.user_id = u.id
                WHERE o.id = ?
            """, (order_id,))
            
            order = cursor.fetchone()
            if not order:
                return None
            
            order_dict = dict(order)
            # Add formatted display ID
            order_dict['display_id'] = self.format_order_id(order_dict['id'])
            
            # Get order items
            cursor.execute("""
                SELECT oi.*, m.name, m.dosage_form
                FROM order_items oi
                JOIN medicines m ON oi.medicine_id = m.id
                WHERE oi.order_id = ?
            """, (order_dict['id'],))
            
            order_dict['items'] = [dict(row) for row in cursor.fetchall()]
            
            return order_dict
            
        except sqlite3.Error as e:
            logger.error(f"Error getting order by ID: {e}")
            return None
        finally:
            conn.close()
    
    def get_all_orders_with_clean_ids(self, limit: int = 50, status_filter: str = None) -> List[Dict]:
        """Get all orders with clean display IDs"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT o.*, u.first_name, u.last_name, u.username
                FROM orders o
                JOIN users u ON o.user_id = u.id
            """
            
            params = []
            if status_filter:
                query += " WHERE o.status = ?"
                params.append(status_filter)
            
            query += " ORDER BY o.created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            orders = [dict(row) for row in cursor.fetchall()]
            
            # Add formatted display IDs
            for order in orders:
                order['display_id'] = self.format_order_id(order['id'])
            
            return orders
            
        except sqlite3.Error as e:
            logger.error(f"Error getting all orders: {e}")
            return []
        finally:
            conn.close()
    
    def update_order_status(self, order_number: str, new_status: str, changed_by: int = None, 
                          change_reason: str = None) -> bool:
        """Update order status"""
        conn = self.get_connection()
        cursor = conn.cursor()
    
    def update_order_status_by_id(self, order_id: int, new_status: str, changed_by: int = None, 
                          change_reason: str = None) -> bool:
        """Update order status by order ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE order_number = ?
            """, (new_status, order_number))
            
            if cursor.rowcount > 0:
                # Get order ID for status history
                cursor.execute("SELECT id FROM orders WHERE order_number = ?", (order_number,))
                order_id = cursor.fetchone()[0]
                
                # Add status history entry (handled by trigger, but we can add reason)
                if changed_by and change_reason:
                    cursor.execute("""
                        UPDATE order_status_history 
                        SET changed_by = ?, change_reason = ?
                        WHERE order_id = ? AND new_status = ? AND changed_by IS NULL
                        ORDER BY changed_at DESC LIMIT 1
                    """, (changed_by, change_reason, order_id, new_status))
                
                conn.commit()
                return True
            
            return False
            
        except sqlite3.Error as e:
            logger.error(f"Error updating order status: {e}")
            return False
        finally:
            conn.close()
    
    def get_user_orders(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get user's orders"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT order_number, total_amount, status, order_date, delivery_method
                FROM orders
                WHERE user_id = ?
                ORDER BY order_date DESC
                LIMIT ?
            """, (user_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting user orders: {e}")
            return []
        finally:
            conn.close()
    
    # NOTIFICATION METHODS
    
    def create_notification(self, user_id: int, title: str, message: str, 
                          notification_type: str = 'info', related_order_id: int = None) -> bool:
        """Create notification for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO notifications (user_id, title, message, type, related_order_id)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, title, message, notification_type, related_order_id))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error creating notification: {e}")
            return False
        finally:
            conn.close()
    
    def get_user_notifications(self, user_id: int, unread_only: bool = False) -> List[Dict]:
        """Get user notifications"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT * FROM notifications 
                WHERE user_id = ? AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """
            
            if unread_only:
                query += " AND is_read = 0"
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, (user_id,))
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting notifications: {e}")
            return []
        finally:
            conn.close()
    
    def mark_notification_read(self, notification_id: int) -> bool:
        """Mark notification as read"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE notifications SET is_read = 1 WHERE id = ?
            """, (notification_id,))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except sqlite3.Error as e:
            logger.error(f"Error marking notification as read: {e}")
            return False
        finally:
            conn.close()
    
    # SETTINGS AND UTILITIES
    
    def get_setting(self, setting_key: str) -> Optional[str]:
        """Get system setting value"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT setting_value FROM settings WHERE setting_key = ?", 
                         (setting_key,))
            row = cursor.fetchone()
            return row[0] if row else None
            
        except sqlite3.Error as e:
            logger.error(f"Error getting setting: {e}")
            return None
        finally:
            conn.close()
    
    def update_setting(self, setting_key: str, setting_value: str) -> bool:
        """Update system setting"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE settings SET setting_value = ?, updated_at = CURRENT_TIMESTAMP
                WHERE setting_key = ?
            """, (setting_value, setting_key))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except sqlite3.Error as e:
            logger.error(f"Error updating setting: {e}")
            return False
        finally:
            conn.close()
    
    def get_categories(self) -> List[str]:
        """Get all medicine categories (dosage forms)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT DISTINCT dosage_form FROM medicines 
                WHERE is_active = 1 AND dosage_form IS NOT NULL 
                ORDER BY dosage_form ASC
            """)
            
            return [row[0] for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting categories: {e}")
            return []
        finally:
            conn.close()
    
    def get_therapeutic_categories(self) -> List[str]:
        """Get all therapeutic categories"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT DISTINCT therapeutic_category FROM medicines 
                WHERE is_active = 1 AND therapeutic_category IS NOT NULL 
                ORDER BY therapeutic_category ASC
            """)
            
            return [row[0] for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting therapeutic categories: {e}")
            return []
        finally:
            conn.close()
    
    # ANALYTICS AND REPORTING METHODS
    
    def get_daily_sales_summary(self, date: str = None) -> Dict:
        """Get daily sales summary for analytics (simplified version)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Use today if no date provided
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
            
            # Get basic daily statistics from orders table
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_orders,
                    COUNT(DISTINCT user_id) as total_customers,
                    COALESCE(SUM(total_amount), 0) as total_revenue,
                    COALESCE(AVG(total_amount), 0) as avg_order_value
                FROM orders 
                WHERE DATE(order_date) = ? AND status != 'cancelled'
            """, (date,))
            
            result = cursor.fetchone()
            summary = {
                'total_orders': result[0] if result[0] else 0,
                'total_customers': result[1] if result[1] else 0,
                'total_revenue': result[2] if result[2] else 0,
                'avg_order_value': result[3] if result[3] else 0,
                'total_items_sold': 0,  # Will calculate from order_items if available
                'top_category': 'Various',  # Default
                'top_medicine': 'Various'   # Default
            }
            
            # Try to get items sold from order_items table
            try:
                cursor.execute("""
                    SELECT COALESCE(SUM(oi.quantity), 0) as total_items
                    FROM orders o
                    JOIN order_items oi ON o.id = oi.order_id
                    WHERE DATE(o.order_date) = ? AND o.status != 'cancelled'
                """, (date,))
                
                items_result = cursor.fetchone()
                if items_result and items_result[0]:
                    summary['total_items_sold'] = items_result[0]
            except:
                pass
            
            # Try to get top category
            try:
                cursor.execute("""
                    SELECT m.therapeutic_category, COUNT(*) as sales_count
                    FROM orders o
                    JOIN order_items oi ON o.id = oi.order_id
                    JOIN medicines m ON oi.medicine_id = m.id
                    WHERE DATE(o.order_date) = ? AND o.status != 'cancelled' 
                    AND m.therapeutic_category IS NOT NULL
                    GROUP BY m.therapeutic_category
                    ORDER BY sales_count DESC
                    LIMIT 1
                """, (date,))
                
                top_category = cursor.fetchone()
                if top_category and top_category[0]:
                    summary['top_category'] = top_category[0]
            except:
                pass
            
            # Try to get top medicine
            try:
                cursor.execute("""
                    SELECT m.name, COUNT(*) as sales_count
                    FROM orders o
                    JOIN order_items oi ON o.id = oi.order_id
                    JOIN medicines m ON oi.medicine_id = m.id
                    WHERE DATE(o.order_date) = ? AND o.status != 'cancelled'
                    GROUP BY m.name
                    ORDER BY sales_count DESC
                    LIMIT 1
                """, (date,))
                
                top_medicine = cursor.fetchone()
                if top_medicine and top_medicine[0]:
                    summary['top_medicine'] = top_medicine[0]
            except:
                pass
            
            return summary
            
        except sqlite3.Error as e:
            logger.error(f"Error getting daily sales summary: {e}")
            return {
                'total_orders': 0,
                'total_customers': 0, 
                'total_revenue': 0,
                'avg_order_value': 0,
                'total_items_sold': 0,
                'top_category': 'N/A',
                'top_medicine': 'N/A'
            }
        finally:
            conn.close()
    
    
    def get_medicine_by_id(self, medicine_id: int) -> Optional[Dict]:
        """Get medicine by ID (alias for get_medicine)"""
        return self.get_medicine(medicine_id)
    
    def delete_medicine_by_id(self, medicine_id: int) -> bool:
        """Delete medicine by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE medicines SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (medicine_id,))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except sqlite3.Error as e:
            logger.error(f"Error deleting medicine: {e}")
            return False
        finally:
            conn.close()
    
    def delete_all_medicines(self) -> bool:
        """Delete all medicines (set inactive)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE medicines SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE is_active = 1
            """)
            
            conn.commit()
            return cursor.rowcount > 0
            
        except sqlite3.Error as e:
            logger.error(f"Error deleting all medicines: {e}")
            return False
        finally:
            conn.close()
    
    def get_medicines_by_category(self, category: str, limit: int = 50) -> List[Dict]:
        """Get medicines by therapeutic category"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM medicines 
                WHERE is_active = 1 AND therapeutic_category = ?
                ORDER BY name ASC LIMIT ?
            """, (category, limit))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting medicines by category: {e}")
            return []
        finally:
            conn.close()
    
    def get_low_stock_medicines(self, limit: int = 50) -> List[Dict]:
        """Get medicines with low stock"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM low_stock_alerts LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting low stock medicines: {e}")
            return []
        finally:
            conn.close()
    
    
    def delete_medicine(self, medicine_id: int, user_id: int = None) -> bool:
        """Delete a single medicine (soft delete)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get medicine details before deletion for audit
            cursor.execute("SELECT name FROM medicines WHERE id = ? AND is_active = 1", (medicine_id,))
            row = cursor.fetchone()
            if not row:
                return False
            
            medicine_name = row[0]
            
            # Perform soft delete
            cursor.execute("""
                UPDATE medicines SET 
                    is_active = 0, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND is_active = 1
            """, (medicine_id,))
            
            if cursor.rowcount > 0:
                conn.commit()
                
                # Log the audit trail
                if user_id:
                    self.log_audit(user_id, "Delete medicine", "medicines", medicine_id, 
                                 f"Medicine: {medicine_name}", "Deleted (set to inactive)")
                
                logger.info(f"Medicine {medicine_id} ({medicine_name}) deleted by user {user_id}")
                return True
            
            return False
            
        except sqlite3.Error as e:
            logger.error(f"Error deleting medicine: {e}")
            return False
        finally:
            conn.close()
    
    # SALES TRACKING METHODS
    
    def record_sale(self, order_id: int, medicine_id: int, medicine_name: str, 
                   therapeutic_category: str, quantity: int, unit_price: float, 
                   total_price: float, customer_id: int, staff_id: int = None) -> bool:
        """Record a sale for statistics tracking"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO sales_records (order_id, medicine_id, medicine_name, therapeutic_category,
                                         quantity, unit_price, total_price, sale_date, 
                                         customer_id, staff_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, DATE('now'), ?, ?)
            """, (order_id, medicine_id, medicine_name, therapeutic_category, 
                  quantity, unit_price, total_price, customer_id, staff_id))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error recording sale: {e}")
            return False
        finally:
            conn.close()
    
    
    def get_weekly_sales_data(self, weeks_back: int = 3) -> List[Dict]:
        """Get weekly sales data for the last N weeks"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    strftime('%Y-%W', sale_date) as week,
                    MIN(sale_date) as week_start,
                    MAX(sale_date) as week_end,
                    COUNT(DISTINCT order_id) as total_orders,
                    SUM(quantity) as total_items_sold,
                    SUM(total_price) as total_revenue,
                    COUNT(DISTINCT customer_id) as total_customers,
                    AVG(total_price) as avg_order_value
                FROM sales_records 
                WHERE sale_date >= DATE('now', '-' || ? || ' weeks')
                GROUP BY strftime('%Y-%W', sale_date)
                ORDER BY week DESC
            """, (weeks_back,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting weekly sales data: {e}")
            return []
        finally:
            conn.close()
    
    def get_category_sales_breakdown(self, date: str = None) -> List[Dict]:
        """Get sales breakdown by therapeutic category"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
            
            cursor.execute("""
                SELECT 
                    therapeutic_category,
                    COUNT(*) as transaction_count,
                    SUM(quantity) as total_quantity,
                    SUM(total_price) as total_revenue,
                    AVG(unit_price) as avg_unit_price
                FROM sales_records 
                WHERE sale_date = ? AND therapeutic_category IS NOT NULL
                GROUP BY therapeutic_category
                ORDER BY total_revenue DESC
            """, (date,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting category sales breakdown: {e}")
            return []
        finally:
            conn.close()


# Global database manager instance
db_manager = None

def initialize_database(db_path: str = "blue_pharma.db"):
    """Initialize the global database manager"""
    global db_manager
    db_manager = DatabaseManager(db_path)
    return db_manager

def get_db():
    """Get the global database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = initialize_database()
    return db_manager
