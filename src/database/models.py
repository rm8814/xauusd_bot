"""
Database Models
SQLAlchemy models for trades, signals, positions, and settings
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Boolean,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class Trade(Base):
    """Trade history record"""

    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String(50), nullable=False)
    strategy_name = Column(String(100))
    timeframe = Column(String(10), nullable=False)
    mode = Column(String(10), nullable=False)  # PURE or ATR
    entry_type = Column(String(20), nullable=False)  # STANDARD, PULLBACK, etc.
    direction = Column(String(10), nullable=False)  # LONG or SHORT

    # Entry details
    entry_time = Column(DateTime, nullable=False)
    entry_price = Column(Float, nullable=False)

    # Exit details
    exit_time = Column(DateTime)
    exit_price = Column(Float)
    exit_reason = Column(String(50))  # SL_HIT, TP_HIT, SIGNAL_REVERSAL

    # Position details
    position_size = Column(Float, nullable=False)
    stop_loss = Column(Float)
    take_profit = Column(Float)

    # Results
    pnl = Column(Float)  # Profit/Loss in dollars
    pnl_percent = Column(Float)  # P&L as percentage
    duration_minutes = Column(Integer)

    # Metadata
    atr = Column(Float)
    quality_score = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    position = relationship("Position", back_populates="trade", uselist=False)

    def __repr__(self):
        return f"<Trade(id={self.id}, strategy={self.strategy_id}, direction={self.direction}, pnl={self.pnl})>"


class Signal(Base):
    """Signal history record"""

    __tablename__ = 'signals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(String(100), unique=True, nullable=False)
    strategy_id = Column(String(50), nullable=False)
    strategy_name = Column(String(100))
    timeframe = Column(String(10), nullable=False)

    # Signal details
    signal_time = Column(DateTime, nullable=False)
    entry_type = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)

    # Indicator values
    primary_value = Column(Float)
    volume_value = Column(Float)
    confirmation_value = Column(Float)
    baseline_value = Column(Float)

    # Price details
    price = Column(Float, nullable=False)
    atr = Column(Float)
    quality_score = Column(Integer)

    # Status
    status = Column(String(20), nullable=False)  # pending, entered, invalidated, missed

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Signal(id={self.id}, strategy={self.strategy_id}, direction={self.direction}, status={self.status})>"


class Position(Base):
    """Open position tracker"""

    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(Integer, ForeignKey('trades.id'), unique=True)

    # Position details
    status = Column(String(20), nullable=False)  # open, closed
    current_price = Column(Float)
    current_pnl = Column(Float)
    current_pnl_percent = Column(Float)

    # Trailing stop
    trailing_stop_enabled = Column(Boolean, default=False)
    trailing_stop_price = Column(Float)

    # Metadata
    last_update = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    trade = relationship("Trade", back_populates="position")

    def __repr__(self):
        return f"<Position(id={self.id}, trade_id={self.trade_id}, status={self.status}, pnl={self.current_pnl})>"


class UserSetting(Base):
    """User settings and preferences"""

    __tablename__ = 'user_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(Text, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserSetting(key={self.setting_key}, value={self.setting_value})>"


class PerformanceMetric(Base):
    """Daily/weekly/monthly performance metrics"""

    __tablename__ = 'performance_metrics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    strategy_id = Column(String(50))

    # Trade counts
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)

    # Performance metrics
    win_rate = Column(Float)
    total_pnl = Column(Float)
    total_pnl_percent = Column(Float)
    profit_factor = Column(Float)
    max_drawdown = Column(Float)
    sharpe_ratio = Column(Float)

    # Additional metrics
    avg_win = Column(Float)
    avg_loss = Column(Float)
    largest_win = Column(Float)
    largest_loss = Column(Float)
    avg_duration_minutes = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PerformanceMetric(date={self.date}, strategy={self.strategy_id}, pnl={self.total_pnl})>"


class TradingSession(Base):
    """Track trading sessions and system status"""

    __tablename__ = 'trading_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    status = Column(String(20), nullable=False)  # active, stopped, error

    # Session stats
    signals_detected = Column(Integer, default=0)
    trades_opened = Column(Integer, default=0)
    trades_closed = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)

    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TradingSession(id={self.id}, start={self.start_time}, status={self.status})>"


class Database:
    """Database connection and session management"""

    def __init__(self, db_path: str = "database/trades.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.Session = sessionmaker(bind=self.engine)

    def create_tables(self):
        """Create all tables"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info(f"Database tables created successfully at {self.db_path}")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise

    def get_session(self):
        """Get a new database session"""
        return self.Session()

    def drop_all_tables(self):
        """Drop all tables (use with caution!)"""
        try:
            Base.metadata.drop_all(self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Error dropping tables: {e}")
            raise

    def backup_database(self, backup_path: str):
        """Create database backup"""
        import shutil

        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return False
