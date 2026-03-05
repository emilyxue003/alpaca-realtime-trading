import os
import glob
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")

def hard_reset():
    """
    Deletes both the DuckDB database and Parquet backup files.
    
    When updating start dates or switching to a different stock, run the following workflow:
        1. Run python reset_db.py (and type y to confirm).
        2. Run python duol_data_manager.py to pull the full historical dataset from Alpaca.
        3. Run python backtest.py to see the results.
    """
    
    print("🧹 Starting database hard reset...")
    
    # 1. Find and delete DuckDB files (catches the main db and any .wal files)
    db_files = glob.glob("data/trading.duckdb*")
    for f in db_files:
        try:
            os.remove(f)
            logging.info(f"Deleted database file: {f}")
        except Exception as e:
            logging.error(f"Error deleting {f}: {e}")

    # 2. Define the exact Parquet files from your manager
    parquet_files = [
        "data/daily/duol_daily.parquet",
        "data/hourly/duol_hourly.parquet",
        "data/minute/duol_minute.parquet"
    ]
    
    # 3. Delete Parquet backups
    for f in parquet_files:
        if os.path.exists(f):
            try:
                os.remove(f)
                logging.info(f"Deleted parquet backup: {f}")
            except Exception as e:
                logging.error(f"Error deleting {f}: {e}")
                
    print("\n✅ Reset complete! Run `python duol_data_manager.py` to pull fresh data.")

if __name__ == "__main__":
    # Add a quick safety prompt just in case someone runs it by accident
    confirm = input("Are you sure you want to delete all local market data? (y/n): ")
    if confirm.lower() == 'y':
        hard_reset()
    else:
        print("Reset cancelled.")