"""
Configuration Loader
Loads configuration from YAML files and environment variables
"""

import yaml
import os
from typing import Dict, Optional
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load configuration from files and environment"""

    def __init__(self, config_dir: str = "config"):
        """
        Initialize config loader

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = config_dir
        load_dotenv()  # Load environment variables

    def load_yaml(self, filename: str) -> Optional[Dict]:
        """Load YAML configuration file"""
        try:
            filepath = os.path.join(self.config_dir, filename)
            with open(filepath, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {filepath}")
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {filepath}")
            return None
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {filepath}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading configuration from {filepath}: {e}")
            return None

    def load_config(self) -> Dict:
        """Load main configuration"""
        return self.load_yaml("config.yaml") or {}

    def load_strategies(self) -> Dict:
        """Load strategies configuration"""
        return self.load_yaml("strategies.yaml") or {}

    def load_indicators(self) -> Dict:
        """Load indicators configuration"""
        return self.load_yaml("indicators.yaml") or {}

    def load_risk_management(self) -> Dict:
        """Load risk management configuration"""
        return self.load_yaml("risk_management.yaml") or {}

    def get_env(self, key: str, default: str = None) -> Optional[str]:
        """Get environment variable"""
        value = os.getenv(key, default)
        if value is None:
            logger.warning(f"Environment variable not set: {key}")
        return value

    def get_telegram_config(self) -> Dict:
        """Get Telegram configuration from environment"""
        return {
            'bot_token': self.get_env('TELEGRAM_BOT_TOKEN', ''),
            'chat_id': self.get_env('TELEGRAM_CHAT_ID', ''),
        }

    def get_api_config(self) -> Dict:
        """Get API configuration from environment"""
        return {
            'twelve_data_key': self.get_env('TWELVE_DATA_API_KEY', ''),
        }

    def get_trading_config(self) -> Dict:
        """Get trading configuration from environment"""
        return {
            'initial_balance': float(self.get_env('INITIAL_BALANCE', '100')),
            'lot_size': float(self.get_env('LOT_SIZE', '0.01')),
            'enable_live_trading': self.get_env('ENABLE_LIVE_TRADING', 'false').lower() == 'true',
        }

    def get_database_config(self) -> Dict:
        """Get database configuration"""
        return {
            'path': self.get_env('DATABASE_PATH', 'database/trades.db'),
        }

    def get_all_config(self) -> Dict:
        """Load all configuration"""
        return {
            'main': self.load_config(),
            'strategies': self.load_strategies(),
            'indicators': self.load_indicators(),
            'risk_management': self.load_risk_management(),
            'telegram': self.get_telegram_config(),
            'api': self.get_api_config(),
            'trading': self.get_trading_config(),
            'database': self.get_database_config(),
        }

    def validate_config(self, config: Dict) -> bool:
        """Validate configuration"""
        required_keys = ['telegram', 'api', 'strategies', 'indicators']

        for key in required_keys:
            if key not in config or not config[key]:
                logger.error(f"Missing or empty configuration: {key}")
                return False

        # Validate Telegram config
        if not config['telegram'].get('bot_token'):
            logger.error("Telegram bot token not configured")
            return False

        if not config['telegram'].get('chat_id'):
            logger.error("Telegram chat ID not configured")
            return False

        # Validate API config
        if not config['api'].get('twelve_data_key'):
            logger.error("TwelveData API key not configured")
            return False

        logger.info("Configuration validated successfully")
        return True
