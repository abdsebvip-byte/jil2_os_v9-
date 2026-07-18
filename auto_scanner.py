# auto_scanner.py
import time
import asyncio
from datetime import datetime
import logging
from scanner import FreeMarketScanner
from intelligence import QuantIntelligence
from notifier import TelegramNotifier
from database import QuantDatabase
from alerts_tracker import get_active_halts, get_sec_filings_sentiment

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
        tickers = yq.Ticker(symbols)
        price_data = tickers.price
        
        for p in pending:
            sym = p["symbol"]
            alert_id = p["id"]
            entry_price = float(p["price"])
            target_pct = float(p["target_percent"])
            current_max = float(p["max_price_reached"])
            
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

def start_scheduler():
    """
    Main entry point for the background scheduler.
    Checks halts every 60 seconds.
    Runs a full market scan every 180 seconds.
    """
    print("Background Scanner: Scheduler thread started successfully.")
    scanner = FreeMarketScanner()
    intel = QuantIntelligence()
    notifier = TelegramNotifier()
    db = QuantDatabase()
    
    # Initialize async loop inside this daemon thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    cycle_counter = 0
    notified_halts = set()
    recommended_halts = set()
    
    while True:
        try:
            # تحديث حالات الصفقات النشطة بالخلفية
            update_pending_signals_status(db)
            
            session = scanner.get_current_market_session()
            
            # If market is closed, sleep longer but check halts less frequently
            if session == "NIGHT_CLOSED":
                print("Background Scanner: Market is closed (Night). Sleeping for 10 minutes...")
                time.sleep(600)
                continue
                
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
                            
                            anomaly_info = {"is_anomaly": True, "confidence_score": 7.0} 
                            score, details, prc, chg, rv = intel.calculate_7_layer_conviction(price_data, session, anomaly_info)
                            
                            # Fetch news catalyst (SEC Form 4 or 8-K)
                            sec_sentiment = get_sec_filings_sentiment(sym)
                            is_dilution = sec_sentiment["dilution_warning"]
                            
                            # Apply SEC boosts
                            if sec_sentiment.get("insider_buy"):
                                score = min(100, score + 15)
                            if sec_sentiment.get("material_news"):
                                score = min(100, score + 10)
                            if is_dilution:
                                score = max(0, score - 70)
                                
                            # Skip if dilution warning or low conviction
                            if is_dilution or score < 75:
                                notified_halts.add(sym)
                                continue
                                
                            # Determine dynamic target percentage
                            target_pct = intel.calculate_dynamic_target(score, 70.0)
                            
                            notes = ""
                            if sec_sentiment["insider_buy"]:
                                notes += "\n⭐ *تنبيه المطلعين:* تم رصد شراء مسؤولين لأسهمهم (Form 4)!"
                            if sec_sentiment["material_news"]:
                                notes += "\n📝 *حدث جوهري:* تم رصد أخبار أو شراكة جديدة (Form 8-K)!"
                                
                            alert_text = (
                                f"🎯 *توصية صفقة استئناف موصى بها!* 🎯\n\n"
                                f"🏢 *رمز السهم:* `{sym}`\n"
                                f"📈 *نوع الإيقاف:* `صعود حاد مفاجئ` ({reason})\n"
                                f"💵 *سعر الدخول المقترح:* `${price:.2f}` (عند الاستئناف)\n"
                                f"📊 *نسبة التغير اليومي:* `+{change:.2f}%`\n"
                                f"🔊 *الحجم النسبي RVOL:* `{rvol:.2f}x`\n\n"
                                f"🔥 *نقاط تطابق الخوارزمية:* `{score}%`"
                                f"{notes}\n\n"
                                f"🎯 *الهدف المقترح ديناميكياً:* `+{target_pct}%` (سعر: `${price * (1 + target_pct/100.0):.2f}`)\n"
                                f"🛡️ *وقف الخسارة الصارم:* `-5%` (سعر: `${price * 0.95:.2f}`)\n\n"
                                f"⚠️ *توجيه:* يرجى تفعيل الشراء بسعر محدد (Limit Order) قريباً من سعر الدخول لتجنب الانزلاق السعري عند فتح التداول."
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
                                    status="PENDING"
                                )
                        except Exception as ex:
                            logging.warning(f"Error checking halt symbol {sym} price details: {ex}")
                            notified_halts.add(sym)
                        
                # Check for resumption
                resumed_syms = []
                for sym in list(notified_halts):
                    if sym not in active_halts:
                        if sym in recommended_halts:
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
            cycle_counter += 1
            if cycle_counter >= 3:
                cycle_counter = 0
                print(f"Background Scanner: Running full market scan for session {session}...")
                
                symbols = scanner.fetch_all_us_symbols()
                if not symbols:
                    time.sleep(60)
                    continue
                    
                raw_data = loop.run_until_complete(scanner.scan_entire_market())
                if not raw_data:
                    time.sleep(60)
                    continue
                    
                anomaly_map = intel.fit_anomaly_detector(raw_data, session)
                
                for quote in raw_data:
                    try:
                        score, details, price, change, rvol = intel.calculate_7_layer_conviction(quote, session, anomaly_map)
                        sym = quote.get("symbol")
                        
                        # Exclude derivatives/warrants/SPAC units
                        if len(sym) > 4 or sym.endswith(("U", "W", "R")):
                            continue
                            
                        # Price/Change Filters
                        if price <= 0.0 or price > 20.0 or change < 3.0 or change > 45.0:
                            continue
                            
                        # Session specific filters
                        if session == "PRE_MARKET":
                            pre_chg = quote.get("preMarketChangePercent")
                            if pre_chg is None or float(pre_chg) == 0.0:
                                continue
                        elif session == "AFTER_HOURS":
                            post_chg = quote.get("postMarketChangePercent")
                            if post_chg is None or float(post_chg) == 0.0:
                                continue
                                
                        anomaly_info = anomaly_map.get(sym, {"is_anomaly": False, "confidence_score": 1.0})
                        
                        # Trigger alert if algorithm conviction is strong
                        if score >= 80 and anomaly_info["confidence_score"] >= 5.0:
                            if db.check_alert_sent_recently(sym, hours=3):
                                continue
                                
                            # SEC Filings Sentiment Check
                            sec_sentiment = get_sec_filings_sentiment(sym)
                            
                            # Dilution Protection: Skip alert if Form S-1 Dilution detected!
                            if sec_sentiment["dilution_warning"]:
                                logging.warning(f"Background Scanner: Skipped dilution target {sym}.")
                                continue
                                
                            # Dynamic Score Adjustments:
                            # 1. Insider buying (Form 4) boost (+15%)
                            if sec_sentiment.get("insider_buy"):
                                score = min(100, score + 15)
                            # 2. Material event (Form 8-K) boost (+10%)
                            if sec_sentiment.get("material_news"):
                                score = min(100, score + 10)
                                
                            # Add custom notes for positive catalysts
                            notes = ""
                            if sec_sentiment["insider_buy"]:
                                notes += "\n⭐ *تنبيه المطلعين:* تم رصد شراء مسؤولين لأسهمهم (Form 4)!"
                            if sec_sentiment["material_news"]:
                                notes += "\n📝 *حدث جوهري:* تم رصد أخبار أو شراكة جديدة (Form 8-K)!"
                                
                            target_pct = intel.calculate_dynamic_target(score, anomaly_info["confidence_score"] * 10.0)
                            
                            alert_msg = (
                                f"🎯 *فرصة انفجار سعري مكتشفة!*\n\n"
                                f"🏢 *رمز السهم:* `{sym}`\n"
                                f"💵 *السعر الحالي:* `${price:.4f}`\n"
                                f"📈 *التغير اليومي:* `+{change:.2f}%`\n"
                                f"🔊 *الحجم النسبي RVOL:* `{rvol:.2f}x`\n\n"
                                f"🔥 *نسبة تطابق الخوارزمية:* `{score}%`\n"
                                f"⭐ *مؤشر ثقة السيولة (ML):* `{anomaly_info['confidence_score']}/10`"
                                f"{notes}\n\n"
                                f"🎯 *الهدف المقترح ديناميكياً:* `+{target_pct}%` (سعر: `${price * (1 + target_pct/100.0):.2f}`)\n"
                                f"🛡️ *وقف الخسارة الصارم:* `-5%` (سعر: `${price * 0.95:.2f}`)\n\n"
                                f"⚠️ *ملاحظة:* هذه محاكاة تداول حية للحفاظ على رأس مالك."
                            )
                            
                            success = notifier.send_custom_message(alert_msg)
                            if success:
                                db.log_sent_alert(sym)
                                db.log_alert_history(
                                    symbol=sym,
                                    price=price,
                                    score=score,
                                    alert_type="شراء فوري بسعر السوق (رادار)",
                                    session=session,
                                    target_percent=target_pct,
                                    status="PENDING"
                                )
                                
                    except Exception as e:
                        logging.warning(f"Background Scanner Symbol Processing Error for {sym}: {e}")
                        continue
                        
            # Sleep 60 seconds for next halts check
            time.sleep(60)
        except Exception as e:
            logging.error(f"Background Scanner Main Loop Critical Error: {e}")
            time.sleep(60)
