# strategies/crossover.py
import pandas as pd

def compute_signals(daily_df: pd.DataFrame, hourly_df: pd.DataFrame) -> dict:
    """
    Computes SMA crossover (daily) and EMA crossover (hourly).
    Returns a signal dict with trend, momentum, and final action.
    """
    daily = daily_df.copy()
    hourly = hourly_df.copy()

    # Daily SMA — trend direction
    daily['sma20'] = daily['close'].rolling(20).mean()
    daily['sma50'] = daily['close'].rolling(50).mean()
    latest_daily = daily.iloc[-1]
    trend_strength = (latest_daily['sma20'] - latest_daily['sma50']) / latest_daily['sma50']
    # trend = "bull" if latest_daily['sma20'] > latest_daily['sma50'] else "bear"
    trend = "bull" if trend_strength > 0 else "bear"

    # Hourly EMA — entry timing
    hourly['ema12'] = hourly['close'].ewm(span=12).mean() # Faster EMA
    hourly['ema26'] = hourly['close'].ewm(span=26).mean()
    latest_hourly = hourly.iloc[-1]
    momentum_strength = (latest_hourly['ema12'] - latest_hourly['ema26']) / latest_hourly['ema26']
    # momentum = "buy" if latest_hourly['ema10'] > latest_hourly['ema20'] else "sell"
    momentum = "buy" if momentum_strength > 0 else "sell"

    # Volume confirmation
    if len(hourly) >= 10:
        vol_median = hourly['volume'].median()
        volume_ok = latest_hourly['volume'] > vol_median
    else:
        volume_ok = True

    # if len(hourly) >= 20:
        # hourly['vol_avg'] = hourly['volume'].rolling(20).mean()
        # volume_ok = latest_hourly['volume'] > hourly['vol_avg'].iloc[-1]
    # else:
        # volume_ok = True  # Not enough data yet
    # print(f"Hourly rows: {len(hourly)}, volume_ok: {volume_ok}")  # debug

    # hourly['vol_avg'] = hourly['volume'].rolling(20).mean()
    # volume_ok = latest_hourly['volume'] > latest_hourly['vol_avg']

    # Final action — both locks must open
    if trend == "bull" and momentum == "buy": # removed "and volume_ok" 
        action = "BUY"
    elif trend == "bear" and momentum == "sell" and volume_ok:
        action = "SELL"
    else:
        action = "HOLD"

    return {
        "trend": trend,
        "momentum": momentum,
        "volume_ok": volume_ok,
        "action": action,
        "trend_strength": trend_strength,
        "momentum_strength": momentum_strength,
        "latest_close": latest_hourly['close']
        # "sma20": latest_daily['sma20'],
        # "sma50": latest_daily['sma50'],
        # "ema10": latest_hourly['ema10'],
        # "ema20": latest_hourly['ema20'],
    }