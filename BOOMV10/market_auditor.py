import time
import os
from datetime import datetime, date
import yahooquery as yq
from database import QuantDatabase
import traceback

ARTIFACT_PATH = r"C:\Users\sahar\.gemini\antigravity\brain\09dfacce-6dd5-4f15-946b-62ee586e69a9\end_of_day_audit_report.md"

def fetch_market_gainers():
    try:
        screener = yq.Screener()
        data = screener.get_screeners(screen_ids=['day_gainers', 'small_cap_gainers'], count=50)
        gainers = {}
        for key in ['day_gainers', 'small_cap_gainers']:
            if key in data and isinstance(data[key], dict):
                quotes = data[key].get('quotes', [])
                for q in quotes:
                    sym = q.get('symbol')
                    if sym and sym.isalpha():
                        gainers[sym] = {
                            "price": q.get('regularMarketPrice', 0),
                            "change": q.get('regularMarketChangePercent', 0),
                            "dayHigh": q.get('regularMarketDayHigh', 0),
                            "volume": q.get('regularMarketVolume', 0)
                        }
        return gainers
    except Exception as e:
        print(f"Error fetching gainers: {e}")
        return {}

def run_audit():
    db = QuantDatabase()
    today = date.today().strftime("%Y-%m-%d")
    
    # 1. Get all ACCEPTED traces today
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT symbol, price, change, evaluated_at, score, rvol 
            FROM evaluation_trace 
            WHERE status='ACCEPTED' AND date(evaluated_at) = ?
        """, (today,))
        accepted_rows = c.fetchall()
        
        c.execute("""
            SELECT symbol, price, change, evaluated_at, rejection_reason 
            FROM evaluation_trace 
            WHERE status='REJECTED' AND date(evaluated_at) = ?
        """, (today,))
        rejected_rows = c.fetchall()

    accepted_data = {}
    for r in accepted_rows:
        sym = r[0]
        if sym not in accepted_data or r[3] < accepted_data[sym]['time']: # keep earliest
            accepted_data[sym] = {'price': r[1], 'change': r[2], 'time': r[3], 'score': r[4], 'rvol': r[5]}
            
    rejected_data = {}
    for r in rejected_rows:
        sym = r[0]
        if sym not in rejected_data:
            rejected_data[sym] = []
        rejected_data[sym].append({'price': r[1], 'change': r[2], 'time': r[3], 'reason': r[4]})

    gainers = fetch_market_gainers()
    
    report_lines = [
        "# 📊 التقرير الرقابي لمدير المشروع (Live Audit Report)",
        f"**آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "> [!IMPORTANT]",
        "> هذا التقرير يتم تحديثه تلقائياً في الخلفية كل 15 دقيقة لمراقبة أداء المنصة.",
        "",
        "## 1. التوصيات الناجحة والفاشلة (True/False Positives)",
        "الأسهم التي رشحتها المنصة (ACCEPTED) اليوم ومتابعة أدائها بعد التوصية:",
        ""
    ]
    
    if not accepted_data:
        report_lines.append("*لم تقم المنصة باختيار أي سهم كفرصة مقبولة حتى الآن.*")
    else:
        report_lines.append("| السهم | وقت الرصد | السيولة (RVOL) | الدخول | أعلى سعر | الربح | التقييم |")
        report_lines.append("|---|---|---|---|---|---|---|")
        for sym, d in accepted_data.items():
            if sym in gainers:
                day_high = gainers[sym]['dayHigh']
                current_price = gainers[sym]['price']
            else:
                try:
                    t = yq.Ticker(sym)
                    day_high = t.price[sym].get('regularMarketDayHigh', d['price']) if isinstance(t.price, dict) and sym in t.price else d['price']
                    current_price = t.price[sym].get('regularMarketPrice', d['price']) if isinstance(t.price, dict) and sym in t.price else d['price']
                except:
                    day_high = d['price']
                    current_price = d['price']
            
            day_high = max(day_high, d['price']) # Safe fallback
            gain_pct = ((day_high - d['price']) / d['price']) * 100
            
            # Strict PM rules: 10% is a failure. Must be > 40% and hold highs.
            if gain_pct >= 40 and current_price >= d['price']:
                eval_str = "🚀 انفجار حقيقي"
            elif gain_pct >= 40 and current_price < d['price']:
                eval_str = "⚠️ انفجر ثم انهار للسالب"
            elif gain_pct >= 15 and current_price >= d['price']:
                eval_str = "✅ صعود متوسط (وليس انفجار)"
            else:
                eval_str = "❌ فاشل (تلاشى أو لم ينفجر)"
                
            time_str = d['time'].split('T')[1][:5] if 'T' in d['time'] else d['time'][:5]
            report_lines.append(f"| **{sym}** | {time_str} | {d.get('rvol', 0):.1f}x | ${d['price']} | ${day_high} | +{gain_pct:.1f}% | {eval_str} |")
            
    report_lines.extend([
        "",
        "## 2. الفرص الضائعة (False Negatives)",
        "الأسهم التي انفجرت في السوق اليوم ولماذا لم ترشحها المنصة:",
        ""
    ])
    
    missed_count = 0
    if gainers:
        report_lines.append("| السهم | التغير الحالي | هل رصدته المنصة؟ | سبب الاستبعاد (لماذا فاتنا؟) |")
        report_lines.append("|---|---|---|---|")
        for sym, data in sorted(gainers.items(), key=lambda x: x[1]['change'], reverse=True)[:15]:
            if data['change'] < 20: continue # Only care about big gainers
            if sym in accepted_data:
                continue # Caught it
                
            missed_count += 1
            if sym in rejected_data:
                reasons = [r['reason'] for r in rejected_data[sym]]
                primary_reason = reasons[-1] if reasons else "غير معروف"
                short_reason = primary_reason.split("—")[0].strip()
                report_lines.append(f"| {sym} | +{data['change']:.1f}% | 🟡 تم الرصد واستبعد | {short_reason} |")
            else:
                report_lines.append(f"| {sym} | +{data['change']:.1f}% | 🔴 لم يرصده الرادار نهائياً | السهم لم يظهر في فلتر TradingView الأساسي |")
                
    if missed_count == 0:
        report_lines.append("*لا توجد فرص ضائعة كبرى حتى الآن، المنصة مسيطرة.*")
        
    report_lines.append("\n---\n*تم إنشاء هذا التقرير آلياً بواسطة سكريبت مدير المشروع.*")
    
    with open(ARTIFACT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"Audit completed at {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    print("Market Auditor Daemon Started...")
    while True:
        try:
            run_audit()
        except Exception as e:
            print("Audit Error:", e)
            traceback.print_exc()
        time.sleep(900) # 15 minutes
