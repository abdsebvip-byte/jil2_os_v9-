# ml_classifier.py
import os
import pickle
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.calibration import CalibratedClassifierCV
from yahooquery import Ticker, Screener
from scanner import FreeMarketScanner

MODEL_PATH = os.path.join(os.path.dirname(__file__), "breakout_xgb.pkl")

class QuantMLClassifier:
    def __init__(self):
        self.model = None
        self.load_or_train()
        
    def load_or_train(self):
        """
        Load the pre-trained XGBoost model if it exists, otherwise train a new one.
        """
        if os.path.exists(MODEL_PATH):
            try:
                with open(MODEL_PATH, "rb") as f:
                    self.model = pickle.load(f)
                print("QuantMLClassifier: XGBoost Model loaded successfully.")
                return
            except Exception as e:
                print(f"QuantMLClassifier: Failed to load XGBoost model: {e}. Retraining...")
                
        self.train_model()

    def train_model(self):
        """
        Train a calibrated XGBoost Classifier model on historical breakout data of 500+ active tickers.
        """
        print("QuantMLClassifier: Training new Calibrated XGBoost Classifier on 500+ symbols...")
        
        # 1. Fetch 500+ unique active symbols using multiple screeners
        screener = Screener()
        screeners_to_query = [
            'day_gainers', 'most_actives', 'small_cap_gainers', 
            'day_losers', 'undervalued_growth_stocks', 'growth_technology_stocks'
        ]
        
        symbols_set = set()
        try:
            data = screener.get_screeners(screen_ids=screeners_to_query, count=150)
            for key in screeners_to_query:
                screener_data = data.get(key, {})
                if isinstance(screener_data, dict):
                    raw_quotes = screener_data.get('quotes', [])
                    for q in raw_quotes:
                        symbol = q.get('symbol')
                        if symbol and symbol.isalpha():
                            symbols_set.add(symbol)
        except Exception as e:
            print(f"QuantMLClassifier Screener Warning: {e}")
            
        train_symbols = list(symbols_set)
        if len(train_symbols) < 100:
            # Fallback list if screeners fail
            train_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "PLTR", "SOFI"] * 10
            
        print(f"QuantMLClassifier: Loaded {len(train_symbols)} symbols for training.")
        
        # 2. Fetch key stats (float & short percent) for training symbols in batches
        stats_map = {}
        batch_size = 40
        for i in range(0, len(train_symbols), batch_size):
            batch = train_symbols[i:i+batch_size]
            try:
                stats = Ticker(batch).key_stats
                for sym in batch:
                    if sym in stats and isinstance(stats[sym], dict):
                        float_s = float(stats[sym].get("floatShares") or 10000000.0)
                        short_p = float(stats[sym].get("shortPercentOfFloat") or 0.0) * 100.0
                        stats_map[sym] = {
                            "float_shares_m": float_s / 1000000.0,
                            "short_percent": short_p
                        }
            except:
                pass
                
        # 3. Fetch 6-month historical daily candles in bulk
        tickers = Ticker(train_symbols)
        df = tickers.history(period="6mo")
        if df is None or df.empty:
            print("QuantMLClassifier Error: Could not fetch training data. Using default dummy model.")
            self.model = self._create_fallback_model()
            return
            
        df = df.reset_index()
        df['date'] = pd.to_datetime(df['date'], utc=True)
        df = df.set_index(['symbol', 'date']).sort_index()
        
        features_list = []
        labels_list = []
        
        unique_syms = df.index.levels[0]
        for sym in unique_syms:
            try:
                stock_data = df.loc[sym].copy()
                if len(stock_data) < 25:
                    continue
                    
                # Calculate indicators
                stock_data['prev_close'] = stock_data['close'].shift(1)
                stock_data['pct_change'] = ((stock_data['close'] - stock_data['prev_close']) / stock_data['prev_close']) * 100
                stock_data['vol_sma20'] = stock_data['volume'].rolling(20).mean()
                stock_data['rvol'] = stock_data['volume'] / stock_data['vol_sma20']
                
                # Standard deviation over 10 days for consolidation
                stock_data['std_10d'] = stock_data['close'].rolling(10).std()
                stock_data['mean_10d'] = stock_data['close'].rolling(10).mean()
                stock_data['volatility_10d'] = (stock_data['std_10d'] / stock_data['mean_10d']) * 100
                
                # Yesterday's indicators
                stock_data['prev_rvol'] = stock_data['rvol'].shift(1)
                stock_data['prev_change'] = stock_data['pct_change'].shift(1)
                
                # Labeling: 1 if high price in the next 2 days rises >= 15% from today's close
                stock_data['next_max_high'] = stock_data['high'].shift(-1).rolling(2, min_periods=1).max()
                stock_data['target_gain'] = ((stock_data['next_max_high'] - stock_data['close']) / stock_data['close']) * 100
                stock_data['label'] = (stock_data['target_gain'] >= 15.0).astype(int)
                
                # Clean up NaN rows
                stock_data = stock_data.dropna(subset=['rvol', 'volatility_10d', 'prev_rvol', 'prev_change', 'label'])
                
                # Get fundamental features
                f_data = stats_map.get(sym, {"float_shares_m": 10.0, "short_percent": 0.0})
                
                for _, row in stock_data.iterrows():
                    features_list.append([
                        float(row['close']),
                        float(row['pct_change']),
                        float(row['rvol']),
                        float(row['volatility_10d']),
                        float(row['prev_rvol']),
                        float(row['prev_change']),
                        float(f_data['float_shares_m']),
                        float(f_data['short_percent'])
                    ])
                    labels_list.append(int(row['label']))
            except Exception as e:
                pass
                
        if len(features_list) < 100:
            print("QuantMLClassifier: Insufficient data samples. Using fallback model.")
            self.model = self._create_fallback_model()
            return
            
        X = np.array(features_list)
        y = np.array(labels_list)
        
        # Train calibrated XGBoost
        xgb_base = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            eval_metric='logloss'
        )
        
        # CalibratedClassifierCV ensures predicted probability matches empirical frequency
        calibrated_xgb = CalibratedClassifierCV(estimator=xgb_base, method='sigmoid', cv=3)
        calibrated_xgb.fit(X, y)
        
        self.model = calibrated_xgb
        
        # Save model to disk
        try:
            with open(MODEL_PATH, "wb") as f:
                pickle.dump(self.model, f)
            print(f"QuantMLClassifier: Calibrated XGBoost Model trained on {len(X)} samples and saved to {MODEL_PATH}")
        except Exception as e:
            print(f"QuantMLClassifier Warning: Could not save model to disk: {e}")

    def _create_fallback_model(self):
        """
        Create a dummy model in case training fails.
        """
        from sklearn.dummy import DummyClassifier
        dummy = DummyClassifier(strategy="stratified", random_state=42)
        X = np.random.rand(100, 8)
        y = np.random.randint(0, 2, 100)
        dummy.fit(X, y)
        return dummy

    def predict_probability(self, price, change, rvol, volatility_10d, prev_rvol, prev_change, float_shares_m, short_percent):
        """
        Predict the calibrated probability of a breakout succeeding (0.0 to 100.0) using XGBoost.
        """
        if self.model is None:
            return 50.0
            
        try:
            features = np.array([[
                float(price),
                float(change),
                float(rvol),
                float(volatility_10d),
                float(prev_rvol),
                float(prev_change),
                float(float_shares_m),
                float(short_percent)
            ]])
            probs = self.model.predict_proba(features)[0]
            class_1_prob = float(probs[1]) * 100.0
            return round(class_1_prob, 1)
        except Exception as e:
            return 50.0
