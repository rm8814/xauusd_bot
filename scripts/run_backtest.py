#!/usr/bin/env python3
"""
Run Backtest Script
Backtests trading strategies on historical data
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analytics.backtest import Backtest
from src.data.data_fetcher import DataFetcher
from src.utils.config_loader import ConfigLoader
from src.monitoring.logger import setup_logging
import argparse
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def print_results(results: dict, strategy_name: str):
    """Print backtest results in a nice format"""

    print("\n" + "=" * 70)
    print(f"BACKTEST RESULTS: {strategy_name}")
    print("=" * 70)

    # Check if there were any trades
    if results.get('total_trades', 0) == 0:
        print(f"\n⚠️  NO TRADES EXECUTED")
        print(f"\n   No valid entry signals were detected during the backtest period.")
        print(f"   This could mean:")
        print(f"   - Indicators didn't align (4-layer confirmation required)")
        print(f"   - Data period too short")
        print(f"   - Strategy conditions too strict")
        print(f"\n   Try:")
        print(f"   - Increasing --days parameter")
        print(f"   - Testing a different strategy")
        print(f"   - Checking indicator calculations")
        print("\n" + "=" * 70)
        return

    print(f"\n📊 TRADING STATISTICS")
    print(f"   Total Trades: {results['total_trades']}")
    print(f"   Winning Trades: {results['winning_trades']}")
    print(f"   Losing Trades: {results['losing_trades']}")
    print(f"   Win Rate: {results['win_rate']:.2f}%")

    print(f"\n💰 P&L METRICS")
    print(f"   Initial Balance: ${results.get('initial_balance', 0):.2f}")
    print(f"   Final Balance: ${results.get('final_balance', 0):.2f}")
    print(f"   Total P&L: ${results.get('total_pnl', 0):.2f}")
    print(f"   Total Return: {results.get('total_return', 0):.2f}%")

    print(f"\n📈 PERFORMANCE METRICS")
    pf = results.get('profit_factor', 0)
    print(f"   Profit Factor: {pf:.2f}" if pf != float('inf') else "   Profit Factor: ∞")
    print(f"   Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
    print(f"   Max Drawdown: {results.get('max_drawdown', 0):.2f}%")

    print(f"\n💵 TRADE AVERAGES")
    print(f"   Average Win: ${results.get('avg_win', 0):.2f}")
    print(f"   Average Loss: ${results.get('avg_loss', 0):.2f}")
    print(f"   Largest Win: ${results.get('largest_win', 0):.2f}")
    print(f"   Largest Loss: ${results.get('largest_loss', 0):.2f}")
    print(f"   Avg Duration: {results.get('avg_trade_duration', 0):.1f} bars")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description='Backtest trading strategies')
    parser.add_argument(
        '--strategy',
        type=str,
        default='all',
        help='Strategy ID to test (1-6 or "all")'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=365,
        help='Number of days of historical data (default: 365)'
    )
    parser.add_argument(
        '--balance',
        type=float,
        default=100.0,
        help='Initial balance (default: 100)'
    )
    parser.add_argument(
        '--risk',
        type=float,
        default=1.0,
        help='Risk per trade as percentage (default: 1.0)'
    )
    parser.add_argument(
        '--commission',
        type=float,
        default=0.0,
        help='Commission per trade as percentage (default: 0.0)'
    )
    parser.add_argument(
        '--export',
        type=str,
        help='Export trades to CSV file'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging('INFO')

    logger.info("Starting backtest script...")

    # Load configuration
    config_loader = ConfigLoader()
    config = config_loader.get_all_config()

    if not config_loader.validate_config(config):
        logger.error("Configuration validation failed")
        sys.exit(1)

    strategies = config['strategies'].get('strategies', {})
    indicators = config['indicators'].get('indicators', {})

    # Determine which strategies to test
    if args.strategy == 'all':
        strategy_ids = list(strategies.keys())
    else:
        strategy_id = f"strategy_{args.strategy}"
        if strategy_id not in strategies:
            logger.error(f"Strategy {args.strategy} not found")
            sys.exit(1)
        strategy_ids = [strategy_id]

    # Initialize data fetcher
    api_key = config['api']['twelve_data_key']
    data_fetcher = DataFetcher(api_key)

    # Run backtests
    all_results = {}

    for strategy_id in strategy_ids:
        strategy = strategies[strategy_id]
        timeframe = strategy['timeframe']
        strategy_name = strategy.get('name', strategy_id)

        logger.info(f"\n{'='*70}")
        logger.info(f"Testing {strategy_name} ({timeframe})")
        logger.info(f"{'='*70}")

        # Fetch historical data
        # Calculate how many candles we need based on timeframe
        if timeframe == '1h':
            candles_needed = args.days * 24
        elif timeframe == '4h':
            candles_needed = args.days * 6
        elif timeframe == '1day':
            candles_needed = args.days
        else:
            candles_needed = 365

        # TwelveData free tier has limits, cap at 5000
        candles_needed = min(candles_needed, 5000)

        logger.info(f"Fetching {candles_needed} candles of {timeframe} data...")
        df = data_fetcher.fetch_ohlcv(timeframe, outputsize=candles_needed, use_cache=False)

        if df is None or len(df) == 0:
            logger.error(f"Failed to fetch data for {strategy_name}")
            continue

        logger.info(f"Fetched {len(df)} candles from {df.index[0]} to {df.index[-1]}")

        # Run backtest
        backtester = Backtest(
            strategy_config={strategy_id: strategy},
            indicator_params=indicators,
            initial_balance=args.balance,
            risk_percent=args.risk,
        )

        results = backtester.run(df, strategy_id, commission=args.commission)

        if results:
            all_results[strategy_name] = results
            print_results(results, strategy_name)

            # Export trades if requested
            if args.export and len(results['trades']) > 0:
                trades_df = backtester.get_trades_dataframe()
                export_file = f"{args.export}_{strategy_name.replace(' ', '_')}.csv"
                trades_df.to_csv(export_file, index=False)
                logger.info(f"Trades exported to {export_file}")

    # Print summary if testing multiple strategies
    if len(all_results) > 1:
        print("\n" + "=" * 70)
        print("SUMMARY - ALL STRATEGIES")
        print("=" * 70)
        print(f"\n{'Strategy':<20} {'Trades':<8} {'Win%':<8} {'Return%':<10} {'Profit Factor':<15}")
        print("-" * 70)

        for name, res in all_results.items():
            print(
                f"{name:<20} "
                f"{res['total_trades']:<8} "
                f"{res['win_rate']:<8.2f} "
                f"{res['total_return']:<10.2f} "
                f"{res['profit_factor']:<15.2f}"
            )

        print("=" * 70)

    logger.info("\nBacktest complete!")


if __name__ == '__main__':
    main()
