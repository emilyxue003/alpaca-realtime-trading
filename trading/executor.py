# trading/executor.py
import logging
import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from dotenv import load_dotenv

load_dotenv()

class TradeExecutor:
    def __init__(self):
        self.client = TradingClient(
            os.getenv("APCA_API_KEY_ID"),
            os.getenv("APCA_API_SECRET_KEY"),
            paper=True  # ← paper trading, flip to False when ready
        )
        self.symbol = "DUOL"

    def get_position(self):
        """Returns current position qty and average entry price."""
        try:
            pos = self.client.get_open_position(self.symbol)
            return float(pos.qty), float(pos.avg_entry_price)
        except Exception:
            return 0, None

    def get_cash(self):
        """Returns the current available cash in the Alpaca account."""
        try:
            account = self.client.get_account()
            return float(account.cash)
        except Exception as e:
            logging.error(f"Failed to fetch account balance: {e}")
            return 0.0

    def buy(self, qty):
        try:
            order = MarketOrderRequest(
                symbol=self.symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            self.client.submit_order(order)
            logging.info(f"BUY order submitted: {qty} share(s) of {self.symbol}")
        except Exception as e:
            logging.error(f"BUY failed: {e}")

    def sell(self, qty):
        try:
            order = MarketOrderRequest(
                symbol=self.symbol,
                qty=qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )
            self.client.submit_order(order)
            logging.info(f"SELL order submitted: {qty} share(s) of {self.symbol}")
        except Exception as e:
            logging.error(f"SELL failed: {e}")