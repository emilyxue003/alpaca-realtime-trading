import pandas as pd
from strategies.crossover import compute_signals
from fetch_db import fetch_duol_bars

print("🔄 Weekly Returns Backtest (15-Minute Strategy)")
print("="*80)

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

if len(hourly) < 21:
    print("Not enough hourly data.")
    exit()

# --- CONFIGURATION ---
X_WEEKS = 52  # Change this number to test more/fewer weeks
latest_ts = fifteen_min['timestamp'].max()
start_ts = latest_ts - pd.Timedelta(weeks=X_WEEKS)
# Align start date to Monday morning for clean weekly buckets
start_ts = start_ts - pd.Timedelta(days=start_ts.dayofweek)
start_ts = start_ts.replace(hour=0, minute=0, second=0)

fifteen_test = fifteen_min[fifteen_min['timestamp'] >= start_ts].reset_index(drop=True)

print(f"Testing last {X_WEEKS} weeks (from {start_ts:%Y-%m-%d} to {latest_ts:%Y-%m-%d})")

cash = 100000.0
shares = 0  
trades = 0
entry_price = None
cooldown = False

# --- WEEKLY TRACKING SETUP ---
weekly_metrics = []
current_iso_week = fifteen_test['timestamp'].iloc[0].isocalendar().week
week_start_value = cash
week_start_date = fifteen_test['timestamp'].iloc[0]

# NEW: Track the stock's starting price for the benchmark
week_start_stock_price = fifteen_test['close'].iloc[0] 
baseline_start_price = week_start_stock_price # For the overall X-week benchmark

# Iterate through every 15-minute chunk
for i in range(len(fifteen_test)):
    current_ts = fifteen_test['timestamp'].iloc[i]
    price = fifteen_test['close'].iloc[i]

    # Check if we have entered a new calendar week
    this_iso_week = current_ts.isocalendar().week
    if this_iso_week != current_iso_week:
        current_portfolio_value = cash + (shares * price)
        strat_return = ((current_portfolio_value / week_start_value) - 1) * 100
        
        # Calculate Benchmark (DUOL) Return
        duol_return = ((price / week_start_stock_price) - 1) * 100
        
        weekly_metrics.append({
            "Week": week_start_date.strftime('%Y-%m-%d'),
            "Strat Return": strat_return,
            "DUOL Return": duol_return,
            "Value": current_portfolio_value
        })
        
        # Reset trackers for the new week
        current_iso_week = this_iso_week
        week_start_value = current_portfolio_value
        week_start_date = current_ts
        week_start_stock_price = price
    
    # Create slices UP TO this exact time. Add Timedelta to prevent Hourly future-leakage!
    hourly_slice = hourly[hourly['timestamp'] + pd.Timedelta(hours=1) <= current_ts]
    fifteen_slice = fifteen_min[fifteen_min['timestamp'] <= current_ts]
    
    if len(hourly_slice) < 21:
        continue # Wait for the SMA warm-up

    signal = compute_signals(hourly_slice, fifteen_slice, entry_price=entry_price, position=shares)

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

# Append the final incomplete week
final_value = cash + (shares * fifteen_test['close'].iloc[-1])
final_strat_return = ((final_value / week_start_value) - 1) * 100
final_duol_return = ((fifteen_test['close'].iloc[-1] / week_start_stock_price) - 1) * 100

weekly_metrics.append({
    "Week": week_start_date.strftime('%Y-%m-%d'),
    "Strat Return": final_strat_return,
    "DUOL Return": final_duol_return,
    "Value": final_value
})

total_strat_return = (final_value / 100000 - 1) * 100
total_duol_return = ((fifteen_test['close'].iloc[-1] / baseline_start_price) - 1) * 100

print("\n📊 WEEKLY BREAKDOWN (Strategy vs Benchmark)")
print("-" * 63)
print(f"{'Week Starting':<14} | {'DUOL Return':>12} | {'Strat Return':>13} | {'End Value':>10}")
print("-" * 63)
for w in weekly_metrics:
    # Highlight if the strategy beat the market that week
    beat_market = "⭐" if w['Strat Return'] > w['DUOL Return'] else "  "
    print(f"{w['Week']:<14} | {w['DUOL Return']:>11.2f}% | {w['Strat Return']:>12.2f}% | ${w['Value']:>10,.0f} {beat_market}")

print("\n📈 OVERALL PERFORMANCE")
print("-" * 50)
print(f"Total Period: {X_WEEKS} Weeks ({start_ts:%Y-%m-%d} to {latest_ts:%Y-%m-%d})")
print(f"Final Value: ${final_value:,.2f}")
print(f"Total Trades: {trades}")
print(f"Strat Return: {total_strat_return:+.2f}%")
print(f"DUOL Return:  {total_duol_return:+.2f}%")
print(f"Total Alpha:  {(total_strat_return - total_duol_return):+.2f}%")

# Save to backtest_results file
with open('backtest_results.txt', 'w') as f:
    f.write(f"Time Period: {X_WEEKS} Weeks ({start_ts:%Y-%m-%d} to {latest_ts:%Y-%m-%d})\n")

    f.write(f"Final Value: ${final_value:,.2f}\n")
    f.write(f"Total Trades: {trades}\n")
    f.write(f"Overall Strat: {total_strat_return:+.2f}%\n")
    f.write(f"Overall DUOL: {total_duol_return:+.2f}%\n")
    f.write(f"Alpha: {(total_strat_return - total_duol_return):+.2f}%\n")

    f.write("\n📊 WEEKLY BREAKDOWN\n")
    f.write("-" * 48 + "\n")
    f.write(f"{'Week Starting':<14} | {'DUOL Return':>12} | {'Strat Return':>13}\n")
    f.write("-" * 48 + "\n")
    for w in weekly_metrics:
        beat_market = "⭐" if w['Strat Return'] > w['DUOL Return'] else "  "
        f.write(f"{w['Week']:<14} | {w['DUOL Return']:>+11.2f}% | {w['Strat Return']:>+12.2f}% {beat_market}\n")

print("✅ Results successfully saved to backtest_results.txt")