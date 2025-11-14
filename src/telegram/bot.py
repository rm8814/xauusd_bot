"""
Main Telegram Bot
Handles bot initialization and message routing
"""

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from typing import Optional, Dict
import os

from src.telegram.formatters.signal_formatter import SignalFormatter
from src.telegram.formatters.position_formatter import PositionFormatter

logger = logging.getLogger(__name__)


class TradingBot:
    """Main Telegram trading bot"""

    def __init__(self, token: str, chat_id: str):
        """
        Initialize bot

        Args:
            token: Telegram bot token
            chat_id: Telegram chat ID for alerts
        """
        self.token = token
        self.chat_id = chat_id
        self.application = None

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🤖 **XAU/USD Trading Bot**

Welcome! I'm your automated trading assistant for XAU/USD (Gold).

**Available Commands:**

📊 **Trading**
/signals - Check current signals
/status - View open positions
/dashboard - Full trading dashboard

📈 **Analytics**
/stats - Performance statistics
/journal - Trade history

⚙️ **Settings**
/help - Show this help message
/settings - Configure bot settings

🎯 **Strategy**
6 pre-backtested strategies across 3 timeframes (1h, 4h, 1day)
4-layer confirmation system for high-probability setups

Let's start trading! 🚀
"""
        await update.message.reply_text(welcome_message, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """
📚 **Command Reference**

**Trading Commands:**
/signals - Check all active signals
/status - View open positions and P&L
/dashboard - Complete trading overview

**Position Management:**
/close [trade_id] - Close specific position
/trail [trade_id] - Enable trailing stop

**Analytics:**
/stats [period] - Performance stats (day/week/month)
/journal [period] - Trade history
/export - Export trades to CSV

**Risk:**
/risk [entry] [sl] [balance] [%] - Calculate position size

**System:**
/help - This help message
/settings - Bot configuration

💡 **Tips:**
- Wait for 5-minute confirmation on all signals
- Follow risk management rules strictly
- Review your journal regularly

For detailed documentation, visit the project README.
"""
        await update.message.reply_text(help_message, parse_mode='Markdown')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        # This will be connected to the position manager
        message = """
📊 **Status Update**

Open Positions: 0
Today's Trades: 0
Daily P&L: $0.00

No open positions at the moment.

Use /signals to check for new trading opportunities.
"""
        await update.message.reply_text(message, parse_mode='Markdown')

    async def signals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /signals command"""
        # This will be connected to the signal detector
        message = """
📊 **Signal Status**

No active signals at the moment.

Monitoring 6 strategies across 3 timeframes:
✅ 1H Pure Momentum
✅ 1H ATR Momentum
✅ 4H Pure AO
✅ 4H ATR Momentum
✅ 1D Pure AO
✅ 1D ATR Momentum

All systems operational. Waiting for 4-layer alignment...
"""
        await update.message.reply_text(message, parse_mode='Markdown')

    async def dashboard_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /dashboard command"""
        message = """
📈 **Trading Dashboard**

**Open Positions:** 0
**Daily Trades:** 0
**Daily P&L:** $0.00 (0%)

**Active Signals:** 0 pending

**Risk Status:**
✅ Within daily loss limit
✅ Within position limits
✅ System operational

**Market:** XAU/USD
**Status:** 🟢 Monitoring

Last updated: Just now
"""
        await update.message.reply_text(message, parse_mode='Markdown')

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        message = """
📊 **Performance Statistics**

**This Week:**
Total Trades: 0
Win Rate: 0%
P&L: $0.00

**This Month:**
Total Trades: 0
Win Rate: 0%
P&L: $0.00

Start trading to see your statistics!
"""
        await update.message.reply_text(message, parse_mode='Markdown')

    async def journal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /journal command"""
        message = """
📓 **Trade Journal**

No trades yet.

Your trade history will appear here once you start trading.

Use /signals to find trading opportunities.
"""
        await update.message.reply_text(message, parse_mode='Markdown')

    async def error_handler(
        self, update: object, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")

        try:
            if isinstance(update, Update) and update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ An error occurred while processing your request. "
                    "Please try again later."
                )
        except Exception as e:
            logger.error(f"Error sending error message: {e}")

    async def send_message(self, message: str, parse_mode: str = 'Markdown'):
        """
        Send message to configured chat

        Args:
            message: Message text
            parse_mode: Parse mode (Markdown or HTML)
        """
        try:
            if self.application:
                await self.application.bot.send_message(
                    chat_id=self.chat_id, text=message, parse_mode=parse_mode
                )
                logger.info("Message sent successfully")
            else:
                logger.warning("Bot application not initialized")
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def send_entry_alert(self, signal: Dict):
        """Send entry signal alert"""
        try:
            message = SignalFormatter.format_entry_alert(signal)
            await self.send_message(message)
        except Exception as e:
            logger.error(f"Error sending entry alert: {e}")

    async def send_exit_alert(self, position: Dict, exit_reason: str, exit_price: float):
        """Send exit signal alert"""
        try:
            message = PositionFormatter.format_exit_alert(
                position, exit_reason, exit_price
            )
            await self.send_message(message)
        except Exception as e:
            logger.error(f"Error sending exit alert: {e}")

    async def send_position_update(self, position: Dict):
        """Send position update"""
        try:
            message = PositionFormatter.format_position_update(position)
            await self.send_message(message)
        except Exception as e:
            logger.error(f"Error sending position update: {e}")

    def setup(self):
        """Setup bot handlers"""
        self.application = Application.builder().token(self.token).build()

        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("signals", self.signals_command))
        self.application.add_handler(CommandHandler("dashboard", self.dashboard_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("journal", self.journal_command))

        # Add error handler
        self.application.add_error_handler(self.error_handler)

        logger.info("Bot handlers configured")

    async def start(self):
        """Start the bot"""
        if not self.application:
            self.setup()

        logger.info("Starting bot...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("Bot started successfully")

    async def stop(self):
        """Stop the bot"""
        if self.application:
            logger.info("Stopping bot...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Bot stopped")
