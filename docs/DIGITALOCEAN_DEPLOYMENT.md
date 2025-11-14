# DigitalOcean Droplet Deployment Guide

Complete guide to deploy the XAU/USD Trading Bot on a DigitalOcean droplet.

## Prerequisites

- DigitalOcean account
- GitHub account with your bot repository
- Telegram Bot Token
- TwelveData API Key
- SSH key (recommended)

---

## Step 1: Create DigitalOcean Droplet

### 1.1 Create Droplet

1. Log into DigitalOcean
2. Click **Create** → **Droplets**
3. Choose configuration:
   - **Image**: Ubuntu 22.04 LTS (or 24.04)
   - **Plan**: Basic (Shared CPU)
   - **CPU Options**: Regular - $6/month (1GB RAM, 25GB SSD)
   - **Datacenter**: Choose closest to you
   - **Authentication**: SSH Key (recommended) or Password
   - **Hostname**: `xauusd-trading-bot`

4. Click **Create Droplet**
5. Wait 1-2 minutes for provisioning
6. Note your droplet's IP address

### 1.2 Connect to Droplet

Using SSH:
```bash
ssh root@YOUR_DROPLET_IP
```

If using password, enter it when prompted.

---

## Step 2: Initial Server Setup

### 2.1 Update System

```bash
# Update package lists
apt update

# Upgrade installed packages
apt upgrade -y
```

### 2.2 Install Python 3.11+

Ubuntu 22.04 comes with Python 3.10, let's ensure we have Python 3.11+:

```bash
# Check current Python version
python3 --version

# Install Python 3.11 if needed
apt install software-properties-common -y
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install python3.11 python3.11-venv python3.11-dev -y

# Set Python 3.11 as default (optional)
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

### 2.3 Install Essential Tools

```bash
# Install git, pip, and build tools
apt install git python3-pip build-essential -y

# Install system dependencies for TA-Lib
apt install wget -y
```

### 2.4 Install TA-Lib (Required for technical indicators)

```bash
# Download TA-Lib
cd /tmp
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz

# Extract and install
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
make install

# Update library cache
ldconfig

# Clean up
cd ~
rm -rf /tmp/ta-lib*
```

---

## Step 3: Clone and Setup Bot

### 3.1 Clone Repository

```bash
# Clone your repository
cd /root
git clone https://github.com/rm8814/xauusd_bot.git
cd xauusd_bot

# Checkout the correct branch
git checkout claude/xauusd-trading-bot-poc-01EV2bQKRwpAzDwerZR6rTNZ
```

### 3.2 Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 3.3 Install Python Dependencies

```bash
# Install requirements
pip install -r requirements.txt

# Verify TA-Lib installation
python -c "import talib; print('TA-Lib OK')"
```

If TA-Lib fails, try:
```bash
pip install --no-cache-dir TA-Lib
```

---

## Step 4: Configure Environment

### 4.1 Create .env File

```bash
# Copy template
cp .env.template .env

# Edit .env file
nano .env
```

### 4.2 Add Your Credentials

Edit the `.env` file with your actual credentials:

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=YOUR_ACTUAL_BOT_TOKEN
TELEGRAM_CHAT_ID=YOUR_ACTUAL_CHAT_ID

# Data Source
TWELVE_DATA_API_KEY=YOUR_ACTUAL_API_KEY

# Trading Configuration
INITIAL_BALANCE=100
LOT_SIZE=0.01
ENABLE_LIVE_TRADING=false

# Risk Management
MAX_RISK_PERCENT=1
MAX_DAILY_LOSS_PERCENT=5
MAX_OPEN_POSITIONS=4

# Active Strategies
ACTIVE_TIMEFRAMES=1h,4h,1day
ACTIVE_STRATEGIES=all

# Monitoring
LOG_LEVEL=INFO
SENTRY_DSN=

# Database
DATABASE_PATH=database/trades.db
```

**Save and exit**: Press `Ctrl+X`, then `Y`, then `Enter`

---

## Step 5: Test the Bot

### 5.1 Run Test

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run the bot
python main.py
```

You should see:
```
2024-01-XX XX:XX:XX - INFO - Starting XAU/USD Trading Bot...
2024-01-XX XX:XX:XX - INFO - Loading configuration...
2024-01-XX XX:XX:XX - INFO - Database initialized...
2024-01-XX XX:XX:XX - INFO - Bot started successfully
```

### 5.2 Check Telegram

1. Open Telegram and find your bot
2. Send `/start`
3. You should receive a welcome message

### 5.3 Stop Test

Press `Ctrl+C` to stop the bot.

---

## Step 6: Keep Bot Running (Choose One Method)

### Method A: Using systemd (Recommended for Production)

#### Create systemd service:

```bash
# Create service file
nano /etc/systemd/system/xauusd-bot.service
```

#### Add this content:

```ini
[Unit]
Description=XAU/USD Trading Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/xauusd_bot
Environment="PATH=/root/xauusd_bot/venv/bin"
ExecStart=/root/xauusd_bot/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=append:/root/xauusd_bot/logs/bot.log
StandardError=append:/root/xauusd_bot/logs/errors.log

[Install]
WantedBy=multi-user.target
```

**Save and exit**: `Ctrl+X`, `Y`, `Enter`

#### Enable and start service:

```bash
# Reload systemd
systemctl daemon-reload

# Enable service (start on boot)
systemctl enable xauusd-bot

# Start service
systemctl start xauusd-bot

# Check status
systemctl status xauusd-bot
```

#### Useful systemd commands:

```bash
# Stop bot
systemctl stop xauusd-bot

# Restart bot
systemctl restart xauusd-bot

# View logs
journalctl -u xauusd-bot -f

# View recent logs
journalctl -u xauusd-bot -n 100
```

---

### Method B: Using screen (Simple Alternative)

```bash
# Install screen
apt install screen -y

# Create new screen session
screen -S xauusd-bot

# Activate virtual environment
cd /root/xauusd_bot
source venv/bin/activate

# Run bot
python main.py

# Detach from screen: Press Ctrl+A then D
```

#### Screen commands:

```bash
# List sessions
screen -ls

# Reattach to session
screen -r xauusd-bot

# Kill session
screen -X -S xauusd-bot quit
```

---

## Step 7: Monitor and Maintain

### 7.1 View Logs

```bash
# Real-time logs
tail -f /root/xauusd_bot/logs/bot.log

# Error logs
tail -f /root/xauusd_bot/logs/errors.log

# Trade logs
tail -f /root/xauusd_bot/logs/trades.log

# View last 100 lines
tail -n 100 /root/xauusd_bot/logs/bot.log
```

### 7.2 Database Location

```bash
# Database file
ls -lh /root/xauusd_bot/database/trades.db

# Backup database
cp /root/xauusd_bot/database/trades.db /root/backup_$(date +%Y%m%d).db
```

### 7.3 Monitor Resources

```bash
# Check CPU and RAM usage
htop

# Check disk usage
df -h

# Check bot process
ps aux | grep python
```

---

## Step 8: Updates and Maintenance

### 8.1 Update Bot Code

```bash
# Stop the bot
systemctl stop xauusd-bot  # or kill screen session

# Navigate to directory
cd /root/xauusd_bot

# Pull latest changes
git pull origin claude/xauusd-trading-bot-poc-01EV2bQKRwpAzDwerZR6rTNZ

# Activate virtual environment
source venv/bin/activate

# Update dependencies (if needed)
pip install -r requirements.txt

# Restart bot
systemctl start xauusd-bot
```

### 8.2 Backup Database

```bash
# Create backup script
nano /root/backup_bot.sh
```

Add:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp /root/xauusd_bot/database/trades.db /root/backups/trades_$DATE.db
echo "Backup created: trades_$DATE.db"
```

Make executable:
```bash
chmod +x /root/backup_bot.sh

# Create backups directory
mkdir -p /root/backups

# Run backup
/root/backup_bot.sh
```

### 8.3 Automate Backups (Cron)

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /root/backup_bot.sh
```

---

## Step 9: Security Hardening

### 9.1 Setup Firewall

```bash
# Install UFW
apt install ufw -y

# Allow SSH
ufw allow 22/tcp

# Enable firewall
ufw enable

# Check status
ufw status
```

### 9.2 Create Non-Root User (Optional but Recommended)

```bash
# Create user
adduser trader

# Add to sudo group
usermod -aG sudo trader

# Switch to new user
su - trader

# Move bot to user directory
sudo mv /root/xauusd_bot /home/trader/
sudo chown -R trader:trader /home/trader/xauusd_bot

# Update systemd service to use new user
sudo nano /etc/systemd/system/xauusd-bot.service
# Change User=root to User=trader
# Change WorkingDirectory to /home/trader/xauusd_bot
```

### 9.3 Secure .env File

```bash
# Restrict permissions
chmod 600 /root/xauusd_bot/.env
```

---

## Step 10: Troubleshooting

### Common Issues

#### 1. TA-Lib Installation Fails

```bash
# Try installing dependencies
apt install python3-dev build-essential -y

# Reinstall TA-Lib from source (see Step 2.4)
```

#### 2. Bot Doesn't Start

```bash
# Check logs
journalctl -u xauusd-bot -n 50

# Check Python path
which python3

# Verify virtual environment
source venv/bin/activate
python --version
```

#### 3. Database Errors

```bash
# Ensure directory exists
mkdir -p /root/xauusd_bot/database

# Check permissions
ls -la /root/xauusd_bot/database/
```

#### 4. API Connection Issues

```bash
# Test internet connectivity
ping -c 3 api.twelvedata.com

# Check DNS
nslookup api.twelvedata.com

# Verify API key
cat .env | grep TWELVE_DATA_API_KEY
```

#### 5. Out of Memory

```bash
# Check memory usage
free -h

# If droplet has < 1GB RAM, create swap file
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# Make swap permanent
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

---

## Step 11: Monitoring & Alerts

### 11.1 Setup Log Rotation

```bash
# Create logrotate config
nano /etc/logrotate.d/xauusd-bot
```

Add:
```
/root/xauusd_bot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### 11.2 Monitor Bot Health

Create health check script:
```bash
nano /root/check_bot.sh
```

Add:
```bash
#!/bin/bash
if ! systemctl is-active --quiet xauusd-bot; then
    echo "Bot is down! Restarting..."
    systemctl restart xauusd-bot
fi
```

```bash
chmod +x /root/check_bot.sh

# Add to cron (check every 5 minutes)
crontab -e
*/5 * * * * /root/check_bot.sh
```

---

## Quick Reference Commands

```bash
# Start bot
systemctl start xauusd-bot

# Stop bot
systemctl stop xauusd-bot

# Restart bot
systemctl restart xauusd-bot

# Check status
systemctl status xauusd-bot

# View logs
journalctl -u xauusd-bot -f

# View bot logs
tail -f /root/xauusd_bot/logs/bot.log

# Update bot
cd /root/xauusd_bot && git pull && systemctl restart xauusd-bot

# Backup database
cp /root/xauusd_bot/database/trades.db /root/backup_$(date +%Y%m%d).db
```

---

## Summary Checklist

- ✅ Droplet created and SSH access working
- ✅ System updated and Python 3.11+ installed
- ✅ TA-Lib compiled and installed
- ✅ Repository cloned
- ✅ Virtual environment created
- ✅ Dependencies installed
- ✅ .env file configured with credentials
- ✅ Bot tested manually
- ✅ systemd service created and enabled
- ✅ Bot running in background
- ✅ Telegram notifications working
- ✅ Logs being generated
- ✅ Firewall configured
- ✅ Backups scheduled

---

## Cost Estimate

**Monthly Costs:**
- DigitalOcean Droplet (1GB): $6/month
- **Total: $6/month**

**Free Tier:**
- TwelveData API: Free (800 calls/day)
- Telegram Bot: Free

---

## Support

If you encounter issues:

1. Check logs: `/root/xauusd_bot/logs/`
2. Check service status: `systemctl status xauusd-bot`
3. Test manually: `cd /root/xauusd_bot && source venv/bin/activate && python main.py`
4. Check GitHub Issues: Your repository issues page

---

**Your bot is now running 24/7 on DigitalOcean! 🚀**
