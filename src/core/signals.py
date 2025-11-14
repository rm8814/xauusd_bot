"""
Signal Detection Module
Implements 3-layer confirmation system for trading signals
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

from src.core.indicators import Indicators

logger = logging.getLogger(__name__)


class SignalDetector:
    """Detects trading signals using 3-layer confirmation system"""

    def __init__(self, strategy_config: dict, indicator_params: dict, wait_time_minutes: int = 5):
        """
        Initialize signal detector

        Args:
            strategy_config: Strategy configuration from strategies.yaml
            indicator_params: Indicator parameters from indicators.yaml
            wait_time_minutes: Minutes to wait after initial signal alignment
        """
        self.strategy_config = strategy_config
        self.indicator_params = indicator_params
        self.wait_time_minutes = wait_time_minutes
        self.pending_signals = {}  # Track signals waiting for confirmation

    def check_signal(
        self, df: pd.DataFrame, strategy_id: str, current_time: datetime
    ) -> Optional[Dict]:
        """
        Check if valid trading signal exists

        Returns:
            Dict with signal details if valid signal found, None otherwise
        """
        try:
            # Get strategy configuration
            strategy = self.strategy_config[strategy_id]
            indicators = strategy['indicators']

            # Calculate all 3 indicator signals
            primary_signal = self._get_indicator_signal(
                df, indicators['primary']['type']
            )
            confirmation_signal = self._get_indicator_signal(
                df, indicators['confirmation']['type']
            )
            baseline_signal = self._get_indicator_signal(
                df, indicators['baseline']['type']
            )

            # Get latest signals
            primary = primary_signal.iloc[-1] if len(primary_signal) > 0 else 0
            confirmation = confirmation_signal.iloc[-1] if len(confirmation_signal) > 0 else 0
            baseline = baseline_signal.iloc[-1] if len(baseline_signal) > 0 else 0

            # Check if all 3 indicators are aligned
            if primary != 0 and primary == confirmation == baseline:
                signal_key = f"{strategy_id}_{primary}"

                # Check if this is a new signal or existing pending signal
                if signal_key not in self.pending_signals:
                    # New signal - start waiting period
                    self.pending_signals[signal_key] = {
                        'detected_at': current_time,
                        'direction': 'LONG' if primary > 0 else 'SHORT',
                        'primary': primary,
                        'confirmation': confirmation,
                        'baseline': baseline,
                        'strategy_id': strategy_id,
                        'strategy_name': strategy.get('name', strategy_id),
                        'timeframe': strategy.get('timeframe', 'unknown'),
                        'mode': strategy.get('mode', 'PURE'),
                    }
                    logger.info(
                        f"New signal detected for {strategy_id}: "
                        f"{self.pending_signals[signal_key]['direction']}"
                    )
                    return None  # Signal pending, not ready yet

                else:
                    # Existing signal - check if wait time has passed
                    pending = self.pending_signals[signal_key]
                    time_elapsed = (
                        current_time - pending['detected_at']
                    ).total_seconds() / 60

                    if time_elapsed >= self.wait_time_minutes:
                        # Wait time passed, validate signal still holds
                        if primary == confirmation == baseline:
                            # Signal confirmed! Generate entry signal
                            signal = self._generate_signal(df, pending, current_time)

                            # Remove from pending
                            del self.pending_signals[signal_key]

                            logger.info(
                                f"Signal confirmed for {strategy_id}: "
                                f"{signal['direction']} at ${signal['entry_price']:.2f}"
                            )
                            return signal
                        else:
                            # Signal no longer valid
                            logger.warning(
                                f"Signal invalidated for {strategy_id} - "
                                f"indicators no longer aligned"
                            )
                            del self.pending_signals[signal_key]
                            return None
            else:
                # Check if any pending signals should be invalidated
                signal_key = f"{strategy_id}_1"  # Bullish
                if signal_key in self.pending_signals:
                    if primary != 1 or confirmation != 1 or baseline != 1:
                        logger.warning(f"Bullish signal invalidated for {strategy_id}")
                        del self.pending_signals[signal_key]

                signal_key = f"{strategy_id}_-1"  # Bearish
                if signal_key in self.pending_signals:
                    if primary != -1 or confirmation != -1 or baseline != -1:
                        logger.warning(f"Bearish signal invalidated for {strategy_id}")
                        del self.pending_signals[signal_key]

            return None

        except Exception as e:
            logger.error(f"Error checking signal for {strategy_id}: {e}")
            return None

    def _get_indicator_signal(self, df: pd.DataFrame, indicator_type: str) -> pd.Series:
        """Get signal from indicator"""
        params = self.indicator_params.get(indicator_type, {})
        return Indicators.get_indicator_signal(df, indicator_type, params)

    def _generate_signal(
        self, df: pd.DataFrame, pending_signal: Dict, current_time: datetime
    ) -> Dict:
        """Generate full signal details with entry price, SL, TP"""
        strategy_id = pending_signal['strategy_id']
        strategy = self.strategy_config[strategy_id]

        # Get current price (close of last candle)
        entry_price = float(df['close'].iloc[-1])

        # Calculate ATR for SL/TP
        atr_params = self.indicator_params.get('atr', {})
        atr = Indicators.calculate_atr(df, atr_params.get('period', 14))
        current_atr = float(atr.iloc[-1])

        # Generate signal dict
        signal = {
            'signal_id': f"{strategy_id}_{int(current_time.timestamp())}",
            'strategy_id': strategy_id,
            'strategy_name': pending_signal['strategy_name'],
            'timeframe': pending_signal['timeframe'],
            'mode': pending_signal['mode'],
            'direction': pending_signal['direction'],
            'entry_type': 'STANDARD',  # Default entry type
            'entry_price': entry_price,
            'atr': current_atr,
            'signal_time': current_time,
            'detected_at': pending_signal['detected_at'],
            'indicators': {
                'primary': {
                    'name': strategy['indicators']['primary']['name'],
                    'signal': pending_signal['primary'],
                },
                'confirmation': {
                    'name': strategy['indicators']['confirmation']['name'],
                    'signal': pending_signal['confirmation'],
                },
                'baseline': {
                    'name': strategy['indicators']['baseline']['name'],
                    'signal': pending_signal['baseline'],
                },
            },
        }

        # Add SL/TP for ATR mode
        if strategy['mode'] == 'ATR':
            atr_config = strategy.get('atr', {})
            sl_multiplier = atr_config.get('stop_loss_multiplier', 1.5)
            tp_multiplier = atr_config.get('take_profit_multiplier', 4.5)

            if pending_signal['direction'] == 'LONG':
                signal['stop_loss'] = entry_price - (current_atr * sl_multiplier)
                signal['take_profit'] = entry_price + (current_atr * tp_multiplier)
            else:  # SHORT
                signal['stop_loss'] = entry_price + (current_atr * sl_multiplier)
                signal['take_profit'] = entry_price - (current_atr * tp_multiplier)

            signal['risk_reward_ratio'] = tp_multiplier / sl_multiplier

        # Calculate quality score (0-100)
        signal['quality_score'] = self._calculate_quality_score(df, signal)

        return signal

    def _calculate_quality_score(self, df: pd.DataFrame, signal: Dict) -> int:
        """
        Calculate signal quality score (0-100)
        Based on:
        - Indicator strength
        - Trend strength
        - Volume
        - Volatility
        """
        score = 70  # Base score for 3-layer alignment

        try:
            # Check trend strength (price distance from baseline)
            # Higher distance = stronger trend = higher score
            close = df['close'].iloc[-1]

            # Add points for strong volume
            if len(df) > 20:
                avg_volume = df['volume'].iloc[-20:].mean()
                current_volume = df['volume'].iloc[-1]
                if current_volume > avg_volume * 1.2:
                    score += 10
                elif current_volume > avg_volume:
                    score += 5

            # Add points for momentum
            if len(df) > 10:
                momentum = df['close'].iloc[-1] - df['close'].iloc[-10]
                if signal['direction'] == 'LONG' and momentum > 0:
                    score += 10
                elif signal['direction'] == 'SHORT' and momentum < 0:
                    score += 10

            # Cap at 100
            score = min(100, score)

        except Exception as e:
            logger.error(f"Error calculating quality score: {e}")

        return score

    def check_continuation_entry(
        self, df: pd.DataFrame, strategy_id: str, current_time: datetime
    ) -> Optional[Dict]:
        """
        Check for continuation entry signal
        Requires: Strong trend + volatility expansion + new high/low + 3-layer alignment
        """
        try:
            strategy = self.strategy_config[strategy_id]

            # First check if 3-layer alignment exists
            signal = self.check_signal(df, strategy_id, current_time)
            if not signal:
                return None

            # Check for volatility expansion
            volatility_indicator = strategy['indicators']['volatility']['type']
            volatility_params = self.indicator_params.get(volatility_indicator, {})

            is_expanding = Indicators.calculate_volatility_expansion(
                df, volatility_indicator, volatility_params
            )

            if not is_expanding:
                return None

            # Check for new high/low
            lookback = 20
            if len(df) < lookback:
                return None

            current_high = df['high'].iloc[-1]
            current_low = df['low'].iloc[-1]
            recent_high = df['high'].iloc[-lookback:-1].max()
            recent_low = df['low'].iloc[-lookback:-1].min()

            is_new_high = current_high > recent_high
            is_new_low = current_low < recent_low

            if signal['direction'] == 'LONG' and is_new_high:
                signal['entry_type'] = 'CONTINUATION'
                signal['quality_score'] = min(100, signal['quality_score'] + 10)
                logger.info(f"Continuation entry detected for {strategy_id}: LONG")
                return signal
            elif signal['direction'] == 'SHORT' and is_new_low:
                signal['entry_type'] = 'CONTINUATION'
                signal['quality_score'] = min(100, signal['quality_score'] + 10)
                logger.info(f"Continuation entry detected for {strategy_id}: SHORT")
                return signal

            return None

        except Exception as e:
            logger.error(f"Error checking continuation entry: {e}")
            return None

    def get_pending_signals(self) -> Dict:
        """Get all pending signals waiting for confirmation"""
        return self.pending_signals.copy()

    def clear_old_pending_signals(self, max_age_minutes: int = 30):
        """Clear pending signals older than max_age_minutes"""
        current_time = datetime.now()
        to_remove = []

        for key, signal in self.pending_signals.items():
            age = (current_time - signal['detected_at']).total_seconds() / 60
            if age > max_age_minutes:
                to_remove.append(key)

        for key in to_remove:
            logger.info(f"Removing stale pending signal: {key}")
            del self.pending_signals[key]
