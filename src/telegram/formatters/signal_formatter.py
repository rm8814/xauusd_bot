"""
Signal Message Formatter
Formats trading signals for Telegram messages
"""

from typing import Dict
from datetime import datetime


class SignalFormatter:
    """Format signal messages"""

    @staticmethod
    def format_entry_alert(signal: Dict) -> str:
        """
        Format entry signal alert

        Args:
            signal: Signal dictionary

        Returns:
            Formatted message string
        """
        direction_emoji = "🟢" if signal['direction'] == 'LONG' else "🔴"

        message = f"""
{direction_emoji} **XAU/USD {signal['timeframe'].upper()} {signal['mode']} - {signal['entry_type']}**

**Indicators:**
✅ Primary: {signal['indicators']['primary']['name']} {signal['direction']}
✅ Volume: {signal['indicators']['volume']['name']} {signal['direction']}
✅ Confirmation: {signal['indicators']['confirmation']['name']} {signal['direction']}
✅ Baseline: {signal['indicators']['baseline']['name']} {signal['direction']}

⏰ **Wait 5 minutes before entry**
📊 Entry Price: ${signal['entry_price']:.2f}
"""

        # Add SL/TP for ATR mode
        if signal['mode'] == 'ATR' and 'stop_loss' in signal:
            sl_distance = abs(signal['entry_price'] - signal['stop_loss'])
            tp_distance = abs(signal['entry_price'] - signal['take_profit'])

            message += f"""
**{signal['mode']} Settings:**
🛑 Stop Loss: ${signal['stop_loss']:.2f} (-${sl_distance:.2f})
🎯 Take Profit: ${signal['take_profit']:.2f} (+${tp_distance:.2f})
📊 Risk/Reward: 1:{signal.get('risk_reward_ratio', 0):.1f}
"""

        # Add quality score
        message += f"\n⭐ Quality Score: {signal.get('quality_score', 0)}/100\n"

        # Add ATR info
        if 'atr' in signal:
            message += f"📈 ATR: ${signal['atr']:.2f}\n"

        return message.strip()

    @staticmethod
    def format_pending_signal(signal_key: str, signal: Dict) -> str:
        """Format pending signal message"""
        direction_emoji = "🟢" if signal['direction'] == 'LONG' else "🔴"

        wait_time = 5  # minutes

        message = f"""
⏳ **PENDING SIGNAL**

{direction_emoji} {signal['strategy_name']} - {signal['direction']}
Timeframe: {signal['timeframe']}
Mode: {signal['mode']}

All 4 indicators aligned!
Waiting {wait_time} minutes for confirmation...

Detected at: {signal['detected_at'].strftime('%H:%M:%S')}
"""
        return message.strip()

    @staticmethod
    def format_signal_invalidated(strategy_name: str, reason: str) -> str:
        """Format signal invalidation message"""
        message = f"""
⚠️ **SIGNAL INVALIDATED**

Strategy: {strategy_name}
Reason: {reason}

Indicators no longer aligned. Waiting for next opportunity.
"""
        return message.strip()

    @staticmethod
    def format_signal_list(signals: list) -> str:
        """Format list of current signals"""
        if not signals:
            return "ℹ️ No active signals at the moment."

        message = "📊 **CURRENT SIGNALS**\n\n"

        for signal in signals:
            direction_emoji = "🟢" if signal['direction'] == 'LONG' else "🔴"
            message += f"{direction_emoji} {signal['strategy_name']}\n"
            message += f"   Timeframe: {signal['timeframe']}, Mode: {signal['mode']}\n"
            message += f"   Price: ${signal.get('price', 0):.2f}\n"
            message += f"   Status: {signal.get('status', 'unknown').upper()}\n\n"

        return message.strip()
