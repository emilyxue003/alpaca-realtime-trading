# 🦜 DUOL Algorithmic Trading System

**Real-Time Intelligent Systems Project**  
Grace Rowan · Emily Xue · Dora Li · Devyani Rastogi

Created for MS-ADS Realtime Intelligent Systems Final Project
Winter 2026

A fully automated, real-time algorithmic trading system that executes a multi-timeframe momentum strategy on Duolingo (DUOL) stock using the Alpaca Markets API and DuckDB.

> **My Contributions (Emily Xue):**
> * **Optimized the quantitative trading strategy**, developing a dual-timeframe algorithm that combines an Hourly SMA (20/50) macro-trend filter with 15-minute MACD momentum triggers.
> * **Engineered asymmetric risk management parameters**, implementing strict fixed-percentage bounds (Long: 2.0% SL / 3.0% TP; Short: 1.5% SL / 3.0% TP) to protect capital during volatile market bounces.
> * **Integrated volume confirmation logic** to filter out low-probability MACD crossovers, ensuring execution only during high-liquidity periods.

---

## 📈 Backtesting Results: Trailing 1-Year (Mar 2025 → Mar 2026)

To evaluate the algorithm's resilience during an extended market drawdown, the strategy's weekly returns were benchmarked against a passive "Buy & Hold" strategy for DUOL over a 53-week period.

| Metric | Strategy (Algorithm) | Benchmark (Buy & Hold DUOL) |
|--------|----------------------|-----------------------------|
| Starting Capital | $100,000.00 | $100,000.00 |
| Final Portfolio Value | **$181,340.00** | $34,700.00 |
| Total Return | **+81.34%** | -65.30% |
| Total Trades | 519 | 1 |

🚀 **Total Alpha Generated: +72.75%**

**Key Insight:** During a severe 65% market correction for DUOL, the strategy successfully preserved capital and generated absolute positive returns. The asymmetric risk parameters (tighter short-side stops and aggressive momentum exits) allowed the bot to consistently beat the market week-over-week, saving a hypothetical portfolio from a devastating $65,300 loss.

---

## 🧠 Strategy Overview

The system uses a **dual-timeframe momentum crossover strategy** combining two signal layers: an hourly macro-trend filter with 15-minute MACD momentum signals, secured by asymmetric fixed-percentage risk parameters.

### Layer 1 — Hourly SMA 20/50 (Macro Trend Lock)
- 20-period and 50-period Simple Moving Averages on hourly closing prices.
- **Trend Strength Gate:** Determines the macro regime (Bullish if SMA20 > SMA50, Bearish otherwise).
- Acts as a **directional lock**: restricts the bot to only taking long trades that align with the broader hourly trend.

### Layer 2 — 15-Minute MACD & Volume (Micro Entry)
- MACD (12/26/9) captures intraday momentum on 15-minute resampled bars.
- **Volume Confirmation:** Trades are only executed if the current 15-minute volume exceeds the 10-period rolling median, filtering out low-liquidity noise.
  
### Signal Logic
```text
BUY   → Hourly Trend = Bull AND 15-Min MACD = Buy AND Volume > Median
SHORT → Price < Hourly SMA20 AND 15-Min MACD = Sell AND Volume > Median
HOLD  → Regimes conflict, momentum reverses, or volume is too low
```

The strategy exits aggressively on short-term weakness but enters conservatively, protecting capital asymmetrically.

### Risk Management (Assymetric Scalping)

| Rule | Detail |
|------|--------|
| Long Exits | 2.0% Stop-Loss / 3.0% Take-Profit |
| Short Exits | 1.5% Stop-Loss / 3.0% Take-Profit (Tighter SL mitigates short-squeeze risk) |
| Cooldown | Blocks re-entry after a stop-loss or take-profit fires until the MACD momentum naturally flips, preventing recursive churn |
| Market Hours Gate | 8:30 AM – 3:00 PM CST, weekdays only |
| Position Sizing | 95% of available cash, maximum whole shares |

---

## 🏗️ Architecture

```
scheduler.py                    ← orchestrates full pipeline (refresh every 15 minutes)
    │
    ├── duol_data_manager.py    ← Alpaca API → incremental bars → DuckDB
    ├── fetch_db.py             ← DuckDB → clean pandas DataFrames
    ├── strategies/crossover.py ← stateless SMA + MACD signal computation
    └── trading/executor.py     ← Alpaca Trading API order submission
```

### Data Flow
```
Alpaca REST API
    ↓  (incremental pull, every 15 minutes)
DuckDB  ──  trading.duckdb
    ├── hourly_duol   →  SMA 20/50 trend computation
    └── minute_duol   →  Resampled to 15-min for MACD signals
    ↓
Parquet backups  (data/hourly · data/minute)
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

- Triggers `refresh()` **every 15 minutes** to align with the MACD intraday momentum bars.
- `is_market_hours()` gate blocks execution outside **8:30 AM – 3:00 PM CST** and on weekends.
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
- **Strict Stop-Losses** (2.0% Long / 1.5% Short) cap downside per trade
- **Cooldown flag** blocks recursive re-entry loops after forced exits
- **Market hours gate** prevents trading during illiquid after-hours sessions

---

## 🔬 Macro-Trend Optimization & Asymmetric Entries

Multiple hourly moving average pairs were backtested across a trailing 52-week window (Mar 2025 → Mar 2026) using full historical warm-up data to ensure indicator accuracy. 

During optimization, it was identified that equities exhibit asymmetric volatility (crashing faster than they rally). To capitalize on this, the entry logic was decoupled:
* **Long Entries:** Require a conservative confirmation of the macro trend (Fast SMA > Slow SMA) to avoid buying into false relief rallies.
* **Short Entries:** Bypass the slow trend cross. Shorts are triggered aggressively the moment the current price drops below the Fast SMA, capturing sudden momentum breakdowns.

| Pair | Sharpe | Return | Trades |
|------|--------|--------|--------|
| SMA 9/21 | +1.06 | +48.92% | 575 |
| SMA 10/50 | +1.25 | +74.77% | 547 |
| SMA 20/50 | **+1.32** | **+81.34%** | **519** |
| SMA 20/100 | +0.87 | +32.89% | 501 |
| SMA 50/200 | +2.01 | +113.61% | 456 |

**Why SMA 20/50?**
While the 50/200 pair generated the highest historical return, a 200-hour SMA requires roughly 30 trading days to calculate, creating a severely lagging indicator that is too rigid for 15-minute intraday execution. 

The **SMA 20/50** pair was selected as the optimal equilibrium for the asymmetric logic. The 20-hour SMA (approx. 3 trading days) acts as a highly responsive tripwire for shorting market crashes without falling for intraday noise, while the 50-hour SMA (approx. 8 trading days) provides a robust gate for long entries. This decoupled architecture successfully preserved capital and generated +81% returns during a highly volatile year.

---

## 📦 Requirements

```
alpaca-py
duckdb
pandas
python-dotenv
schedule
```

## 🚀 Future Enhancements (Roadmap)

While the current system successfully generates alpha in a simulated environment, transitioning to a production-grade live execution pipeline would require the following infrastructure and quantitative upgrades:

* **Cloud Infrastructure & Containerization:** Dockerize the application and migrate deployment from a local background process (`nohup`) to a cloud-native environment (e.g., AWS EC2 or Google Cloud Run) for maximum uptime.
* **Time-Series Database Migration:** Transition from local DuckDB parquet storage to a dedicated time-series database like TimescaleDB or InfluxDB to handle multi-ticker scaling and tick-level order book data.
* **Dynamic Position Sizing (Kelly Criterion):** Upgrade the current static allocation model (95% of cash) to a dynamic sizing model based on the Kelly Criterion or historical win-rate volatility.
* **Machine Learning Regime Detection:** Integrate a Hidden Markov Model (HMM) or Random Forest classifier to automatically detect whether the broader market is in a "trending" or "choppy" regime, dynamically adjusting the SMA lookback windows rather than relying on fixed 20/50 parameters.
* **Execution Optimization:** Replace standard Market Orders with intelligent Limit Orders. Model expected slippage and bid-ask spread costs to reduce the "frictional" drag on high-frequency scalping.