# VM deployment (week-long paper trading)

After cloning on the VM, the app creates `data/` and `logs/` on first run; the only thing you must add is `.env` with your Alpaca paper API keys.

---

## First run on the VM (step-by-step)

Do these in order so you can catch any issues before leaving the scheduler running.

### 1. Clone and enter the project

```bash
cd ~   # or wherever you want the project
git clone <your-repo-url> alpaca-realtime-trading
cd alpaca-realtime-trading
```

### 2. Create venv and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Add your Alpaca paper API keys

Create a `.env` file in the project root (same folder as `scheduler.py`):

```bash
echo 'APCA_API_KEY_ID=your_key_here' >> .env
echo 'APCA_API_SECRET_KEY=your_secret_here' >> .env
```

Or copy your existing `.env` from your laptop (e.g. with `scp`). Never commit this file.

### 4. (Optional) Set timezone for market hours

If the VM is not in Central time and you want 9:30am–4pm ET:

```bash
sudo timedatectl set-timezone America/Chicago
```

### 5. Do a one-time test run (recommended)

Run the scheduler in the foreground so you see output and any errors. It will run one refresh immediately, then wait for the next :05 past the hour.

```bash
source venv/bin/activate
python scheduler.py
```

**What to look for:**

- **During market hours:** You should see `--- Refresh triggered ---`, then log lines with `Action: BUY | ...` or `Action: HOLD | ...` or `Action: SELL | ...`, and no Python tracebacks.
- **Outside market hours:** You should see `Outside market hours, skipping refresh` and no errors.

If you see `ModuleNotFoundError` or import errors, fix the venv/install. If you see Alpaca auth errors, fix `.env`. When it looks good, stop with `Ctrl+c`.

### 6. Start the scheduler in tmux (long-running)

```bash
tmux new -s trading
source venv/bin/activate
python scheduler.py
```

You should see the same “Scheduler started…” and one immediate refresh. Detach with **`Ctrl+b`** then **`d`**. The process keeps running.

### 7. Verify everything is running as expected

**From the VM (in a new SSH session or after reattaching):**

| Check | Command / action |
|-------|-------------------|
| Scheduler is still running | `tmux ls` → you should see `trading` in the list. Reattach with `tmux attach -t trading` to see live output. |
| Refresh is being attempted each hour | `tail -20 logs/scheduler.log` — look for `--- Refresh triggered ---` or `Outside market hours, skipping refresh` with recent timestamps. |
| Data is being fetched | `tail -20 logs/data_updates.log` — look for “Updating daily/hourly bars” and “Updated … bars: N new rows”. |
| DuckDB and parquet exist | `ls -la data/` and `ls data/daily data/hourly` — you should see `trading.duckdb` and `duol_daily.parquet`, `duol_hourly.parquet` after at least one refresh. |

**Outside the VM:**

- Open your **Alpaca paper trading dashboard** and confirm:
  - Orders (if any) show up under Paper account.
  - Positions and cash look correct.

If any of these fail, check `logs/scheduler.log` and `logs/data_updates.log` for errors (e.g. API keys, network, or missing tables).

---

## Reference

- **Tmux:** Detach = `Ctrl+b` then `d`. Reattach = `tmux attach -t trading`. Kill session = reattach, `Ctrl+c`, then `tmux kill-session -t trading`.
- **Data:** Scheduler creates `data/` and `logs/` on first run. To reset: delete `data/trading.duckdb` and the parquet files in `data/daily`, `data/hourly`; they will be re-downloaded from Alpaca.

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
