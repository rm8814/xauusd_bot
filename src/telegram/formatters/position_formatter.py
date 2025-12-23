"""
Position Message Formatter
Formats position information for Telegram messages
"""

from typing import Dict, List
from datetime import datetime


class PositionFormatter:
    """Format position messages"""

    @staticmethod
    def format_position_update(position: Dict) -> str:
        """Format position update message"""
        direction_emoji = "🟢" if position['direction'] == 'LONG' else "🔴"
        pnl_emoji = "💰" if position['pnl'] >= 0 else "📉"

        message = f"""
{direction_emoji} **Position #{position['trade_id']}**

**Details:**
Strategy: {position['strategy']}
Timeframe: {position['timeframe']} | Mode: {position['mode']}

**Prices:**
Entry: ${position['entry_price']:.2f}
Current: ${position['current_price']:.2f}

{pnl_emoji} **P&L: ${position['pnl']:.2f} ({position['pnl_percent']:.2f}%)**

**Levels:**
"""

        if position.get('stop_loss'):
            message += f"🛑 SL: ${position['stop_loss']:.2f}\n"

        if position.get('take_profit'):
            tp_distance = abs(position['current_price'] - position['take_profit'])
            entry_distance = abs(position['take_profit'] - position['entry_price'])
            progress = (
                (1 - (tp_distance / entry_distance)) * 100 if entry_distance > 0 else 0
            )
            message += f"🎯 TP: ${position['take_profit']:.2f}\n"
            message += f"Progress to TP: {progress:.1f}%\n"

        message += f"\n⏱️ Duration: {position['duration_hours']:.1f}h\n"
        message += f"Status: {position['status'].upper()}"

        return message.strip()

    @staticmethod
    def format_exit_alert(position: Dict, exit_reason: str, exit_price: float) -> str:
        """Format exit alert message"""
        pnl = (
            (exit_price - position['entry_price']) * position.get('position_size', 0.01)
            if position['direction'] == 'LONG'
            else (position['entry_price'] - exit_price) * position.get('position_size', 0.01)
        )
        pnl_percent = (pnl / (position['entry_price'] * position.get('position_size', 0.01))) * 100

        pnl_emoji = "✅" if pnl >= 0 else "❌"

        message = f"""
{pnl_emoji} **EXIT SIGNAL - Position #{position['trade_id']}**

**Reason:** {exit_reason}

**Summary:**
Entry: ${position['entry_price']:.2f}
Exit: ${exit_price:.2f}
Result: ${pnl:.2f} ({pnl_percent:.2f}%)

Duration: {position['duration_hours']:.1f}h

Action required: Close at next candle or market price.
"""
        return message.strip()

    @staticmethod
    def format_position_closed(
        trade_id: int, entry: float, exit: float, pnl: float, pnl_percent: float, duration_hours: float
    ) -> str:
        """Format position closed confirmation"""
        pnl_emoji = "✅" if pnl >= 0 else "❌"

        message = f"""
{pnl_emoji} **POSITION CLOSED**

Position #{trade_id}

**Results:**
Entry: ${entry:.2f}
Exit: ${exit:.2f}
P&L: ${pnl:.2f} ({pnl_percent:.2f}%)

Duration: {duration_hours:.1f}h

Trade recorded in journal.
"""
        return message.strip()

    @staticmethod
    def format_positions_list(positions: List[Dict]) -> str:
        """Format list of open positions"""
        if not positions:
            return "ℹ️ No open positions."

        message = "📊 **OPEN POSITIONS**\n\n"

        total_pnl = 0

        for pos in positions:
            direction_emoji = "🟢" if pos['direction'] == 'LONG' else "🔴"
            pnl_emoji = "💰" if pos.get('pnl', 0) >= 0 else "📉"

            message += f"{direction_emoji} **#{pos['trade_id']}** {pos['strategy']}\n"
            message += f"   {pos['timeframe']} | {pos['direction']}\n"
            message += f"   Entry: ${pos['entry_price']:.2f} → ${pos.get('current_price', 0):.2f}\n"
            message += f"   {pnl_emoji} P&L: ${pos.get('pnl', 0):.2f} ({pos.get('pnl_percent', 0):.2f}%)\n"
            message += f"   Duration: {pos.get('duration_hours', 0):.1f}h\n\n"

            total_pnl += pos.get('pnl', 0)

        total_emoji = "💰" if total_pnl >= 0 else "📉"
        message += f"{total_emoji} **Total P&L: ${total_pnl:.2f}**"

        return message.strip()

    @staticmethod
    def format_position_not_found(trade_id: int) -> str:
        """Format position not found message"""
        return f"❌ Position #{trade_id} not found."

    @staticmethod
    def format_no_open_positions() -> str:
        """Format no open positions message"""
        return "ℹ️ No open positions to display."
