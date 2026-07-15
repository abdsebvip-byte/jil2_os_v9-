# module: auto_scanner.py
import time
import asyncio
from datetime import datetime, timedelta
import pytz
from scanner import FreeMarketScanner
from intelligence import QuantIntelligence
from notifier import TelegramNotifier

# قاموس لتتبع الأسهم التي تم إرسال تنبيهات لها لمنع التكرار المزعج (صلاحية التنبيه 3 ساعات)
sent_alerts = {}

def start_scheduler():
    """
    Main entry point for the background scheduler.
    Runs a continuous loop to check the market during active trading hours.
    """
    print("Background Scanner: Scheduler thread started successfully.")
    scanner = FreeMarketScanner()
    intel = QuantIntelligence()
    notifier = TelegramNotifier()
    
    # تهيئة نفق الاستدعاء غير المتزامن داخل الخيط المنفصل
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while True:
        try:
            session = scanner.get_current_market_session()
            
            # إذا كان السوق مغلقاً تماماً في الليل، ننام لفترة أطول لتوفير موارد الخادم
            if session == "NIGHT_CLOSED":
                print("Background Scanner: Market is closed (Night). Sleeping for 15 minutes...")
                time.sleep(900)
                continue
                
            print(f"Background Scanner: Active session detected: {session}. Running scan...")
            
            # جلب قائمة الرموز النشطة
            symbols = scanner.fetch_all_us_symbols()
            if not symbols:
                time.sleep(120)
                continue
                
            # جلب تفاصيل الأسعار والبيانات اللحظية
            raw_data = loop.run_until_complete(scanner.scan_entire_market())
            if not raw_data:
                time.sleep(120)
                continue
                
            # تدريب Isolation Forest لرصد الشذوذ
            anomaly_map = intel.fit_anomaly_detector(raw_data, session)
            
            # فحص وحساب التوافق للفرص
            for quote in raw_data:
                try:
                    score, details, price, change, rvol = intel.calculate_7_layer_conviction(quote, session, anomaly_map)
                    sym = quote.get("symbol")
                    
                    # الفلاتر الصارمة المعتمدة للانفجار
                    if price <= 0.0 or price > 20.0 or change < 3.0 or change > 45.0:
                        continue
                        
                    # تصفية الأسهم الخاملة خارج ساعات التداول الرسمية
                    if session == "PRE_MARKET":
                        pre_chg = quote.get("preMarketChangePercent")
                        if pre_chg is None or float(pre_chg) == 0.0:
                            continue
                    elif session == "AFTER_HOURS":
                        post_chg = quote.get("postMarketChangePercent")
                        if post_chg is None or float(post_chg) == 0.0:
                            continue
                            
                    anomaly_info = anomaly_map.get(sym, {"is_anomaly": False, "confidence_score": 1.0})
                    
                    # نرسل التنبيه فقط إذا كانت مطابقة الخوارزمية ممتازة ومؤشر الثقة مرتفع
                    if score >= 80 and anomaly_info["confidence_score"] >= 5.0:
                        now = datetime.now()
                        
                        # منع تكرار إرسال التنبيه لنفس السهم خلال 3 ساعات
                        if sym in sent_alerts:
                            last_sent = sent_alerts[sym]
                            if now - last_sent < timedelta(hours=3):
                                continue
                                
                        # إرسال التنبيه مباشرة إلى هاتف أبو فيصل عبر تيليجرام
                        success = notifier.send_breakout_alert(
                            symbol=sym,
                            price=price,
                            change=change,
                            rvol=rvol,
                            score=score,
                            confidence=anomaly_info["confidence_score"]
                        )
                        if success:
                            sent_alerts[sym] = now
                            
                except Exception as e:
                    print(f"Background Scanner: Error processing symbol: {str(e)}")
                    continue
                    
            # النوم لمدة 3 دقائق قبل إجراء المسح التالي
            print("Background Scanner: Scan cycle complete. Sleeping for 3 minutes...")
            time.sleep(180)
            
        except Exception as e:
            print(f"Background Scanner: Main loop exception: {str(e)}")
            time.sleep(120)
