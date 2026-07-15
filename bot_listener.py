# module: bot_listener.py
import time
import requests
import json
from yahooquery import Ticker
from database import QuantDatabase
from scanner import FreeMarketScanner
from intelligence import QuantIntelligence

class TelegramBotListener:
    def __init__(self):
        self.db = QuantDatabase()
        self.scanner = FreeMarketScanner()
        self.intel = QuantIntelligence()
        self.token = None
        self.chat_id = None
        self.gemini_key = None
        self.offset = 0
        self.load_credentials()

    def load_credentials(self):
        # محاولة التحميل من إعدادات سحابة Streamlit أولاً
        try:
            import streamlit as st
            if "TELEGRAM_BOT_TOKEN" in st.secrets:
                self.token = st.secrets["TELEGRAM_BOT_TOKEN"]
                self.chat_id = st.secrets["TELEGRAM_CHAT_ID"]
                self.gemini_key = st.secrets.get("GEMINI_API_KEY")
                return
        except:
            pass

        # محاولة التحميل من ملف config.env المحلي
        import os
        if os.path.exists("config.env"):
            with open("config.env", "r") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        parts = line.strip().split("=")
                        if len(parts) == 2:
                            key, val = parts[0].strip(), parts[1].strip()
                            if key == "TELEGRAM_BOT_TOKEN":
                                self.token = val
                            elif key == "TELEGRAM_CHAT_ID":
                                self.chat_id = val
                            elif key == "GEMINI_API_KEY":
                                self.gemini_key = val

    def get_live_price(self, symbol):
        symbol = symbol.upper().strip()
        try:
            t = Ticker(symbol)
            price_info = t.price.get(symbol, {})
            price = price_info.get("regularMarketPrice", 0.0)
            
            sess = self.scanner.get_current_market_session()
            if sess == "PRE_MARKET" and price_info.get("preMarketPrice"):
                price = price_info.get("preMarketPrice")
            elif sess == "AFTER_HOURS" and price_info.get("postMarketPrice"):
                price = price_info.get("postMarketPrice")
                
            return float(price)
        except:
            return 0.0

    def send_message(self, text, show_keyboard=True):
        if not self.token or not self.chat_id:
            return
        
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        if show_keyboard:
            keyboard = {
                "keyboard": [
                    [{"text": "💼 عرض المحفظة"}, {"text": "⚡ تصفية السوق"}],
                    [{"text": "🔍 تجميع صامت"}, {"text": "📖 دليل الأوامر"}]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            payload["reply_markup"] = keyboard

        try:
            requests.post(url, json=payload, timeout=8)
        except Exception as e:
            print(f"BotListener: send_message failed: {str(e)}")

    def call_gemini_advisor(self, user_message):
        """
        Calls Gemini API dynamically to provide free-form conversational advice in Arabic.
        Includes automatic retry, 60s timeout, and response length limitation.
        """
        if not self.gemini_key:
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={self.gemini_key}"
        headers = {"Content-Type": "application/json"}
        
        system_instruction = (
            "أنت 'مستشار التداول الكمي المالي الذكي والخاص بأبو فيصل'. أنت لست مجرد بوت أوامر، بل خبير إحصائي ومحلل مالي رفيع المستوى ومضارب محترف يملك خبرة واسعة في وول ستريت.\n"
            "طريقة تفاعلك وإجاباتك:\n"
            "1. تفاعل مع أبو فيصل بحرية كاملة وناقش معه الاستراتيجيات والأفكار التداولية بعمق وذكاء فائق.\n"
            "2. عند السؤال عن المفاهيم (مثل التجميع الصامت، الـ Float، مؤشر ATR، و Isolation Forest)، اشرحها بأسلوب علمي دقيق واحترافي ولكن مبسط وعملي.\n"
            "3. حلل الأسهم والأفكار من منظور احتمالي وإحصائي صارم، مع التركيز التام على إدارة المخاطر وتحديد مستويات الدخول والخروج الافتراضية وحماية رأس المال.\n"
            "4. اطرح سيناريوهات تداول افتراضية وحفز أبو فيصل بأسئلة تفاعلية ذكية لتطوير خطته للوصول إلى أهدافه المالية بذكاء وبطريقة علمية حقيقية.\n"
            "5. تجنب تماماً الردود الجافة المختصرة أو تكرار قوالب الترحيب الجامدة. تحدث بمرونة وعمق واحترافية كخبير حقيقي متاح لمساعدته 24 ساعة."
        )

        payload = {
            "contents": [{"parts": [{"text": user_message}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {
                "maxOutputTokens": 800  # زيادة سقف المخرجات للسماح بنقاشات عميقة وذكية
            }
        }

        # آلية إعادة المحاولة تلقائياً لمرتين متتاليتين لتجنب الانقطاع المؤقت
        for attempt in range(2):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    reply = data['candidates'][0]['content']['parts'][0]['text']
                    return reply
                elif response.status_code == 503:
                    # في حال وجود ضغط مؤقت، انتظر ثانية ونصف وجرب مجدداً
                    time.sleep(1.5)
                    continue
                else:
                    return f"⚠️ خادم الذكاء الاصطناعي استجاب برمز خطأ: {response.status_code}"
            except requests.exceptions.Timeout:
                if attempt == 0:
                    time.sleep(1)
                    continue
                return "⚠️ تعذر الاتصال بمحرك الاستشارات الذكي: انتهت مهلة الـ 60 ثانية دون استجابة."
            except Exception as e:
                return f"⚠️ تعذر الاتصال بمحرك الاستشارات الذكي: {str(e)}"
        
        return "⚠️ تعذر الاتصال بمحرك الاستشارات الذكي حالياً بسبب الضغط العالي على الخوادم."

    def process_message(self, text):
        text = text.strip()
        # توحيد التاء المربوطة والهاء في نهاية الكلمات لتجنب مشاكل الإملاء العربي (مثال: استشارة مقابل استشاره)
        normalized_text = text.replace("ة", "ه").lower()
        parts = normalized_text.split()
        if not parts:
            return
            
        command = parts[0]
        original_parts = text.split()  # نأخذ الأجزاء الأصلية للحفاظ على حالة الحروف الكبيرة للرموز
        
        # 1. أمر الاستشارة وتحليل السهم
        if command in ["استشاره", "تحليل", "استشارة"]:
            if len(original_parts) < 2:
                self.send_message("⚠️ صيغة الاستشارة غير مكتملة. الصيغة الصحيحة:\n`استشارة [رمز السهم]` (مثال: `استشارة CLSK`)")
                return
                
            symbol = original_parts[1].upper()
            self.send_message(f"🔍 جاري تحليل السهم `{symbol}` لحظياً وفق معادلة اليقين...")
            price = self.get_live_price(symbol)
            if price <= 0.0:
                self.send_message(f"❌ لم يتم العثور على بيانات للسهم `{symbol}`. يرجى التأكد من الرمز.")
                return
                
            try:
                t = Ticker(symbol)
                q = t.price.get(symbol, {})
                
                formatted_quote = {
                    "symbol": symbol,
                    "regularMarketPrice": q.get("regularMarketPrice", 0.0),
                    "regularMarketChangePercent": q.get("regularMarketChangePercent", 0.0),
                    "preMarketPrice": q.get("preMarketPrice"),
                    "preMarketChangePercent": q.get("preMarketChangePercent"),
                    "postMarketPrice": q.get("postMarketPrice"),
                    "postMarketChangePercent": q.get("postMarketChangePercent"),
                    "regularMarketVolume": q.get("regularMarketVolume", 0.0),
                    "averageDailyVolume3Month": q.get("averageDailyVolume3Month", 100000.0),
                    "regularMarketOpen": q.get("regularMarketOpen", 0.0),
                    "regularMarketPreviousClose": q.get("regularMarketPreviousClose", 0.0),
                    "bid": q.get("bid", 0.0),
                    "ask": q.get("ask", 0.0),
                    "bidSize": q.get("bidSize", 0.0),
                    "askSize": q.get("askSize", 0.0)
                }
                
                sess = self.scanner.get_current_market_session()
                score, details, prc, chg, rvol = self.intel.calculate_7_layer_conviction(formatted_quote, sess, {})
                
                match_text = "\n".join([f"{'✅' if v else '❌'} {k}" for k, v in details.items()])
                response = (
                    f"📊 *تقرير استشارة السهم {symbol}*:\n\n"
                    f"💵 *السعر الحالي:* `${prc:.4f}`\n"
                    f"📈 *التغير اليومي:* `{chg:+.2f}%`\n"
                    f"🔊 *الحجم النسبي RVOL:* `{rvol:.2f}x`\n\n"
                    f"🔥 *درجة مطابقة الخوارزمية:* `{score}%`\n\n"
                    f"🛡️ *حالة طبقات اليقين السبعة:*\n{match_text}"
                )
                self.send_message(response)
            except Exception as e:
                self.send_message(f"❌ حدث خطأ أثناء تحليل السهم: {str(e)}")

        # 2. أمر الشراء الافتراضي
        elif command == "شراء":
            if len(original_parts) < 3:
                self.send_message("⚠️ صيغة الشراء غير مكتملة. الصيغة الصحيحة:\n`شراء [رمز السهم] [الكمية]` (مثال: `شراء CLSK 100`)")
                return
            symbol = original_parts[1].upper()
            try:
                quantity = float(original_parts[2])
                price = self.get_live_price(symbol)
                if price <= 0.0:
                    self.send_message(f"❌ فشل جلب سعر السهم اللحظي لـ `{symbol}`.")
                    return
                success, msg = self.db.execute_buy(symbol, quantity, price)
                self.send_message(msg)
            except ValueError:
                self.send_message("⚠️ صيغة الكمية غير صحيحة. مثال: `شراء CLSK 10`")

        # 3. أمر البيع الافتراضي
        elif command == "بيع":
            if len(original_parts) < 3:
                self.send_message("⚠️ صيغة البيع غير مكتملة. الصيغة الصحيحة:\n`بيع [رمز السهم] [الكمية]` (مثال: `بيع CLSK 50`)")
                return
            symbol = original_parts[1].upper()
            try:
                quantity = float(original_parts[2])
                price = self.get_live_price(symbol)
                if price <= 0.0:
                    self.send_message(f"❌ فشل جلب سعر السهم اللحظي لـ `{symbol}`.")
                    return
                success, msg = self.db.execute_sell(symbol, quantity, price)
                self.send_message(msg)
            except ValueError:
                self.send_message("⚠️ صيغة الكمية غير صحيحة. مثال: `بيع CLSK 10`")

        # 4. أمر عرض المحفظة الافتراضية
        elif "محفظه" in normalized_text or "محفظة" in normalized_text:
            portfolio = self.db.get_portfolio()
            cash = self.db.get_cash()
            if not portfolio:
                self.send_message(f"💼 *محفظتك الافتراضية فارغة حالياً.*\n💵 *السيولة النقدية المتاحة:* `{cash:.2f}$`\n*لشراء سهم اكتب:* `شراء [الرمز] [الكمية]`")
                return
                
            msg = "💼 *محفظة أبو فيصل الافتراضية حياً*:\n\n"
            total_valuation = 0.0
            
            for item in portfolio:
                sym = item["symbol"]
                qty = item["quantity"]
                entry = item["entry_price"]
                current = self.get_live_price(sym)
                
                value = qty * current
                total_valuation += value
                pnl = (current - entry) * qty
                pnl_pct = ((current - entry) / entry) * 100 if entry > 0 else 0.0
                pnl_icon = "🟢" if pnl >= 0 else "🔴"
                
                msg += (
                    f"🔹 *{sym}* | الكمية: `{qty}`\n"
                    f"💸 سعر الدخول: `${entry:.2f}` | الحالي: `${current:.2f}`\n"
                    f"💰 القيمة: `${value:.2f}`\n"
                    f"{pnl_icon} الأرباح/الخسائر: `{pnl:+.2f}$` ({pnl_pct:+.2f}%)\n\n"
                )
                
            total_wealth = cash + total_valuation
            msg += (
                f"--- \n"
                f"💵 *السيولة النقدية (Cash):* `{cash:.2f}$`\n"
                f"📊 *قيمة الأسهم الحالية:* `{total_valuation:.2f}$`\n"
                f"🏆 *صافي الثروة الكلي:* `{total_wealth:.2f}$`"
            )
            self.send_message(msg)

        # 5. أمر مسح التجميع الصامت
        elif "تجميع" in normalized_text:
            self.send_message("🔬 جاري فحص السوق ورصد التجميع الصامت والـ Float المنخفض...")
            try:
                from accumulation import SilentAccumulationScanner
                accum_scanner = SilentAccumulationScanner()
                setups = accum_scanner.scan_for_accumulation()
                
                if not setups:
                    self.send_message("⚠️ لم يتم رصد أي أسهم تمر بمرحلة تجميع صامت مطابقة للشروط حالياً.")
                    return
                    
                msg = "🔍 *فرص التجميع الصامت المكتشفة حالياً*:\n\n"
                for idx, item in enumerate(setups):
                    msg += (
                        f"{idx+1}. *{item['Symbol']}* | السعر: `${item['Price']:.2f}`\n"
                        f"📊 *التوجيه الفني الكامل:*\n{item['Guidance']}\n\n"
                    )
                self.send_message(msg)
            except Exception as e:
                self.send_message(f"❌ حدث خطأ أثناء فحص التجميع الصامت: {str(e)}")

        # 6. أمر مسح السوق وتصفية الفرص الفورية
        elif "تصفيه" in normalized_text or "تصفية" in normalized_text or "فحص" in normalized_text:
            self.send_message("🔬 جاري مسح السوق وتصفية أفضل الفرص السبعة حالياً بالـ ML...")
            try:
                symbols = self.scanner.fetch_all_us_symbols()
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                raw_data = loop.run_until_complete(self.scanner.scan_entire_market())
                
                sess = self.scanner.get_current_market_session()
                anomaly_map = self.intel.fit_anomaly_detector(raw_data, sess)
                
                opportunities = []
                for quote in raw_data:
                    score, details, prc, chg, rvol = self.intel.calculate_7_layer_conviction(quote, sess, anomaly_map)
                    sym = quote.get("symbol")
                    if prc <= 0.0 or prc > 20.0 or chg < 3.0 or chg > 45.0:
                        continue
                        
                    anomaly_info = anomaly_map.get(sym, {"is_anomaly": False})
                    opportunities.append((sym, prc, chg, score, anomaly_info["is_anomaly"]))
                    
                opportunities = sorted(opportunities, key=lambda x: x[3], reverse=True)[:5]
                
                if not opportunities:
                    self.send_message("⚠️ لم يتم العثور على فرص صعود تنطبق عليها الشروط الصارمة حالياً.")
                    return
                    
                msg = f"🏆 *أفضل 5 فرص صعود لحظية في جلسة {sess}*:\n\n"
                for idx, opp in enumerate(opportunities):
                    sym, prc, chg, score, is_anom = opp
                    anom_tag = "🚨 شذوذ حجمي" if is_anom else "مستقر"
                    msg += (
                        f"{idx+1}. *{sym}* | السعر: `${prc:.2f}` | صعود: `+{chg:.2f}%`\n"
                        f"🔥 تطابق: `{score}%` | حالة السيولة: `{anom_tag}`\n"
                        f"*للاستشارة:* `استشارة {sym}` | *للشراء:* `شراء {sym} 10`\n\n"
                    )
                self.send_message(msg)
            except Exception as e:
                self.send_message(f"❌ حدث خطأ أثناء فحص السوق: {str(e)}")

        # 7. دليل المساعدة والتعليمات الافتراضي
        elif "دليل" in normalized_text or "تعليمات" in normalized_text or "مساعده" in normalized_text or "مساعدة" in normalized_text:
            help_text = (
                "👋 *مرحباً بك يا أبو فيصل في مساعد التداول التفاعلي!*\n\n"
                "إليك الأوامر المتاحة باللغة العربية للتحكم في رادارك:\n\n"
                "🔍 *استشارة وتحليل أي سهم:*\n"
                "👈 اكتب: `استشارة [رمز السهم]` (مثال: `استشارة CLSK`)\n\n"
                "🛒 *تنفيذ صفقات شراء افتراضية:*\n"
                "👈 اكتب: `شراء [رمز السهم] [الكمية]` (مثال: `شراء CLSK 100`)\n\n"
                "💰 *تنفيذ صفقات بيع افتراضية:*\n"
                "👈 اكتب: `بيع [رمز السهم] [الكمية]` (مثال: `بيع CLSK 50`)\n\n"
                "💼 *عرض المحفظة الافتراضية والسيولة النقدية:*\n"
                "👈 اضغط على زر: *عرض المحفظة* بالأسفل\n\n"
                "⚡ *مسح السوق وتصفية أفضل 5 فرص صعود:*\n"
                "👈 اضغط على زر: *تصفية السوق* بالأسفل\n\n"
                "🔍 *رصد أسهم التجميع الصامت المنخفضة الفلوت:*\n"
                "👈 اضغط على زر: *تجميع صامت* بالأسفل"
            )
            self.send_message(help_text)

        # 8. التحدث الحر عبر Gemini AI (إذا كانت المفاتيح مفعلة)
        else:
            if self.gemini_key:
                reply = self.call_gemini_advisor(text)
                if reply:
                    self.send_message(reply)
                else:
                    self.send_message("⚠️ لم يتمكن خادم المستشار من الرد حالياً.")
            else:
                self.process_message("دليل")

    def start_polling(self):
        print("BotListener: Start polling for Telegram updates...")
        while True:
            if not self.token:
                time.sleep(10)
                self.load_credentials()
                continue
                
            url = f"https://api.telegram.org/bot{self.token}/getUpdates"
            params = {"offset": self.offset, "timeout": 30}
            try:
                response = requests.get(url, params=params, timeout=35)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        for update in data.get("result", []):
                            self.offset = update.get("update_id") + 1
                            message = update.get("message", {})
                            chat = message.get("chat", {})
                            
                            if str(chat.get("id")) == str(self.chat_id):
                                text = message.get("text")
                                if text:
                                    self.process_message(text)
            except Exception as e:
                print(f"BotListener: Polling error: {str(e)}")
                
            time.sleep(1)

def start_bot_thread():
    bot = TelegramBotListener()
    bot.start_polling()
