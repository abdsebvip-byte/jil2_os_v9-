# auto_scanner.py
import time
import asyncio
import os
from datetime import datetime
import logging
from dotenv import load_dotenv
load_dotenv("config.env")

logging.basicConfig(
    filename="auto_scanner.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

from scanner import FreeMarketScanner
from intelligence import QuantIntelligence
from notifier import TelegramNotifier
from database import QuantDatabase
from alerts_tracker import get_active_halts, get_sec_filings_sentiment
from decision_engine import DecisionEngine


def _env_int(name, default, minimum=1):
    try:
        return max(minimum, int(os.getenv(name, default)))
    except (TypeError, ValueError):
        return default


def _chunks(items, size):
    for idx in range(0, len(items), size):
        yield items[idx:idx + size]


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def update_pending_signals_status(db):
    """
    Fetch all active 'PENDING' signals from the database, download their latest prices,
    check if target or stop loss was triggered, and update DB.
    """
    import yahooquery as yq
    try:
        pending = db.get_pending_alerts()
        if not pending:
            return
            
        symbols = [p["symbol"] for p in pending]
        batch_size = _env_int("PRICE_STATUS_BATCH_SIZE", 40, 1)
        price_data = {}
        for batch in _chunks(symbols, batch_size):
            tickers = yq.Ticker(batch)
            batch_prices = tickers.price
            if isinstance(batch_prices, dict):
                price_data.update(batch_prices)
            time.sleep(0.15)
        
        for p in pending:
            sym = p["symbol"]
            alert_id = p["id"]
            entry_price = float(p["price"] if p["price"] is not None else 0.0)
            if entry_price <= 0.0:
                continue
            target_pct = float(p["target_percent"] if p["target_percent"] is not None else 12.0)
            current_max = float(p["max_price_reached"] if p["max_price_reached"] is not None else entry_price)
            
            if sym in price_data and isinstance(price_data[sym], dict):
                p_info = price_data[sym]
                current_price = float(p_info.get("regularMarketPrice") or entry_price)
                day_high = float(p_info.get("regularMarketDayHigh") or current_price)
                day_low = float(p_info.get("regularMarketDayLow") or current_price)
                
                new_max = max(current_max, day_high, current_price)
                max_gain = ((new_max - entry_price) / entry_price) * 100.0
                
                target_price = entry_price * (1.0 + target_pct / 100.0)
                stop_price = entry_price * 0.95
                
                status = "PENDING"
                if new_max >= target_price:
                    status = "SUCCESS"
                elif day_low <= stop_price:
                    if max_gain >= 10.0:
                        status = "PARTIAL"
                    else:
                        status = "FAILED"
                        
                db.update_alert_status(alert_id, new_max, status)
                if status != "PENDING":
                    logging.info(f"Signal Tracker: Locked Alert {alert_id} for {sym} as {status}. Max Gain: {max_gain:.2f}%")
    except Exception as e:
        logging.warning(f"Signal Tracker Update Error: {e}")

def get_direct_action(r):
    if r.get("Is_Dilution"):
        return "🔴 تجنب (🚨 خطر تخفيف)"
    if r.get("Change_%", 0.0) > 30.0:
        return f"⚠️ مراقبة (تجاوز الشراء الآمن +{r.get('Change_%', 0.0):.1f}%)"
    if r.get("Change_%", 0.0) > 100.0:
        return "🔴 تجنب (🚨 صعود فجوة تضخم)"
    score = r.get("Conviction_Score", 0)
    if score >= 90:
        return "🚀 شراء مؤكد (انفجار شديد القوة)"
    elif score >= 80:
        return "🔥 شراء قوي (زخم متسارع)"
    elif score >= 70:
        return "📈 شراء للمتابعة (قيد التكوين)"
    return "⏳ مراقبة وتأكيد"

def start_scheduler():
    """
    Main entry point for the background scheduler.
    Checks halts every 60 seconds.
    Runs a full market scan every 180 seconds.
    """
    print("Background Scanner: Scheduler thread started successfully.")
    # إعادة المحاولة عند فشل الاتصال بـ Yahoo Finance (timeout) بدلاً من إيقاف الـ daemon
    scanner = None
    for attempt in range(1, 20):
        try:
            scanner = FreeMarketScanner()
            print(f"Background Scanner: FreeMarketScanner initialized (attempt {attempt})")
            break
        except Exception as init_err:
            print(f"Background Scanner: Init attempt {attempt} failed: {init_err}. Retrying in 30s...")
            time.sleep(30)
    if scanner is None:
        print("Background Scanner: All init attempts failed. Exiting.")
        return
    intel = QuantIntelligence()
    notifier = TelegramNotifier()
    db = QuantDatabase()
    halt_poll_seconds = _env_int("HALT_POLL_SECONDS", 60, 15)
    full_scan_seconds = _env_int("FULL_SCAN_SECONDS", 180, 60)
    closed_sleep_seconds = _env_int("CLOSED_MARKET_SLEEP_SECONDS", 600, 60)
    
    # Initialize async loop inside this daemon thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    last_optimization_date = ""
    last_full_scan_at = 0.0
    notified_halts = set()
    recommended_halts = set()
    
    while True:
        try:
            # تحديث النبض اللحظي للمحرك الخلفي لتأكيد العمل
            db.update_heartbeat()
            
            # تحديث حالات الصفقات النشطة بالخلفية
            update_pending_signals_status(db)
            
            # تشغيل الجرد اليومي التلقائي للفترات الثلاث (الساعة 9:00 مساءً بتوقيت نيويورك)
            import pytz
            est_tz = pytz.timezone('US/Eastern')
            now_est = datetime.now(est_tz)
            current_date_str = now_est.strftime("%Y-%m-%d")
            
            if now_est.hour >= 21 and current_date_str != last_optimization_date:
                print(f"Background Scheduler: Running automated daily three-session self-optimization for {current_date_str}...")
                try:
                    from self_optimizer import QuantSelfOptimizer
                    opt = QuantSelfOptimizer()
                    opt.run_optimization()
                    last_optimization_date = current_date_str
                    print("Background Scheduler: Daily self-optimization completed successfully.")
                except Exception as opt_err:
                    logging.warning(f"Background Scheduler: Daily self-optimization failed: {opt_err}")
            
            session = scanner.get_current_market_session()
            
            # If market is closed (night), still scan for gap-up setups that will open next day
            if session == "NIGHT_CLOSED":
                print(f"Background Scanner: Market closed (Night). Running overnight gap-up setup scan...")
                session = "PRE_MARKET"
                
            # 1. Real-time Halts Monitor (Runs every 60 seconds)
            try:
                active_halts = get_active_halts()
                
                # Check for new halts
                for sym, reason in active_halts.items():
                    if sym not in notified_halts:
                        # Exclude warrants/ SPACs
                        if len(sym) > 4 or sym.endswith(("U", "W", "R")):
                            notified_halts.add(sym)
                            continue
                            
                        # Fetch quote details in real-time
                        import yahooquery as yq
                        try:
                            t = yq.Ticker(sym)
                            price_data = t.price.get(sym, {})
                            if not isinstance(price_data, dict):
                                notified_halts.add(sym)
                                continue
                                
                            price = float(price_data.get("regularMarketPrice") or 0.0)
                            prev_close = float(price_data.get("regularMarketPreviousClose") or price)
                            change = ((price - prev_close) / prev_close * 100.0) if prev_close > 0 else 0.0
                            
                            # Only trade upward halts (bullish breakouts)
                            if change < 5.0:
                                # Log silently to database and mark as notified to avoid spamming
                                notified_halts.add(sym)
                                continue
                                
                            # Calculate conviction score and features
                            avg_vol = float(price_data.get("averageDailyVolume3Month") or 100000.0)
                            current_vol = float(price_data.get("regularMarketVolume") or 0.0)
                            rvol = current_vol / avg_vol if avg_vol > 0 else 1.0
                            
                            # Fetch news catalyst (SEC Form 4 or 8-K)
                            sec_sentiment = get_sec_filings_sentiment(sym)
                            anomaly_info = {"is_anomaly": True, "confidence_score": 7.0} 
                            
                            engine = DecisionEngine()
                            trace = engine.evaluate_symbol(
                                quote=price_data,
                                session=session,
                                anomaly_info=anomaly_info,
                                sec_sentiment=sec_sentiment,
                                is_trending=False
                            )
                            
                            # تسجيل كامل مسار القرار في قاعدة البيانات لضمان الشفافية
                            db.log_evaluation_trace(
                                symbol=sym,
                                price=trace["price"],
                                change=trace["change"],
                                rvol=trace["rvol"],
                                score=trace["score"],
                                ml_prob=trace["ml_prob"],
                                status=trace["status"],
                                reason=trace["rejection_reason"],
                                details=trace["details"]
                            )
                            
                            if trace["status"] != "ACCEPTED":
                                notified_halts.add(sym)
                                continue
                                
                            score = trace["score"]
                            ml_prob = trace["ml_prob"]
                            
                            # Determine dynamic target percentage
                            target_pct = intel.calculate_dynamic_target(score, ml_prob, quote=price_data)
                            
                            action_lbl = intel.get_execution_directive(
                                quote=price_data,
                                score=score,
                                ml_prob=ml_prob,
                                session=session,
                                sec_sentiment=sec_sentiment,
                                is_halted=True
                            )
                            
                            exit_strategy = intel.get_exit_strategy(target_pct)
                            
                            notes = ""
                            if sec_sentiment["insider_buy"]:
                                notes += "\n⭐ *تنبيه المطلعين:* تم رصد شراء مسؤولين لأسهمهم (Form 4)!"
                            if sec_sentiment["material_news"]:
                                notes += "\n📝 *حدث جوهري:* تم رصد أخبار أو شراكة جديدة (Form 8-K)!"
                                
                            # تقييم مستوى المخاطرة
                            if change >= 50.0:
                                risk_label = "🔴 مخاطرة عالية جداً"
                                risk_note = f"⚠️ *تحذير:* السهم ارتفع بالفعل `+{change:.1f}%` — ادرس السبب جيداً قبل الدخول."
                            elif change >= 20.0:
                                risk_label = "🟡 مخاطرة متوسطة"
                                risk_note = f"⚠️ *تنبيه:* ارتفاع `+{change:.1f}%` — تأكد من وجود محفز حقيقي."
                            else:
                                risk_label = "🟢 مخاطرة منخفضة نسبياً"
                                risk_note = f"✅ ارتفاع `+{change:.1f}%` ضمن نطاق الاكتشاف المبكر."

                            tier_code, tier_lbl, tier_color, target_range = intel.calculate_predictive_yield_tier(price_data, score, trace.get("details", ""))
                            liq_code, liq_lbl, formatted_vol = intel.calculate_liquidity_rating(price_data)

                            alert_text = (
                                f"🎯 *توصية صفقة استئناف موصى بها!* 🎯\n\n"
                                f"🏢 *رمز السهم:* `{sym}`\n"
                                f"📊 *فئة الانفجار المتوقع:* *{tier_lbl}*\n"
                                f"💧 *تقييم السيولة النقدية:* *{liq_lbl}*\n"
                                f"🚦 *توجيه الشراء:* {action_lbl}\n"
                                f"⚡ *مستوى المخاطرة:* {risk_label}\n\n"
                                f"📈 *نوع الإيقاف:* `صعود حاد مفاجئ` ({reason})\n"
                                f"💵 *سعر الدخول المقترح:* `${price:.2f}` (عند الاستئناف)\n"
                                f"📊 *نسبة التغير اليومي:* `+{change:.2f}%`\n"
                                f"🔊 *الحجم النسبي RVOL:* `{rvol:.2f}x`\n"
                                f"🔥 *نقاط تطابق الخوارزمية:* `{score}%`"
                                f"{notes}\n\n"
                                f"🎯 *الهدف المقترح ديناميكياً:* `+{target_pct}%` (سعر: `${price * (1 + target_pct/100.0):.2f}`)\n"
                                f"🛡️ *وقف الخسارة الصارم:* `-5%` (سعر: `${price * 0.95:.2f}`)\n"
                                f"💰 *استراتيجية التداول:* {exit_strategy}\n\n"
                                f"{risk_note}\n"
                                f"📌 *قرار التداول مسؤوليتك الكاملة — استخدم Limit Order لتجنب الانزلاق.*"
                            )
                            
                            success = notifier.send_custom_message(alert_text)
                            if success:
                                notified_halts.add(sym)
                                recommended_halts.add(sym)
                                db.log_alert_history(
                                    symbol=sym,
                                    price=price,
                                    score=score,
                                    alert_type=f"صفقة استئناف ({reason})",
                                    session=session,
                                    target_percent=target_pct,
                                    status="PENDING",
                                    initial_change=change
                                )
                        except Exception as ex:
                            logging.warning(f"Error checking halt symbol {sym} price details: {ex}")
                            notified_halts.add(sym)
                        
                # Check for resumption
                resumed_syms = []
                for sym in list(notified_halts):
                    if sym not in active_halts:
                        if sym in recommended_halts:
                            send_res = os.getenv("SEND_RESUMPTION_ALERTS", "FALSE").upper() == "TRUE"
                            if send_res:
                                res_text = (
                                    f"🟢 *استئناف التداول: عاد سهم {sym} للعمل الآن!* 🟢\n\n"
                                    f"📈 راقب حركة شمعة الدقيقة الأولى لتأكيد اتجاه السيولة."
                                )
                                success = notifier.send_custom_message(res_text)
                                if success:
                                    db.log_alert_history(sym, 0.0, 100.0, "استئناف التداول")
                            recommended_halts.discard(sym)
                        resumed_syms.append(sym)
                for sym in resumed_syms:
                    notified_halts.remove(sym)
            except Exception as e:
                logging.warning(f"Background Scanner Halts Loop Error: {e}")
                
            # 2. Full Market Anomaly & Conviction Scan (Runs every 180 seconds / 3 cycles)
            now_ts = time.monotonic()
            if now_ts - last_full_scan_at >= full_scan_seconds:
                last_full_scan_at = now_ts
                print(f"Background Scanner: Running full market scan for session {session}...")
                
                symbols = scanner.fetch_all_us_symbols()
                if not symbols:
                    notifier.send_custom_message("🚨 *تنبيه تقني عاجل:* توقف تام في قنوات جلب رموز الأسعار اللحظية (TradingView & Yahoo Fallback). السيرفر غير قادر على بدء دورة المسح.")
                    time.sleep(halt_poll_seconds)
                    continue
                    
                raw_data = loop.run_until_complete(scanner.scan_entire_market())
                if not raw_data:
                    notifier.send_custom_message("🚨 *تنبيه تقني عاجل:* تم جلب الرموز ولكن مصفوفة تفاصيل الأسعار اللحظية فارغة. تحقق من استجابة خوادم البيانات.")
                    time.sleep(halt_poll_seconds)
                    continue
                    
                # جلب رادار الشهرة (الأكثر بحثاً ونقاشاً) من Yahoo & Reddit
                retail_trending = scanner.fetch_retail_trending_symbols()
                yahoo_trending = retail_trending["yahoo"]
                reddit_trending = retail_trending["reddit"]
                
                anomaly_map = intel.fit_anomaly_detector(raw_data, session)
                
                for quote in raw_data:
                    try:
                        sym = quote.get("symbol")
                        if not sym:
                            continue
                            
                        # Exclude derivatives/warrants/SPAC units
                        if len(sym) > 4 or sym.endswith(("U", "W", "R")):
                            continue
                            
                        # Quick manual calculation of price and change to avoid redundant network calls
                        price = _safe_float(quote.get("regularMarketPrice"), 0.0)
                        prev_close = _safe_float(quote.get("regularMarketPreviousClose"), price)
                        change = ((price - prev_close) / prev_close) * 100.0 if prev_close > 0 else 0.0
                        
                        if session == "PRE_MARKET" and quote.get("preMarketPrice") is not None:
                            price = _safe_float(quote.get("preMarketPrice"), price)
                            change = ((price - prev_close) / prev_close) * 100.0 if prev_close > 0 else change
                        elif session == "AFTER_HOURS" and quote.get("postMarketPrice") is not None:
                            price = _safe_float(quote.get("postMarketPrice"), price)
                            change = ((price - prev_close) / prev_close) * 100.0 if prev_close > 0 else change

                        # Fetch news catalyst (SEC Form 4 or 8-K) only for active candidates to avoid rate limits
                        vol_val = _safe_float(quote.get("regularMarketVolume"), 0.0)
                        if abs(change) >= 1.0 or vol_val >= 50000.0:
                            sec_sentiment = get_sec_filings_sentiment(sym)
                        else:
                            sec_sentiment = {"insider_buy": False, "material_news": False, "dilution_warning": False, "details": []}
                        anomaly_info = anomaly_map.get(sym, {"is_anomaly": False, "confidence_score": 1.0})
                        
                        is_yahoo = sym in yahoo_trending
                        is_reddit = sym in reddit_trending
                        is_trending = is_yahoo or is_reddit
                        
                        # 1. تقييم السهم عبر محرك القرار المركزي
                        engine = DecisionEngine()
                        trace = engine.evaluate_symbol(
                            quote=quote,
                            session=session,
                            anomaly_info=anomaly_info,
                            sec_sentiment=sec_sentiment,
                            is_trending=is_trending
                        )
                        
                        # 2. تسجيل القرار كاملاً في قاعدة البيانات (سواء مقبول أو مستبعد)
                        db.log_evaluation_trace(
                            symbol=sym,
                            price=trace["price"],
                            change=trace["change"],
                            rvol=trace["rvol"],
                            score=trace["score"],
                            ml_prob=trace["ml_prob"],
                            status=trace["status"],
                            reason=trace["rejection_reason"],
                            details=trace["details"]
                        )
                        
                        # 3. إرسال تنبيه في حال القبول فقط
                        if trace["status"] == "ACCEPTED":
                            if db.check_alert_sent_recently(sym, hours=3):
                                continue
                                
                            # 🔄 تحديث مباشر ولحظي للسعر الآن قبل إرسال التنبيه لإلغاء أي تأخير بيانات (Stale Data Guard)
                            try:
                                import yfinance as _yf
                                _fast_info = _yf.Ticker(sym).fast_info
                                _live_p = float(_fast_info.get("lastPrice") or 0.0)
                                _live_pc = float(_fast_info.get("previousClose") or 0.0)
                                if _live_p > 0.0 and _live_pc > 0.0:
                                    price = _live_p
                                    change = ((_live_p - _live_pc) / _live_pc) * 100.0
                            except Exception as _p_err:
                                pass

                            # حارس الارتفاع المفرط اللحظي: إذا أظهر السعر المباشر الآن أن السهم انفجر وتجاوز +45% -> يُلغى التنبيه فوراً!
                            if change > 45.0:
                                logging.info(f"AutoScanner: Cancelled alert for {sym} - live price updated to ${price:.4f} (+{change:.1f}%) > +45% safe limit.")
                                continue

                            score = trace["score"]
                            ml_prob = trace["ml_prob"]
                            rvol = trace["rvol"]
                            
                            # Add custom notes for positive catalysts
                            notes = ""
                            if sec_sentiment.get("insider_buy"):
                                notes += "\n⭐ *تنبيه المطلعين:* تم رصد شراء مسؤولين لأسهمهم (Form 4)!"
                            if sec_sentiment.get("material_news"):
                                notes += "\n📝 *حدث جوهري:* تم رصد أخبار أو شراكة جديدة (Form 8-K)!"
                                
                            # Add custom notes for popularity
                            if is_yahoo and is_reddit:
                                notes += "\n🔥 *الشهرة والبحث:* عليه بحث ونقاش مكثف جداً في ياهو وريديت!"
                            elif is_yahoo:
                                notes += "\n📈 *الشهرة والبحث:* بحث نشط على ياهو فاينانس!"
                            elif is_reddit:
                                notes += "\n💬 *الشهرة والبحث:* نقاش متداول في منتدى ريديت!"
                                
                            target_pct = intel.calculate_dynamic_target(score, ml_prob, quote=quote)
                            
                            action_lbl = intel.get_execution_directive(
                                quote=quote,
                                score=score,
                                ml_prob=ml_prob,
                                session=session,
                                sec_sentiment=sec_sentiment,
                                is_halted=False
                            )
                            
                            exit_strategy = intel.get_exit_strategy(target_pct)
                                
                            # --- تقييم مستوى المخاطرة والتوجيه بناءً على حجم الارتفاع المسبق ---
                            if change >= 30.0:
                                header_text = "⚠️ *رصد حركة متقدمة (دخول بحذر — Limit Order فقط!)* ⚠️"
                                action_lbl = f"⚠️ أمر محدد فقط (Limit Order) بسعر `${price * 0.98:.4f}` أو أقل (ممنوع الشراء بسعر السوق ماركت!)"
                                risk_label = "🔴 مخاطرة عالية (ارتفاع مسبق)"
                                risk_note = f"🛑 *تحذير صارم:* السهم مرتفع بالفعل `+{change:.1f}%` — **ممنوع تماماً الشراء بسعر السوق (Market Order)** لتجنب الانزلاق والهبوط المفاجئ! ادخل فقط بأمر محدد بسعر أقل من الحالي."
                            elif change >= 18.0:
                                header_text = "🎯 *فرصة انفجار سعري مكتشفة!* 🚀"
                                risk_label = "🟡 مخاطرة متوسطة"
                                risk_note = f"⚠️ *تنبيه:* الارتفاع الحالي `+{change:.1f}%` — يفضل انتظار تراجع بسيط أو الشراء بأمر محدد."
                            else:
                                header_text = "🚀 *فرصة اكتشاف مبكر نادرة (آمنة للغاية)!* 🟢"
                                risk_label = "🟢 مخاطرة منخفضة (اكتشاف في القاع)"
                                risk_note = f"✅ الارتفاع الحالي `+{change:.1f}%` في البداية المطلوبة — دخول ممتاز في بداية الزخم."

                            alert_msg = (
                                f"{header_text}\n\n"
                                f"🏢 *رمز السهم:* `{sym}`\n"
                                f"🚦 *توجيه الشراء:* {action_lbl}\n"
                                f"⚡ *مستوى المخاطرة:* {risk_label}\n\n"
                                f"💵 *السعر الحالي:* `${price:.4f}`\n"
                                f"📈 *التغير اليومي:* `+{change:.2f}%`\n"
                                f"🔊 *الحجم النسبي RVOL:* `{rvol:.2f}x`\n"
                                f"🔥 *نسبة تطابق الخوارزمية:* `{score}%`\n"
                                f"⭐ *مؤشر ثقة السيولة (ML):* `{ml_prob:.1f}%`"
                                f"{notes}\n\n"
                                f"🎯 *الهدف المقترح ديناميكياً:* `+{target_pct}%` (سعر: `${price * (1 + target_pct/100.0):.2f}`)\n"
                                f"🛡️ *وقف الخسارة الصارم:* `-5%` (سعر: `${price * 0.95:.2f}`)\n"
                                f"💰 *استراتيجية التداول:* {exit_strategy}\n\n"
                                f"{risk_note}\n\n"
                                f"📌 *هذه منصة رصد وبحث — قرار التداول مسؤوليتك الكاملة.*"
                            )
                            
                            success = notifier.send_custom_message(alert_msg)
                            if success:
                                db.log_sent_alert(sym)
                                alert_id = db.log_alert_history(
                                    symbol=sym,
                                    price=price,
                                    score=score,
                                    alert_type="شراء فوري بسعر السوق (رادار)",
                                    session=session,
                                    target_percent=target_pct,
                                    status="PENDING",
                                    initial_change=change
                                )
                                # Save features and score to signals database
                                try:
                                    # Calculate ML score and get features
                                    ml_score, features = intel.calculate_ml_score(quote, session, anomaly_info)
                                    import zlib
                                    blob = zlib.compress(features.tobytes())
                                    with db.get_connection() as conn:
                                        cursor = conn.cursor()
                                        cursor.execute(
                                            "INSERT INTO signals (id, ts_utc, symbol, features, score, persisted) VALUES (?, ?, ?, ?, ?, 1)",
                                            (alert_id, datetime.now().isoformat(), sym, blob, float(ml_score))
                                        )
                                        conn.commit()
                                except Exception as db_ex:
                                    logging.warning(f"Error saving alert features to signals db: {db_ex}")
                                
                    except Exception as e:
                        logging.warning(f"Background Scanner Symbol Processing Error for {sym}: {e}")
                        continue
                        
            # Sleep 60 seconds for next halts check
            time.sleep(halt_poll_seconds)
        except Exception as e:
            logging.error(f"Background Scanner Main Loop Critical Error: {e}")
            time.sleep(halt_poll_seconds)


if __name__ == "__main__":
    import dotenv
    import os
    dotenv.load_dotenv("config.env")
    with open("auto_scanner.pid", "w") as f:
        f.write(str(os.getpid()))
    start_scheduler()
