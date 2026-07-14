# module: yahoo_scanner.py
import asyncio
import pandas as pd
from datetime import datetime
import pytz
from yahooquery import Screener

class FreeMarketScanner:
    def __init__(self):
        self.screener = Screener()
        self.cached_quotes = []

    def get_current_market_session(self):
        """
        Detect current US market session dynamically based on Eastern Standard Time (EST).
        Pre-market: 04:00 - 09:30 EST
        Regular market: 09:30 - 16:00 EST
        After-hours: 16:00 - 20:00 EST
        Night/Closed: 20:00 - 04:00 EST
        """
        est_tz = pytz.timezone('US/Eastern')
        now_est = datetime.now(est_tz)
        current_time = now_est.time()
        
        pre_start = datetime.strptime("04:00:00", "%H:%M:%S").time()
        reg_start = datetime.strptime("09:30:00", "%H:%M:%S").time()
        reg_end = datetime.strptime("16:00:00", "%H:%M:%S").time()
        post_end = datetime.strptime("20:00:00", "%H:%M:%S").time()
        
        if pre_start <= current_time < reg_start:
            return "PRE_MARKET"
        elif reg_start <= current_time < reg_end:
            return "REGULAR_SESSION"
        elif reg_end <= current_time < post_end:
            return "AFTER_HOURS"
        else:
            return "NIGHT_CLOSED"

    def fetch_all_us_symbols(self):
        """
        Pull all active tickers from Yahoo Finance screeners.
        """
        print("fetch_all_us_symbols: Querying Yahoo Screener for active symbols...")
        try:
            # نسحب 200 سهم من الصاعدين و 200 سهم من الأكثر نشاطاً لضمان تغطية واسعة
            data = self.screener.get_screeners(screen_ids=['day_gainers', 'most_actives'], count=200)
            
            quotes = []
            seen_symbols = set()
            
            for key in ['day_gainers', 'most_actives']:
                screener_data = data.get(key, {})
                if isinstance(screener_data, dict):
                    raw_quotes = screener_data.get('quotes', [])
                    for q in raw_quotes:
                        symbol = q.get('symbol')
                        if symbol and symbol.isalpha() and symbol not in seen_symbols:
                            seen_symbols.add(symbol)
                            quotes.append(q)
            
            self.cached_quotes = quotes
            symbols = list(seen_symbols)
            print(f"fetch_all_us_symbols: Found {len(symbols)} active stocks moving in the entire market.")
            return symbols
        except Exception as e:
            print(f"fetch_all_us_symbols: Screener query failed: {str(e)}")
            self.cached_quotes = []
            return ["AMC", "GME", "SNDL", "NIO", "PLTR", "SOFI", "LCID", "MARA", "RIOT"]

    async def scan_entire_market(self, all_symbols):
        """
        Return the pre-fetched quotes.
        """
        formatted_quotes = []
        for q in self.cached_quotes:
            formatted_quotes.append({
                "symbol": q.get("symbol"),
                "regularMarketPrice": q.get("regularMarketPrice", 0.0),
                "regularMarketChangePercent": q.get("regularMarketChangePercent", 0.0),
                "preMarketPrice": q.get("preMarketPrice"),
                "preMarketChangePercent": q.get("preMarketChangePercent"),
                "postMarketPrice": q.get("postMarketPrice"),
                "postMarketChangePercent": q.get("postMarketChangePercent"),
                "regularMarketVolume": q.get("regularMarketVolume", 0.0),
                "averageDailyVolume3Month": q.get("averageDailyVolume3Month", 100000.0),
                "marketState": q.get("marketState", ""),
                "regularMarketOpen": q.get("regularMarketOpen", 0.0),
                "regularMarketPreviousClose": q.get("regularMarketPreviousClose", 0.0),
                "bid": q.get("bid", 0.0),
                "ask": q.get("ask", 0.0),
                "bidSize": q.get("bidSize", 0.0),
                "askSize": q.get("askSize", 0.0)
            })
        await asyncio.sleep(0.1)
        return formatted_quotes

    def calculate_7_layer_conviction(self, quote, session):
        """
        Calculate Abu Faisal's 7-Layer Conviction Matching Score (0 - 100%).
        Returns (Score_Percentage, Matches_Details)
        """
        score = 0
        details = {}
        
        price = float(quote.get("regularMarketPrice", 0.0))
        price_change = float(quote.get("regularMarketChangePercent", 0.0))
        open_price = float(quote.get("regularMarketOpen", price))
        prev_close = float(quote.get("regularMarketPreviousClose", price))
        
        # مواءمة الأسعار بناءً على الجلسة الحالية
        if session == "PRE_MARKET" and quote.get("preMarketPrice") is not None:
            price = float(quote.get("preMarketPrice"))
        elif session == "AFTER_HOURS" and quote.get("postMarketPrice") is not None:
            price = float(quote.get("postMarketPrice"))

        # الطبقة 1: فلتر السعر (<= 20$)
        if 0.0 < price <= 20.0:
            score += 15
            details["Price_Filter"] = True
        else:
            details["Price_Filter"] = False

        # الطبقة 2: درع الفجوة الافتتاحية (أقل من 15%)
        # الفجوة = (افتتاح اليوم - إغلاق أمس) / إغلاق أمس
        gap = ((open_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
        if abs(gap) <= 15.0:
            score += 15
            details["Gap_Shield"] = True
        else:
            details["Gap_Shield"] = False

        # الطبقة 3: منطقة صعود الاختراق المبكر (مضاد الـ FOMO بين +5% و +15%)
        # إذا تجاوز +40% يغلق المنفذ فوراً (يخصم نقاط)
        if 5.0 <= price_change <= 15.0:
            score += 20
            details["Early_Breakout"] = "IDEAL"
        elif 15.0 < price_change <= 40.0:
            score += 10
            details["Early_Breakout"] = "HIGH"
        elif price_change > 40.0:
            score -= 10
            details["Early_Breakout"] = "FOMO_BLOCKED"
        else:
            details["Early_Breakout"] = "LOW_CHANGE"

        # الطبقة 4: تسارع السيولة اللحظي (RVOL >= 1.2x)
        volume = float(quote.get("regularMarketVolume", 0.0))
        avg_volume = float(quote.get("averageDailyVolume3Month", 100000.0))
        rvol = volume / avg_volume if avg_volume > 0 else 1.0
        if rvol >= 1.2:
            score += 20
            details["RVOL_Acceleration"] = True
        else:
            details["RVOL_Acceleration"] = False

        # الطبقة 5: تدفق كتل الحيتان الافتراضي (Whale Block Trades)
        # نقوم بمحاكاة رصد الكتل الكبيرة بناءً على حجم التداول الكثيف بالنسبة لمتوسط اليوم
        if rvol >= 2.5:
            score += 15
            details["Whale_Block"] = True
        else:
            details["Whale_Block"] = False

        # الطبقة 6: حساب عدم توازن عمق السوق التجريبي (Order Book Imbalance - OBI)
        # OBI = (Bid Size - Ask Size) / (Bid Size + Ask Size)
        bid_size = float(quote.get("bidSize", 0.0))
        ask_size = float(quote.get("askSize", 0.0))
        obi = (bid_size - ask_size) / (bid_size + ask_size) if (bid_size + ask_size) > 0 else 0.0
        if obi >= 0.3:
            score += 10
            details["OBI_Imbalance"] = True
        else:
            details["OBI_Imbalance"] = False

        # الطبقة 7: المحفز الإخباري الافتراضي (Catalyst Sentiment Analysis)
        # نقوم بتقييم وجود خبر إيجابي بناءً على ارتباط السعر المرتفع بحجم تداول كثيف
        if price_change > 10.0 and rvol >= 1.5:
            score += 5
            details["News_Catalyst"] = "STRONG_POSITIVE"
        else:
            details["News_Catalyst"] = "NEUTRAL"

        # حصر النتيجة بين 0% و 100%
        final_score = max(0, min(100, score))
        return final_score, details, price, price_change, rvol

    def filter_breakout_opportunities(self, raw_quotes, session):
        """
        Process and calculate conviction scores for all scanned symbols based on session.
        """
        opportunities = []
        for quote in raw_quotes:
            try:
                score, details, price, change, rvol = self.calculate_7_layer_conviction(quote, session)
                
                # فلاتر التصفية الصارمة للمنصة:
                # 1. السعر تحت 20$
                # 2. التغير اليومي إيجابي (أكبر من 3%)
                # 3. عدم تجاوز فخ الـ FOMO الحاد (> 45%)
                if price <= 0.0 or price > 20.0 or change < 3.0 or change > 45.0:
                    continue

                opportunities.append({
                    "Symbol": quote.get("symbol"),
                    "Price": price,
                    "Change_%": change,
                    "Volume": float(quote.get("regularMarketVolume", 0.0)),
                    "RVOL": rvol,
                    "Conviction_Score": score,
                    "Matches": details
                })
            except Exception as e:
                continue
                
        df = pd.DataFrame(opportunities)
        if not df.empty:
            df = df.sort_values(by="Conviction_Score", ascending=False)
        return df

if __name__ == "__main__":
    scanner = FreeMarketScanner()
    sess = scanner.get_current_market_session()
    print(f"Current Session detected: {sess}")
    symbols = scanner.fetch_all_us_symbols()
    if symbols:
        import asyncio
        loop = asyncio.get_event_loop()
        raw_data = loop.run_until_complete(scanner.scan_entire_market(symbols))
        df_ops = scanner.filter_breakout_opportunities(raw_data, sess)
        print("\n--- Conviction Score Results ---")
        if not df_ops.empty:
            print(df_ops[["Symbol", "Price", "Change_%", "RVOL", "Conviction_Score"]].head(15).to_string(index=False))
