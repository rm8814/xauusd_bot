# Quick Deploy to DigitalOcean - Condensed Guide

## 1. Create Droplet (2 minutes)

- Go to DigitalOcean → Create → Droplets
- Choose: Ubuntu 22.04, $6/month (1GB RAM)
- Create and note IP address

## 2. Connect via SSH

```bash
ssh root@YOUR_DROPLET_IP
```

## 3. Run Installation Script (Copy & Paste All)

```bash
# Update system
apt update && apt upgrade -y

# Install Python 3.11 and tools
apt install -y software-properties-common git python3-pip build-essential wget
add-apt-repository -y ppa:deadsnakes/ppa
apt update && apt install -y python3.11 python3.11-venv python3.11-dev

# Install TA-Lib (required for indicators)
cd /tmp
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr && make && make install
ldconfig
cd ~

# Clone repository
git clone https://github.com/rm8814/xauusd_bot.git
cd xauusd_bot
git checkout claude/xauusd-trading-bot-poc-01EV2bQKRwpAzDwerZR6rTNZ

# Setup virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
cp .env.template .env
```

## 4. Configure Credentials

```bash
nano .env
```

**Edit these lines:**
```
TELEGRAM_BOT_TOKEN=YOUR_ACTUAL_BOT_TOKEN
TELEGRAM_CHAT_ID=YOUR_ACTUAL_CHAT_ID
TWELVE_DATA_API_KEY=YOUR_ACTUAL_API_KEY
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

## 5. Test Run

```bash
source venv/bin/activate
python main.py
```

Send `/start` to your Telegram bot. You should get a welcome message.

Press `Ctrl+C` to stop.

## 6. Setup Auto-Start Service

```bash
# Create systemd service
cat > /etc/systemd/system/xauusd-bot.service << 'EOF'
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
EOF

# Start the service
systemctl daemon-reload
systemctl enable xauusd-bot
systemctl start xauusd-bot
systemctl status xauusd-bot
```

## 7. Useful Commands

```bash
# Check if bot is running
systemctl status xauusd-bot

# View live logs
tail -f /root/xauusd_bot/logs/bot.log

# Restart bot
systemctl restart xauusd-bot

# Stop bot
systemctl stop xauusd-bot

# Update bot
cd /root/xauusd_bot && git pull && systemctl restart xauusd-bot
```

## Done! ✅

Your bot is now running 24/7 on DigitalOcean for $6/month.

Check Telegram - your bot should be sending updates!

---

## Troubleshooting

**TA-Lib fails to install?**
```bash
apt install python3-dev build-essential -y
```

**Bot doesn't start?**
```bash
journalctl -u xauusd-bot -n 50
```

**Check bot is running:**
```bash
ps aux | grep python
```

**View all logs:**
```bash
ls -la /root/xauusd_bot/logs/
tail -f /root/xauusd_bot/logs/bot.log
```
