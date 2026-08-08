# module: broker_bridge.py
import os
import logging
import requests
from dotenv import load_dotenv

# Initialize logging
logger = logging.getLogger("BrokerBridge")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

class AlpacaBrokerBridge:
    def __init__(self):
        load_dotenv("config.env", override=True)
        self.enabled = os.getenv("AUTO_TRADING_ENABLED", "False").lower() == "true"
        self.key_id = os.getenv("ALPACA_API_KEY_ID", "").strip() or os.getenv("ALPACA_KEY_ID_1", "").strip()
        self.secret_key = os.getenv("ALPACA_API_SECRET_KEY", "").strip() or os.getenv("ALPACA_SECRET_KEY_1", "").strip()
        self.is_paper = os.getenv("ALPACA_IS_PAPER", "True").lower() == "true"
        self.position_size_pct = float(os.getenv("MAX_POSITION_SIZE_PCT", "2.0"))

        if self.is_paper:
            self.base_url = "https://paper-api.alpaca.markets"
        else:
            self.base_url = "https://api.alpaca.markets"

        self.headers = {
            "APCA-API-KEY-ID": self.key_id,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json"
        }

    def get_account_equity(self):
        """
        Fetch the current account equity from Alpaca.
        Falls back to a default value of $100,000 if request fails.
        """
        if not self.key_id or not self.secret_key:
            logger.warning("Alpaca credentials missing. Defaulting mock equity to $100,000.")
            return 100000.0

        url = f"{self.base_url}/v2/account"
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                equity = float(data.get("equity", 100000.0))
                logger.info(f"Alpaca: Account equity retrieved: ${equity:,.2f}")
                return equity
            else:
                logger.error(f"Alpaca: Failed to fetch account: {res.status_code} - {res.text}")
                return 100000.0
        except Exception as e:
            logger.error(f"Alpaca: Connection error while fetching account: {e}")
            return 100000.0

    def place_bracket_order(self, symbol, price, target_pct, stop_loss_pct=5.0):
        """
        Place a bracket order (buy entry, take profit, stop loss) on Alpaca.
        Returns the order dict if successful, None otherwise.
        """
        symbol = symbol.upper().strip()
        if not self.enabled:
            logger.info(f"Alpaca: Auto-trading disabled. Suppressing order for {symbol}.")
            return None

        if not self.key_id or not self.secret_key:
            logger.error(f"Alpaca: Credentials missing. Order for {symbol} aborted.")
            return None

        # 1. Calculate order position size and quantity
        equity = self.get_account_equity()
        risk_amount = equity * (self.position_size_pct / 100.0)
        
        # Calculate quantity (ensure at least 1 share)
        qty = int(risk_amount / price)
        if qty <= 0:
            qty = 1
            
        # 2. Calculate target exit and stop loss prices
        limit_price = round(price, 4)
        take_profit_price = round(price * (1.0 + (target_pct / 100.0)), 2)
        stop_loss_price = round(price * (1.0 - (stop_loss_pct / 100.0)), 2)

        # 3. Build Bracket Order Payload
        payload = {
            "symbol": symbol,
            "qty": qty,
            "side": "buy",
            "type": "limit",
            "time_in_force": "gtc",
            "limit_price": limit_price,
            "order_class": "bracket",
            "take_profit": {
                "limit_price": take_profit_price
            },
            "stop_loss": {
                "stop_price": stop_loss_price,
                "limit_price": stop_loss_price
            }
        }

        url = f"{self.base_url}/v2/orders"
        logger.info(f"Alpaca: Submitting Bracket Order for {symbol} | Qty: {qty} | Entry: ${limit_price} | TP (+{target_pct}%): ${take_profit_price} | SL (-{stop_loss_pct}%): ${stop_loss_price}")

        try:
            res = requests.post(url, json=payload, headers=self.headers, timeout=10)
            if res.status_code in [200, 201]:
                order = res.json()
                logger.info(f"Alpaca: Bracket Order for {symbol} placed successfully! Order ID: {order.get('id')}")
                return order
            else:
                logger.error(f"Alpaca: Order failed: {res.status_code} - {res.text}")
                return None
        except Exception as e:
            logger.error(f"Alpaca: Connection error while placing order: {e}")
            return None
