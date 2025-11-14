"""
Data Fetcher Module
Fetches real-time OHLCV data from TwelveData API
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging
import time
import os

logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetches price data from TwelveData API"""

    def __init__(self, api_key: str, symbol: str = "XAU/USD"):
        """
        Initialize data fetcher

        Args:
            api_key: TwelveData API key
            symbol: Trading symbol (default: XAU/USD)
        """
        self.api_key = api_key
        self.symbol = symbol
        self.base_url = "https://api.twelvedata.com"
        self.cache = {}  # Simple in-memory cache

    def fetch_ohlcv(
        self, timeframe: str, outputsize: int = 100, use_cache: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data for specified timeframe

        Args:
            timeframe: Timeframe (1h, 4h, 1day)
            outputsize: Number of candles to fetch
            use_cache: Whether to use cached data

        Returns:
            DataFrame with OHLCV data or None if error
        """
        try:
            # Check cache first
            cache_key = f"{self.symbol}_{timeframe}_{outputsize}"
            if use_cache and cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                # Cache valid for 1 minute
                if (datetime.now() - cached_time).seconds < 60:
                    logger.debug(f"Using cached data for {cache_key}")
                    return cached_data.copy()

            # Convert timeframe to TwelveData format
            interval = self._convert_timeframe(timeframe)

            # Build request parameters
            params = {
                'symbol': self.symbol,
                'interval': interval,
                'outputsize': outputsize,
                'apikey': self.api_key,
                'format': 'JSON',
            }

            # Make API request
            logger.info(f"Fetching {timeframe} data for {self.symbol}")
            response = requests.get(f"{self.base_url}/time_series", params=params, timeout=10)

            if response.status_code != 200:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None

            data = response.json()

            # Check for errors
            if 'status' in data and data['status'] == 'error':
                logger.error(f"API error: {data.get('message', 'Unknown error')}")
                return None

            # Check if we have data
            if 'values' not in data or not data['values']:
                logger.warning(f"No data returned for {self.symbol}")
                return None

            # Convert to DataFrame
            df = self._parse_response(data)

            if df is None or len(df) == 0:
                logger.warning(f"Empty dataframe for {self.symbol}")
                return None

            # Cache the result
            self.cache[cache_key] = (df.copy(), datetime.now())

            logger.info(f"Successfully fetched {len(df)} candles for {self.symbol} {timeframe}")
            return df

        except requests.exceptions.Timeout:
            logger.error("API request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return None

    def _convert_timeframe(self, timeframe: str) -> str:
        """Convert internal timeframe to TwelveData interval"""
        mapping = {
            '1h': '1h',
            '4h': '4h',
            '1day': '1day',
            '1d': '1day',
        }
        return mapping.get(timeframe.lower(), timeframe)

    def _parse_response(self, data: Dict) -> Optional[pd.DataFrame]:
        """Parse API response into DataFrame"""
        try:
            values = data['values']

            # Create DataFrame
            df = pd.DataFrame(values)

            # Rename columns
            df = df.rename(
                columns={
                    'datetime': 'timestamp',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume',
                }
            )

            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['open'] = pd.to_numeric(df['open'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['close'] = pd.to_numeric(df['close'])
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0)

            # Sort by timestamp (oldest first)
            df = df.sort_values('timestamp').reset_index(drop=True)

            # Set timestamp as index
            df = df.set_index('timestamp')

            return df

        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return None

    def get_latest_candle(self, timeframe: str) -> Optional[Dict]:
        """
        Get the most recent closed candle

        Returns:
            Dict with candle data or None
        """
        try:
            df = self.fetch_ohlcv(timeframe, outputsize=1, use_cache=False)
            if df is None or len(df) == 0:
                return None

            latest = df.iloc[-1]
            return {
                'timestamp': df.index[-1],
                'open': float(latest['open']),
                'high': float(latest['high']),
                'low': float(latest['low']),
                'close': float(latest['close']),
                'volume': float(latest['volume']),
            }

        except Exception as e:
            logger.error(f"Error getting latest candle: {e}")
            return None

    def get_current_price(self) -> Optional[float]:
        """Get current market price"""
        try:
            params = {
                'symbol': self.symbol,
                'apikey': self.api_key,
            }

            response = requests.get(f"{self.base_url}/price", params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if 'price' in data:
                    return float(data['price'])

            # Fallback to latest candle
            candle = self.get_latest_candle('1h')
            if candle:
                return candle['close']

            return None

        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return None

    def clear_cache(self):
        """Clear data cache"""
        self.cache.clear()
        logger.info("Cache cleared")

    def get_api_usage(self) -> Optional[Dict]:
        """Get API usage statistics"""
        try:
            params = {'apikey': self.api_key}
            response = requests.get(f"{self.base_url}/api_usage", params=params, timeout=5)

            if response.status_code == 200:
                return response.json()

            return None

        except Exception as e:
            logger.error(f"Error getting API usage: {e}")
            return None


class DataValidator:
    """Validates OHLCV data quality"""

    @staticmethod
    def validate_dataframe(df: pd.DataFrame, min_candles: int = 50) -> bool:
        """
        Validate DataFrame has sufficient quality data

        Args:
            df: DataFrame to validate
            min_candles: Minimum required candles

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check if DataFrame exists and not empty
            if df is None or len(df) == 0:
                logger.warning("DataFrame is empty")
                return False

            # Check minimum candles
            if len(df) < min_candles:
                logger.warning(f"Insufficient candles: {len(df)} < {min_candles}")
                return False

            # Check required columns
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = set(required_columns) - set(df.columns)
            if missing_columns:
                logger.warning(f"Missing columns: {missing_columns}")
                return False

            # Check for NaN values
            if df[required_columns].isnull().any().any():
                logger.warning("DataFrame contains NaN values")
                return False

            # Check data integrity (high >= low, etc.)
            if not (df['high'] >= df['low']).all():
                logger.warning("Invalid OHLC data: high < low")
                return False

            if not (df['high'] >= df['open']).all() or not (df['high'] >= df['close']).all():
                logger.warning("Invalid OHLC data: high < open or close")
                return False

            if not (df['low'] <= df['open']).all() or not (df['low'] <= df['close']).all():
                logger.warning("Invalid OHLC data: low > open or close")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating DataFrame: {e}")
            return False

    @staticmethod
    def check_data_gaps(df: pd.DataFrame, timeframe: str) -> bool:
        """Check for gaps in time series data"""
        try:
            if df is None or len(df) < 2:
                return False

            # Convert timeframe to timedelta
            timeframe_map = {
                '1h': timedelta(hours=1),
                '4h': timedelta(hours=4),
                '1day': timedelta(days=1),
                '1d': timedelta(days=1),
            }

            expected_delta = timeframe_map.get(timeframe.lower())
            if not expected_delta:
                return True  # Unknown timeframe, skip check

            # Check gaps
            timestamps = df.index
            for i in range(1, len(timestamps)):
                delta = timestamps[i] - timestamps[i - 1]
                if delta > expected_delta * 1.5:  # Allow 50% tolerance
                    logger.warning(f"Data gap detected: {delta} at {timestamps[i]}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error checking data gaps: {e}")
            return False
