import duckdb
import pandas as pd
from datetime import datetime

DB_PATH = "data/trading.duckdb"

def fetch_duol_bars(timeframe: str = "daily",
                     start_date: datetime = None,
                     end_date: datetime = None) -> pd.DataFrame:
    """
    Fetch DUOL bars from DuckDB and return a clean pandas DataFrame.
    
    Parameters:
        timeframe (str): "daily", "hourly", or "minute"
        start_date (datetime, optional): start of date range
        end_date (datetime, optional): end of date range
        
    Returns:
        pd.DataFrame: sorted DataFrame with timestamp as datetime
    """
    con = duckdb.connect(DB_PATH)
    table_name = f"{timeframe}_duol"
    
    query = f"SELECT * FROM {table_name}"
    
    if start_date and end_date:
        query += f" WHERE timestamp BETWEEN '{start_date}' AND '{end_date}'"
    elif start_date:
        query += f" WHERE timestamp >= '{start_date}'"
    elif end_date:
        query += f" WHERE timestamp <= '{end_date}'"
    
    query += " ORDER BY timestamp"
    
    df = con.execute(query).fetchdf()
    
    # Ensure timestamp column is datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Reset index
    df = df.reset_index(drop=True)
    
    return df

# ------------------------
# Example usage
# ------------------------
if __name__ == "__main__":
    # Fetch daily bars for 2023
    df_daily = fetch_duol_bars(
        timeframe="daily",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31)
    )
    print(df_daily.head())
