# 🚀 Quick Setup Guide

Get your Blue Pharma Trading PLC Telegram Bot running in 5 minutes!

## ⚡ Fast Track Setup

### 1. Get Your Bot Token
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`
3. Choose a name: `Blue Pharma Bot`
4. Choose a username: `bluepharma_bot` (must be unique)
5. **Copy the token** - you'll need it next!

### 2. Configure Your Bot
1. Copy `.env.template` to `.env`
2. Edit `.env` and replace:
   ```env
   BOT_TOKEN=paste_your_actual_token_here
   ADMIN_TELEGRAM_ID=your_telegram_user_id
   ```

### 3. Install & Run
```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py
```

That's it! Your bot is now running! 🎉

## 📱 Get Your Telegram ID
1. Message [@userinfobot](https://t.me/userinfobot) 
2. It will tell you your Telegram ID
3. Add this as `ADMIN_TELEGRAM_ID` in your `.env` file

## 🤖 Set Bot Commands with BotFather

1. Message [@BotFather](https://t.me/BotFather)
2. Send `/setcommands`
3. Select your bot
4. Paste this command list:

```
start - Main menu and welcome
help - Show available commands  
contact - Contact information
hours - Business hours
check - Check medicine price and stock
search - Search medicines by keyword
order - Place a new order
my_orders - View your order history
wholesale_check - Check wholesale prices
bulk_order - Place bulk orders
wholesale_catalog - View wholesale catalog
request_wholesale - Request wholesale access
update_stock - Update medicine stock
update_price - Update medicine prices
view_orders - View all orders
mark_order - Update order status
stats - View statistics
pending_requests - View wholesale requests
approve_wholesale - Approve wholesale access
```

## 🏥 Customize Your Pharmacy

Edit these in your `.env` file:

```env
BUSINESS_NAME=Your Pharmacy Name
CONTACT_PHONE=+1-555-123-4567
CONTACT_EMAIL=contact@yourpharmacy.com
ADDRESS=123 Main St, Your City, State 12345
BUSINESS_HOURS=Mon-Fri: 9AM-6PM, Sat: 9AM-2PM
```

## ✅ Test Your Bot

1. Find your bot on Telegram (search for the username you created)
2. Send `/start`
3. You should see a welcome message with buttons!

## 🎯 Next Steps

### Add Sample Medicines (Optional)
The bot comes with 5 sample medicines. To add more:
1. Get staff access by using `/start` (you're automatically admin)
2. Use `/update_stock Medicine_Name 100 500` to add new medicines

### User Roles
- **You** are automatically an admin
- **New users** are customers by default  
- **Customers** can request wholesale access
- **Staff** can approve wholesale requests

### Wholesale Client Management
1. Customer requests wholesale access: `/request_wholesale`
2. You (staff) see pending requests: `/pending_requests`
3. You approve them: `/approve_wholesale [telegram_id]`

## 🚨 Troubleshooting

### Bot doesn't respond?
- ✅ Check your token is correct in `.env`
- ✅ Make sure bot is started: `python main.py`
- ✅ Try `/start` command

### "Import error" when starting?
```bash
pip install -r requirements.txt
```

### Can't find the bot on Telegram?
- Make sure the username is unique and available
- Try creating a new bot with different username

## 📞 Need Help?

Check the full [README.md](README.md) for detailed documentation, or:

1. Check logs in `logs/bot.log` 
2. Verify your `.env` configuration
3. Make sure Python 3.8+ is installed

---

🎉 **Congratulations!** Your pharmacy bot is ready to serve customers 24/7!
