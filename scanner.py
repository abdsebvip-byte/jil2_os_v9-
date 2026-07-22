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
        Pull all active tickers from TradingView's real-time API (NASDAQ/NYSE/AMEX).
        Falls back to Yahoo Finance screeners on failure (Zero Latency + High Stability).
        """
        import requests
        
        url = "https://scanner.tradingview.com/america/scan"
        payload = {
            "filter": [
                {"left": "close", "operation": "egreater", "right": 0.1},
                {"left": "close", "operation": "eless", "right": 20.0},
                {"left": "change", "operation": "egreater", "right": 2.0},
                {"left": "volume", "operation": "egreater", "right": 20000},
                {"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]}
            ],
            "options": {"active_symbols_only": True},
            "markets": ["america"],
            "symbols": {"query": {"types": []}, "tickers": []},
            "columns": [
                "name",
                "close",
                "change",
                "volume",
                "relative_volume_10d_active",
                "float_shares_outstanding",
                "average_volume_30d_calc",
                "VWAP",
                "Value.Traded"
            ],
            "sort": {"sortBy": "change", "sortOrder": "desc"},
            "range": [0, 100]
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Content-Type": "application/json"
        }
        
        try:
            print("fetch_all_us_symbols: Fetching real-time gainers from TradingView API...")
            response = requests.post(url, json=payload, headers=headers, timeout=8)
            if response.status_code == 200:
                data = response.json()
                rows = data.get("data", [])
                quotes = []
                seen_symbols = set()
                
                for item in rows:
                    sym = item.get("s", "")
                    d = item.get("d", [])
                    if not sym or len(d) < 9:
                        continue
                    ticker = sym.split(":")[-1]
                    if ticker and ticker.isalpha() and ticker not in seen_symbols:
                        seen_symbols.add(ticker)
                        
                        # Map TradingView variables to simulated Yahoo quote format
                        quotes.append({
                            "symbol": ticker,
                            "regularMarketPrice": float(d[1] or 0.0),
                            "regularMarketChangePercent": float(d[2] or 0.0),
                            "regularMarketVolume": float(d[3] or 0.0),
                            "averageDailyVolume3Month": float(d[6] or 100000.0),
                            "regularMarketPreviousClose": float(d[1] or 0.0) / (1.0 + (float(d[2] or 0.0) / 100.0)) if d[2] else float(d[1] or 0.0),
                            "regularMarketOpen": float(d[1] or 0.0),
                            "preMarketPrice": float(d[1] or 0.0),
                            "preMarketChangePercent": float(d[2] or 0.0),
                            "postMarketPrice": float(d[1] or 0.0),
                            "postMarketChangePercent": float(d[2] or 0.0),
                            "bid": float(d[1] or 0.0),
                            "ask": float(d[1] or 0.0),
                            "bidSize": 100.0,
                            "askSize": 100.0,
                            "vwap": float(d[7] or 0.0),
                            "value_traded": float(d[8] or 0.0),
                            "float_shares_outstanding": float(d[5] or 10000000.0)
                        })
                
                self.cached_quotes = quotes
                symbols = list(seen_symbols)
                print(f"fetch_all_us_symbols (TradingView): Found {len(symbols)} real-time active stocks.")
                return symbols
            else:
                print(f"fetch_all_us_symbols: TradingView returned status {response.status_code}. Reverting to Yahoo fallback...")
                raise ValueError("TradingView API Down")
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
                "float_shares_outstanding": q.get("float_shares_outstanding")
            })
        await asyncio.sleep(0.02)
        return formatted_quotes
