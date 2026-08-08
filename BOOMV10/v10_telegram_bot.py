import sqlite3
import time
import datetime
from notifier import TelegramNotifier

DB_PATH = r"C:\Users\sahar\.gemini\antigravity\scratch\jil2_os_v9\quant_platform.db"

def start_v10_bot():
    print(f"[{datetime.datetime.now()}] بدء تشغيل بوت V10 (رادار النماذج الكلاسيكية)...")
    notifier = TelegramNotifier()
    
    # Keep track of what we sent today so we don't spam
    # Set of strings: "SYMBOL_PATTERN"
    sent_today = set()
    last_reset_day = datetime.datetime.now().day
    
    while True:
        try:
            current_day = datetime.datetime.now().day
            if current_day != last_reset_day:
                sent_today.clear()
                last_reset_day = current_day
                
            conn = sqlite3.connect(DB_PATH)
            
            # Fetch high probability patterns
            patterns = conn.execute("SELECT symbol, pattern_name, pattern_type, probability, details FROM global_patterns WHERE probability >= 75.0").fetchall()
            
            for row in patterns:
                sym = row[0]
                p_name = row[1]
                p_type = row[2]
                prob = row[3]
                details = row[4]
                
                alert_id = f"{sym}_{p_name}"
                
                if alert_id not in sent_today:
                    icon = "🟢" if p_type == "BULLISH" else "🔴" if p_type == "BEARISH" else "⚪"
                    
                    msg = (
                        f"🌐 *رادار النماذج الفنية (V10)* 🌐\n\n"
                        f"🏢 *السهم:* `{sym}`\n"
                        f"📐 *النموذج:* {p_name}\n"
                        f"🎯 *نسبة الدقة:* `{prob}%`\n"
                        f"{icon} *التصنيف:* {p_type}\n\n"
                        f"💡 *ملاحظة:* {details}"
                    )
                    
                    success = notifier.send_custom_message(msg)
                    if success:
                        print(f"[{datetime.datetime.now()}] أرسلت تنبيه للسهم {sym}")
                        sent_today.add(alert_id)
                    else:
                        print(f"[{datetime.datetime.now()}] فشل في إرسال التنبيه للسهم {sym}")
                        
            conn.close()
        except Exception as e:
            print(f"[{datetime.datetime.now()}] خطأ في بوت V10: {e}")
            
        # Check every 5 minutes
        time.sleep(300)

if __name__ == "__main__":
    start_v10_bot()
