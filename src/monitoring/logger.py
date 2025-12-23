"""
Logging Configuration
Sets up logging for the application
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logging(log_level: str = "INFO", log_dir: str = "logs"):
    """
    Setup logging configuration

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    # Convert log level string to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler (simple format)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # Main log file (rotating)
    main_log_file = os.path.join(log_dir, "bot.log")
    main_handler = RotatingFileHandler(
        main_log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
    )
    main_handler.setLevel(level)
    main_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(main_handler)

    # Error log file (only errors and above)
    error_log_file = os.path.join(log_dir, "errors.log")
    error_handler = RotatingFileHandler(
        error_log_file, maxBytes=5 * 1024 * 1024, backupCount=3  # 5MB
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)

    # Trade log file (for trade-specific logs)
    trade_log_file = os.path.join(log_dir, "trades.log")
    trade_handler = RotatingFileHandler(
        trade_log_file, maxBytes=5 * 1024 * 1024, backupCount=3  # 5MB
    )
    trade_handler.setLevel(logging.INFO)
    trade_handler.setFormatter(detailed_formatter)

    # Create trade logger
    trade_logger = logging.getLogger("trade")
    trade_logger.addHandler(trade_handler)
    trade_logger.setLevel(logging.INFO)

    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.info(f"Logging initialized - Level: {log_level}, Directory: {log_dir}")


def get_logger(name: str) -> logging.Logger:
    """Get logger for specific module"""
    return logging.getLogger(name)


def log_trade(message: str):
    """Log trade-specific message"""
    trade_logger = logging.getLogger("trade")
    trade_logger.info(message)
