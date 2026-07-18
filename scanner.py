# module: scanner.py
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
        Or weekends (Saturday/Sunday) -> NIGHT_CLOSED
        """
        est_tz = pytz.timezone('US/Eastern')
        now_est = datetime.now(est_tz)
        
        # التحقق من عطلة نهاية الأسبوع (السبت = 5، الأحد = 6)
        if now_est.weekday() >= 5:
            return "NIGHT_CLOSED"
            
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
        Pull all active tickers from multiple Yahoo Finance screeners to expand coverage.
        Queries 100% valid Yahoo screeners.
        """
        screeners_to_query = [
            'day_gainers', 
            'most_actives', 
            'small_cap_gainers'
        ]
        try:
            data = self.screener.get_screeners(screen_ids=screeners_to_query, count=150)
            quotes = []
            seen_symbols = set()
            
            for key in screeners_to_query:
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
            print(f"fetch_all_us_symbols: Found {len(symbols)} unique active stocks moving in the market.")
            return symbols
        except Exception as e:
            print(f"fetch_all_us_symbols: Screener query failed: {str(e)}")
            self.cached_quotes = []
            return ["AMC", "GME", "SNDL", "NIO", "PLTR", "SOFI", "LCID", "MARA", "RIOT"]

    async def scan_entire_market(self):
        """
        Return the pre-fetched quotes in a structured, standard format.
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
        await asyncio.sleep(0.05)
        return formatted_quotes
