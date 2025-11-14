# XAU/USD Trading Bot - Setup Guide

## Quick Start

### 1. Prerequisites

- Python 3.9 or higher
- Git
- Telegram account
- TwelveData API account (free tier available)

### 2. Installation

Clone the repository:
```bash
git clone <your-repo-url>
cd xauusd_bot
```

Run the setup script:
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

Or install manually:
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

1. **Copy environment template:**
```bash
cp .env.template .env
```

2. **Get Telegram Bot Token:**
   - Open Telegram and search for @BotFather
   - Send `/newbot` and follow instructions
   - Copy the bot token

3. **Get Telegram Chat ID:**
   - Send a message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find your chat ID in the response

4. **Get TwelveData API Key:**
   - Sign up at https://twelvedata.com/
   - Go to your dashboard
   - Copy your API key (free tier: 800 calls/day)

5. **Edit `.env` file:**
```bash
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
TWELVE_DATA_API_KEY=your_api_key_here
```

### 4. Run the Bot

Activate virtual environment (if not already active):
```bash
source venv/bin/activate
```

Run the bot:
```bash
python main.py
```

### 5. Verify Installation

1. Open Telegram and find your bot
2. Send `/start` command
3. You should receive a welcome message
4. Try `/help` to see available commands

## Configuration Files

### Main Config (`config/config.yaml`)
- Trading pair settings
- Risk management rules
- Data update intervals
- Alert preferences

### Strategies (`config/strategies.yaml`)
- 6 pre-configured strategies
- Indicator assignments
- ATR multipliers for SL/TP

### Indicators (`config/indicators.yaml`)
- Technical indicator parameters
- Calculation settings

### Risk Management (`config/risk_management.yaml`)
- Position sizing rules
- Account protection limits
- Psychology safeguards

## Testing

Run tests:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=src tests/
```

## Troubleshooting

### Bot doesn't start
- Check `.env` file has correct credentials
- Verify Python version: `python --version` (should be 3.9+)
- Check logs in `logs/bot.log`

### No signals detected
- Verify TwelveData API key is valid
- Check API usage: https://twelvedata.com/account/usage
- Wait for indicators to align (4-layer confirmation required)

### Database errors
- Delete `database/trades.db` to reset
- Check write permissions in database folder

### Import errors
- Reinstall dependencies: `pip install -r requirements.txt`
- Check virtual environment is activated

## Production Deployment

### Using systemd (Linux)

1. Create service file:
```bash
sudo nano /etc/systemd/system/xauusd-bot.service
```

2. Add content:
```ini
[Unit]
Description=XAU/USD Trading Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/xauusd_bot
ExecStart=/path/to/xauusd_bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable xauusd-bot
sudo systemctl start xauusd-bot
```

4. Check status:
```bash
sudo systemctl status xauusd-bot
```

### Using screen (Simple method)

```bash
screen -S xauusd-bot
python main.py
# Press Ctrl+A then D to detach
# Reattach with: screen -r xauusd-bot
```

## Important Notes

⚠️ **Paper Trading**
- Set `ENABLE_LIVE_TRADING=false` in `.env` for paper trading
- Bot will send alerts but won't execute trades automatically

⚠️ **API Limits**
- TwelveData free tier: 800 calls/day
- Bot uses ~1 call per minute per timeframe
- Monitor usage at: https://twelvedata.com/account/usage

⚠️ **Risk Management**
- Always test with paper trading first
- Start with small position sizes
- Review risk settings in `config/risk_management.yaml`

## Next Steps

1. ✅ Complete setup and configuration
2. ✅ Run bot in paper trading mode
3. ✅ Monitor signals and alerts
4. ✅ Review trade journal regularly
5. ✅ Adjust risk settings as needed
6. 🎯 When confident, enable live trading

## Support

- Check logs in `logs/` directory
- Review documentation in `docs/`
- Read `TROUBLESHOOTING.md` for common issues

## License

MIT License - See LICENSE file for details
