# ml_classifier.py
import os
import pickle
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from yahooquery import Ticker
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
        Train an XGBoost Classifier model on historical breakout data of active tickers.
        """
        print("QuantMLClassifier: Training new XGBoost Classifier...")
        scanner = FreeMarketScanner()
        symbols = scanner.fetch_all_us_symbols()
        # Limit to top 60 symbols for training speed and stability
        train_symbols = symbols[:60]
        
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
                
                for _, row in stock_data.iterrows():
                    features_list.append([
                        float(row['close']),
                        float(row['pct_change']),
                        float(row['rvol']),
                        float(row['volatility_10d']),
                        float(row['prev_rvol']),
                        float(row['prev_change'])
                    ])
                    labels_list.append(int(row['label']))
            except Exception as e:
                pass
                
        if len(features_list) < 50:
            print("QuantMLClassifier: Insufficient data samples. Using fallback model.")
            self.model = self._create_fallback_model()
            return
            
        X = np.array(features_list)
        y = np.array(labels_list)
        
        # Train XGBoost Classifier
        xgb = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            eval_metric='logloss'
        )
        xgb.fit(X, y)
        
        self.model = xgb
        
        # Save model to disk
        try:
            with open(MODEL_PATH, "wb") as f:
                pickle.dump(self.model, f)
            print(f"QuantMLClassifier: XGBoost Model trained on {len(X)} samples and saved to {MODEL_PATH}")
        except Exception as e:
            print(f"QuantMLClassifier Warning: Could not save model to disk: {e}")

    def _create_fallback_model(self):
        """
        Create a dummy model in case training fails.
        """
        from sklearn.dummy import DummyClassifier
        dummy = DummyClassifier(strategy="stratified", random_state=42)
        X = np.random.rand(100, 6)
        y = np.random.randint(0, 2, 100)
        dummy.fit(X, y)
        return dummy

    def predict_probability(self, price, change, rvol, volatility_10d, prev_rvol, prev_change):
        """
        Predict the probability of a breakout succeeding (0.0 to 100.0) using XGBoost.
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
                float(prev_change)
            ]])
            probs = self.model.predict_proba(features)[0]
            class_1_prob = float(probs[1]) * 100.0
            return round(class_1_prob, 1)
        except Exception as e:
            return 50.0
