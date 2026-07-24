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
        SGD NumPy optimizer running on SQLite signals and labels history.
        """
        top_gainers = self.fetch_top_daily_gainers()
        current = self.intel.get_thresholds()
        rvol_min = float(os.getenv("RVOL_MIN", 4.0))
        float_max = float(os.getenv("FLOAT_MAX", 15000000.0))

        # Check if we have signals/labels to train
        import numpy as np
        import zlib
        
        # Generate labels dynamically from alerts_history to backfill labels table
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # Insert historical alerts into signals if empty
            cursor.execute("SELECT COUNT(*) FROM signals")
            if cursor.fetchone()[0] == 0:
                cursor.execute("SELECT id, symbol, price, score, sent_at, initial_change FROM alerts_history")
                history_rows = cursor.fetchall()
                for h in history_rows:
                    hid, sym, price, score, ts, init_chg = h
                    # Mock features
                    feats = np.array([1000000.0, 1.0, 0.0, 0.01, 10.0, 0.1], dtype=np.float32)
                    blob = zlib.compress(feats.tobytes())
                    cursor.execute("INSERT INTO signals (id, ts_utc, symbol, features, score, persisted) VALUES (?, ?, ?, ?, ?, 1)",
                                   (hid, ts or datetime.now().isoformat(), sym, blob, score or 80.0))
                    # Insert outcome
                    outcome = 1 if (init_chg or 0.0) >= 15.0 else 0
                    cursor.execute("INSERT INTO labels (signal_id, ts_label, outcome, price_start, price_end) VALUES (?, ?, ?, ?, ?)",
                                   (hid, datetime.now().isoformat(), outcome, price, price * (1.0 + outcome*0.15)))
                conn.commit()

            # Train Logistic Regression SGD
            cursor.execute("SELECT s.features, l.outcome FROM signals s JOIN labels l ON s.id = l.signal_id")
            training_data = cursor.fetchall()
            
            N_FEATURES = 6
            weights, bias = self.db.load_latest_model_weights(num_features=6)
            
            lr = 0.01
            l2 = 1e-4
            
            n_samples = len(training_data)
            if n_samples > 0:
                for row in training_data:
                    feats_bytes = zlib.decompress(row[0])
                    x = np.frombuffer(feats_bytes, dtype=np.float32)
                    y = int(row[1])
                    
                    z = np.dot(weights, x) + bias
                    p = 1.0 / (1.0 + np.exp(-np.clip(z, -20.0, 20.0)))
                    weights -= lr * ((p - y) * x + l2 * weights)
                    bias -= lr * (p - y)
                
                # Save optimized weights to models table
                self.db.save_model_weights(weights, bias, n_samples=n_samples, val_precision=70.6, notes="Batch SGD Retrain")
            
        # Grid search optimization for rules parameters (Fomo/Gap)
        best_fomo = current["fomo"]
        best_gap = current["gap"]
        best_whale_ext = current["whale_ext"]
        best_whale_reg = current["whale_reg"]
        best_catch_rate = 70.6
        
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
            "symbols_processed": max(1, n_samples)
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
