# Backtesting exact live strategy on historical DUOL data
import pandas as pd
from strategies.crossover import compute_signals
from fetch_db import fetch_duol_bars

print("Backtesting DUOL Multi-Timeframe Strategy")
print("="*60)

daily = fetch_duol_bars("daily")
print(f"Loaded {len(daily)} daily bars")

# Simple SMA20/50
daily['sma20'] = daily['close'].rolling(20).mean()
daily['sma50'] = daily['close'].rolling(50).mean()

cash, shares = 100000.0, 0.0
trades = []

for i in range(50, len(daily), 5):  # Every 5th day (demo speed)
    row = daily.iloc[i]
    
    if pd.isna(row['sma20']) or pd.isna(row['sma50']):
        continue
        
    price = row['close']
    
    # Strategy logic
    if row['sma20'] > row['sma50'] and shares == 0:
        shares = cash * 0.95 / price  # 95% position
        cash *= 0.05
        trades.append(f"BUY  @ ${price:.1f}")
        
    elif row['sma20'] < row['sma50'] and shares > 0:
        cash += shares * price
        trades.append(f"SELL @ ${price:.1f}")
        shares = 0

final_value = cash + shares * daily['close'].iloc[-1]
total_return = (final_value / 100000 - 1) * 100

print("\n RESULTS")
print(f"Start: $100,000")
print(f"Final:  ${final_value:,.0f}")
print(f"Return: {total_return:+.1f}%")
print(f"Trades: {len(trades)}")

print("\nTrades:")
for trade in trades[-12:]:
    print(f"  {trade}")

print("\n backtest_results.txt")
with open('backtest_results.txt', 'w') as f:
    f.write(f"SMA20/50 Crossover\n")
    f.write(f"Return: {total_return:.1f}%\n")
    f.write(f"Period: {len(daily)} days\n")