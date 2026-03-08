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

    # 1. Pull fresh data into DuckDB
    manager = DuolDataManager()
    manager.update_hourly()

    # 2. Fetch from DuckDB into DataFrames
    daily_df  = fetch_duol_bars(timeframe="daily")
    hourly_df = fetch_duol_bars(timeframe="hourly")

    # 3. Ask Alpaca for our current shares and what we paid for them
    position, entry_price = executor.get_position()

    # 4. Compute signals
    signal = compute_signals(daily_df, hourly_df, entry_price=entry_price)
    
    # 5. Reset the cooldown if momentum drops to "sell"
    if signal['momentum'] == 'sell':
        cooldown = False

    logging.info(f"[{datetime.now().strftime('%H:%M')}] Action: {signal['action']} | "
                 f"Trend: {signal['trend']} | Momentum: {signal['momentum']} | "
                 f"Close={signal['latest_close']:.2f} | Cooldown: {cooldown}")

    # 6. Execute trade based on signal
    if signal['action'] == "BUY" and position == 0 and not cooldown:
        available_cash = executor.get_cash()
        latest_price = signal['latest_close']
        shares_to_buy = int((available_cash * 0.95) // latest_price)
        if shares_to_buy > 0:
            executor.buy(qty=shares_to_buy)
        else:
            logging.info("Not enough cash to buy a full share.")
    elif signal['action'] == "SELL" and position > 0:
        executor.sell(qty=position)
        
        # Trigger cooldown if we hit our profit or loss targets
        if signal.get('momentum') in ['take_profit', 'stop_loss']:
            cooldown = True
            logging.info(f"Triggered {signal['momentum']}, entering cooldown.")
    else:
        logging.info(f"HOLD — position={position}, action={signal['action']}")

# Run at :05 past every hour
schedule.every().hour.at(":05").do(refresh)

if __name__ == "__main__":
    print("Scheduler started. Waiting for next :05...")
    refresh()  # run once immediately on start
    while True:
        schedule.run_pending()
        time.sleep(30)