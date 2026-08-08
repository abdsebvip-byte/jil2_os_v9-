import yahooquery as yq
import pandas as pd
from datetime import datetime
import sqlite3
import os

def detect_whales_and_store():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] بدء المسح الاستخباراتي لاصطياد الهوامير (Whale Accumulation Scan)...")
    try:
        screener = yq.Screener()
        data = screener.get_screeners(screen_ids=['most_actives', 'day_gainers', 'small_cap_gainers'], count=100)
        
        candidates = []
        seen = set()
        
        for key in data.keys():
            if isinstance(data[key], dict) and 'quotes' in data[key]:
                for q in data[key]['quotes']:
                    sym = q.get('symbol')
                    if not sym or sym in seen: continue
                    seen.add(sym)
                    
                    price = q.get('regularMarketPrice', 0)
                    change = q.get('regularMarketChangePercent', 0)
                    vol = q.get('regularMarketVolume', 0)
                    avg_vol = q.get('averageDailyVolume3Month', 1) 
                    
                    if avg_vol == 0: avg_vol = 1
                    
                    rvol = vol / avg_vol
                    market_cap = q.get('marketCap', 0)
                    
                    # Criteria: Low Cap, High RVOL, positive change (Removed arbitrary FOMO caps!)
                    if rvol >= 2.0 and change >= 2.0 and market_cap < 500_000_000:
                        reason = f"تضاعفت سيولته {rvol:.1f} أضعاف بشكل مريب مع ارتفاع (+{change:.1f}%)"
                        candidates.append({
                            'Symbol': sym,
                            'Price': price,
                            'Change%': round(change, 1),
                            'RVOL': round(rvol, 1),
                            'MarketCap': market_cap,
                            'Reason': reason
                        })
                        
        if candidates:
            candidates = sorted(candidates, key=lambda x: x['RVOL'], reverse=True)
            conn = sqlite3.connect('quant_platform.db')
            cursor = conn.cursor()
            
            # Clear old alerts for the day (to keep the table clean for Streamlit)
            cursor.execute("DELETE FROM whale_alerts")
            
            now_str = datetime.now().isoformat()
            telegram_msg = "🚨 *رادار الحيتان (قائمة توقعات الغد)* 🚨\n\n"
            
            for c in candidates[:5]:
                cursor.execute('''
                    INSERT INTO whale_alerts (symbol, ts, price, change_pct, rvol, market_cap, reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (c['Symbol'], now_str, c['Price'], c['Change%'], c['RVOL'], c['MarketCap'], c['Reason']))
                
                telegram_msg += (
                    f"🏢 *{c['Symbol']}*\n"
                    f"💵 السعر: `${c['Price']}` (+{c['Change%']}%)\n"
                    f"💡 *السبب:* {c['Reason']}\n\n"
                )
                
            conn.commit()
            conn.close()
            
            telegram_msg += "⚠️ *ملاحظة:* هذه أسهم استباقية مرجح انفجارها غداً أو بعد الإغلاق. جهزها للمراقبة ولا تدخل بشكل أعمى."
            
            # Send to Telegram via notifier
            from notifier import TelegramNotifier
            notif = TelegramNotifier()
            notif.send_custom_message(telegram_msg)
            
            print(f"تم تخزين {len(candidates[:5])} أسهم وإرسال تقرير التلجرام.")
        else:
            print("\nهدوء تام.. لم يتم رصد سيولة تجميعية غير مألوفة.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    detect_whales_and_store()
