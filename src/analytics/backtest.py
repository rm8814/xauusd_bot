"""
Backtesting Module
Tests trading strategies on historical data
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import logging

from src.core.indicators import Indicators
from src.core.signals import SignalDetector
from src.data.data_fetcher import DataFetcher

logger = logging.getLogger(__name__)


class Backtest:
    """Backtesting engine for trading strategies"""

    def __init__(
        self,
        strategy_config: dict,
        indicator_params: dict,
        initial_balance: float = 100.0,
        risk_percent: float = 1.0,
    ):
        """
        Initialize backtester

        Args:
            strategy_config: Strategy configuration
            indicator_params: Indicator parameters
            initial_balance: Starting balance
            risk_percent: Risk per trade as percentage
        """
        self.strategy_config = strategy_config
        self.indicator_params = indicator_params
        self.initial_balance = initial_balance
        self.risk_percent = risk_percent
        self.trades = []
        self.equity_curve = []

    def run(
        self,
        df: pd.DataFrame,
        strategy_id: str,
        commission: float = 0.0,
    ) -> Dict:
        """
        Run backtest on historical data

        Args:
            df: Historical OHLCV data
            strategy_id: Strategy to test
            commission: Commission per trade (as percentage)

        Returns:
            Dict with backtest results
        """
        try:
            logger.info(f"Starting backtest for {strategy_id}")

            # Get strategy configuration
            strategy = self.strategy_config[strategy_id]
            mode = strategy['mode']
            indicators = strategy['indicators']

            # Calculate all indicators
            primary_signal = Indicators.get_indicator_signal(
                df, indicators['primary']['type'], self.indicator_params
            )
            volume_signal = Indicators.get_indicator_signal(
                df, indicators['volume']['type'], self.indicator_params
            )
            confirmation_signal = Indicators.get_indicator_signal(
                df, indicators['confirmation']['type'], self.indicator_params
            )
            baseline_signal = Indicators.get_indicator_signal(
                df, indicators['baseline']['type'], self.indicator_params
            )

            # Calculate ATR for position sizing and SL/TP
            atr = Indicators.calculate_atr(df, self.indicator_params.get('atr', {}).get('period', 14))

            # Initialize variables
            balance = self.initial_balance
            position = None
            equity = balance

            # Iterate through data
            for i in range(len(df)):
                current_time = df.index[i]
                current_price = df['close'].iloc[i]
                current_atr = atr.iloc[i] if i < len(atr) else 0

                # Update equity curve
                if position:
                    if position['direction'] == 'LONG':
                        unrealized_pnl = (current_price - position['entry_price']) * position['size']
                    else:
                        unrealized_pnl = (position['entry_price'] - current_price) * position['size']
                    equity = balance + unrealized_pnl
                else:
                    equity = balance

                self.equity_curve.append({
                    'timestamp': current_time,
                    'equity': equity,
                    'balance': balance,
                })

                # Check exit conditions if in position
                if position:
                    should_exit, exit_reason = self._check_exit(
                        position, current_price, primary_signal.iloc[i], mode, i
                    )

                    if should_exit:
                        # Close position
                        if position['direction'] == 'LONG':
                            pnl = (current_price - position['entry_price']) * position['size']
                        else:
                            pnl = (position['entry_price'] - current_price) * position['size']

                        # Apply commission
                        commission_cost = current_price * position['size'] * (commission / 100)
                        pnl -= commission_cost * 2  # Entry + exit

                        balance += pnl

                        # Record trade
                        self.trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': current_time,
                            'direction': position['direction'],
                            'entry_price': position['entry_price'],
                            'exit_price': current_price,
                            'size': position['size'],
                            'pnl': pnl,
                            'pnl_percent': (pnl / (position['entry_price'] * position['size'])) * 100,
                            'exit_reason': exit_reason,
                            'duration_bars': i - position['entry_bar'],
                        })

                        logger.debug(
                            f"Closed {position['direction']} at {current_price:.2f}, "
                            f"P&L: ${pnl:.2f}, Reason: {exit_reason}"
                        )

                        position = None

                # Check entry conditions if not in position
                if not position and i > 50:  # Need enough data for indicators
                    # Check if all 4 indicators align
                    primary = primary_signal.iloc[i]
                    volume = volume_signal.iloc[i]
                    confirmation = confirmation_signal.iloc[i]
                    baseline = baseline_signal.iloc[i]

                    if primary != 0 and primary == volume == confirmation == baseline:
                        # Entry signal detected
                        direction = 'LONG' if primary > 0 else 'SHORT'

                        # Calculate position size
                        if mode == 'ATR' and current_atr > 0:
                            sl_multiplier = strategy.get('atr', {}).get('stop_loss_multiplier', 1.5)
                            sl_distance = current_atr * sl_multiplier
                            risk_amount = balance * (self.risk_percent / 100)
                            position_size = risk_amount / sl_distance

                            # Set SL/TP
                            if direction == 'LONG':
                                stop_loss = current_price - sl_distance
                                take_profit = current_price + (current_atr * strategy.get('atr', {}).get('take_profit_multiplier', 4.5))
                            else:
                                stop_loss = current_price + sl_distance
                                take_profit = current_price - (current_atr * strategy.get('atr', {}).get('take_profit_multiplier', 4.5))
                        else:
                            # PURE mode or no ATR
                            position_size = balance * 0.01  # Fixed 1% position
                            stop_loss = None
                            take_profit = None

                        # Apply commission
                        commission_cost = current_price * position_size * (commission / 100)
                        balance -= commission_cost

                        # Open position
                        position = {
                            'entry_time': current_time,
                            'entry_bar': i,
                            'entry_price': current_price,
                            'direction': direction,
                            'size': position_size,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                        }

                        logger.debug(
                            f"Opened {direction} at {current_price:.2f}, "
                            f"Size: {position_size:.4f}"
                        )

            # Close any remaining position at end
            if position:
                current_price = df['close'].iloc[-1]
                if position['direction'] == 'LONG':
                    pnl = (current_price - position['entry_price']) * position['size']
                else:
                    pnl = (position['entry_price'] - current_price) * position['size']

                balance += pnl

                self.trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': df.index[-1],
                    'direction': position['direction'],
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'size': position['size'],
                    'pnl': pnl,
                    'pnl_percent': (pnl / (position['entry_price'] * position['size'])) * 100,
                    'exit_reason': 'END_OF_DATA',
                    'duration_bars': len(df) - 1 - position['entry_bar'],
                })

            # Calculate metrics
            results = self._calculate_metrics(balance)

            logger.info(f"Backtest complete for {strategy_id}")
            logger.info(f"Total Trades: {results['total_trades']}, Win Rate: {results['win_rate']:.2f}%")
            logger.info(f"Final Balance: ${results['final_balance']:.2f}, Total Return: {results['total_return']:.2f}%")

            return results

        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return {}

    def _check_exit(
        self,
        position: Dict,
        current_price: float,
        primary_signal: int,
        mode: str,
        current_bar: int,
    ) -> Tuple[bool, str]:
        """Check if position should exit"""

        # Check stop loss
        if position.get('stop_loss'):
            if position['direction'] == 'LONG' and current_price <= position['stop_loss']:
                return True, 'STOP_LOSS'
            elif position['direction'] == 'SHORT' and current_price >= position['stop_loss']:
                return True, 'STOP_LOSS'

        # Check take profit
        if position.get('take_profit'):
            if position['direction'] == 'LONG' and current_price >= position['take_profit']:
                return True, 'TAKE_PROFIT'
            elif position['direction'] == 'SHORT' and current_price <= position['take_profit']:
                return True, 'TAKE_PROFIT'

        # Check signal reversal
        if position['direction'] == 'LONG' and primary_signal < 0:
            return True, 'SIGNAL_REVERSAL'
        elif position['direction'] == 'SHORT' and primary_signal > 0:
            return True, 'SIGNAL_REVERSAL'

        return False, ''

    def _calculate_metrics(self, final_balance: float) -> Dict:
        """Calculate backtest performance metrics"""

        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'total_return': 0,
                'final_balance': final_balance,
                'initial_balance': self.initial_balance,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'largest_win': 0,
                'largest_loss': 0,
                'avg_trade_duration': 0,
                'trades': [],
                'equity_curve': self.equity_curve,
            }

        trades_df = pd.DataFrame(self.trades)

        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] < 0]

        total_pnl = trades_df['pnl'].sum()
        total_return = ((final_balance - self.initial_balance) / self.initial_balance) * 100

        # Calculate equity curve metrics
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df['returns'] = equity_df['equity'].pct_change()

        # Drawdown
        equity_df['cummax'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['cummax']) / equity_df['cummax']
        max_drawdown = equity_df['drawdown'].min() * 100

        # Sharpe ratio (simplified, assuming risk-free rate = 0)
        if len(equity_df['returns']) > 1:
            sharpe = equity_df['returns'].mean() / equity_df['returns'].std() * (252 ** 0.5) if equity_df['returns'].std() > 0 else 0
        else:
            sharpe = 0

        # Profit factor
        gross_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Average trade metrics
        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0

        return {
            'total_trades': len(trades_df),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(trades_df)) * 100,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'final_balance': final_balance,
            'initial_balance': self.initial_balance,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': winning_trades['pnl'].max() if len(winning_trades) > 0 else 0,
            'largest_loss': losing_trades['pnl'].min() if len(losing_trades) > 0 else 0,
            'avg_trade_duration': trades_df['duration_bars'].mean(),
            'trades': self.trades,
            'equity_curve': self.equity_curve,
        }

    def get_trades_dataframe(self) -> pd.DataFrame:
        """Get trades as DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame(self.trades)

    def get_equity_dataframe(self) -> pd.DataFrame:
        """Get equity curve as DataFrame"""
        if not self.equity_curve:
            return pd.DataFrame()
        return pd.DataFrame(self.equity_curve)
