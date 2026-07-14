# module: notifier.py
import requests
import os

class TelegramNotifier:
    def __init__(self):
        self.token = None
        self.chat_id = None
        self.load_credentials()

    def load_credentials(self):
        """
        Loads credentials from config.env or streamlit secrets.
        """
        # محاولة التحميل من إعدادات سحابة Streamlit أولاً
        try:
            import streamlit as st
            if "TELEGRAM_BOT_TOKEN" in st.secrets:
                self.token = st.secrets["TELEGRAM_BOT_TOKEN"]
                self.chat_id = st.secrets["TELEGRAM_CHAT_ID"]
                return
        except:
            pass

        # محاولة التحميل من ملف config.env المحلي
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
            print("TelegramNotifier: Credentials not loaded.")
            return False

        message = (
            f"🎯 *فرصة انفجار سعري مكتشفة!*\n\n"
            f"🏢 *رمز السهم:* `{symbol}`\n"
            f"💵 *السعر الحالي:* `${price:.4f}`\n"
            f"📈 *التغير اليومي:* `+{change:.2f}%`\n"
            f"🔊 *الحجم النسبي RVOL:* `{rvol:.2f}x`\n\n"
            f"🔥 *نسبة تطابق الخوارزمية:* `{score}%`\n"
            f"⭐ *مؤشر ثقة السيولة (ML):* `{confidence}/10`\n\n"
            f"⚠️ *ملاحظة:* هذه محاكاة تداول حية للحفاظ على رأس مالك."
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
                print(f"TelegramNotifier: Alert sent for {symbol}")
                return True
            else:
                print(f"TelegramNotifier: Failed to send. HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            print(f"TelegramNotifier: Connection error: {str(e)}")
            return False
