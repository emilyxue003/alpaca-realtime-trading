# VM deployment (week-long paper trading)

## Checklist

1. **Python & venv**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Secrets**
   - Copy `.env` to the VM (or set `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` in the environment).
   - Do not commit `.env`; the repo already ignores it.

3. **Timezone**
   - Market-hours logic in `scheduler.py` uses **local** time with hours 8:30–15:00 (CST).
   - Set the VM timezone to Central if you want 9:30–4pm ET:
     ```bash
     sudo timedatectl set-timezone America/Chicago
     ```
   - Or use a different timezone and adjust the hour constants in `is_market_hours()`.

4. **Run in tmux (recommended)**
   - Start a named session and run the scheduler:
     ```bash
     cd /path/to/alpaca-realtime-trading
     tmux new -s trading
     source venv/bin/activate
     python scheduler.py
     ```
   - **Detach** (session keeps running): `Ctrl+b` then `d`.
   - **Reattach** later to check output: `tmux attach -t trading`.
   - **Kill** the session when done: attach, then `Ctrl+c` to stop the script, then `exit` or `tmux kill-session -t trading`.
   - Logs are in `logs/scheduler.log` and `logs/data_updates.log` even when detached.

5. **Data**
   - `DuolDataManager` and the scheduler create `data/` and `logs/` on first run.
   - For a clean start you can remove `data/trading.duckdb` and parquet files; they will be recreated from Alpaca.

## Alternative: systemd

To run as a service (survives reboots, auto-restart), use `deploy/alpaca-scheduler.service`. Edit the unit file for your user and paths, then:

```bash
sudo cp deploy/alpaca-scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable alpaca-scheduler
sudo systemctl start alpaca-scheduler
```

## Quick health check

- `curl` or browser to Alpaca paper dashboard to confirm orders/positions.
- `tail -f logs/scheduler.log` to confirm hourly runs and “market hours” skips on weekends/night.
