# intraday_tracker.py
import pandas as pd
from yahooquery import Ticker

def get_historical_features(symbols):
    """
    Download the last 15 days of daily history for the scanned symbols
    and calculate historical features (volatility_10d, prev_rvol, prev_change).
    """
    if not symbols:
        return {}
        
    print(f"IntradayTracker: Fetching 15-day history for {len(symbols)} symbols in bulk...")
    try:
        tickers = Ticker(symbols)
        df_hist = tickers.history(period="15d")
        if df_hist is None or df_hist.empty:
            return {}
            
        df_hist = df_hist.reset_index()
        df_hist['date'] = pd.to_datetime(df_hist['date'], utc=True)
        df_hist = df_hist.set_index(['symbol', 'date']).sort_index()
        
        feature_map = {}
        unique_syms = df_hist.index.levels[0]
        
        for sym in unique_syms:
            try:
                stock_data = df_hist.loc[sym].copy()
                if len(stock_data) < 11:
                    continue
                    
                # Yesterday's row (the last complete daily candle)
                row_prev = stock_data.iloc[-1]
                
                # 1. Yesterday's price change %
                prev_close = float(row_prev['close'])
                prev_open = float(row_prev['open'])
                # Shift by 2 to get yesterday's previous close for accurate change calculation
                prev_prev_close = float(stock_data['close'].iloc[-2])
                prev_change = ((prev_close - prev_prev_close) / prev_prev_close) * 100 if prev_prev_close > 0 else 0.0
                
                # 2. Yesterday's RVOL (volume / 20-day average)
                # Since we only have 15 days, we use the average of the last 10 days for volume baseline
                avg_vol_10d = stock_data['volume'].iloc[:-1].mean()
                prev_rvol = float(row_prev['volume']) / avg_vol_10d if avg_vol_10d > 0 else 1.0
                
                # 3. Consolidation Volatility over last 10 days
                closes_10d = stock_data['close'].iloc[-10:]
                max_p = closes_10d.max()
                min_p = closes_10d.min()
                mean_p = closes_10d.mean()
                volatility_10d = ((max_p - min_p) / mean_p) * 100 if mean_p > 0 else 0.0
                
                feature_map[sym] = {
                    "volatility_10d": round(volatility_10d, 2),
                    "prev_rvol": round(prev_rvol, 2),
                    "prev_change": round(prev_change, 2)
                }
            except Exception as e:
                pass
                
        return feature_map
    except Exception as e:
        print(f"IntradayTracker Error: {e}")
        return {}
