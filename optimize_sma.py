import pandas as pd
import numpy as np
from fetch_db import fetch_duol_bars
from strategies.crossover import compute_signals

print("🔬 Running SMA Parameter Sweep (Trailing 52-Weeks, Warm-Data Accurate)...")

# 1. Fetch Data
hourly = fetch_duol_bars("hourly")
minute = fetch_duol_bars("minute")

minute.set_index('timestamp', inplace=True)
fifteen_min = minute.resample('15min').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
}).dropna().reset_index()

# Isolate the exact 52-week window for execution testing
X_WEEKS = 52
latest_ts = fifteen_min['timestamp'].max()
start_ts = latest_ts - pd.Timedelta(weeks=X_WEEKS)
start_ts = start_ts - pd.Timedelta(days=start_ts.dayofweek)
start_ts = start_ts.replace(hour=0, minute=0, second=0)

fifteen_test = fifteen_min[fifteen_min['timestamp'] >= start_ts].reset_index(drop=True)

print(f"Testing period: {start_ts:%Y-%m-%d} to {latest_ts:%Y-%m-%d}\n")

sma_pairs = [(9, 21), (10, 50), (20, 50), (20, 100), (50, 200)]
results = []

for fast, slow in sma_pairs:
    cash = 100000.0
    shares = 0
    trades = 0
    entry_price = None
    cooldown = False
    
    daily_values = []
    current_day = fifteen_test['timestamp'].iloc[0].date()
    
    for i in range(len(fifteen_test)):
        current_ts = fifteen_test['timestamp'].iloc[i]
        price = fifteen_test['close'].iloc[i]
        
        # Log daily value for Sharpe Ratio
        if current_ts.date() != current_day:
            daily_values.append(cash + (shares * price))
            current_day = current_ts.date()

        # --- THE FIX: Slice from the FULL historical dataset for accurate warm-up ---
        hourly_slice = hourly[hourly['timestamp'] + pd.Timedelta(hours=1) <= current_ts]
        fifteen_slice = fifteen_min[fifteen_min['timestamp'] <= current_ts]
        
        if len(hourly_slice) < slow: 
            continue

        # --- USE YOUR PRODUCTION FUNCTION ---
        signal = compute_signals(
            hourly_df=hourly_slice, 
            fifteen_df=fifteen_slice, 
            entry_price=entry_price, 
            position=shares,
            sma_fast=fast,
            sma_slow=slow
        )

        # Reset cooldown on natural momentum flip
        if (signal['trend'] == 'bull' and signal['momentum'] == 'sell') or \
           (signal['trend'] == 'bear' and signal['momentum'] == 'buy'):
            cooldown = False

        # --- EXECUTE ACTIONS ---
        if signal['action'] == 'BUY' and shares == 0 and not cooldown:
            qty = int((cash * 0.95) // price)
            if qty > 0:
                shares = qty
                cash -= shares * price
                trades += 1
                entry_price = price
                
        elif signal['action'] == 'SHORT' and shares == 0 and not cooldown:
            qty = int((cash * 0.95) // price)
            if qty > 0:
                shares = -qty
                cash += abs(shares) * price
                trades += 1
                entry_price = price
                
        elif signal['action'] == 'SELL' and shares > 0:
            cash += shares * price
            shares = 0
            trades += 1
            entry_price = None
            if signal.get('momentum') in ['take_profit', 'stop_loss']:
                cooldown = True
                
        elif signal['action'] == 'COVER' and shares < 0:
            cash -= abs(shares) * price
            shares = 0
            trades += 1
            entry_price = None
            if signal.get('momentum') in ['take_profit', 'stop_loss']:
                cooldown = True

    # End of simulation for this pair
    final_val = cash + (shares * fifteen_test['close'].iloc[-1])
    ret_pct = ((final_val / 100000.0) - 1) * 100
    
    daily_returns = pd.Series(daily_values).pct_change().dropna()
    sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if len(daily_returns) > 0 else 0
    
    results.append((f"SMA {fast}/{slow}", sharpe, ret_pct, trades))

print("\n✅ Accurate Optimization Complete:")
print("| Pair | Sharpe | Return | Trades |")
print("|------|--------|--------|--------|")
for r in results:
    print(f"| {r[0]} | {r[1]:+.2f} | {r[2]:+.2f}% | {r[3]} |")