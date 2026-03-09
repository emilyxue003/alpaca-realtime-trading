# 🦜 DUOL Algorithmic Trading System

**Real-Time Intelligent Systems Project**  
Grace Rowan · Emily Xue · Dora Li · Devyani Rastogi

Created for MS-ADS Realtime Intelligent Systems Final Project
Winter 2026

A fully automated, real-time algorithmic trading system that executes a multi-timeframe momentum strategy on Duolingo (DUOL) stock using the Alpaca Markets API and DuckDB.

---

## 📈 Backtesting Results

| Metric | Value |
|--------|-------|
| Backtest Period | Aug 2021 → Mar 2026 |
| Starting Capital | $100,000 |
| Final Portfolio Value | $226,442.33 |
| Total Return | **+126.4%** |
| Total Trades | 300 |

---

## 🧠 Strategy Overview

The system uses a **multi-timeframe moving average crossover strategy** combining two independent signal layers:

### Layer 1 — Daily SMA 9/21 (Macro Trend)
- 9-day and 21-day Simple Moving Averages on daily closing prices
- Golden Cross (SMA9 > SMA21) → bullish regime → bias long
- Death Cross (SMA9 < SMA21) → bearish regime → stay flat
- Acts as a **gate**: sets the macro trend direction before any trade is considered

### Layer 2 — Hourly MACD (Entry Timing)
- 12/26-period EMA difference smoothed with a 9-period signal line
- Captures intraday momentum and acceleration on hourly bars
- More responsive than SMA for DUOL's 67% annualized volatility
- Acts as a **trigger**: confirms precise entry and exit timing

### Signal Logic
```
BUY  → Daily SMA9 > SMA21 (bull) AND Hourly MACD > Signal AND Volume > median
SELL → Hourly MACD < Signal AND Volume confirms  (no need to wait for daily)
HOLD → Signals conflict or insufficient volume
```

The strategy exits aggressively on short-term weakness but enters conservatively, protecting capital asymmetrically.

### Risk Management

| Rule | Detail |
|------|--------|
| Stop-Loss | 5% below entry price |
| Take-Profit | 6% above entry price |
| Cooldown | Blocks re-entry after stop/take-profit fires until MACD resets |
| Market Hours Gate | 8:30 AM – 3:00 PM CST, weekdays only |
| Position Sizing | 95% of available cash, maximum whole shares |

---

## 🏗️ Architecture

```
scheduler.py                    ← orchestrates full pipeline (hourly at :05)
    │
    ├── duol_data_manager.py    ← Alpaca API → incremental bars → DuckDB
    ├── fetch_db.py             ← DuckDB → clean pandas DataFrames
    ├── strategies/crossover.py ← stateless SMA + MACD signal computation
    └── trading/executor.py     ← Alpaca Trading API order submission
```

### Data Flow
```
Alpaca REST API
    ↓  (incremental pull, hourly)
DuckDB  ──  trading.duckdb
    ├── daily_duol    →  SMA 9/21 trend computation
    ├── hourly_duol   →  MACD signal computation
    └── minute_duol   →  granular reference data
    ↓
Parquet backups  (data/daily · data/hourly · data/minute)
```

---

## 📁 Project Structure

```
alpaca-realtime-trading/
├── deploy/
│   ├── README.md                    # deployment instructions
│   └── alpaca-scheduler.service     # systemd service for background execution
├── notebooks/
│   └── EDA.ipynb                    # exploratory analysis, parameter selection
├── strategies/
│   └── crossover.py                 # SMA + MACD signal computation
├── trading/
│   └── executor.py                  # Alpaca order execution wrapper
├── .gitignore
├── README.md
├── backtest.py                      # historical backtesting loop
├── backtest_results.txt             # backtest output log
├── duol_data_manager.py             # data pipeline: Alpaca → DuckDB
├── fetch_db.py                      # DuckDB → pandas query utility
├── main.py                          # manual one-time trigger
├── requirements.txt
├── reset_db.py                      # wipes and rebuilds DuckDB from scratch
├── scheduler.py                     # autonomous hourly scheduling loop
└── .env                             # API keys (never committed)
```

---

## ⚙️ Setup

### 1. Clone the repository
```bash
git clone https://github.com/gkrowan/alpaca-realtime-trading.git
cd alpaca-realtime-trading
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API keys
Create a `.env` file in the project root using **paper trading** credentials from [paper.alpaca.markets](https://paper.alpaca.markets):
```
APCA_API_KEY_ID=your_paper_key
APCA_API_SECRET_KEY=your_paper_secret
```

### 4. Initialize historical data
```bash
python duol_data_manager.py
```
Fetches all DUOL bars from IPO (July 28, 2021) to present and stores them in DuckDB.

### 5. Verify data
```bash
python fetch_db.py
```

### 6. Run the system

**Foreground (development/testing):**
```bash
python scheduler.py
```

**Background (production — survives terminal close):**
```bash
nohup python -u scheduler.py &
```

**Monitor live logs:**
```bash
tail -f logs/scheduler.log
```

---

## 🔁 Scheduler Behavior

- Triggers `refresh()` at **:05 past every hour** — waits for the previous bar to fully close
- `is_market_hours()` gate blocks execution outside **8:30 AM – 3:00 PM CST** and on weekends
- Every signal evaluation and trade action is written to `logs/scheduler.log`
- Runs indefinitely in the background via `nohup` or as a `systemd` service (see `deploy/`)

---

## 🔄 Resetting the Database

If you need to wipe and rebuild DuckDB from scratch (e.g. after a schema change or corruption):
```bash
python reset_db.py
python duol_data_manager.py
```

---

## 📊 Monitoring

**Local logs:**
```bash
tail -f logs/scheduler.log
```
Each entry records: timestamp · action · daily trend · hourly momentum · latest close · cooldown status

**Alpaca Paper Dashboard:**  
[paper.alpaca.markets](https://paper.alpaca.markets) — live portfolio value, buying power, trade history

---

## 🔒 Compliance & Safety

- API credentials stored in `.env`, never hard-coded or committed to version control
- `paper=True` in `executor.py` by default — prevents accidental live money execution
- **5% stop-loss** caps downside per trade
- **Cooldown flag** blocks recursive re-entry loops after forced exits
- **Market hours gate** prevents trading during illiquid after-hours sessions

---

## 🔬 SMA Parameter Selection

Multiple window pairs were backtested on full DUOL history before selecting 9/21:

| Pair | Sharpe | Return | Trades |
|------|--------|--------|--------|
| SMA 10/50 | -0.35 | -86.7% | 33 |
| SMA 20/50 | -0.09 | -71.4% | 27 |
| SMA 20/100 | +0.09 | -49.6% | 12 |
| SMA 50/200 | +0.20 | -26.3% | 6 |

Longer windows improve Sharpe but generate too few signals for a short evaluation window. **SMA 9/21** balances reactivity with noise filtering — fast enough to generate actionable trades, robust enough to avoid excessive whipsawing on DUOL's 67% annualized volatility.

---

## 📦 Requirements

```
alpaca-py
duckdb
pandas
python-dotenv
schedule
```
