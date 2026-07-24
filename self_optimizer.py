# self_optimizer.py
import os
import requests
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from database import QuantDatabase
from intelligence import QuantIntelligence
from scanner import FreeMarketScanner

class QuantSelfOptimizer:
    def __init__(self, db_path="quant_platform.db"):
        self.db = QuantDatabase(db_path)
        self.intel = QuantIntelligence()
        self.scanner = FreeMarketScanner()

    def fetch_top_daily_gainers(self):
        """
        Fetch the top 20 gainer symbols in the US market using TradingView America Scan API.
        """
        url = "https://scanner.tradingview.com/america/scan"
        payload = {
            "filter": [
                {"left": "close", "operation": "egreater", "right": 0.5},
                {"left": "change", "operation": "egreater", "right": 10.0},
                {"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]}
            ],
            "options": {"active_symbols_only": True},
            "markets": ["america"],
            "symbols": {"query": {"types": []}, "tickers": []},
            "columns": ["name", "close", "change", "volume", "relative_volume_10d_active", "float_shares_outstanding", "average_volume_30d_calc", "VWAP", "Value.Traded"],
            "sort": {"sortBy": "change", "sortOrder": "desc"},
            "range": [0, 20]
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json().get("data", [])
                symbols = []
                for item in data:
                    sym = item.get("s", "").split(":")[-1]
                    if sym and sym.isalpha() and len(sym) <= 4:
                        symbols.append(sym)
                return symbols
        except Exception as e:
            print(f"Error fetching top daily gainers: {e}")
        return []

    def diagnose_symbol(self, symbol, current_thresholds):
        """
        Analyze why a specific symbol was skipped under the current thresholds.
        """
        import yahooquery as yq
        try:
            ticker = yq.Ticker(symbol)
            price_data = ticker.price.get(symbol, {})
            if not isinstance(price_data, dict):
                return "No data available from Yahoo Query"
                
            price = float(price_data.get("regularMarketPrice") or 0.0)
            prev_close = float(price_data.get("regularMarketPreviousClose") or price)
            change = ((price - prev_close) / prev_close * 100.0) if prev_close > 0 else 0.0
            open_price = float(price_data.get("regularMarketOpen") or price)
            gap = ((open_price - prev_close) / prev_close * 100.0) if prev_close > 0 else 0.0
            
            reasons = []
            if price > 20.0 or price <= 0.0:
                reasons.append("Price outside filter limit (<= $20)")
            if abs(gap) > current_thresholds["gap"]:
                reasons.append(f"Gap Up too high (+{gap:.1f}% > +{current_thresholds['gap']:.1f}%)")
            if change > current_thresholds["fomo"]:
                reasons.append(f"FOMO block limit reached (+{change:.1f}% > +{current_thresholds['fomo']:.1f}%)")
            
            # RVOL
            avg_vol = float(price_data.get("averageDailyVolume3Month") or 100000.0)
            current_vol = float(price_data.get("regularMarketVolume") or 0.0)
            rvol = current_vol / avg_vol if avg_vol > 0 else 1.0
            if rvol < current_thresholds.get("rvol_min", 4.0):
                reasons.append(f"RVOL too low ({rvol:.2f}x < {current_thresholds.get('rvol_min', 4.0):.1f}x)")
                
            if not reasons:
                return "Passed all filters but probably conviction score was below 80%"
            return ", ".join(reasons)
        except Exception as e:
            return f"Diagnostic Error: {e}"

    def run_optimization(self):
        """
        Evaluates top daily gainers and optimizes filters parameters within safe limits.
        """
        top_gainers = self.fetch_top_daily_gainers()
        if not top_gainers:
            return {"status": "SKIPPED", "reason": "Could not retrieve top daily gainers."}

        current = self.intel.get_thresholds()
        
        # Safe ranges for tuning parameters
        fomo_candidates = [35.0, 40.0, 45.0, 50.0, 55.0, 60.0, 65.0]
        gap_candidates = [10.0, 15.0, 20.0, 25.0, 30.0]
        whale_ext_candidates = [200000.0, 300000.0, 400000.0, 500000.0, 750000.0, 1000000.0]
        whale_reg_candidates = [1000000.0, 1250000.0, 1500000.0, 1750000.0, 2000000.0]
        rvol_min = float(os.getenv("RVOL_MIN", 4.0))
        float_max = float(os.getenv("FLOAT_MAX", 15000000.0))

        best_fomo = current["fomo"]
        best_gap = current["gap"]
        best_whale_ext = current["whale_ext"]
        best_whale_reg = current["whale_reg"]
        best_catch_rate = 0.0
        
        import yahooquery as yq
        symbols_data = []
        try:
            tickers = yq.Ticker(top_gainers)
            price_data = tickers.price
            for sym in top_gainers:
                if sym in price_data and isinstance(price_data[sym], dict):
                    p_info = price_data[sym]
                    price = float(p_info.get("regularMarketPrice") or 0.0)
                    prev_close = float(p_info.get("regularMarketPreviousClose") or price)
                    change = ((price - prev_close) / prev_close * 100.0) if prev_close > 0 else 0.0
                    open_price = float(p_info.get("regularMarketOpen") or price)
                    gap = ((open_price - prev_close) / prev_close * 100.0) if prev_close > 0 else 0.0
                    
                    if 0.0 < price <= 20.0 and change >= 3.0:
                        symbols_data.append({"symbol": sym, "gap": abs(gap), "change": change})
        except Exception as e:
            print(f"Error compiling optimization simulation data: {e}")
            
        if not symbols_data:
            return {"status": "SKIPPED", "reason": "No valid pricing data found for daily gainers."}

        # Grid search optimization
        for f in fomo_candidates:
            for g in gap_candidates:
                # Calculate simulated catch rate
                captured = 0
                for data in symbols_data:
                    # Stock must pass the gap shield limit and fomo block limit
                    if data["gap"] <= g and data["change"] <= f:
                        captured += 1
                rate = (captured / len(symbols_data)) * 100.0
                if rate > best_catch_rate:
                    best_catch_rate = rate
                    best_fomo = f
                    best_gap = g

        # Choose the optimal whale limits adaptively based on today's volumes
        best_whale_ext = 400000.0 if best_catch_rate > 50.0 else 500000.0
        best_whale_reg = 1250000.0 if best_catch_rate > 50.0 else 1500000.0

        # Apply parameters to config.env
        self.update_config_env(best_fomo, best_gap, best_whale_ext, best_whale_reg, rvol_min, float_max)
        
        # Log to DB
        missed_list = ", ".join(top_gainers)
        self.db.log_optimization_run(missed_list, best_fomo, best_gap, best_whale_ext, best_whale_reg, best_catch_rate)
        
        return {
            "status": "OPTIMIZED",
            "fomo": best_fomo,
            "gap": best_gap,
            "whale_ext": best_whale_ext,
            "whale_reg": best_whale_reg,
            "catch_rate": best_catch_rate,
            "symbols_processed": len(symbols_data)
        }

    def update_config_env(self, fomo, gap, whale_ext, whale_reg, rvol_min=4.0, float_max=15000000.0):
        """
        Overwrite the parameters in config.env safely.
        """
        env_path = "config.env"
        lines = []
        if os.path.exists(env_path):
            lines = open(env_path, encoding='utf-8').read().replace('\r\n', '\n').split('\n')
        
        # Remove existing definitions of these variables
        new_lines = []
        for line in lines:
            if not any(line.startswith(var) for var in [
                "FOMO_THRESHOLD=",
                "GAP_THRESHOLD=",
                "WHALE_THRESHOLD_EXT=",
                "WHALE_THRESHOLD_REG=",
                "RVOL_MIN=",
                "FLOAT_MAX=",
            ]):
                new_lines.append(line)
        
        # Append new values
        new_lines.append(f"FOMO_THRESHOLD={fomo}")
        new_lines.append(f"GAP_THRESHOLD={gap}")
        new_lines.append(f"WHALE_THRESHOLD_EXT={whale_ext}")
        new_lines.append(f"WHALE_THRESHOLD_REG={whale_reg}")
        new_lines.append(f"RVOL_MIN={rvol_min}")
        new_lines.append(f"FLOAT_MAX={float_max}")
        
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))
        
        # Reload dotenv
        load_dotenv("config.env", override=True)

if __name__ == "__main__":
    opt = QuantSelfOptimizer()
    print("Running Self Optimizer manual test...")
    res = opt.run_optimization()
    print("Result:", res)
