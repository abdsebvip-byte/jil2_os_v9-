import sys
import os
import yfinance as yf
import numpy as np

sys.path.append(os.getcwd())

from broker_bridge import AlpacaBrokerBridge
from intelligence import QuantIntelligence

def test_autotrading_and_trend():
    print("==================================================")
    print("🔍 بدء اختبار التداول الآلي والاتجاه اليومي المطور")
    print("==================================================")

    # 1. اختبار محرك توافق الاتجاه اليومي (Daily Trend Alignment)
    print("\n[1] فحص محرك الاتجاه اليومي (SMA-20):")
    intel = QuantIntelligence()
    
    test_symbols = ["AAPL", "CELZ"]
    for sym in test_symbols:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="30d", interval="1d")
            if len(hist) >= 20:
                closes = hist["Close"].values[-20:]
                sma_20 = float(np.mean(closes))
                current_price = float(hist["Close"].values[-1])
                is_aligned = intel.check_daily_trend_alignment(sym, current_price)
                
                status_lbl = "✅ متوافق (صاعد)" if is_aligned else "❌ غير متوافق (هابط/منهار)"
                print(f"  - سهم {sym:6s} | السعر الحالي: ${current_price:.2f} | متوسط SMA-20: ${sma_20:.2f} | النتيجة: {status_lbl}")
            else:
                print(f"  - سهم {sym} | عطل في جلب البيانات التاريخية.")
        except Exception as e:
            print(f"  - سهم {sym} | خطأ أثناء التحقق: {e}")

    # 2. اختبار جسر الاتصال بالوسيط Alpaca
    print("\n[2] فحص جسر الاتصال والمحفظة Alpaca:")
    bridge = AlpacaBrokerBridge()
    print(f"  - حالة تفعيل التداول التلقائي: {bridge.enabled}")
    print(f"  - وضع الحساب (ورقي/تجريبي): {bridge.is_paper}")
    print(f"  - مفتاح الـ API المستخدم: {bridge.key_id[:8]}...{bridge.key_id[-4:] if len(bridge.key_id) > 4 else ''}")
    
    # محاولة جلب السيولة الفعلية لإثبات صحة المفاتيح والاتصال المباشر
    equity = bridge.get_account_equity()
    print(f"  - سيولة المحفظة الفعلية المسترجعة: ${equity:,.2f}")

    # 3. اختبار محاكاة إرسال Bracket Order (تمكين تلقائي مؤقت للاختبار)
    print("\n[3] اختبار محاكاة إرسال Bracket Order إلى Alpaca:")
    
    # تفعيل قسري للاختبار فقط دون تغيير ملف config.env
    bridge.enabled = True
    
    # سنقوم بإرسال أمر شراء محدد لسهم AAPL بسعر $1.00 (سعر تافه جداً لمنع التنفيذ الفوري وسلامة المحفظة)
    test_symbol = "AAPL"
    test_price = 1.00
    test_target_pct = 50.0  # جني الأرباح عند +50%
    
    order = bridge.place_bracket_order(
        symbol=test_symbol,
        price=test_price,
        target_pct=test_target_pct,
        stop_loss_pct=5.0
    )
    
    if order:
        print("\n==================================================")
        print("✅ إثبات تشغيل حقيقي: تم إرسال أمر التداول التلقائي بنجاح!")
        print(f"  - رمز السهم: {order.get('symbol')}")
        print(f"  - معرف الصفقة (Order ID): {order.get('id')}")
        print(f"  - نوع الأمر: {order.get('type')} / {order.get('order_class')}")
        print(f"  - الكمية المطلوبة: {order.get('qty')} سهم")
        print(f"  - سعر الدخول المحدد: ${float(order.get('limit_price', 0)):.2f}")
        print(f"  - الحالة الحالية في البورصة: {order.get('status')}")
        print("==================================================")
        
        # نقوم بإلغاء هذا الأمر التجريبي فوراً لعدم تلويث الحساب
        order_id = order.get('id')
        cancel_url = f"{bridge.base_url}/v2/orders/{order_id}"
        try:
            res = requests.delete(cancel_url, headers=bridge.headers, timeout=10)
            if res.status_code == 204:
                print(f"  - تم إلغاء الأمر التجريبي {order_id} فوراً بنجاح.")
            else:
                print(f"  - تنبيه: فشل إلغاء الأمر التجريبي تلقائياً: {res.text}")
        except Exception as e:
            print(f"  - تنبيه: فشل إلغاء الأمر التجريبي: {e}")
    else:
        print("\n  ❌ فشل إرسال الأمر التجريبي. يرجى التحقق من صحة مفاتيح الـ API وصلاحية حساب Alpaca.")

if __name__ == "__main__":
    import requests
    test_autotrading_and_trend()
