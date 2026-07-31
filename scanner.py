# module: scanner.py
import asyncio
import pandas as pd
from datetime import datetime
import pytz
from yahooquery import Screener

class FreeMarketScanner:
    def __init__(self):
        # تأجيل تهيئة Screener حتى أول استخدام فعلي لتجنب الـ timeout عند الإقلاع
        self._screener = None
        self.cached_quotes = []

    @property
    def screener(self):
        if self._screener is None:
            self._screener = Screener()
        return self._screener

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
        Pull active tickers from TradingView's real-time API (NASDAQ/NYSE/AMEX).
        Uses a Dual Engine (RVOL Acceleration + Top Gainers) scanning up to 1,000 stocks simultaneously.
        This guarantees early discovery of stocks right as volume spikes (+1.5% to +10%) before prices explode.
        """
        import requests
        
        url = "https://scanner.tradingview.com/america/scan"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Content-Type": "application/json"
        }

        columns = [
            "name", "close", "change", "volume", "relative_volume_10d_active",
            "float_shares_outstanding", "average_volume_30d_calc", "VWAP", "Value.Traded",
            "premarket_close", "premarket_change", "postmarket_close", "postmarket_change",
            "short_percent_of_float", "short_ratio"
        ]

        # Engine 1: Early Volume Acceleration / RVOL Spikes (Early Discovery at +1.5% to +15%)
        payload_rvol = {
            "filter": [
                {"left": "close", "operation": "egreater", "right": 0.1},
                {"left": "close", "operation": "eless", "right": 30.0},
                {"left": "change", "operation": "egreater", "right": 1.5},
                {"left": "volume", "operation": "egreater", "right": 15000},
                {"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]}
            ],
            "options": {"active_symbols_only": True},
            "markets": ["america"],
            "symbols": {"query": {"types": []}, "tickers": []},
            "columns": columns,
            "sort": {"sortBy": "relative_volume_10d_active", "sortOrder": "desc"},
            "range": [0, 500]
        }

        # Engine 2: Top Market Price Gainers
        payload_gainers = {
            "filter": [
                {"left": "close", "operation": "egreater", "right": 0.1},
                {"left": "close", "operation": "eless", "right": 30.0},
                {"left": "change", "operation": "egreater", "right": 2.0},
                {"left": "volume", "operation": "egreater", "right": 20000},
                {"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]}
            ],
            "options": {"active_symbols_only": True},
            "markets": ["america"],
            "symbols": {"query": {"types": []}, "tickers": []},
            "columns": columns,
            "sort": {"sortBy": "change", "sortOrder": "desc"},
            "range": [0, 500]
        }

        quotes = []
        seen_symbols = set()

        try:
            for payload, label in [(payload_rvol, "RVOL Early Discovery"), (payload_gainers, "Top Gainers")]:
                try:
                    res = requests.post(url, json=payload, headers=headers, timeout=8)
                    if res.status_code == 200:
                        rows = res.json().get("data", [])
                        for item in rows:
                            sym = item.get("s", "")
                            d = item.get("d", [])
                            if not sym or len(d) < 9:
                                continue
                            ticker = sym.split(":")[-1]
                            if ticker and ticker.isalpha() and ticker not in seen_symbols:
                                seen_symbols.add(ticker)
                                quotes.append({
                                    "symbol": ticker,
                                    "regularMarketPrice": float(d[1] or 0.0),
                                    "regularMarketChangePercent": float(d[2] or 0.0),
                                    "regularMarketVolume": float(d[3] or 0.0),
                                    "averageDailyVolume3Month": float(d[6] or 100000.0),
                                    "regularMarketPreviousClose": float(d[1] or 0.0) / (1.0 + (float(d[2] or 0.0) / 100.0)) if d[2] else float(d[1] or 0.0),
                                    "regularMarketOpen": float(d[1] or 0.0),
                                    "preMarketPrice": float(d[9] or d[1] or 0.0) if len(d) > 9 and d[9] is not None else float(d[1] or 0.0),
                                    "preMarketChangePercent": float(d[10] or 0.0) if len(d) > 10 and d[10] is not None else 0.0,
                                    "postMarketPrice": float(d[11] or d[1] or 0.0) if len(d) > 11 and d[11] is not None else float(d[1] or 0.0),
                                    "postMarketChangePercent": float(d[12] or 0.0) if len(d) > 12 and d[12] is not None else 0.0,
                                    "bid": float(d[1] or 0.0),
                                    "ask": float(d[1] or 0.0),
                                    "bidSize": 100.0,
                                    "askSize": 100.0,
                                    "vwap": float(d[7] or 0.0),
                                    "value_traded": float(d[8] or 0.0),
                                    "float_shares_outstanding": float(d[5] or 10000000.0),
                                    "short_percent": float(d[13] or 0.0) if len(d) > 13 and d[13] is not None else 0.0,
                                    "days_to_cover": float(d[14] or 0.0) if len(d) > 14 and d[14] is not None else 0.0
                                })
                except Exception as e:
                    print(f"fetch_all_us_symbols: {label} query error ({e})")

            if quotes:
                self.cached_quotes = quotes
                symbols = list(seen_symbols)
                print(f"fetch_all_us_symbols (Dual Engine): Found {len(symbols)} real-time active stocks across RVOL and Gainers.")
                return symbols
            else:
                print("fetch_all_us_symbols: TradingView API returned empty. Reverting to Yahoo fallback...")
                raise ValueError("TradingView API Empty")
        except Exception as tv_err:
            print(f"fetch_all_us_symbols: TradingView query failed ({str(tv_err)}). Reverting to Yahoo Finance fallback...")
            # Fallback to Yahoo screeners
            screeners_to_query = ['day_gainers', 'most_actives', 'small_cap_gainers']
            try:
                data = self.screener.get_screeners(screen_ids=screeners_to_query, count=100)
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
                print(f"fetch_all_us_symbols (Yahoo Fallback): Found {len(symbols)} active stocks.")
                return symbols
            except Exception as yf_err:
                print(f"fetch_all_us_symbols: Yahoo Fallback failed too ({str(yf_err)}). Using offline hardcoded tickers.")
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
                "marketState": q.get("marketState", "REGULAR"),
                "regularMarketOpen": q.get("regularMarketOpen", 0.0),
                "regularMarketPreviousClose": q.get("regularMarketPreviousClose", 0.0),
                "bid": q.get("bid", 0.0),
                "ask": q.get("ask", 0.0),
                "bidSize": q.get("bidSize", 0.0),
                "askSize": q.get("askSize", 0.0),
                "vwap": q.get("vwap", 0.0),
                "value_traded": q.get("value_traded", 0.0),
                "float_shares_outstanding": q.get("float_shares_outstanding"),
                "short_percent": q.get("short_percent", 0.0),
                "days_to_cover": q.get("days_to_cover", 0.0)
            })
        await asyncio.sleep(0.02)
        return formatted_quotes

    def fetch_retail_trending_symbols(self):
        """
        Fetch the top popular and trending tickers on Yahoo Finance and Reddit WallStreetBets.
        Returns a dict: {'yahoo': set(), 'reddit': set()}
        """
        import requests
        
        yahoo_trending = set()
        reddit_trending = set()
        
        # 1. Fetch from Yahoo Finance Trending
        url_yf = "https://query1.finance.yahoo.com/v1/finance/trending/US"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        try:
            r = requests.get(url_yf, headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json().get("finance", {}).get("result", [])
                for item in data:
                    quotes = item.get("quotes", [])
                    for q in quotes:
                        sym = q.get("symbol")
                        if sym and sym.isalpha():
                            yahoo_trending.add(sym)
        except Exception as e:
            print(f"fetch_retail_trending_symbols: Yahoo error ({e})")
            
        # 2. Fetch from Reddit WSB (Tradestie)
        url_reddit = "https://tradestie.com/api/v1/apps/reddit"
        try:
            r = requests.get(url_reddit, timeout=5)
            if r.status_code == 200:
                data = r.json()
                for item in data:
                    sym = item.get("ticker")
                    if sym and sym.isalpha():
                        reddit_trending.add(sym)
        except Exception as e:
            print(f"fetch_retail_trending_symbols: Reddit error ({e})")
            
        return {
            "yahoo": yahoo_trending,
            "reddit": reddit_trending
        }
