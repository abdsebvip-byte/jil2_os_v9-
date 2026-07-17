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
    
    while True:
        try:
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
                        alert_text = (
                            f"🚨 *تنبيه عاجل: تم إيقاف تداول سهم {sym}!* 🚨\n\n"
                            f"🔹 *السبب:* `LULD/Volatility` ({reason})\n"
                            f"⏱️ *حالة السعر:* متجمد حالياً.\n"
                            f"💡 *التوجيه:* راقب السعر وتأهب لصفقة الاختراق فور استئناف التداول!"
                        )
                        notifier.send_custom_message(alert_text)
                        notified_halts.add(sym)
                        
                # Check for resumption
                resumed_syms = []
                for sym in list(notified_halts):
                    if sym not in active_halts:
                        res_text = (
                            f"🟢 *استئناف التداول: عاد سهم {sym} للعمل الآن!* 🟢\n\n"
                            f"📈 راقب حركة شمعة الدقيقة الأولى لتأكيد اتجاه السيولة."
                        )
                        notifier.send_custom_message(res_text)
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
                                
                            # Add custom notes for positive catalysts
                            notes = ""
                            if sec_sentiment["insider_buy"]:
                                notes += "\n⭐ *تنبيه المطلعين:* تم رصد شراء مسؤولين لأسهمهم (Form 4)!"
                            if sec_sentiment["material_news"]:
                                notes += "\n📝 *حدث جوهري:* تم رصد أخبار أو شراكة جديدة (Form 8-K)!"
                                
                            alert_msg = (
                                f"🎯 *فرصة انفجار سعري مكتشفة!*\n\n"
                                f"🏢 *رمز السهم:* `{sym}`\n"
                                f"💵 *السعر الحالي:* `${price:.4f}`\n"
                                f"📈 *التغير اليومي:* `+{change:.2f}%`\n"
                                f"🔊 *الحجم النسبي RVOL:* `{rvol:.2f}x`\n\n"
                                f"🔥 *نسبة تطابق الخوارزمية:* `{score}%`\n"
                                f"⭐ *مؤشر ثقة السيولة (ML):* `{anomaly_info['confidence_score']}/10`"
                                f"{notes}\n\n"
                                f"⚠️ *ملاحظة:* هذه محاكاة تداول حية للحفاظ على رأس مالك."
                            )
                            
                            success = notifier.send_custom_message(alert_msg)
                            if success:
                                db.log_sent_alert(sym)
                                
                    except Exception as e:
                        logging.warning(f"Background Scanner Symbol Processing Error for {sym}: {e}")
                        continue
                        
            # Sleep 60 seconds for next halts check
            time.sleep(60)
        except Exception as e:
            logging.error(f"Background Scanner Main Loop Critical Error: {e}")
            time.sleep(60)
