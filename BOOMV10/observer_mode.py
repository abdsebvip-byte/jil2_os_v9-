import sqlite3
import datetime
import yfinance as yf
import pandas as pd
import os

DB_PATH = r"C:\Users\sahar\.gemini\antigravity\scratch\jil2_os_v9\quant_platform.db"

def run_observer_audit():
    print(f"\n[{datetime.datetime.now()}] بدء المراجعة الذاتية (Observer Mode) 🧠")
    print("-" * 50)
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Audit Global Patterns
    print("\n🔍 تدقيق النماذج الكلاسيكية (السوق الكلي):")
    patterns = conn.execute("SELECT symbol, pattern_name, pattern_type, probability, ts_utc FROM global_patterns").fetchall()
    
    if not patterns:
        print("لا توجد نماذج محفوظة للمراجعة.")
    else:
        symbols = [p[0] for p in patterns]
        try:
            # Fetch current/close price for these symbols
            data = yf.download(symbols, period="2d", interval="1d", progress=False)
            
            success_count = 0
            for row in patterns:
                sym = row[0]
                p_name = row[1]
                p_type = row[2]
                prob = row[3]
                
                if isinstance(data.columns, pd.MultiIndex):
                    stock_data = data.xs(sym, level='Ticker', axis=1)
                else:
                    stock_data = data
                    
                stock_data = stock_data.dropna()
                if len(stock_data) >= 2:
                    open_price = stock_data['Open'].iloc[-1]
                    close_price = stock_data['Close'].iloc[-1]
                    
                    change = ((close_price - open_price) / open_price) * 100
                    
                    is_success = False
                    if p_type == "BULLISH" and change > 0: is_success = True
                    elif p_type == "BEARISH" and change < 0: is_success = True
                    elif p_type == "NEUTRAL" and abs(change) > 0.5: is_success = True
                    
                    if is_success: success_count += 1
                    
                    status = "✅ صابت" if is_success else "❌ خابت"
                    print(f"- السهم: {sym} | النموذج: {p_name} | الحركة: {change:+.2f}% | النتيجة: {status}")
            
            if len(patterns) > 0:
                print(f"\n🎯 الدقة الإجمالية لنماذج اليوم: {(success_count/len(patterns))*100:.1f}%")
                
        except Exception as e:
            print("خطأ في جلب الأسعار للتدقيق:", e)

    # 2. Audit Explosive Signals (V9)
    print("\n💥 تدقيق أسهم الانفجار السريع (V9 Radar):")
    # Get today's signals
    today_str = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    signals = conn.execute("SELECT symbol, score, features FROM signals WHERE ts_utc LIKE ? ORDER BY score DESC LIMIT 5", (f"{today_str}%",)).fetchall()
    
    if not signals:
        print("لا توجد إشارات انفجارية مسجلة اليوم.")
    else:
        for row in signals:
            print(f"- السهم: {row[0]} | قوة الانفجار: {row[1]*100:.1f}% | التفاصيل: {row[2][:50]}...")
            
    conn.close()
    print("\n" + "-" * 50)
    print("✅ تمت المراجعة الذاتية بنجاح.")

if __name__ == "__main__":
    run_observer_audit()
