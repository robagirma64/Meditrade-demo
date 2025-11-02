"""
Enhanced logging and error handling for Blue Pharma Trading PLC Telegram Bot
"""

# -*- coding: utf-8 -*-
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from config.config import config
from error_handlers import ErrorHandler, global_error_handler

def setup_logging():
    """Set up comprehensive logging for the bot"""
    
    # Ensure log directory exists
    log_dir = os.path.dirname(config.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Console handler (for immediate feedback)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation (for persistent logging)
    file_handler = logging.handlers.RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Error file handler (for errors only)
    error_handler = logging.handlers.RotatingFileHandler(
        config.LOG_FILE.replace('.log', '_errors.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # Reduce noise from external libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    
    return root_logger

def log_user_action(user_id: int, username: str, action: str, details: str = None):
    """Log user actions for audit trail"""
    logger = logging.getLogger('user_actions')
    
    log_message = f"User {user_id} (@{username}) - {action}"
    if details:
        log_message += f" - {details}"
    
    logger.info(log_message)

def log_database_operation(operation: str, table: str, record_id: int = None, success: bool = True, error: str = None):
    """Log database operations"""
    logger = logging.getLogger('database')
    
    log_message = f"DB {operation} on {table}"
    if record_id:
        log_message += f" (ID: {record_id})"
    
    if success:
        logger.info(f"{log_message} - SUCCESS")
    else:
        logger.error(f"{log_message} - FAILED: {error}")

def log_business_event(event_type: str, details: dict):
    """Log important business events"""
    logger = logging.getLogger('business')
    
    log_message = f"BUSINESS EVENT - {event_type}: {details}"
    logger.info(log_message)

def log_security_event(event_type: str, user_id: int, details: str):
    """Log security-related events"""
    logger = logging.getLogger('security')
    
    log_message = f"SECURITY - {event_type} - User {user_id}: {details}"
    logger.warning(log_message)

class BotErrorHandler:
    """Enhanced error handling for bot operations"""
    
    def __init__(self, db_manager=None):
        self.logger = logging.getLogger('error_handler')
        self.error_handler = ErrorHandler(db_manager)
    
    async def handle_command_error(self, update, context, command_name: str, error: Exception):
        """Handle command execution errors"""
        user_id = update.effective_user.id if update.effective_user else None
        username = update.effective_user.username if update.effective_user else "Unknown"
        
        # Use enhanced error handler
        error_id, user_message = self.error_handler.log_error(
            error,
            {
                "command": command_name,
                "username": username,
                "chat_id": update.effective_chat.id if update.effective_chat else None
            },
            user_id
        )
        
        # Send user-friendly error message
        if update.message:
            await update.message.reply_text(
                f"❌ {user_message}\n\nError ID: `{error_id}`",
                parse_mode='Markdown'
            )
        
        return f"Command /{command_name} failed: {error_id}"
    
    async def handle_database_error(self, operation: str, error: Exception, user_id: int = None):
        """Handle database errors"""
        # Use enhanced error handler
        error_id, user_message = self.error_handler.log_error(
            error,
            {"database_operation": operation},
            user_id
        )
        
        log_database_operation(operation, "unknown", None, False, str(error))
        
        return f"Database operation '{operation}' failed: {error_id}"
    
    async def handle_permission_error(self, user_id: int, username: str, required_role: str, attempted_action: str):
        """Handle permission violations"""
        error_msg = f"Permission denied: User {user_id} (@{username}) attempted {attempted_action} requiring {required_role} role"
        
        log_security_event("PERMISSION_DENIED", user_id, f"{attempted_action} (requires {required_role})")
        
        return error_msg
    
    def log_startup_info(self):
        """Log startup information"""
        self.logger.info(f"=" * 50)
        self.logger.info(f"🤖 {config.BUSINESS_NAME} Telegram Bot Starting")
        self.logger.info(f"📅 Startup Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"📞 Contact: {config.CONTACT_PHONE}")
        self.logger.info(f"🏢 Address: {config.ADDRESS}")
        self.logger.info(f"🔧 Log Level: {config.LOG_LEVEL}")
        self.logger.info(f"🛡️ Debug Mode: {config.DEBUG_MODE}")
        self.logger.info(f"📊 Rate Limit: {config.RATE_LIMIT_MESSAGES} msgs/{config.RATE_LIMIT_WINDOW}s")
        self.logger.info(f"=" * 50)
    
    def log_shutdown_info(self):
        """Log shutdown information"""
        self.logger.info(f"🛑 {config.BUSINESS_NAME} Telegram Bot Shutting Down")
        self.logger.info(f"📅 Shutdown Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"=" * 50)

# Input validation functions
def validate_medicine_name(name: str) -> bool:
    """Validate medicine name input"""
    if not name or len(name.strip()) < 2:
        return False
    if len(name) > 100:
        return False
    # Allow letters, numbers, spaces, hyphens, and parentheses
    import re
    if not re.match(r'^[a-zA-Z0-9\s\-\(\)\.]+$', name):
        return False
    return True

def validate_quantity(quantity_str: str, max_quantity: int = None) -> tuple:
    """Validate quantity input"""
    try:
        quantity = int(quantity_str)
        if quantity <= 0:
            return False, "Quantity must be greater than 0"
        if max_quantity and quantity > max_quantity:
            return False, f"Quantity cannot exceed {max_quantity}"
        return True, quantity
    except ValueError:
        return False, "Please enter a valid number"

def validate_price(price_str: str) -> tuple:
    """Validate price input"""
    try:
        price = float(price_str)
        if price <= 0:
            return False, "Price must be greater than 0"
        if price > 10000:  # Reasonable upper limit
            return False, "Price seems unusually high"
        return True, round(price, 2)
    except ValueError:
        return False, "Please enter a valid price"

def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """Basic phone validation"""
    import re
    # Allow various phone formats
    phone_clean = re.sub(r'[\s\-\(\)]+', '', phone)
    return len(phone_clean) >= 10 and phone_clean.replace('+', '').isdigit()

def sanitize_input(text: str) -> str:
    """Sanitize user input"""
    if not text:
        return ""
    
    # Remove any control characters
    import re
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Limit length
    text = text[:500]
    
    return text.strip()

# Rate limiting helper
class RateLimiter:
    """Simple rate limiter for bot commands"""
    
    def __init__(self):
        self.user_requests = {}
        self.logger = logging.getLogger('rate_limiter')
    
    def check_rate_limit(self, user_id: int, window_seconds: int = 60, max_requests: int = 30) -> bool:
        """Check if user has exceeded rate limit"""
        now = datetime.now()
        
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []
        
        # Clean old requests
        cutoff_time = now.timestamp() - window_seconds
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id] 
            if req_time > cutoff_time
        ]
        
        # Check current count
        current_count = len(self.user_requests[user_id])
        
        if current_count >= max_requests:
            self.logger.warning(f"Rate limit exceeded for user {user_id}: {current_count} requests in {window_seconds}s")
            return False
        
        # Add current request
        self.user_requests[user_id].append(now.timestamp())
        return True

# Initialize logging
logger = setup_logging()
error_handler = BotErrorHandler()
rate_limiter = RateLimiter()

# Function to initialize error handler with database
def initialize_error_handler(db_manager):
    """Initialize error handler with database manager"""
    global error_handler
    error_handler = BotErrorHandler(db_manager)
