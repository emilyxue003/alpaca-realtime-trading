import pandas as pd
from strategies.crossover import compute_signals
from fetch_db import fetch_duol_bars

print("🔄 Backtesting crossover.py (15-Minute Short Scalp)")
print("="*70)

# Fetch data
hourly = fetch_duol_bars("hourly")
minute = fetch_duol_bars("minute")

# Resample 1-minute data into 15-minute blocks
minute.set_index('timestamp', inplace=True)
fifteen_min = minute.resample('15min').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna().reset_index()

cash = 100000.0
shares = 0  
trades = 0
entry_price = None
cooldown = False

if len(hourly) < 21:
    print("Not enough hourly data.")
    exit()

# Custom start date if we want to test shorter periods
custom_start = pd.to_datetime("2021-07-28")
warmup_date = hourly['timestamp'].iloc[21]
start_ts = max(warmup_date, custom_start)

fifteen_test = fifteen_min[fifteen_min['timestamp'] >= start_ts].reset_index(drop=True)

print(f"Starting 15-min simulation from {start_ts} (approx {len(fifteen_test)} periods to process...)")

# Iterate through every 15-minute chunk
for i in range(len(fifteen_test)):
    current_ts = fifteen_test['timestamp'].iloc[i]
    
    # Create slices UP TO this exact time. Add Timedelta to prevent Hourly future-leakage!
    hourly_slice = hourly[hourly['timestamp'] + pd.Timedelta(hours=1) <= current_ts]
    fifteen_slice = fifteen_min[fifteen_min['timestamp'] <= current_ts]
    
    if len(hourly_slice) < 21:
        continue # Wait for the SMA warm-up

    signal = compute_signals(hourly_slice, fifteen_slice, entry_price=entry_price, position=shares)
    price = fifteen_test['close'].iloc[i]

    # Reset cooldown on natural flip
    if (signal['trend'] == 'bull' and signal['momentum'] == 'sell') or \
       (signal['trend'] == 'bear' and signal['momentum'] == 'buy'):
        cooldown = False
    
    # Execute Actions
    if signal['action'] == 'BUY' and shares == 0 and not cooldown:
        qty = int((cash * 0.95) // price)
        if qty > 0:
            shares = qty
            cash -= shares * price
            trades += 1
            entry_price = price
            print(f"[{current_ts}] BUY (Long)  {signal['trend']}/{signal['momentum']} @ ${price:.2f}")
            
    elif signal['action'] == 'SHORT' and shares == 0 and not cooldown:
        qty = int((cash * 0.95) // price)
        if qty > 0:
            shares = -qty  
            cash += abs(shares) * price  
            trades += 1
            entry_price = price
            print(f"[{current_ts}] SHORT       {signal['trend']}/{signal['momentum']} @ ${price:.2f}")
            
    elif signal['action'] == 'SELL' and shares > 0:
        cash += shares * price
        shares = 0
        trades += 1
        entry_price = None
        if signal.get('momentum') in ['take_profit', 'stop_loss']:
            cooldown = True
            print(f"[{current_ts}] SELL (Close) {signal['momentum'].upper()} @ ${price:.2f} (Cooldown Active)")
        else:
            print(f"[{current_ts}] SELL (Close) {signal['trend']}/{signal['momentum']} @ ${price:.2f}")

    elif signal['action'] == 'COVER' and shares < 0:
        cash -= abs(shares) * price  
        shares = 0
        trades += 1
        entry_price = None
        if signal.get('momentum') in ['take_profit', 'stop_loss']:
            cooldown = True
            print(f"[{current_ts}] COVER       {signal['momentum'].upper()} @ ${price:.2f} (Cooldown Active)")
        else:
            print(f"[{current_ts}] COVER       {signal['trend']}/{signal['momentum']} @ ${price:.2f}")

final_value = cash + (shares * fifteen_test['close'].iloc[-1])
total_return = (final_value / 100000 - 1) * 100

print("\n📊 BACKTESTING RESULTS")
print(f"Period: {fifteen_test['timestamp'].iloc[0]:%Y-%m-%d} → {fifteen_test['timestamp'].iloc[-1]:%Y-%m-%d}")
print(f"Final Value: ${final_value:,.2f}")
print(f"Return: {total_return:+.1f}%")
print(f"Trades: {trades}")

with open('backtest_results.txt', 'w') as f:
    f.write("📊 BACKTESTING RESULTS\n")
    f.write(f"Period: {fifteen_test['timestamp'].iloc[0]:%Y-%m-%d} → {fifteen_test['timestamp'].iloc[-1]:%Y-%m-%d}\n")
    f.write(f"Final Value: ${final_value:,.2f}\n")
    f.write(f"Return: {total_return:+.1f}%\n")
    f.write(f"Trades: {trades}\n")

print("✅ Results successfully saved to backtest_results.txt")