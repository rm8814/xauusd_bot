"""
Position Manager Module
Manages open positions, tracks P&L, monitors exit conditions
"""

from __future__ import annotations
from typing import Dict, List, Optional
from datetime import datetime
import logging
from sqlalchemy.orm import Session
import pandas as pd

from src.database.models import Trade, Position
from src.database.trades_db import TradeDB
from src.core.indicators import Indicators

logger = logging.getLogger(__name__)


class PositionManager:
    """Manages trading positions"""

    def __init__(self, db_session: Session, strategy_config: dict):
        """
        Initialize position manager

        Args:
            db_session: Database session
            strategy_config: Strategy configuration
        """
        self.db_session = db_session
        self.strategy_config = strategy_config

    def open_position(self, signal: Dict, position_size: float = 0.01) -> Optional[int]:
        """
        Open a new position

        Args:
            signal: Signal dict from SignalDetector
            position_size: Position size (lot size)

        Returns:
            Trade ID if successful, None otherwise
        """
        try:
            # Create trade record
            trade_data = {
                'strategy_id': signal['strategy_id'],
                'strategy_name': signal.get('strategy_name', ''),
                'timeframe': signal['timeframe'],
                'mode': signal['mode'],
                'entry_type': signal.get('entry_type', 'STANDARD'),
                'direction': signal['direction'],
                'entry_time': signal.get('signal_time', datetime.utcnow()),
                'entry_price': signal['entry_price'],
                'position_size': position_size,
                'stop_loss': signal.get('stop_loss'),
                'take_profit': signal.get('take_profit'),
                'atr': signal.get('atr'),
                'quality_score': signal.get('quality_score', 0),
            }

            trade = TradeDB.create_trade(self.db_session, trade_data)
            if not trade:
                logger.error("Failed to create trade record")
                return None

            # Create position record
            position = Position(
                trade_id=trade.id,
                status='open',
                current_price=signal['entry_price'],
                current_pnl=0,
                current_pnl_percent=0,
            )

            self.db_session.add(position)
            self.db_session.commit()

            logger.info(
                f"Position opened: Trade ID={trade.id}, "
                f"{trade.direction} {trade.strategy_id} @ ${trade.entry_price:.2f}"
            )

            return trade.id

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error opening position: {e}")
            return None

    def update_position(self, trade_id: int, current_price: float) -> bool:
        """
        Update position with current price

        Args:
            trade_id: Trade ID
            current_price: Current market price

        Returns:
            True if successful, False otherwise
        """
        try:
            position = (
                self.db_session.query(Position)
                .filter(Position.trade_id == trade_id, Position.status == 'open')
                .first()
            )

            if not position:
                logger.warning(f"Open position not found for trade {trade_id}")
                return False

            trade = position.trade

            # Calculate current P&L
            if trade.direction == "LONG":
                pnl = (current_price - trade.entry_price) * trade.position_size
            else:  # SHORT
                pnl = (trade.entry_price - current_price) * trade.position_size

            pnl_percent = (pnl / (trade.entry_price * trade.position_size)) * 100

            # Update position
            position.current_price = current_price
            position.current_pnl = pnl
            position.current_pnl_percent = pnl_percent
            position.last_update = datetime.utcnow()

            self.db_session.commit()

            return True

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error updating position: {e}")
            return False

    def close_position(
        self, trade_id: int, exit_price: float, exit_reason: str
    ) -> bool:
        """
        Close position

        Args:
            trade_id: Trade ID
            exit_price: Exit price
            exit_reason: Reason for exit

        Returns:
            True if successful, False otherwise
        """
        try:
            # Update position status
            position = (
                self.db_session.query(Position)
                .filter(Position.trade_id == trade_id)
                .first()
            )

            if position:
                position.status = 'closed'
                position.current_price = exit_price
                self.db_session.commit()

            # Close trade
            success = TradeDB.close_trade(
                self.db_session, trade_id, exit_price, exit_reason
            )

            if success:
                logger.info(f"Position closed: Trade ID={trade_id}, Reason={exit_reason}")

            return success

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error closing position: {e}")
            return False

    def check_exit_conditions(
        self, trade_id: int, current_price: float, df: pd.DataFrame = None
    ) -> Optional[Dict]:
        """
        Check if position should exit

        Args:
            trade_id: Trade ID
            current_price: Current market price
            df: DataFrame with OHLCV data (for signal checking)

        Returns:
            Dict with exit details if should exit, None otherwise
        """
        try:
            position = (
                self.db_session.query(Position)
                .filter(Position.trade_id == trade_id, Position.status == 'open')
                .first()
            )

            if not position:
                return None

            trade = position.trade
            strategy = self.strategy_config.get(f"strategy_{trade.strategy_id}")

            if not strategy:
                logger.warning(f"Strategy not found: {trade.strategy_id}")
                return None

            # Check ATR mode conditions (SL/TP)
            if trade.mode == "ATR":
                # Check Stop Loss
                if trade.stop_loss:
                    if trade.direction == "LONG" and current_price <= trade.stop_loss:
                        return {
                            'should_exit': True,
                            'exit_price': trade.stop_loss,
                            'exit_reason': 'SL_HIT',
                        }
                    elif trade.direction == "SHORT" and current_price >= trade.stop_loss:
                        return {
                            'should_exit': True,
                            'exit_price': trade.stop_loss,
                            'exit_reason': 'SL_HIT',
                        }

                # Check Take Profit
                if trade.take_profit:
                    if trade.direction == "LONG" and current_price >= trade.take_profit:
                        return {
                            'should_exit': True,
                            'exit_price': trade.take_profit,
                            'exit_reason': 'TP_HIT',
                        }
                    elif trade.direction == "SHORT" and current_price <= trade.take_profit:
                        return {
                            'should_exit': True,
                            'exit_price': trade.take_profit,
                            'exit_reason': 'TP_HIT',
                        }

            # Check signal reversal for both PURE and ATR modes
            if df is not None and len(df) > 0:
                # Get primary indicator signal
                primary_indicator = strategy['indicators']['primary']['type']
                indicator_params = {}  # Should load from config

                signal = Indicators.get_indicator_signal(
                    df, primary_indicator, indicator_params
                )

                if len(signal) > 0:
                    current_signal = signal.iloc[-1]

                    # Check for reversal
                    if trade.direction == "LONG" and current_signal < 0:
                        return {
                            'should_exit': True,
                            'exit_price': current_price,
                            'exit_reason': 'SIGNAL_REVERSAL',
                        }
                    elif trade.direction == "SHORT" and current_signal > 0:
                        return {
                            'should_exit': True,
                            'exit_price': current_price,
                            'exit_reason': 'SIGNAL_REVERSAL',
                        }

            # No exit conditions met
            return None

        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
            return None

    def get_open_positions(self) -> List[Position]:
        """Get all open positions"""
        try:
            return (
                self.db_session.query(Position)
                .filter(Position.status == 'open')
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting open positions: {e}")
            return []

    def get_position_by_trade_id(self, trade_id: int) -> Optional[Position]:
        """Get position by trade ID"""
        try:
            return (
                self.db_session.query(Position)
                .filter(Position.trade_id == trade_id)
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None

    def update_trailing_stop(self, trade_id: int, current_price: float) -> bool:
        """
        Update trailing stop for position

        Args:
            trade_id: Trade ID
            current_price: Current market price

        Returns:
            True if updated, False otherwise
        """
        try:
            position = (
                self.db_session.query(Position)
                .filter(Position.trade_id == trade_id, Position.status == 'open')
                .first()
            )

            if not position or not position.trailing_stop_enabled:
                return False

            trade = position.trade

            # Calculate new trailing stop
            distance = abs(current_price - trade.entry_price) * 0.5  # 50% of profit

            if trade.direction == "LONG":
                new_stop = current_price - distance
                if (
                    position.trailing_stop_price is None
                    or new_stop > position.trailing_stop_price
                ):
                    position.trailing_stop_price = new_stop
                    self.db_session.commit()
                    logger.info(f"Trailing stop updated: ${new_stop:.2f}")
                    return True
            else:  # SHORT
                new_stop = current_price + distance
                if (
                    position.trailing_stop_price is None
                    or new_stop < position.trailing_stop_price
                ):
                    position.trailing_stop_price = new_stop
                    self.db_session.commit()
                    logger.info(f"Trailing stop updated: ${new_stop:.2f}")
                    return True

            return False

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error updating trailing stop: {e}")
            return False

    def enable_trailing_stop(self, trade_id: int) -> bool:
        """Enable trailing stop for position"""
        try:
            position = (
                self.db_session.query(Position)
                .filter(Position.trade_id == trade_id)
                .first()
            )

            if not position:
                return False

            position.trailing_stop_enabled = True
            self.db_session.commit()
            logger.info(f"Trailing stop enabled for trade {trade_id}")
            return True

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error enabling trailing stop: {e}")
            return False

    def get_position_summary(self, trade_id: int) -> Optional[Dict]:
        """Get position summary for display"""
        try:
            position = (
                self.db_session.query(Position)
                .filter(Position.trade_id == trade_id)
                .first()
            )

            if not position:
                return None

            trade = position.trade

            duration = (datetime.utcnow() - trade.entry_time).total_seconds() / 3600

            return {
                'trade_id': trade.id,
                'strategy': trade.strategy_name or trade.strategy_id,
                'timeframe': trade.timeframe,
                'mode': trade.mode,
                'direction': trade.direction,
                'entry_price': trade.entry_price,
                'current_price': position.current_price,
                'pnl': position.current_pnl,
                'pnl_percent': position.current_pnl_percent,
                'stop_loss': trade.stop_loss,
                'take_profit': trade.take_profit,
                'duration_hours': duration,
                'status': position.status,
            }

        except Exception as e:
            logger.error(f"Error getting position summary: {e}")
            return None
