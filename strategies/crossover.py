# strategies/crossover.py
import pandas as pd

def compute_signals(hourly_df: pd.DataFrame, fifteen_df: pd.DataFrame, entry_price: float = None, position: int = 0) -> dict:
    """
    Computes SMA crossover (hourly) and EMA crossover (15-minute).
    Returns a signal dict with trend, momentum, and final action.
    """
    hourly = hourly_df.copy()
    fifteen = fifteen_df.copy()

    # 1. Hourly SMA — Macro Trend
    hourly['sma9'] = hourly['close'].rolling(9).mean()
    hourly['sma21'] = hourly['close'].rolling(21).mean()
    latest_hourly = hourly.iloc[-1]
    trend_strength = (latest_hourly['sma9'] - latest_hourly['sma21']) / latest_hourly['sma21']
    trend = "bull" if trend_strength > 0 else "bear"

    # 2. 15-Minute EMA — Micro Momentum
    fifteen['ema12'] = fifteen['close'].ewm(span=12).mean() 
    fifteen['ema26'] = fifteen['close'].ewm(span=26).mean()
    fifteen['macd'] = fifteen['ema12'] - fifteen['ema26'] 
    fifteen['macd_signal'] = fifteen['macd'].ewm(span=9).mean() 
    latest_fifteen = fifteen.iloc[-1]
    momentum_strength = latest_fifteen['macd'] - latest_fifteen['macd_signal']
    momentum = "buy" if momentum_strength > 0 else "sell"

    # 3. Volume Confirmation (Checked against 15-min median)
    if len(fifteen) >= 10:
        vol_median = fifteen['volume'].median()
        volume_ok = latest_fifteen['volume'] > vol_median
    else:
        volume_ok = True

    latest_close = latest_fifteen['close']
    stop_loss_triggered = False
    take_profit_triggered = False

    # 4. Strict Risk Management (Scalping Parameters)
    if entry_price is not None and position != 0:
        if position > 0: 
            # LONG EXITS (2% SL, 3% TP)
            if latest_close <= (entry_price * 0.98): stop_loss_triggered = True 
            if latest_close >= (entry_price * 1.03): take_profit_triggered = True  
        elif position < 0:
            # SHORT EXITS (1.5% SL, 3% TP)
            if latest_close >= (entry_price * 1.015): stop_loss_triggered = True  
            if latest_close <= (entry_price * 0.97): take_profit_triggered = True  

    # 5. Final Action Logic
    if stop_loss_triggered:
        action = "SELL" if position > 0 else "COVER"
        momentum = "stop_loss"
    elif take_profit_triggered:
        action = "SELL" if position > 0 else "COVER"
        momentum = "take_profit"
    elif position > 0 and momentum == "sell" and volume_ok:
        action = "SELL"   
    elif position < 0 and momentum == "buy" and volume_ok:
        action = "COVER"  
    elif position == 0:
        if trend == "bull" and momentum == "buy":
            action = "BUY"    
        elif trend == "bear" and momentum == "sell":
            action = "SHORT"  
        else:
            action = "HOLD"
    else:
        action = "HOLD"

    return {
        "trend": trend,
        "momentum": momentum,
        "volume_ok": volume_ok,
        "action": action,
        "latest_close": latest_close
    }