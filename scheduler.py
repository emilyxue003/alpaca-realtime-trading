# scheduler.py
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

logging.basicConfig(
    filename="logs/scheduler.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

executor = TradeExecutor()

def is_market_hours():
    """Only run during market hours 9:30am - 4pm ET Mon-Fri."""
    now = datetime.now()
    if now.weekday() >= 5:  # weekend
        return False
    market_open  = now.replace(hour=9,  minute=30, second=0)
    market_close = now.replace(hour=16, minute=0,  second=0)
    return market_open <= now <= market_close

def refresh():
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

    # 3. Compute signals
    signal = compute_signals(daily_df, hourly_df)
    logging.info(f"Signal: {signal}")
    print(f"[{datetime.now().strftime('%H:%M')}] Action={signal['action']} | "
          f"Trend={signal['trend']} | Momentum={signal['momentum']} | "
          f"Close={signal['latest_close']:.2f}")

    # 4. Execute trade based on signal -- Need to uncomment later 
    # position = executor.get_position()

    # if signal['action'] == "BUY" and position == 0:
    #     executor.buy(qty=1)
    # elif signal['action'] == "SELL" and position > 0:
    #     executor.sell(qty=position)
    # else:
    #     logging.info(f"HOLD — position={position}, action={signal['action']}")

# Run at :05 past every hour
schedule.every().hour.at(":05").do(refresh)

if __name__ == "__main__":
    print("Scheduler started. Waiting for next :05...")
    refresh()  # run once immediately on start
    while True:
        schedule.run_pending()
        time.sleep(30)