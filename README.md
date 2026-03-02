# Alpaca Real-Time Trading System

A Python-based real-time trading system using the Alpaca API for live market data and automated execution.

Created for MS-ADS Realtime Intelligent Systems Final Project
Winter 2026

scheduler.py          orchestrates everything, runs on loop
    ↓ calls
duol_data_manager.py  pulls fresh hourly bars → DuckDB
fetch_db.py           reads DuckDB → DataFrames
strategies/crossover.py  computes SMA + EMA signals
trading/executor.py   submits buy/sell orders to Alpaca

Current Trading Logic:
BUY  → Daily SMA20 > SMA50  AND  Hourly EMA10 > EMA20  AND  Volume > avg
SELL → Daily SMA20 < SMA50  AND  Hourly EMA10 < EMA20
HOLD → Signals conflict or volume is insufficient