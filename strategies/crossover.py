# strategies/crossover.py
import pandas as pd

def compute_signals(daily_df: pd.DataFrame, hourly_df: pd.DataFrame, entry_price: float = None) -> dict:
    """
    Computes SMA crossover (daily) and EMA crossover (hourly).
    Returns a signal dict with trend, momentum, and final action.
    """
    daily = daily_df.copy()
    hourly = hourly_df.copy()

    # Daily SMA — trend direction
    daily['sma9'] = daily['close'].ewm(span=9).mean()
    daily['sma21'] = daily['close'].ewm(span=21).mean()
    latest_daily = daily.iloc[-1]
    trend_strength = (latest_daily['sma9'] - latest_daily['sma21']) / latest_daily['sma21']
    # trend = "bull" if latest_daily['sma20'] > latest_daily['sma50'] else "bear"
    trend = "bull" if trend_strength > 0 else "bear"

    # Hourly EMA — entry timing
    hourly['ema12'] = hourly['close'].ewm(span=12).mean() # Faster EMA
    hourly['ema26'] = hourly['close'].ewm(span=26).mean()
    hourly['macd'] = hourly['ema12'] - hourly['ema26'] # Raw momentum (MACD Line)
    hourly['macd_signal'] = hourly['macd'].ewm(span=9).mean() # 9-period EMA (Signal Line)
    latest_hourly = hourly.iloc[-1]
    momentum_strength = latest_hourly['macd'] - latest_hourly['macd_signal']
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

    latest_close = latest_hourly['close']
    stop_loss_triggered = False
    take_profit_triggered = False

    if entry_price is not None:
        # Hard Stop Loss Logic (5% drop)
        if latest_close <= (entry_price * 0.95):
            stop_loss_triggered = True
            
        # 2. NEW LOGIC: Take Profit (6% gain)
        if latest_close >= (entry_price * 1.06):
            take_profit_triggered = True

    # Final action — both locks must open
    if stop_loss_triggered:
        action = "SELL"
        momentum = "stop_loss" # Flag this to see it in the logs
    elif take_profit_triggered:
        action = "SELL"
        momentum = "take_profit" # Flag this to see the wins in the logs
    elif momentum == "sell":
        if volume_ok:
            action = "SELL" # Prioritize getting out if ST momentum breaks
        else:
            action = "HOLD" # Don't sell yet, but definitely don't buy
    elif trend == "bull" and momentum == "buy": # removed "and volume_ok"
        action = "BUY"
    else:
        action = "HOLD"

    return {
        "trend": trend,
        "momentum": momentum,
        "volume_ok": volume_ok,
        "action": action,
        "trend_strength": trend_strength,
        "momentum_strength": momentum_strength,
        "latest_close": latest_close
        # "sma20": latest_daily['sma20'],
        # "sma50": latest_daily['sma50'],
        # "ema10": latest_hourly['ema10'],
        # "ema20": latest_hourly['ema20'],
    }