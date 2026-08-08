# module: notifier.py
import requests
import os
import logging

class TelegramNotifier:
    def __init__(self):
        self.token = None
        self.chat_id = None
        self.load_credentials()

    def load_credentials(self):
        """
        Loads credentials from environment variables, config.env, or streamlit secrets.
        """
        # 1. Load from environment variables (standard for Docker / Render)
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if self.token and self.chat_id:
            return

        # 2. Try loading from Streamlit secrets
        try:
            import streamlit as st
            if "TELEGRAM_BOT_TOKEN" in st.secrets:
                self.token = st.secrets["TELEGRAM_BOT_TOKEN"]
                self.chat_id = st.secrets["TELEGRAM_CHAT_ID"]
                return
        except:
            pass

        # 3. Try loading from local config.env file
        if os.path.exists("config.env"):
            with open("config.env", "r") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        parts = line.strip().split("=")
                        if len(parts) == 2:
                            key, val = parts[0].strip(), parts[1].strip()
                            if key == "TELEGRAM_BOT_TOKEN":
                                self.token = val
                            elif key == "TELEGRAM_CHAT_ID":
                                self.chat_id = val

    def send_breakout_alert(self, symbol, price, change, rvol, score, confidence):
        """
        Sends formatted buy signal alerts to Abu Faisal's Telegram.
        """
        if not self.token or not self.chat_id:
            logging.warning("TelegramNotifier: Credentials not loaded.")
            return False

        # --- PM ARCHITECTURE UPGRADE: 1. Fix Price Lag ---
        # Fetch real-time tick just before sending to ensure 100% precision
        try:
            import yahooquery as yq
            t = yq.Ticker(symbol)
            rt_price = t.price[symbol].get('regularMarketPrice', price) if isinstance(t.price, dict) and symbol in t.price else price
            if rt_price > 0:
                price = rt_price # Use the real-time price instead of scanner snapshot
        except Exception as e:
            logging.warning(f"Failed to fetch real-time tick for {symbol}: {e}")

        # --- PM ARCHITECTURE UPGRADE: 4. Time Stop Warning ---
        message = (
            f"🎯 *فرصة انفجار سعري مكتشفة!*\n\n"
            f"🏢 *رمز السهم:* `{symbol}`\n"
            f"💵 *السعر الحالي (لحظي):* `${price:.4f}`\n"
            f"📈 *التغير اليومي:* `+{change:.2f}%`\n"
            f"🔊 *الحجم النسبي RVOL:* `{rvol:.2f}x`\n\n"
            f"🔥 *نسبة تطابق الخوارزمية:* `{score}%`\n"
            f"⭐ *مؤشر ثقة السيولة (ML):* `{confidence}/10`\n\n"
            f"⏱️ *صلاحية التوصية:* `10 دقائق فقط` (Time Stop)\n"
            f"⚠️ *ملاحظة:* إذا لم ينفجر السهم فوراً، قم بإلغاء الصفقة لتحرير السيولة."
        )

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=8)
            if response.status_code == 200:
                logging.info(f"TelegramNotifier: Alert sent for {symbol}")
                return True
            else:
                logging.error(f"TelegramNotifier: Failed to send. HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            logging.error(f"TelegramNotifier: Connection error: {str(e)}")
            return False

    def send_custom_message(self, text):
        """
        Sends a general custom Markdown text message to the channel.
        """
        if not self.token or not self.chat_id:
            logging.warning("TelegramNotifier: Credentials not loaded.")
            return False
            
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            response = requests.post(url, json=payload, timeout=8)
            if response.status_code == 200:
                return True
            else:
                logging.error(f"TelegramNotifier: Custom message failed. HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            logging.error(f"TelegramNotifier Custom Message Error: {e}")
            return False

