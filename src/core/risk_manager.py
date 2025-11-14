"""
Risk Management Module
Handles position sizing, risk limits, and trading safeguards
"""

from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session

from src.database.trades_db import TradeDB

logger = logging.getLogger(__name__)


class RiskManager:
    """Manages trading risk and position sizing"""

    def __init__(self, config: dict, db_session: Session):
        """
        Initialize risk manager

        Args:
            config: Risk management configuration
            db_session: Database session
        """
        self.config = config
        self.db_session = db_session

        # Position sizing
        self.default_risk_percent = config.get('position_sizing', {}).get(
            'default_risk_percent', 1.0
        )
        self.default_lot_size = config.get('position_sizing', {}).get(
            'default_lot_size', 0.01
        )

        # Position limits
        self.max_open_positions = config.get('position_limits', {}).get(
            'max_open_positions', 4
        )
        self.max_positions_per_timeframe = config.get('position_limits', {}).get(
            'max_positions_per_timeframe', 2
        )

        # Account protection
        self.max_daily_loss_percent = config.get('account_protection', {}).get(
            'max_daily_loss_percent', 5.0
        )
        self.max_weekly_loss_percent = config.get('account_protection', {}).get(
            'max_weekly_loss_percent', 10.0
        )
        self.max_drawdown_percent = config.get('account_protection', {}).get(
            'max_drawdown_percent', 30.0
        )

        # Overtrading prevention
        self.max_trades_per_day = config.get('overtrading', {}).get(
            'max_trades_per_day', 10
        )

    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: float,
        risk_percent: float = None,
    ) -> float:
        """
        Calculate position size based on risk

        Args:
            account_balance: Account balance
            entry_price: Entry price
            stop_loss: Stop loss price
            risk_percent: Risk percentage (default: from config)

        Returns:
            Position size (lot size)
        """
        try:
            if risk_percent is None:
                risk_percent = self.default_risk_percent

            # Calculate risk amount
            risk_amount = account_balance * (risk_percent / 100)

            # Calculate risk per unit
            risk_per_unit = abs(entry_price - stop_loss)

            if risk_per_unit == 0:
                logger.warning("Stop loss equals entry price")
                return self.default_lot_size

            # Calculate position size
            position_size = risk_amount / risk_per_unit

            # Round to 2 decimal places (standard lot size precision)
            position_size = round(position_size, 2)

            # Enforce minimum and maximum
            min_lot = self.config.get('position_sizing', {}).get('min_lot_size', 0.01)
            max_lot = self.config.get('position_sizing', {}).get('max_lot_size', 1.0)

            position_size = max(min_lot, min(max_lot, position_size))

            logger.info(
                f"Position size calculated: {position_size} lots "
                f"(Risk: ${risk_amount:.2f}, {risk_percent}%)"
            )

            return position_size

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return self.default_lot_size

    def can_open_position(
        self, strategy_id: str, timeframe: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if new position can be opened

        Args:
            strategy_id: Strategy ID
            timeframe: Timeframe

        Returns:
            Tuple of (can_open: bool, reason: str)
        """
        try:
            # Check max open positions
            open_trades = TradeDB.get_open_trades(self.db_session)

            if len(open_trades) >= self.max_open_positions:
                return False, f"Maximum open positions reached ({self.max_open_positions})"

            # Check positions per timeframe
            timeframe_positions = [t for t in open_trades if t.timeframe == timeframe]
            if len(timeframe_positions) >= self.max_positions_per_timeframe:
                return (
                    False,
                    f"Maximum positions per timeframe reached ({self.max_positions_per_timeframe})",
                )

            # Check daily trade limit
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_trades = TradeDB.get_trades_by_period(self.db_session, today_start)

            if len(today_trades) >= self.max_trades_per_day:
                return False, f"Daily trade limit reached ({self.max_trades_per_day})"

            # Check daily loss limit
            is_within_limit, reason = self.check_daily_loss_limit()
            if not is_within_limit:
                return False, reason

            # Check weekly loss limit
            is_within_limit, reason = self.check_weekly_loss_limit()
            if not is_within_limit:
                return False, reason

            return True, None

        except Exception as e:
            logger.error(f"Error checking position limits: {e}")
            return False, f"Error: {e}"

    def check_daily_loss_limit(self) -> Tuple[bool, Optional[str]]:
        """Check if daily loss limit is breached"""
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_trades = TradeDB.get_trades_by_period(self.db_session, today_start)

            closed_trades = [t for t in today_trades if t.exit_time is not None]
            if not closed_trades:
                return True, None

            total_pnl = sum(t.pnl for t in closed_trades if t.pnl)

            # Assume initial balance for percentage calculation
            # In production, this should come from account data
            initial_balance = 100  # TODO: Get from config or account

            loss_percent = abs(total_pnl / initial_balance) * 100

            if total_pnl < 0 and loss_percent >= self.max_daily_loss_percent:
                return (
                    False,
                    f"Daily loss limit reached: {loss_percent:.2f}% (Max: {self.max_daily_loss_percent}%)",
                )

            return True, None

        except Exception as e:
            logger.error(f"Error checking daily loss limit: {e}")
            return True, None  # Don't block on error

    def check_weekly_loss_limit(self) -> Tuple[bool, Optional[str]]:
        """Check if weekly loss limit is breached"""
        try:
            week_start = datetime.utcnow() - timedelta(days=7)
            week_trades = TradeDB.get_trades_by_period(self.db_session, week_start)

            closed_trades = [t for t in week_trades if t.exit_time is not None]
            if not closed_trades:
                return True, None

            total_pnl = sum(t.pnl for t in closed_trades if t.pnl)

            initial_balance = 100  # TODO: Get from config or account
            loss_percent = abs(total_pnl / initial_balance) * 100

            if total_pnl < 0 and loss_percent >= self.max_weekly_loss_percent:
                return (
                    False,
                    f"Weekly loss limit reached: {loss_percent:.2f}% (Max: {self.max_weekly_loss_percent}%)",
                )

            return True, None

        except Exception as e:
            logger.error(f"Error checking weekly loss limit: {e}")
            return True, None

    def validate_trade_setup(
        self, signal: Dict, account_balance: float
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Validate trade setup before opening position

        Args:
            signal: Signal dictionary
            account_balance: Account balance

        Returns:
            Tuple of (is_valid: bool, reason: str, position_size: float)
        """
        try:
            # Check if can open position
            can_open, reason = self.can_open_position(
                signal['strategy_id'], signal['timeframe']
            )
            if not can_open:
                return False, reason, None

            # Calculate position size
            if signal.get('stop_loss'):
                position_size = self.calculate_position_size(
                    account_balance, signal['entry_price'], signal['stop_loss']
                )
            else:
                position_size = self.default_lot_size

            # Check risk-reward ratio
            if signal['mode'] == 'ATR':
                min_rr = self.config.get('risk_reward', {}).get(
                    'min_risk_reward_ratio', 2.0
                )
                actual_rr = signal.get('risk_reward_ratio', 0)

                if actual_rr < min_rr:
                    return (
                        False,
                        f"Risk-reward ratio too low: {actual_rr:.2f} < {min_rr}",
                        None,
                    )

            # Check quality score
            min_quality = 60  # TODO: Get from config
            if signal.get('quality_score', 0) < min_quality:
                return (
                    False,
                    f"Signal quality too low: {signal.get('quality_score', 0)} < {min_quality}",
                    None,
                )

            return True, None, position_size

        except Exception as e:
            logger.error(f"Error validating trade setup: {e}")
            return False, f"Validation error: {e}", None

    def get_risk_summary(self) -> Dict:
        """Get current risk summary"""
        try:
            # Get open positions count
            open_trades = TradeDB.get_open_trades(self.db_session)

            # Get today's trades
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_trades = TradeDB.get_trades_by_period(self.db_session, today_start)
            today_closed = [t for t in today_trades if t.exit_time is not None]

            # Calculate daily P&L
            daily_pnl = sum(t.pnl for t in today_closed if t.pnl)

            # Get week's trades
            week_start = datetime.utcnow() - timedelta(days=7)
            week_trades = TradeDB.get_trades_by_period(self.db_session, week_start)
            week_closed = [t for t in week_trades if t.exit_time is not None]

            # Calculate weekly P&L
            weekly_pnl = sum(t.pnl for t in week_closed if t.pnl)

            return {
                'open_positions': len(open_trades),
                'max_open_positions': self.max_open_positions,
                'daily_trades': len(today_trades),
                'max_daily_trades': self.max_trades_per_day,
                'daily_pnl': daily_pnl,
                'max_daily_loss_percent': self.max_daily_loss_percent,
                'weekly_pnl': weekly_pnl,
                'max_weekly_loss_percent': self.max_weekly_loss_percent,
                'can_trade': self.can_open_position('any', 'any')[0],
            }

        except Exception as e:
            logger.error(f"Error getting risk summary: {e}")
            return {}

    def should_reduce_position_size(self) -> Tuple[bool, float]:
        """
        Check if position size should be reduced due to recent losses

        Returns:
            Tuple of (should_reduce: bool, reduction_factor: float)
        """
        try:
            # Get recent trades
            lookback_days = 7
            start_date = datetime.utcnow() - timedelta(days=lookback_days)
            recent_trades = TradeDB.get_trades_by_period(self.db_session, start_date)

            closed_trades = [t for t in recent_trades if t.exit_time is not None]
            if not closed_trades:
                return False, 1.0

            # Count recent losses
            recent_losses = [t for t in closed_trades if t.pnl and t.pnl < 0]

            reduce_after = self.config.get('psychology', {}).get(
                'reduce_size_after_losses', 3
            )
            reduction_percent = self.config.get('psychology', {}).get(
                'size_reduction_percent', 50
            )

            if len(recent_losses) >= reduce_after:
                reduction_factor = 1 - (reduction_percent / 100)
                logger.info(
                    f"Position size reduction: {len(recent_losses)} recent losses, "
                    f"reducing by {reduction_percent}%"
                )
                return True, reduction_factor

            return False, 1.0

        except Exception as e:
            logger.error(f"Error checking position size reduction: {e}")
            return False, 1.0

    def should_take_break(self) -> Tuple[bool, Optional[str]]:
        """
        Check if mandatory break is required

        Returns:
            Tuple of (should_break: bool, reason: str)
        """
        try:
            # Get recent trades
            lookback_days = 7
            start_date = datetime.utcnow() - timedelta(days=lookback_days)
            recent_trades = TradeDB.get_trades_by_period(self.db_session, start_date)

            closed_trades = [t for t in recent_trades if t.exit_time is not None]
            if not closed_trades:
                return False, None

            # Count consecutive losses
            consecutive_losses = 0
            for trade in reversed(closed_trades):
                if trade.pnl and trade.pnl < 0:
                    consecutive_losses += 1
                else:
                    break

            mandatory_break_threshold = self.config.get('psychology', {}).get(
                'mandatory_break_after_losses', 5
            )
            break_duration = self.config.get('psychology', {}).get(
                'break_duration_hours', 24
            )

            if consecutive_losses >= mandatory_break_threshold:
                return (
                    True,
                    f"Mandatory break: {consecutive_losses} consecutive losses. "
                    f"Take a {break_duration}h break.",
                )

            return False, None

        except Exception as e:
            logger.error(f"Error checking mandatory break: {e}")
            return False, None
