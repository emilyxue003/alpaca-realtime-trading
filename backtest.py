import pandas as pd
from strategies.crossover import compute_signals
from fetch_db import fetch_duol_bars

print("🔄 Backtesting crossover.py (True Hourly Loop)")
print("="*70)

# Fetch data
daily = fetch_duol_bars("daily")
hourly = fetch_duol_bars("hourly")

print(f"Daily:  {len(daily)} bars")
print(f"Hourly: {len(hourly)} bars")

cash = 100000.0
shares = 0.0
trades = 0
entry_price = None
cooldown = False

# We need 21 daily bars to calculate the SMA21. 
# Find the date of the 21th day to start our hourly loop there.
if len(daily) < 21:
    print("Not enough daily data.")
    exit()

start_ts = daily['timestamp'].iloc[21]

# Filter our test loop to only include hours after the 21-day warm-up
hourly_test = hourly[hourly['timestamp'] >= start_ts].reset_index(drop=True)

print(f"Starting hourly simulation from {start_ts} (approx {len(hourly_test)} hours to process...)")

# THE NEW LOOP: Iterate through every hour
for i in range(len(hourly_test)):
    current_ts = hourly_test['timestamp'].iloc[i]
    
    # 1. Create slices of history UP TO this exact hour
    # This prevents the algorithm from seeing the future
    hourly_slice = hourly[hourly['timestamp'] <= current_ts]
    daily_slice = daily[daily['timestamp'] <= current_ts]
    
    # 2. Get signal from your exact crossover.py logic
    signal = compute_signals(daily_slice, hourly_slice, entry_price=entry_price)
    
    # Use the current hour's close price to execute trades
    price = hourly_test['close'].iloc[i]

    # If the MACD crosses down, the cooldown is officially over
    if signal['momentum'] == 'sell':
        cooldown = False
    
    # 3. Execute Actions
    if signal['action'] == 'BUY' and shares == 0 and not cooldown:
        # Buy whole shares with 95% of cash
        shares = (cash * 0.95) // price 
        if shares > 0:
            cash -= shares * price
            trades += 1
            entry_price = price
            print(f"[{current_ts}] BUY  {signal['trend']}/{signal['momentum']} @ ${price:.2f}")
        
    elif signal['action'] == 'SELL' and shares > 0:
        cash += shares * price
        shares = 0
        trades += 1
        entry_price = None

        # 4. NEW LOGIC: Trigger cooldown on special exits
        if signal.get('momentum') == 'take_profit':
            cooldown = True
            print(f"[{current_ts}] SELL TAKE PROFIT @ ${price:.2f} (Cooldown Active)")
        elif signal.get('momentum') == 'stop_loss':
            cooldown = True
            print(f"[{current_ts}] SELL STOP LOSS @ ${price:.2f} (Cooldown Active)")
        else:
            print(f"[{current_ts}] SELL {signal['trend']}/{signal['momentum']} @ ${price:.2f}")

# Calculate final metrics
final_value = cash + (shares * hourly_test['close'].iloc[-1])
total_return = (final_value / 100000 - 1) * 100

print("\n📊 BACKTESTING RESULTS")
print(f"Period: {hourly_test['timestamp'].iloc[0]:%Y-%m-%d} → {hourly_test['timestamp'].iloc[-1]:%Y-%m-%d}")
print(f"Final Value: ${final_value:,.2f}")
print(f"Return: {total_return:+.1f}%")
print(f"Trades: {trades}")

with open('backtest_results.txt', 'w') as f:
    f.write("📊 BACKTESTING RESULTS\n")
    f.write(f"Period: {hourly_test['timestamp'].iloc[0]:%Y-%m-%d} → {hourly_test['timestamp'].iloc[-1]:%Y-%m-%d}\n")
    f.write(f"Final Value: ${final_value:,.2f}\n")
    f.write(f"Return: {total_return:+.1f}%\n")
    f.write(f"Trades: {trades}\n")

print("✅ Results successfully saved to backtest_results.txt")