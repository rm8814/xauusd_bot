"""
Technical Indicators Module
Calculates indicators and returns signals: +1 (bullish), -1 (bearish), 0 (neutral)
All indicators are non-repainting (use closed candles only)
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class Indicators:
    """Calculate technical indicators and generate trading signals"""

    @staticmethod
    def awesome_oscillator(df: pd.DataFrame, fast: int = 5, slow: int = 34) -> pd.Series:
        """
        Awesome Oscillator (AO)
        AO = SMA(median price, 5) - SMA(median price, 34)
        Signal: AO > 0 = bullish (+1), AO < 0 = bearish (-1)
        """
        median_price = (df['high'] + df['low']) / 2
        fast_sma = median_price.rolling(window=fast).mean()
        slow_sma = median_price.rolling(window=slow).mean()
        ao = fast_sma - slow_sma

        signals = pd.Series(0, index=df.index)
        signals[ao > 0] = 1  # Bullish
        signals[ao < 0] = -1  # Bearish

        return signals

    @staticmethod
    def momentum(df: pd.DataFrame, period: int = 10) -> pd.Series:
        """
        Momentum Indicator
        Momentum = Close - Close[period]
        Signal: Momentum > 0 = bullish (+1), Momentum < 0 = bearish (-1)
        """
        momentum = df['close'] - df['close'].shift(period)

        signals = pd.Series(0, index=df.index)
        signals[momentum > 0] = 1  # Bullish
        signals[momentum < 0] = -1  # Bearish

        return signals

    @staticmethod
    def chaikin_oscillator(df: pd.DataFrame, fast: int = 3, slow: int = 10) -> pd.Series:
        """
        Chaikin Oscillator
        ADL = Cumulative sum of: ((Close - Low) - (High - Close)) / (High - Low) * Volume
        Chaikin = EMA(ADL, fast) - EMA(ADL, slow)
        Signal: Chaikin > 0 = bullish (+1), Chaikin < 0 = bearish (-1)
        """
        # Calculate Close Location Value (CLV)
        clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (
            df['high'] - df['low']
        )
        clv = clv.fillna(0)  # Handle division by zero

        # Calculate Accumulation/Distribution Line (ADL)
        adl = (clv * df['volume']).cumsum()

        # Calculate Chaikin Oscillator
        fast_ema = adl.ewm(span=fast, adjust=False).mean()
        slow_ema = adl.ewm(span=slow, adjust=False).mean()
        chaikin = fast_ema - slow_ema

        signals = pd.Series(0, index=df.index)
        signals[chaikin > 0] = 1  # Bullish
        signals[chaikin < 0] = -1  # Bearish

        return signals

    @staticmethod
    def rvi(df: pd.DataFrame, period: int = 10, signal_period: int = 4) -> pd.Series:
        """
        Relative Vigor Index (RVI)
        RVI = SMA of (Close - Open) / SMA of (High - Low)
        Signal line = SMA of RVI
        Signal: RVI > signal = bullish (+1), RVI < signal = bearish (-1)
        """
        # Calculate numerator and denominator
        numerator = (df['close'] - df['open']).rolling(window=period).mean()
        denominator = (df['high'] - df['low']).rolling(window=period).mean()

        # Avoid division by zero
        rvi_line = numerator / denominator.replace(0, np.nan)
        rvi_line = rvi_line.fillna(0)

        # Calculate signal line
        signal_line = rvi_line.rolling(window=signal_period).mean()

        signals = pd.Series(0, index=df.index)
        signals[rvi_line > signal_line] = 1  # Bullish
        signals[rvi_line < signal_line] = -1  # Bearish

        return signals

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range (ATR)"""
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    @staticmethod
    def supertrend(
        df: pd.DataFrame, period: int = 10, multiplier: float = 3.0
    ) -> pd.Series:
        """
        SuperTrend Indicator
        Signal: Price > SuperTrend = bullish (+1), Price < SuperTrend = bearish (-1)
        """
        atr = Indicators.calculate_atr(df, period)
        hl_avg = (df['high'] + df['low']) / 2

        upper_band = hl_avg + (multiplier * atr)
        lower_band = hl_avg - (multiplier * atr)

        supertrend = pd.Series(0.0, index=df.index)
        direction = pd.Series(1, index=df.index)

        for i in range(1, len(df)):
            # Update bands
            if df['close'].iloc[i] > upper_band.iloc[i - 1]:
                direction.iloc[i] = 1
            elif df['close'].iloc[i] < lower_band.iloc[i - 1]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = direction.iloc[i - 1]

                if (
                    direction.iloc[i] == 1
                    and lower_band.iloc[i] < lower_band.iloc[i - 1]
                ):
                    lower_band.iloc[i] = lower_band.iloc[i - 1]
                if (
                    direction.iloc[i] == -1
                    and upper_band.iloc[i] > upper_band.iloc[i - 1]
                ):
                    upper_band.iloc[i] = upper_band.iloc[i - 1]

            # Set SuperTrend value
            if direction.iloc[i] == 1:
                supertrend.iloc[i] = lower_band.iloc[i]
            else:
                supertrend.iloc[i] = upper_band.iloc[i]

        signals = pd.Series(0, index=df.index)
        signals[df['close'] > supertrend] = 1  # Bullish
        signals[df['close'] < supertrend] = -1  # Bearish

        return signals

    @staticmethod
    def psar(
        df: pd.DataFrame,
        af_start: float = 0.02,
        af_increment: float = 0.02,
        af_max: float = 0.2,
    ) -> pd.Series:
        """
        Parabolic SAR
        Signal: Price > PSAR = bullish (+1), Price < PSAR = bearish (-1)
        """
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values

        psar = np.zeros(len(df))
        psarbull = np.zeros(len(df))
        psarbear = np.zeros(len(df))
        bull = True
        af = af_start
        ep = low[0]
        hp = high[0]
        lp = low[0]

        for i in range(1, len(df)):
            if bull:
                psar[i] = psar[i - 1] + af * (hp - psar[i - 1])
            else:
                psar[i] = psar[i - 1] + af * (lp - psar[i - 1])

            reverse = False

            if bull:
                if low[i] < psar[i]:
                    bull = False
                    reverse = True
                    psar[i] = hp
                    lp = low[i]
                    af = af_start
            else:
                if high[i] > psar[i]:
                    bull = True
                    reverse = True
                    psar[i] = lp
                    hp = high[i]
                    af = af_start

            if not reverse:
                if bull:
                    if high[i] > hp:
                        hp = high[i]
                        af = min(af + af_increment, af_max)
                    if low[i - 1] < psar[i]:
                        psar[i] = low[i - 1]
                    if low[i - 2] < psar[i]:
                        psar[i] = low[i - 2]
                else:
                    if low[i] < lp:
                        lp = low[i]
                        af = min(af + af_increment, af_max)
                    if high[i - 1] > psar[i]:
                        psar[i] = high[i - 1]
                    if high[i - 2] > psar[i]:
                        psar[i] = high[i - 2]

            if bull:
                psarbull[i] = psar[i]
            else:
                psarbear[i] = psar[i]

        psar_series = pd.Series(psar, index=df.index)
        signals = pd.Series(0, index=df.index)
        signals[df['close'] > psar_series] = 1  # Bullish
        signals[df['close'] < psar_series] = -1  # Bearish

        return signals

    @staticmethod
    def hull_ma(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """
        Hull Moving Average
        Signal: Price > Hull MA = bullish (+1), Price < Hull MA = bearish (-1)
        """
        half_length = int(period / 2)
        sqrt_length = int(np.sqrt(period))

        wma_half = df['close'].rolling(window=half_length).apply(
            lambda x: np.sum(x * np.arange(1, len(x) + 1)) / np.sum(np.arange(1, len(x) + 1)),
            raw=True
        )
        wma_full = df['close'].rolling(window=period).apply(
            lambda x: np.sum(x * np.arange(1, len(x) + 1)) / np.sum(np.arange(1, len(x) + 1)),
            raw=True
        )

        raw_hma = 2 * wma_half - wma_full
        hull_ma = raw_hma.rolling(window=sqrt_length).apply(
            lambda x: np.sum(x * np.arange(1, len(x) + 1)) / np.sum(np.arange(1, len(x) + 1)),
            raw=True
        )

        signals = pd.Series(0, index=df.index)
        signals[df['close'] > hull_ma] = 1  # Bullish
        signals[df['close'] < hull_ma] = -1  # Bearish

        return signals

    @staticmethod
    def keltner_channel(
        df: pd.DataFrame, period: int = 20, atr_period: int = 10, multiplier: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Keltner Channel (for volatility measurement)
        Returns: (upper_band, middle_band, lower_band)
        """
        ema = df['close'].ewm(span=period, adjust=False).mean()
        atr = Indicators.calculate_atr(df, atr_period)

        upper_band = ema + (multiplier * atr)
        lower_band = ema - (multiplier * atr)

        return upper_band, ema, lower_band

    @staticmethod
    def bollinger_band_width(
        df: pd.DataFrame, period: int = 20, std: float = 2.0
    ) -> pd.Series:
        """
        Bollinger Band Width (volatility indicator)
        Width = (Upper Band - Lower Band) / Middle Band
        Higher values indicate higher volatility
        """
        sma = df['close'].rolling(window=period).mean()
        std_dev = df['close'].rolling(window=period).std()

        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)

        bb_width = (upper_band - lower_band) / sma

        return bb_width

    @staticmethod
    def donchian_channel(
        df: pd.DataFrame, period: int = 20
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Donchian Channel (volatility indicator)
        Returns: (upper_band, middle_band, lower_band)
        """
        upper_band = df['high'].rolling(window=period).max()
        lower_band = df['low'].rolling(window=period).min()
        middle_band = (upper_band + lower_band) / 2

        return upper_band, middle_band, lower_band

    @staticmethod
    def get_indicator_signal(
        df: pd.DataFrame, indicator_type: str, params: dict
    ) -> pd.Series:
        """
        Get signal for any indicator type
        Returns: pd.Series with values +1 (bullish), -1 (bearish), 0 (neutral)
        """
        try:
            if indicator_type == "awesome_oscillator":
                return Indicators.awesome_oscillator(
                    df, params.get('fast_period', 5), params.get('slow_period', 34)
                )
            elif indicator_type == "momentum":
                return Indicators.momentum(df, params.get('period', 10))
            elif indicator_type == "chaikin_oscillator":
                return Indicators.chaikin_oscillator(
                    df, params.get('fast_period', 3), params.get('slow_period', 10)
                )
            elif indicator_type == "rvi":
                return Indicators.rvi(
                    df, params.get('period', 10), params.get('signal_period', 4)
                )
            elif indicator_type == "supertrend":
                return Indicators.supertrend(
                    df, params.get('period', 10), params.get('multiplier', 3.0)
                )
            elif indicator_type == "psar":
                return Indicators.psar(
                    df,
                    params.get('af_start', 0.02),
                    params.get('af_increment', 0.02),
                    params.get('af_max', 0.2),
                )
            elif indicator_type == "hull_ma":
                return Indicators.hull_ma(df, params.get('period', 20))
            else:
                logger.error(f"Unknown indicator type: {indicator_type}")
                return pd.Series(0, index=df.index)
        except Exception as e:
            logger.error(f"Error calculating {indicator_type}: {e}")
            return pd.Series(0, index=df.index)

    @staticmethod
    def calculate_volatility_expansion(
        df: pd.DataFrame, indicator_type: str, params: dict, lookback: int = 20
    ) -> bool:
        """
        Check if volatility is expanding (for continuation entries)
        Returns: True if volatility is expanding, False otherwise
        """
        try:
            if indicator_type == "keltner_channel":
                upper, middle, lower = Indicators.keltner_channel(
                    df, params.get('period', 20), params.get('atr_period', 10),
                    params.get('multiplier', 2.0)
                )
                width = upper - lower
                avg_width = width.rolling(window=lookback).mean()
                return width.iloc[-1] > avg_width.iloc[-1]

            elif indicator_type == "bollinger_band_width":
                bb_width = Indicators.bollinger_band_width(
                    df, params.get('period', 20), params.get('std', 2.0)
                )
                avg_width = bb_width.rolling(window=lookback).mean()
                return bb_width.iloc[-1] > avg_width.iloc[-1]

            elif indicator_type == "donchian_channel":
                upper, middle, lower = Indicators.donchian_channel(
                    df, params.get('period', 20)
                )
                width = upper - lower
                avg_width = width.rolling(window=lookback).mean()
                return width.iloc[-1] > avg_width.iloc[-1]

            else:
                return False

        except Exception as e:
            logger.error(f"Error calculating volatility expansion: {e}")
            return False
