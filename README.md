# XAU/USD Telegram Trading Bot

An automated trading bot for XAU/USD (Gold) forex trading with Telegram integration.

## Features

- **6 Pre-Backtested Strategies** across 3 timeframes (1h, 4h, 1day)
- **4-Layer Confirmation System** for high-probability setups
- **Real-time Telegram Alerts** for entry and exit signals
- **Automated Position Management** with SL/TP
- **Trade Journal & Analytics** for performance tracking
- **Risk Management** with psychology safeguards

## Quick Start

### Prerequisites

- Python 3.9+
- Telegram Bot Token
- TwelveData API Key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd xauusd_bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.template .env
# Edit .env with your credentials
```

4. Run the bot:
```bash
python main.py
```

## Configuration

Edit configuration files in the `config/` directory:

- `config.yaml` - Main bot settings
- `strategies.yaml` - Trading strategy definitions
- `indicators.yaml` - Technical indicator parameters
- `risk_management.yaml` - Risk rules and limits

## Telegram Commands

- `/start` - Initialize bot
- `/help` - Show available commands
- `/signals` - Check current signals
- `/status` - View open positions
- `/journal` - View trade history
- `/stats` - Performance statistics

## Project Structure

```
xauusd_bot/
├── config/              # Configuration files
├── src/
│   ├── core/           # Trading engine
│   ├── data/           # Data management
│   ├── telegram/       # Telegram bot
│   ├── database/       # Database layer
│   ├── analytics/      # Performance analytics
│   └── utils/          # Utilities
├── tests/              # Test suite
├── logs/               # Log files
└── database/           # SQLite databases
```

## Strategy Overview

All 6 strategies use a 4-layer confirmation system:

1. **Primary Indicator** - Entry/exit signal
2. **Volume Indicator** - Volume confirmation
3. **Confirmation Indicator** - Second confirmation
4. **Baseline Indicator** - Trend filter

### Available Strategies

| ID | Timeframe | Mode | Primary | Baseline |
|----|-----------|------|---------|----------|
| 1 | 1day | PURE | Awesome Oscillator | SuperTrend |
| 2 | 1day | ATR | Momentum | SuperTrend |
| 3 | 4h | PURE | Awesome Oscillator | SuperTrend |
| 4 | 4h | ATR | Momentum | PSAR |
| 5 | 1h | PURE | Momentum | Hull MA |
| 6 | 1h | ATR | Momentum | Hull MA |

## Risk Management

- Max 1% risk per trade
- Max 4 open positions
- Max 5% daily loss limit
- Overtrading prevention
- Psychology safeguards

## Testing

Run tests with:
```bash
pytest tests/
```

## License

MIT License

## Disclaimer

This bot is for educational purposes. Trading involves risk. Always test thoroughly before live trading.
