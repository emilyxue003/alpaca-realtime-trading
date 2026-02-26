import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import duckdb
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# Load environment variables
load_dotenv()
API_KEY = os.getenv("APCA_API_KEY_ID")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/data_updates.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Setup data folders
os.makedirs("data/daily", exist_ok=True)
os.makedirs("data/hourly", exist_ok=True)
os.makedirs("data/minute", exist_ok=True)

# DuckDB database path
DB_PATH = "data/trading.duckdb"

class DuolDataManager:
    def __init__(self):
        self.client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
        self.symbol = "DUOL"
        self.paths = {
            "daily": "data/daily/duol_daily.parquet",
            "hourly": "data/hourly/duol_hourly.parquet",
            "minute": "data/minute/duol_minute.parquet",
        }
        self.start_dates = {
            "daily": datetime(2021, 7, 28),  # DUOL IPO
            "hourly": datetime.now() - timedelta(days=5),
            "minute": datetime.now() - timedelta(days=5),
        }
        # DuckDB connection
        self.con = duckdb.connect(DB_PATH)

    def ensure_duckdb_table(self, timeframe: str):
        """Create table in DuckDB from Parquet if it doesn't exist."""
        path = self.paths[timeframe]
        table_name = f"{timeframe}_duol"
        if os.path.exists(path):
            self.con.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} AS
                SELECT * FROM '{path}'
            """)
        else:
            # Create empty table if no Parquet exists
            self.con.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    timestamp TIMESTAMP,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume BIGINT
                )
            """)
        return table_name

    def update_bars(self, timeframe: str):
        try:
            path = self.paths[timeframe]
            start_default = self.start_dates[timeframe]
            tf_map = {
                "daily": TimeFrame.Day,
                "hourly": TimeFrame.Hour,
                "minute": TimeFrame.Minute,
            }
            timeframe_obj = tf_map[timeframe]
            table_name = self.ensure_duckdb_table(timeframe)

            # Determine start date
            res = self.con.execute(f"SELECT MAX(timestamp) FROM {table_name}").fetchone()
            last_timestamp = res[0]
            start_date = (last_timestamp + timedelta(minutes=1 if timeframe=="minute" else 1/24)
                          if last_timestamp else start_default)

            logging.info(f"Updating {timeframe} bars from {start_date}")

            # Request new bars
            request = StockBarsRequest(
                symbol_or_symbols=self.symbol,
                timeframe=timeframe_obj,
                start=start_date,
                end=datetime.now(),
                feed="iex",
            )
            bars = self.client.get_stock_bars(request)
            df_new = bars.df.reset_index()

            if df_new.empty:
                logging.info(f"No new {timeframe} bars to update")
                return

            # Register DataFrame in DuckDB
            self.con.register("df_new_temp", df_new)

            # Remove overlapping timestamps
            self.con.execute(f"""
                DELETE FROM {table_name}
                WHERE timestamp IN (SELECT timestamp FROM df_new_temp)
            """)

            # Insert new rows
            self.con.execute(f"INSERT INTO {table_name} SELECT * FROM df_new_temp")

            # Backup to Parquet
            self.con.execute(f"COPY {table_name} TO '{path}' (FORMAT PARQUET)")

            logging.info(f"Updated {timeframe} bars: {len(df_new)} new rows added")
        except Exception as e:
            logging.error(f"Failed to update {timeframe} bars: {e}")

    # Convenience methods
    def update_daily(self):
        self.update_bars("daily")

    def update_hourly(self):
        self.update_bars("hourly")

    def update_minute(self):
        self.update_bars("minute")

# CLI support
if __name__ == "__main__":
    manager = DuolDataManager()
    manager.update_daily()
    manager.update_hourly()
    manager.update_minute()
    logging.info("DUOL data update complete")