# intraday_tracker.py
import pandas as pd
from yahooquery import Ticker

def get_historical_features(symbols):
    """
    Download the last 15 days of daily history and key statistics (float and short interest)
    for the scanned symbols, and calculate features for the XGBoost model.
    """
    if not symbols:
        return {}
        
    print(f"IntradayTracker: Fetching features for {len(symbols)} symbols in bulk...")
    feature_map = {}
    
    # 1. Fetch key stats (float shares & short interest)
    stats_data = {}
    try:
        # Query in batches of 40 to prevent timeouts
        batch_size = 40
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            tickers_batch = Ticker(batch)
            stats = tickers_batch.key_stats
            for sym in batch:
                if sym in stats and isinstance(stats[sym], dict):
                    float_shares = float(stats[sym].get("floatShares") or 10000000.0)
                    short_percent = float(stats[sym].get("shortPercentOfFloat") or 0.0) * 100.0
                    stats_data[sym] = {
                        "float_shares_m": float_shares / 1000000.0, # normalized in millions
                        "short_percent": short_percent
                    }
    except Exception as e:
        print(f"IntradayTracker Stats Warning: {e}")
        
    # 2. Fetch history
    try:
        tickers = Ticker(symbols)
        df_hist = tickers.history(period="15d")
        if df_hist is None or df_hist.empty:
            return {}
            
        df_hist = df_hist.reset_index()
        df_hist['date'] = pd.to_datetime(df_hist['date'], utc=True)
        df_hist = df_hist.set_index(['symbol', 'date']).sort_index()
        
        unique_syms = df_hist.index.levels[0]
        for sym in unique_syms:
            try:
                stock_data = df_hist.loc[sym].copy()
                if len(stock_data) < 11:
                    continue
                    
                row_prev = stock_data.iloc[-1]
                
                # Previous Price Change %
                prev_close = float(row_prev['close'])
                prev_prev_close = float(stock_data['close'].iloc[-2])
                prev_change = ((prev_close - prev_prev_close) / prev_prev_close) * 100 if prev_prev_close > 0 else 0.0
                
                # Previous RVOL
                avg_vol_10d = stock_data['volume'].iloc[:-1].mean()
                prev_rvol = float(row_prev['volume']) / avg_vol_10d if avg_vol_10d > 0 else 1.0
                
                # 10-day Bollinger Band Width (BBW)
                std_10d = closes_10d.std()
                bbw = (4.0 * std_10d) / mean_p if mean_p > 0 else 0.1
                
                # Check historical BBW values over the last 5 days to identify a squeeze
                bbw_list = []
                for j in range(5):
                    sub_closes = stock_data['close'].iloc[-10 - j : -j] if j > 0 else closes_10d
                    sub_mean = sub_closes.mean()
                    sub_std = sub_closes.std()
                    bbw_list.append((4.0 * sub_std) / sub_mean if sub_mean > 0 else 0.1)
                is_squeeze = bbw == min(bbw_list)
                
                # Volatility Contraction Pattern (VCP) detection
                range_3d = stock_data['high'].iloc[-3:].max() - stock_data['low'].iloc[-3:].min()
                range_10d = stock_data['high'].iloc[-10:].max() - stock_data['low'].iloc[-10:].min()
                is_vcp = range_3d < (0.6 * range_10d) if range_10d > 0 else False
                
                # Calculate Squeeze & Compression Score (0 - 100)
                sq_score = 0
                if is_squeeze:
                    sq_score += 50
                if is_vcp:
                    sq_score += 30
                if prev_rvol < 1.2:
                    sq_score += 20
                
                # Fundamental features
                f_data = stats_data.get(sym, {"float_shares_m": 10.0, "short_percent": 0.0})
                
                feature_map[sym] = {
                    "volatility_10d": round(volatility_10d, 2),
                    "prev_rvol": round(prev_rvol, 2),
                    "prev_change": round(prev_change, 2),
                    "float_shares_m": round(f_data["float_shares_m"], 2),
                    "short_percent": round(f_data["short_percent"], 2),
                    "squeeze_score": sq_score
                }
            except Exception as e:
                pass
                
        return feature_map
    except Exception as e:
        print(f"IntradayTracker Error: {e}")
        return {}
