"""
Trade Database Operations
CRUD operations for trades
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
import logging

from src.database.models import Trade, Position

logger = logging.getLogger(__name__)


class TradeDB:
    """Trade database operations"""

    @staticmethod
    def create_trade(session: Session, trade_data: Dict) -> Optional[Trade]:
        """Create a new trade record"""
        try:
            trade = Trade(**trade_data)
            session.add(trade)
            session.commit()
            session.refresh(trade)
            logger.info(f"Trade created: ID={trade.id}, {trade.direction} {trade.strategy_id}")
            return trade
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating trade: {e}")
            return None

    @staticmethod
    def update_trade(session: Session, trade_id: int, updates: Dict) -> bool:
        """Update trade record"""
        try:
            trade = session.query(Trade).filter(Trade.id == trade_id).first()
            if not trade:
                logger.warning(f"Trade not found: {trade_id}")
                return False

            for key, value in updates.items():
                if hasattr(trade, key):
                    setattr(trade, key, value)

            trade.updated_at = datetime.utcnow()
            session.commit()
            logger.info(f"Trade updated: ID={trade_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating trade: {e}")
            return False

    @staticmethod
    def close_trade(
        session: Session,
        trade_id: int,
        exit_price: float,
        exit_reason: str,
        exit_time: datetime = None,
    ) -> bool:
        """Close a trade"""
        try:
            trade = session.query(Trade).filter(Trade.id == trade_id).first()
            if not trade:
                logger.warning(f"Trade not found: {trade_id}")
                return False

            if exit_time is None:
                exit_time = datetime.utcnow()

            # Calculate P&L
            if trade.direction == "LONG":
                pnl = (exit_price - trade.entry_price) * trade.position_size
            else:  # SHORT
                pnl = (trade.entry_price - exit_price) * trade.position_size

            pnl_percent = (pnl / (trade.entry_price * trade.position_size)) * 100

            # Calculate duration
            duration = (exit_time - trade.entry_time).total_seconds() / 60

            # Update trade
            trade.exit_price = exit_price
            trade.exit_time = exit_time
            trade.exit_reason = exit_reason
            trade.pnl = pnl
            trade.pnl_percent = pnl_percent
            trade.duration_minutes = int(duration)
            trade.updated_at = datetime.utcnow()

            session.commit()
            logger.info(
                f"Trade closed: ID={trade_id}, P&L=${pnl:.2f} ({pnl_percent:.2f}%)"
            )
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error closing trade: {e}")
            return False

    @staticmethod
    def get_trade(session: Session, trade_id: int) -> Optional[Trade]:
        """Get trade by ID"""
        try:
            return session.query(Trade).filter(Trade.id == trade_id).first()
        except Exception as e:
            logger.error(f"Error getting trade: {e}")
            return None

    @staticmethod
    def get_open_trades(session: Session) -> List[Trade]:
        """Get all open trades (trades without exit time)"""
        try:
            return (
                session.query(Trade)
                .filter(Trade.exit_time.is_(None))
                .order_by(desc(Trade.entry_time))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting open trades: {e}")
            return []

    @staticmethod
    def get_closed_trades(
        session: Session, limit: int = 100, strategy_id: str = None
    ) -> List[Trade]:
        """Get closed trades"""
        try:
            query = session.query(Trade).filter(Trade.exit_time.isnot(None))

            if strategy_id:
                query = query.filter(Trade.strategy_id == strategy_id)

            return query.order_by(desc(Trade.exit_time)).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting closed trades: {e}")
            return []

    @staticmethod
    def get_trades_by_period(
        session: Session, start_date: datetime, end_date: datetime = None
    ) -> List[Trade]:
        """Get trades within a time period"""
        try:
            if end_date is None:
                end_date = datetime.utcnow()

            return (
                session.query(Trade)
                .filter(
                    and_(
                        Trade.entry_time >= start_date,
                        Trade.entry_time <= end_date,
                    )
                )
                .order_by(Trade.entry_time)
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting trades by period: {e}")
            return []

    @staticmethod
    def get_trades_by_strategy(
        session: Session, strategy_id: str, limit: int = 100
    ) -> List[Trade]:
        """Get trades for specific strategy"""
        try:
            return (
                session.query(Trade)
                .filter(Trade.strategy_id == strategy_id)
                .order_by(desc(Trade.entry_time))
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting trades by strategy: {e}")
            return []

    @staticmethod
    def get_trade_statistics(session: Session, period_days: int = 30) -> Dict:
        """Get trade statistics for a period"""
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            trades = TradeDB.get_trades_by_period(session, start_date)

            if not trades:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'total_pnl': 0,
                    'avg_pnl': 0,
                }

            closed_trades = [t for t in trades if t.exit_time is not None]
            winning_trades = [t for t in closed_trades if t.pnl and t.pnl > 0]
            losing_trades = [t for t in closed_trades if t.pnl and t.pnl < 0]

            total_pnl = sum(t.pnl for t in closed_trades if t.pnl)
            avg_pnl = total_pnl / len(closed_trades) if closed_trades else 0

            win_rate = (
                (len(winning_trades) / len(closed_trades)) * 100
                if closed_trades
                else 0
            )

            return {
                'total_trades': len(trades),
                'closed_trades': len(closed_trades),
                'open_trades': len(trades) - len(closed_trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl,
                'avg_win': (
                    sum(t.pnl for t in winning_trades) / len(winning_trades)
                    if winning_trades
                    else 0
                ),
                'avg_loss': (
                    sum(t.pnl for t in losing_trades) / len(losing_trades)
                    if losing_trades
                    else 0
                ),
                'largest_win': max((t.pnl for t in winning_trades), default=0),
                'largest_loss': min((t.pnl for t in losing_trades), default=0),
            }

        except Exception as e:
            logger.error(f"Error getting trade statistics: {e}")
            return {}

    @staticmethod
    def delete_trade(session: Session, trade_id: int) -> bool:
        """Delete a trade (use with caution!)"""
        try:
            trade = session.query(Trade).filter(Trade.id == trade_id).first()
            if not trade:
                logger.warning(f"Trade not found: {trade_id}")
                return False

            session.delete(trade)
            session.commit()
            logger.info(f"Trade deleted: ID={trade_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting trade: {e}")
            return False
