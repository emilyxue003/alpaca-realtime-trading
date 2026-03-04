"""
MARKET-AWARE SMA (Profitable Across Stocks)


import pandas as pd
from fetch_db import fetch_duol_bars

print("Market-Aware DUOL Strategy")
print("="*60)

daily = fetch_duol_bars("daily")
print(f"Loaded {len(daily)} daily bars")

# SMAs
daily['sma8']  = daily['close'].rolling(8).mean()   # Very fast
daily['sma21'] = daily['close'].rolling(21).mean()  # Medium
daily['sma50'] = daily['close'].rolling(50).mean()  # Slow trend

# SPY proxy (DUOL trend filter)
daily['above_sma50'] = daily['close'] > daily['sma50']

cash = 100000.0
shares = 0.0
trades = 0
wins = 0

for i in range(30, len(daily)):
    row = daily.iloc[i]
    
    if pd.isna(row['sma8']) or pd.isna(row['sma21']) or pd.isna(row['sma50']):
        continue
        
    price = row['close']
    
    # ONLY TRADE IN UPTRENDS
    if not row['above_sma50']:
        if shares > 0:  # Exit if trend breaks
            cash += shares * price
            trades += 1
            shares = 0
        continue
    
    # Golden cross (fast > medium)
    buy_signal = row['sma8'] > row['sma21'] and shares == 0
    sell_signal = row['sma21'] > row['sma50'] and row['sma8'] < row['sma21'] and shares > 0
    
    if buy_signal:
        risk_amount = cash * 0.25  # 25% risk
        shares = risk_amount / price
        cash -= risk_amount
        trades += 1
        print(f"BUY  i={i}: {row['sma8']:.1f}>{row['sma21']:.1f} trend↑")
        
    elif sell_signal:
        cash += shares * price
        pnl_pct = (price / (risk_amount / shares) - 1) * 100 if shares > 0 else 0
        if pnl_pct > 0:
            wins += 1
        print(f"SELL i={i}: PnL{pnl_pct:+4.0f}%")
        shares = 0

final_value = cash + shares * daily['close'].iloc[-1]
total_return = (final_value / 100000 - 1) * 100
win_rate = wins / trades * 100 if trades > 0 else 0

print("\n MARKET-AWARE RESULTS")
print(f"Start:  $100,000")
print(f"Final:  ${final_value:,.0f}")
print(f"Return: {total_return:+.1f}%")
print(f"Trades: {trades}")
print(f"Win Rate: {win_rate:.0f}%")

print("\n Saved")
with open('backtest_results.txt', 'w') as f:
    f.write(f"Market-Aware SMA8/21/50\n")
    f.write(f"Return: {total_return:.1f}%\n")
    f.write(f"Win Rate: {win_rate:.0f}%\n")
"""

# Backtesting exact live strategy on historical DUOL data
"""
BACKTEST EXACT crossover.py STRATEGY
Uses real hourly when available, daily proxy for early years
"""

import pandas as pd
from strategies.crossover import compute_signals
from fetch_db import fetch_duol_bars

print("🔄 Backtesting crossover.py (Live Strategy)")
print("="*70)

daily = fetch_duol_bars("daily")
hourly = fetch_duol_bars("hourly")

print(f"Daily:  {len(daily)} bars")
print(f"Hourly: {len(hourly)} bars (using daily proxy early)")

cash = 100000.0
shares = 0.0
trades = 0

for i in range(100, len(daily)):
    day_ts = daily['timestamp'].iloc[i]
    
    # REAL hourly if available, else daily proxy
    hourly_slice = hourly[hourly['timestamp'] <= day_ts]
    if len(hourly_slice) < 24:
        hourly_slice = daily[daily['timestamp'] <= day_ts].tail(24).copy()
        hourly_slice = hourly_slice.rename(columns={'close': 'close'})  # Match schema
    
    daily_slice = daily[daily['timestamp'] <= day_ts]
    
    signal = compute_signals(daily_slice, hourly_slice)
    price = daily_slice['close'].iloc[-1]
    
    if signal['action'] == 'BUY' and shares == 0:
        shares = cash * 0.9 / price
        cash *= 0.1
        trades += 1
        print(f"BUY  {signal['action']} {signal['trend']}/{signal['momentum']} @ ${price:.1f}")
        
    elif signal['action'] == 'SELL' and shares > 0:
        cash += shares * price
        print(f"SELL {signal['action']} @ ${price:.1f}")
        shares = 0
        trades += 1

final_value = cash + shares * daily['close'].iloc[-1]
total_return = (final_value / 100000 - 1) * 100

print("\n📊 crossover.py STRATEGY RESULTS")
print(f"Period: {daily['timestamp'].iloc[100]:%Y-%m-%d} → {daily['timestamp'].iloc[-1]:%Y-%m-%d}")
print(f"Return: {total_return:+.1f}%")
print(f"Trades: {trades}")

with open('backtest_results.txt', 'w') as f:
    f.write("crossover.py Live Strategy Backtest\n")
    f.write(f"Return: {total_return:.1f}%\n")
    f.write(f"Trades: {trades}\n")
