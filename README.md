# 🏥 Blue Pharma Trading PLC Telegram Bot

A comprehensive pharmacy management Telegram bot with a three-tier user system designed for both retail customers and wholesale clients.

## 📋 Table of Contents
- [Features](#-features)
- [Three-Tier User System](#-three-tier-user-system)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Database Setup](#-database-setup)
- [Running the Bot](#-running-the-bot)
- [Bot Commands](#-bot-commands)
- [Project Structure](#-project-structure)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

## 🚀 Features

### Core Functionality
- **Three-tier user management** (Customer, Wholesale, Staff)
- **Real-time inventory management**
- **Order tracking and management**
- **Role-based permissions**
- **Comprehensive audit logging**
- **Rate limiting and security**
- **24/7 automated customer service**

### For Customers (Tier 1)
- Medicine price and stock checking
- Easy ordering system with delivery
- Order history and tracking
- Medicine search functionality
- Prescription requirement alerts

### For Wholesale Clients (Tier 2)
- Bulk pricing access
- Large quantity orders
- Wholesale catalog browsing
- Company account management
- Dedicated wholesale stock tracking

### For Staff (Tier 3)
- Inventory management (stock & pricing)
- Order status management
- User role management
- Business analytics and statistics
- Wholesale request approvals

## 👥 Three-Tier User System

### Tier 1: Customers (🛒)
- Default role for new users
- Access to retail pricing
- Standard order quantities
- Basic customer support features

### Tier 2: Wholesale Clients (🏢)
- Verified business accounts
- Access to wholesale pricing
- Bulk order capabilities
- Dedicated business features

### Tier 3: Staff & Admin (👨‍💼)
- Inventory management privileges
- Order management capabilities
- User administration
- Business analytics access

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Telegram Bot Token (from @BotFather)

### Step 1: Clone or Download
```bash
# Download the project to C:\BluePharmaBot
# Or clone if using git:
git clone <repository-url> C:\BluePharmaBot
cd C:\BluePharmaBot
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Create Environment File
```bash
# Copy the template and edit with your settings
copy .env.template .env
```

## ⚙️ Configuration

Edit the `.env` file with your actual values:

### Essential Settings
```env
# Get this from @BotFather
BOT_TOKEN=your_actual_bot_token_here

# Your admin Telegram ID
ADMIN_TELEGRAM_ID=your_telegram_user_id

# Business Information
BUSINESS_NAME=Blue Pharma Trading PLC
CONTACT_PHONE=+1-234-567-8900
CONTACT_EMAIL=info@bluepharma.com
ADDRESS=123 Pharmacy Street, Medical District, City, State 12345
```

### Optional Settings
```env
# Database path
DATABASE_PATH=database/bluepharma.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log

# Security
MAX_ORDER_QUANTITY=1000
RATE_LIMIT_MESSAGES=30
RATE_LIMIT_WINDOW=60

# Development
DEBUG_MODE=False
```

## 🗄️ Database Setup

The bot uses SQLite for data storage. The database will be automatically created on first run.

### Initialize Database
```bash
python database/db_init.py
```

This creates:
- **users** table (customer accounts and roles)
- **medicines** table (inventory with retail/wholesale pricing)
- **orders** table (all orders with full tracking)
- **inquiries** table (customer service logs)
- **audit_logs** table (system activity tracking)

### Sample Data
The initialization includes sample medicines:
- Paracetamol 500mg
- Amoxicillin 250mg
- Ibuprofen 400mg
- Omeprazole 20mg
- Metformin 500mg

## 🚀 Running the Bot

### Start the Bot
```bash
python main.py
```

### First-Time Setup Checklist
1. ✅ Python 3.8+ installed
2. ✅ Dependencies installed (`pip install -r requirements.txt`)
3. ✅ `.env` file configured with bot token
4. ✅ Database initialized
5. ✅ Bot commands set up with @BotFather

### Setting Up Bot Commands with @BotFather

1. Message @BotFather on Telegram
2. Use `/setcommands` 
3. Select your bot
4. Paste the command list (provided when running `main.py`)

## 🤖 Bot Commands

### Universal Commands
| Command | Description |
|---------|-------------|
| `/start` | Main menu and welcome |
| `/help` | Show available commands |
| `/contact` | Contact information |
| `/hours` | Business hours |

### Customer Commands (Tier 1)
| Command | Description |
|---------|-------------|
| `/check [medicine]` | Check medicine price and stock |
| `/search [keyword]` | Search medicines |
| `/order` | Place a new order |
| `/my_orders` | View order history |

### Wholesale Commands (Tier 2)
| Command | Description |
|---------|-------------|
| `/wholesale_check [medicine]` | Check wholesale prices |
| `/bulk_order [medicine] [quantity]` | Place bulk orders |
| `/wholesale_catalog` | View wholesale catalog |
| `/request_wholesale` | Request wholesale access |

### Staff Commands (Tier 3)
| Command | Description |
|---------|-------------|
| `/update_stock [medicine] [retail_qty] [wholesale_qty]` | Update inventory |
| `/update_price [medicine] [retail_price] [wholesale_price]` | Update pricing |
| `/view_orders [type]` | View orders (retail/wholesale/all) |
| `/mark_order [order_id] [status]` | Update order status |
| `/stats` | Business statistics |
| `/pending_requests` | Wholesale access requests |
| `/approve_wholesale [telegram_id]` | Approve wholesale access |

## 📁 Project Structure

```
BluePharmaBot/
├── main.py                 # Main application entry point
├── bot.py                  # Core bot implementation
├── bot_extensions.py       # Wholesale & staff command extensions
├── user_manager.py         # User role management system
├── logger.py               # Logging and error handling
├── requirements.txt        # Python dependencies
├── .env.template           # Environment configuration template
├── .env                    # Your actual configuration (create this)
├── README.md               # This documentation
│
├── config/
│   └── config.py           # Configuration management
│
├── database/
│   ├── db_init.py          # Database initialization
│   └── bluepharma.db       # SQLite database (created automatically)
│
└── logs/
    ├── bot.log             # Application logs
    └── bot_errors.log      # Error logs
```

## 🌐 Deployment

### Local Development
```bash
python main.py
```

### Production Deployment Options

#### 1. VPS/Cloud Server
```bash
# Install screen for background running
sudo apt install screen

# Start in background
screen -S bluepharma
python main.py
# Ctrl+A, D to detach

# Reattach later
screen -r bluepharma
```

#### 2. Windows Service
Use `python-windows-service` or Task Scheduler for Windows deployment.

#### 3. Docker (Optional)
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt

CMD ["python", "main.py"]
```

#### 4. Heroku
```bash
# Add Procfile:
echo "worker: python main.py" > Procfile

# Deploy to Heroku
git init
heroku create your-bot-name
git add .
git commit -m "Initial deployment"
git push heroku main
```

## 🔒 Security Features

- **Role-based access control**
- **Rate limiting (30 messages/minute by default)**
- **Input validation and sanitization**
- **Comprehensive audit logging**
- **Permission verification for sensitive operations**
- **SQL injection prevention**

## 📊 Business Analytics

Staff can access comprehensive analytics:
- User statistics by role
- Order tracking and revenue
- Inventory alerts
- Daily/monthly performance metrics

## 🛠️ Troubleshooting

### Common Issues

#### Bot Token Error
```
❌ BOT_TOKEN environment variable is required
```
**Solution**: Add your bot token to `.env` file

#### Database Permission Error
```
❌ Database initialization failed: Permission denied
```
**Solution**: Ensure write permissions to `database/` directory

#### Import Errors
```
❌ Import error: No module named 'telegram'
```
**Solution**: Install dependencies with `pip install -r requirements.txt`

#### Configuration Validation Failed
```
❌ Please update BOT_TOKEN in .env file
```
**Solution**: Replace `your_bot_token_here` with actual token from @BotFather

### Getting Your Bot Token

1. Message @BotFather on Telegram
2. Use `/newbot` command
3. Choose bot name and username
4. Copy the token provided
5. Add to `.env` file

### Getting Your Telegram ID

1. Message @userinfobot on Telegram
2. Your ID will be displayed
3. Add as `ADMIN_TELEGRAM_ID` in `.env`

### Log Files

Check logs for detailed error information:
- `logs/bot.log` - General application logs
- `logs/bot_errors.log` - Error-specific logs

## 🔧 Development

### Adding New Features

1. **New Commands**: Add to `bot.py` or `bot_extensions.py`
2. **Database Changes**: Modify `database/db_init.py`
3. **Configuration**: Update `config/config.py` and `.env.template`

### Testing

```bash
# Test database initialization
python database/db_init.py

# Test configuration
python -c "from config.config import config; print(config.validate_config())"
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- **Email**: info@bluepharma.com
- **Phone**: +1-234-567-8900
- **Address**: 123 Pharmacy Street, Medical District, City, State 12345

---

**Blue Pharma Trading PLC** - Revolutionizing pharmacy management through intelligent automation 🏥🤖
