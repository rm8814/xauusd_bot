# Backtesting Guide

Test your trading strategies on historical data before going live.

## Quick Start

### Run Backtest for All Strategies

```bash
cd /root/xauusd_bot
source venv/bin/activate
python scripts/run_backtest.py
```

### Run Backtest for Specific Strategy

```bash
# Test strategy 1 (1D Pure AO)
python scripts/run_backtest.py --strategy 1

# Test strategy 4 (4H ATR Momentum)
python scripts/run_backtest.py --strategy 4
```

## Options

```bash
python scripts/run_backtest.py [OPTIONS]
```

### Available Options:

| Option | Default | Description |
|--------|---------|-------------|
| `--strategy` | all | Strategy ID (1-6) or "all" |
| `--days` | 365 | Days of historical data |
| `--balance` | 100 | Initial balance |
| `--risk` | 1.0 | Risk per trade (%) |
| `--commission` | 0.0 | Commission per trade (%) |
| `--export` | None | Export trades to CSV |

## Examples

### Test Last 6 Months

```bash
python scripts/run_backtest.py --days 180
```

### Test with $1000 Initial Balance

```bash
python scripts/run_backtest.py --balance 1000
```

### Test with 2% Risk Per Trade

```bash
python scripts/run_backtest.py --risk 2.0
```

### Test with Commission

```bash
python scripts/run_backtest.py --commission 0.1
```

### Export Trades to CSV

```bash
python scripts/run_backtest.py --strategy 1 --export backtest_results
```

This creates: `backtest_results_1D_Pure_AO.csv`

### Complete Example

```bash
python scripts/run_backtest.py \
  --strategy 4 \
  --days 730 \
  --balance 1000 \
  --risk 1.5 \
  --commission 0.05 \
  --export my_backtest
```

## Understanding Results

### Trading Statistics
- **Total Trades**: Number of completed trades
- **Winning Trades**: Trades that made profit
- **Losing Trades**: Trades that lost money
- **Win Rate**: Percentage of winning trades

### P&L Metrics
- **Initial Balance**: Starting capital
- **Final Balance**: Ending capital
- **Total P&L**: Total profit/loss
- **Total Return**: Return as percentage

### Performance Metrics
- **Profit Factor**: Gross profit ÷ Gross loss (>1 is profitable)
- **Sharpe Ratio**: Risk-adjusted return (higher is better)
- **Max Drawdown**: Largest peak-to-trough decline

### Trade Averages
- **Average Win**: Average profit per winning trade
- **Average Loss**: Average loss per losing trade
- **Largest Win**: Biggest winning trade
- **Largest Loss**: Biggest losing trade
- **Avg Duration**: Average trade length in bars

## Sample Output

```
======================================================================
BACKTEST RESULTS: 4H ATR Momentum
======================================================================

📊 TRADING STATISTICS
   Total Trades: 45
   Winning Trades: 27
   Losing Trades: 18
   Win Rate: 60.00%

💰 P&L METRICS
   Initial Balance: $100.00
   Final Balance: $156.50
   Total P&L: $56.50
   Total Return: 56.50%

📈 PERFORMANCE METRICS
   Profit Factor: 2.15
   Sharpe Ratio: 1.25
   Max Drawdown: -12.50%

💵 TRADE AVERAGES
   Average Win: $3.25
   Average Loss: $1.85
   Largest Win: $8.50
   Largest Loss: $4.20
   Avg Duration: 12.5 bars

======================================================================
```

## Interpreting Results

### Good Strategy Indicators:
- ✅ **Win Rate > 45%**
- ✅ **Profit Factor > 1.5**
- ✅ **Sharpe Ratio > 1.0**
- ✅ **Max Drawdown < 30%**
- ✅ **Positive Total Return**

### Warning Signs:
- ⚠️ Win Rate < 35%
- ⚠️ Profit Factor < 1.2
- ⚠️ Max Drawdown > 40%
- ⚠️ Very few trades (< 10 in a year)
- ⚠️ Very many trades (overtrading)

## Strategy Comparison

Test all strategies and compare:

```bash
python scripts/run_backtest.py --strategy all --days 365
```

Results table shows:
- Which strategies perform best
- Which timeframes are most reliable
- PURE vs ATR mode comparison

## Data Limitations

### TwelveData Free Tier:
- **800 API calls per day**
- **Up to 5000 historical candles per request**
- **Rate limits apply**

### Recommended Settings:
- **1H**: `--days 180` (4,320 candles)
- **4H**: `--days 365` (2,190 candles)
- **1Day**: `--days 730` (730 candles)

## Exporting Results

Export trades for further analysis:

```bash
python scripts/run_backtest.py --strategy 1 --export results
```

CSV includes:
- Entry/exit times and prices
- Direction (LONG/SHORT)
- P&L and P&L%
- Exit reason
- Duration

Open in Excel/Google Sheets for analysis.

## Advanced Usage

### Python API

Use the backtester directly in Python:

```python
from src.analytics.backtest import Backtest
from src.data.data_fetcher import DataFetcher

# Fetch data
fetcher = DataFetcher(api_key)
df = fetcher.fetch_ohlcv('4h', outputsize=1000)

# Run backtest
backtester = Backtest(
    strategy_config=strategies,
    indicator_params=indicators,
    initial_balance=100,
    risk_percent=1.0
)

results = backtester.run(df, 'strategy_4', commission=0.0)

# Get trades DataFrame
trades_df = backtester.get_trades_dataframe()

# Get equity curve
equity_df = backtester.get_equity_dataframe()
```

## Tips

1. **Start with small timeframes**: Test 1H first (faster)
2. **Increase data gradually**: Start with 90 days, then 180, then 365
3. **Test all strategies**: Compare performance
4. **Add realistic commission**: Usually 0.05-0.1%
5. **Export and analyze**: Use Excel for detailed analysis
6. **Look for consistency**: Good across different time periods
7. **Consider drawdowns**: Can you handle a 30% drawdown?

## Troubleshooting

### "Failed to fetch data"
- Check your API key in `.env`
- Check API usage: https://twelvedata.com/account/usage
- Reduce `--days` parameter

### "No trades executed"
- Data period may be too short
- Try `--days 365` or more
- Check if indicators are calculating correctly

### "Too many API calls"
- TwelveData free tier limits
- Wait 24 hours for reset
- Use cached data if available

## Next Steps

After backtesting:

1. ✅ Review results for each strategy
2. ✅ Choose best-performing strategies
3. ✅ Adjust risk parameters if needed
4. ✅ Test on different time periods
5. ✅ Start with paper trading
6. 🎯 Go live with confidence!

---

**Remember**: Past performance doesn't guarantee future results. Always start with paper trading!
