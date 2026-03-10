# scheduler.py
import os
import schedule
import time
import logging
import duckdb
from datetime import datetime
from duol_data_manager import DuolDataManager
from fetch_db import fetch_duol_bars
from strategies.crossover import compute_signals
from trading.executor import TradeExecutor

DB_PATH = "data/trading.duckdb"

# Ensure dirs exist for fresh VM / headless deployment
os.makedirs("logs", exist_ok=True)
os.makedirs("data/daily", exist_ok=True)
os.makedirs("data/hourly", exist_ok=True)
os.makedirs("data/minute", exist_ok=True)

logging.basicConfig(
    filename="logs/scheduler.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

executor = TradeExecutor()

# Initialize cooldown memory at the top level
cooldown = False

def is_market_hours():
    """Only run during market hours 9:30am - 4pm ET Mon-Fri."""
    now = datetime.now()
    if now.weekday() >= 5:  # weekend
        return False
    market_open  = now.replace(hour=8,  minute=30, second=0) # Adjusted for CST
    market_close = now.replace(hour=15, minute=0,  second=0) # Adjusted for CST
    return market_open <= now <= market_close

def refresh():
    global cooldown # Use global memory variable

    if not is_market_hours():
        logging.info("Outside market hours, skipping refresh")
        return

    logging.info("--- Refresh triggered ---")

    # 1. Pull fresh data into DuckDB (both daily and hourly needed for signals)
    manager = DuolDataManager()
    manager.update_hourly()
    manager.update_minute()

    # 2. Fetch from DuckDB into DataFrames
    hourly_df  = fetch_duol_bars(timeframe="hourly")
    minute_df = fetch_duol_bars(timeframe="minute")

    # Resample minute to 15-minute blocks
    minute_df.set_index('timestamp', inplace=True)
    fifteen_df = minute_df.resample('15min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna().reset_index()

    # 3. Ask Alpaca for our current shares and what we paid for them
    position, entry_price = executor.get_position()

    # 4. Compute signals
    signal = compute_signals(hourly_df, fifteen_df, entry_price=entry_price, position=position)
    
    # 5. Reset the cooldown if momentum drops to "sell"
    if (signal['trend'] == 'bull' and signal['momentum'] == 'sell') or \
       (signal['trend'] == 'bear' and signal['momentum'] == 'buy'):
        cooldown = False

    logging.info(f"[{datetime.now().strftime('%H:%M')}] Action: {signal['action']} | "
                 f"Trend: {signal['trend']} | Momentum: {signal['momentum']} | "
                 f"Close={signal['latest_close']:.2f} | Cooldown: {cooldown}")

    # 6. Execute trade based on signal
    latest_price = signal['latest_close']
    available_cash = executor.get_cash()
    shares_to_trade = int((available_cash * 0.95) // latest_price)

    if signal['action'] == "BUY" and position == 0 and not cooldown:
        if shares_to_trade > 0:
            executor.buy(qty=shares_to_trade)
            
    elif signal['action'] == "SHORT" and position == 0 and not cooldown:
        if shares_to_trade > 0:
            # Alpaca handles shorting automatically when you 'sell' shares you don't own
            executor.sell(qty=shares_to_trade) 
            
    elif signal['action'] == "SELL" and position > 0:
        executor.sell(qty=position) # Liquidate Long
        if signal.get('momentum') in ['take_profit', 'stop_loss']:
            cooldown = True
            
    elif signal['action'] == "COVER" and position < 0:
        executor.buy(qty=abs(position)) # Buy back Short
        if signal.get('momentum') in ['take_profit', 'stop_loss']:
            cooldown = True

# Run every 15 minutes
schedule.every(15).minutes.do(refresh)

if __name__ == "__main__":
    print("Scheduler started. Waiting for next :05...")
    refresh()  # run once immediately on start
    while True:
        schedule.run_pending()
        time.sleep(30)