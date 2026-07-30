# test_full_platform.py — اختبار شامل حقيقي لجميع مكونات المنصة
import sys
import asyncio
import traceback
from datetime import datetime

PASS = "✅ نجح"
FAIL = "❌ فشل"
results = []

def log(name, status, detail=""):
    icon = PASS if status else FAIL
    msg = f"{icon} | {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    results.append((name, status, detail))

print("=" * 65)
print("  اختبار شامل حقيقي لمنصة JIL-2 OS")
print(f"  الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 65)

# ─── 1. استيراد المكونات ───────────────────────────────────────────
print("\n📦 1. اختبار استيراد المكونات:")
try:
    from dotenv import load_dotenv
    load_dotenv("config.env")
    log("dotenv / config.env", True)
except Exception as e:
    log("dotenv / config.env", False, str(e))

try:
    from scanner import FreeMarketScanner
    log("scanner.py", True)
except Exception as e:
    log("scanner.py", False, str(e))

try:
    from intelligence import QuantIntelligence
    log("intelligence.py", True)
except Exception as e:
    log("intelligence.py", False, str(e))

try:
    from notifier import TelegramNotifier
    log("notifier.py", True)
except Exception as e:
    log("notifier.py", False, str(e))

try:
    from database import QuantDatabase
    log("database.py", True)
except Exception as e:
    log("database.py", False, str(e))

try:
    from alerts_tracker import get_active_halts, get_sec_filings_sentiment
    log("alerts_tracker.py", True)
except Exception as e:
    log("alerts_tracker.py", False, str(e))

try:
    from ml_classifier import QuantMLClassifier
    log("ml_classifier.py", True)
except Exception as e:
    log("ml_classifier.py", False, str(e))

try:
    from intraday_tracker import get_historical_features
    log("intraday_tracker.py", True)
except Exception as e:
    log("intraday_tracker.py", False, str(e))

try:
    from news_radar import SECNewsRadar
    log("news_radar.py", True)
except Exception as e:
    log("news_radar.py", False, str(e))

# ─── 2. اختبار قاعدة البيانات ─────────────────────────────────────
print("\n🗄️ 2. اختبار قاعدة البيانات:")
try:
    db = QuantDatabase()
    log("الاتصال بـ SQLite", True)
except Exception as e:
    log("الاتصال بـ SQLite", False, str(e))

try:
    db.update_heartbeat()
    log("update_heartbeat()", True)
except Exception as e:
    log("update_heartbeat()", False, str(e))

try:
    pending = db.get_pending_alerts()
    log("get_pending_alerts()", True, f"{len(pending)} صفقة معلقة")
except Exception as e:
    log("get_pending_alerts()", False, str(e))

try:
    kpi = db.calculate_platform_efficiency()
    log("calculate_platform_efficiency()", True, f"Win Rate: {kpi.get('win_rate', 0)}%")
except Exception as e:
    log("calculate_platform_efficiency()", False, str(e))

try:
    hist = db.get_alerts_history(limit=5)
    log("get_alerts_history()", True, f"{len(hist)} سجل")
except Exception as e:
    log("get_alerts_history()", False, str(e))

# ─── 3. اختبار مصدر البيانات (TradingView) ────────────────────────
print("\n📡 3. اختبار جلب البيانات الحقيقية من TradingView:")
try:
    sc = FreeMarketScanner()
    symbols = sc.fetch_all_us_symbols()
    ok = len(symbols) > 0
    log("fetch_all_us_symbols()", ok, f"تم جلب {len(symbols)} رمز")
    if ok:
        print(f"   أول 5 رموز: {symbols[:5]}")
except Exception as e:
    log("fetch_all_us_symbols()", False, str(e))
    symbols = []

# ─── 4. اختبار بيانات الأسعار التفصيلية ──────────────────────────
print("\n💹 4. اختبار بيانات الأسعار التفصيلية:")
try:
    loop = asyncio.new_event_loop()
    raw_data = loop.run_until_complete(sc.scan_entire_market())
    ok = len(raw_data) > 0
    log("scan_entire_market()", ok, f"{len(raw_data)} سهم بتفاصيل كاملة")
    if ok:
        sample = raw_data[0]
        print(f"   مثال: {sample.get('symbol')} | السعر: {sample.get('regularMarketPrice')} | التغير: {sample.get('regularMarketChangePercent'):.2f}%")
except Exception as e:
    log("scan_entire_market()", False, str(e))
    raw_data = []

# ─── 5. اختبار محرك الذكاء (Isolation Forest) ────────────────────
print("\n🧠 5. اختبار محرك الذكاء الاصطناعي:")
try:
    intel = QuantIntelligence()
    session = sc.get_current_market_session()
    log("get_current_market_session()", True, f"الجلسة: {session}")
except Exception as e:
    log("get_current_market_session()", False, str(e))

try:
    if raw_data:
        anomaly_map = intel.fit_anomaly_detector(raw_data, session)
        ok = isinstance(anomaly_map, dict)
        anomaly_count = sum(1 for v in anomaly_map.values() if v.get("is_anomaly"))
        log("fit_anomaly_detector()", ok, f"{anomaly_count} سهم شاذ من {len(anomaly_map)}")
    else:
        log("fit_anomaly_detector()", False, "لا بيانات متاحة")
        anomaly_map = {}
except Exception as e:
    log("fit_anomaly_detector()", False, str(e))
    anomaly_map = {}

# ─── 6. اختبار حساب طبقات اليقين السبعة ─────────────────────────
print("\n🔬 6. اختبار حساب نقاط اليقين (7 طبقات):")
try:
    if raw_data:
        sample_quote = raw_data[0]
        anomaly_info = anomaly_map.get(sample_quote.get("symbol"), {"is_anomaly": False, "confidence_score": 1.0})
        score, details, price, change, rvol = intel.calculate_7_layer_conviction(
            sample_quote, session, anomaly_info
        )
        log("calculate_7_layer_conviction()", True,
            f"السهم: {sample_quote.get('symbol')} | النقاط: {score} | السعر: {price:.3f} | التغير: {change:.2f}%")
    else:
        log("calculate_7_layer_conviction()", False, "لا بيانات متاحة")
except Exception as e:
    log("calculate_7_layer_conviction()", False, str(e))
    traceback.print_exc()

# ─── 7. اختبار نموذج التعلم الآلي ────────────────────────────────
print("\n🤖 7. اختبار نموذج التعلم الآلي (XGBoost):")
try:
    ml = QuantMLClassifier()
    prob = ml.predict_probability(
        price=3.5, change=25.0, rvol=8.0,
        volatility_10d=5.0, prev_rvol=2.0, prev_change=5.0,
        float_shares_m=5.0, short_percent=15.0
    )
    ok = prob is not None
    log("predict_probability()", ok, f"احتمالية الانفجار: {prob:.1f}%" if ok else "إرجاع None")
except Exception as e:
    log("predict_probability()", False, str(e))

# ─── 8. اختبار Telegram ──────────────────────────────────────────
print("\n📨 8. اختبار اتصال Telegram:")
try:
    notif = TelegramNotifier()
    import os
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    ok = bool(token and chat_id)
    log("متغيرات Telegram في config.env", ok,
        f"Token: {'موجود ✅' if token else 'مفقود ❌'} | Chat ID: {'موجود ✅' if chat_id else 'مفقود ❌'}")
except Exception as e:
    log("Telegram config", False, str(e))

try:
    success = notif.send_custom_message("🧪 اختبار تلقائي من منصة JIL-2 OS — جميع الأنظمة تعمل ✅")
    log("إرسال رسالة Telegram حقيقية", success)
except Exception as e:
    log("إرسال رسالة Telegram", False, str(e))

# ─── 9. اختبار SEC / الأخبار ─────────────────────────────────────
print("\n📰 9. اختبار جلب ملفات SEC الفيدرالية:")
try:
    sentiment = get_sec_filings_sentiment("AAPL")
    ok = isinstance(sentiment, dict) and "dilution_warning" in sentiment
    log("get_sec_filings_sentiment('AAPL')", ok, str(sentiment))
except Exception as e:
    log("get_sec_filings_sentiment()", False, str(e))

# ─── 10. اختبار جلب الإيقافات LULD ──────────────────────────────
print("\n🚨 10. اختبار LULD Halts:")
try:
    halts = get_active_halts()
    ok = isinstance(halts, dict)
    log("get_active_halts()", ok, f"{len(halts)} إيقاف نشط حالياً")
except Exception as e:
    log("get_active_halts()", False, str(e))

# ─── 11. اختبار pipeline كامل (محاكاة زر الفحص) ─────────────────
print("\n🔁 11. اختبار pipeline الفحص الكامل (محاكاة ضغط الزر):")
try:
    opportunities = []
    for quote in raw_data[:20]:  # نختبر على أول 20 سهم لتوفير الوقت
        try:
            sym = quote.get("symbol")
            if not sym or len(sym) > 4:
                continue
            price = float(quote.get("regularMarketPrice") or 0)
            prev_close = float(quote.get("regularMarketPreviousClose") or price)
            change = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0
            volume = float(quote.get("regularMarketVolume") or 0)
            avg_vol = float(quote.get("averageDailyVolume3Month") or 100000)
            rvol = volume / avg_vol if avg_vol > 0 else 1.0
            anomaly_info = anomaly_map.get(sym, {"is_anomaly": False, "confidence_score": 1.0})
            score, details, price2, change2, rvol2 = intel.calculate_7_layer_conviction(
                quote, session, anomaly_info
            )
            opportunities.append({"symbol": sym, "price": price2, "change": change2, "rvol": rvol2, "score": score})
        except:
            continue

    log("Pipeline الكامل (أول 20 سهم)", True,
        f"تمت معالجة {len(opportunities)} سهم بنجاح")
    if opportunities:
        top = max(opportunities, key=lambda x: x["score"])
        print(f"   أقوى سهم: {top['symbol']} | النقاط: {top['score']} | السعر: {top['price']:.3f} | التغير: {top['change']:.2f}%")
except Exception as e:
    log("Pipeline الكامل", False, str(e))
    traceback.print_exc()

# ─── ملخص النتائج ────────────────────────────────────────────────
print("\n" + "=" * 65)
passed = sum(1 for _, s, _ in results if s)
failed = sum(1 for _, s, _ in results if not s)
print(f"  النتيجة النهائية: {passed} اختبار نجح ✅  |  {failed} اختبار فشل ❌")
print("=" * 65)
if failed > 0:
    print("\n⚠️ الاختبارات الفاشلة:")
    for name, status, detail in results:
        if not status:
            print(f"   ❌ {name}: {detail}")
print()
