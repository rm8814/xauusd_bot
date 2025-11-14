"""
Main Entry Point
XAU/USD Telegram Trading Bot
"""

import asyncio
import signal
import sys
from datetime import datetime
import logging

# Import utilities
from src.monitoring.logger import setup_logging
from src.utils.config_loader import ConfigLoader

# Import core components
from src.data.data_fetcher import DataFetcher, DataValidator
from src.core.signals import SignalDetector
from src.core.position import PositionManager
from src.core.risk_manager import RiskManager
from src.database.models import Database
from src.telegram.bot import TradingBot

logger = logging.getLogger(__name__)


class TradingBotApplication:
    """Main trading bot application"""

    def __init__(self):
        """Initialize application"""
        self.config = None
        self.data_fetcher = None
        self.signal_detectors = {}
        self.position_manager = None
        self.risk_manager = None
        self.bot = None
        self.db = None
        self.db_session = None
        self.running = False
        self.account_balance = 100.0  # Initial balance

    def load_configuration(self):
        """Load all configuration files"""
        logger.info("Loading configuration...")

        config_loader = ConfigLoader()
        self.config = config_loader.get_all_config()

        # Validate configuration
        if not config_loader.validate_config(self.config):
            logger.error("Configuration validation failed")
            sys.exit(1)

        logger.info("Configuration loaded successfully")

    def initialize_database(self):
        """Initialize database"""
        logger.info("Initializing database...")

        db_path = self.config['database']['path']
        self.db = Database(db_path)
        self.db.create_tables()
        self.db_session = self.db.get_session()

        logger.info(f"Database initialized: {db_path}")

    def initialize_components(self):
        """Initialize all bot components"""
        logger.info("Initializing components...")

        # Initialize data fetcher
        api_key = self.config['api']['twelve_data_key']
        self.data_fetcher = DataFetcher(api_key)

        # Initialize signal detectors for each strategy
        strategies = self.config['strategies'].get('strategies', {})
        indicators = self.config['indicators'].get('indicators', {})
        wait_time = self.config['main'].get('signal', {}).get('wait_time_minutes', 5)

        for strategy_id, strategy_config in strategies.items():
            if strategy_config.get('enabled', True):
                self.signal_detectors[strategy_id] = SignalDetector(
                    {strategy_id: strategy_config}, indicators, wait_time
                )
                logger.info(f"Signal detector initialized: {strategy_id}")

        # Initialize position manager
        self.position_manager = PositionManager(
            self.db_session, strategies
        )

        # Initialize risk manager
        self.risk_manager = RiskManager(
            self.config['risk_management'], self.db_session
        )

        # Initialize Telegram bot
        telegram_config = self.config['telegram']
        self.bot = TradingBot(
            telegram_config['bot_token'], telegram_config['chat_id']
        )
        self.bot.setup()

        logger.info("All components initialized")

    async def check_signals(self):
        """Check for trading signals across all strategies"""
        try:
            current_time = datetime.now()

            for strategy_id, detector in self.signal_detectors.items():
                strategy = self.config['strategies']['strategies'][strategy_id]
                timeframe = strategy['timeframe']

                # Fetch data for this timeframe
                df = self.data_fetcher.fetch_ohlcv(timeframe)

                if df is None or not DataValidator.validate_dataframe(df):
                    logger.warning(f"Invalid data for {strategy_id}")
                    continue

                # Check for signals
                signal = detector.check_signal(df, strategy_id, current_time)

                if signal:
                    logger.info(f"Signal detected: {strategy_id} - {signal['direction']}")

                    # Validate with risk manager
                    is_valid, reason, position_size = self.risk_manager.validate_trade_setup(
                        signal, self.account_balance
                    )

                    if is_valid:
                        # Send entry alert
                        await self.bot.send_entry_alert(signal)
                        logger.info(f"Entry alert sent for {strategy_id}")

                        # Check if auto-trading enabled
                        if self.config['trading']['enable_live_trading']:
                            # Open position automatically
                            trade_id = self.position_manager.open_position(
                                signal, position_size
                            )
                            if trade_id:
                                logger.info(f"Position opened: Trade ID {trade_id}")
                    else:
                        logger.warning(f"Signal rejected: {reason}")

        except Exception as e:
            logger.error(f"Error checking signals: {e}")

    async def monitor_positions(self):
        """Monitor open positions and check exit conditions"""
        try:
            open_positions = self.position_manager.get_open_positions()

            for position in open_positions:
                trade = position.trade
                strategy_id = f"strategy_{trade.strategy_id}"
                timeframe = trade.timeframe

                # Get current price
                current_price = self.data_fetcher.get_current_price()

                if current_price is None:
                    logger.warning(f"Could not get current price for position {position.id}")
                    continue

                # Update position with current price
                self.position_manager.update_position(trade.id, current_price)

                # Fetch data for exit condition checking
                df = self.data_fetcher.fetch_ohlcv(timeframe)

                if df is None:
                    continue

                # Check exit conditions
                exit_signal = self.position_manager.check_exit_conditions(
                    trade.id, current_price, df
                )

                if exit_signal and exit_signal.get('should_exit'):
                    logger.info(
                        f"Exit signal for position {trade.id}: {exit_signal['exit_reason']}"
                    )

                    # Get position summary for alert
                    pos_summary = self.position_manager.get_position_summary(trade.id)

                    # Send exit alert
                    await self.bot.send_exit_alert(
                        pos_summary,
                        exit_signal['exit_reason'],
                        exit_signal['exit_price'],
                    )

                    # Close position if auto-trading enabled
                    if self.config['trading']['enable_live_trading']:
                        self.position_manager.close_position(
                            trade.id,
                            exit_signal['exit_price'],
                            exit_signal['exit_reason'],
                        )
                        logger.info(f"Position closed: Trade ID {trade.id}")

        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")

    async def trading_loop(self):
        """Main trading loop"""
        logger.info("Starting trading loop...")

        update_interval = self.config['main'].get('data', {}).get(
            'update_interval_seconds', 60
        )

        while self.running:
            try:
                # Check for new signals
                await self.check_signals()

                # Monitor open positions
                await self.monitor_positions()

                # Clean up old pending signals
                for detector in self.signal_detectors.values():
                    detector.clear_old_pending_signals(max_age_minutes=30)

                # Wait before next iteration
                await asyncio.sleep(update_interval)

            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(10)  # Wait a bit before retrying

    async def run(self):
        """Run the bot"""
        try:
            logger.info("=" * 60)
            logger.info("XAU/USD TRADING BOT STARTING")
            logger.info("=" * 60)

            # Load configuration
            self.load_configuration()

            # Initialize database
            self.initialize_database()

            # Initialize components
            self.initialize_components()

            # Start Telegram bot
            await self.bot.start()

            # Send startup message
            await self.bot.send_message(
                "🚀 **Bot Started**\n\n"
                "XAU/USD Trading Bot is now operational.\n"
                "Monitoring 6 strategies across 3 timeframes.\n\n"
                "Use /help to see available commands."
            )

            # Set running flag
            self.running = True

            # Start trading loop
            await self.trading_loop()

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Shutdown the bot gracefully"""
        logger.info("Shutting down...")

        self.running = False

        # Send shutdown message
        if self.bot:
            try:
                await self.bot.send_message(
                    "⚠️ **Bot Stopping**\n\n"
                    "Trading bot is shutting down.\n"
                    "All open positions remain active."
                )
            except Exception as e:
                logger.error(f"Error sending shutdown message: {e}")

            # Stop bot
            await self.bot.stop()

        # Close database session
        if self.db_session:
            self.db_session.close()

        logger.info("Shutdown complete")


def signal_handler(signum, frame):
    """Handle termination signals"""
    logger.info(f"Received signal {signum}")
    sys.exit(0)


async def main():
    """Main entry point"""
    # Setup logging
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    setup_logging(log_level)

    logger.info("Starting XAU/USD Trading Bot...")

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and run application
    app = TradingBotApplication()
    await app.run()


if __name__ == "__main__":
    import os

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
