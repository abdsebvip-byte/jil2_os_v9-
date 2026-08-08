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
                # Model loaded silently
                return
            except Exception as e:
                print(f"QuantMLClassifier: Failed to load XGBoost model: {e}. Retraining...")
                
        self.train_model()

    def train_model(self):
        """
        Train a calibrated XGBoost Classifier model on historical breakout data.
        Focuses specifically on LOW-FLOAT small-cap stocks (float < 15M shares)
        that are the actual targets of the platform's explosive breakout mandate.

        Key changes vs original:
        - Only trains on small-cap / low-float screeners (NOT blue chips like AAPL)
        - Label threshold raised to 30% (from 15%) to match real explosive moves
        - Adds class_weight balancing (scale_pos_weight) to handle the label imbalance
          (most days stocks don't move 30%+, so positives are rare)
        - Uses 12-month history for more positive samples
        """
        print("QuantMLClassifier: Training XGBoost on LOW-FLOAT explosive breakout targets...")

        # 1. Fetch symbols focused on small-cap / high-momentum stocks only
        screener = Screener()
        screeners_to_query = [
            'small_cap_gainers',
            'day_gainers',
            'most_actives',
        ]

        symbols_set = set()
        try:
            data = screener.get_screeners(screen_ids=screeners_to_query, count=200)
            for key in screeners_to_query:
                screener_data = data.get(key, {})
                if isinstance(screener_data, dict):
                    raw_quotes = screener_data.get('quotes', [])
                    for q in raw_quotes:
                        symbol = q.get('symbol')
                        # Only include pure alphabetical symbols (no warrants/SPACs)
                        if symbol and symbol.isalpha() and len(symbol) <= 4:
                            symbols_set.add(symbol)
        except Exception as e:
            print(f"QuantMLClassifier Screener Warning: {e}")

        train_symbols = list(symbols_set)
        if len(train_symbols) < 50:
            # Focused fallback on known historical small-cap movers
            train_symbols = [
                "SNDL", "XELA", "PROG", "MNMD", "CLOV", "EXPR", "SPRT",
                "BBIG", "ATER", "GFAI", "PHUN", "CXAI", "BFRI", "PTE",
                "MULN", "GOVX", "DWAC", "BWMX", "MMAT", "NKLA", "SOXS",
                "TPVG", "MITI", "FFIE", "GROM", "LNTH", "BOXL", "EDTK",
                "ACST", "GFAI", "NRXP", "SIGA", "UONE", "PALT", "BTBT"
            ] * 3

        print(f"QuantMLClassifier: Loaded {len(train_symbols)} small-cap symbols for training.")

        # 2. Fetch float & short stats and filter out large-cap (float > 15M)
        stats_map = {}
        batch_size = 40
        for i in range(0, len(train_symbols), batch_size):
            batch = train_symbols[i:i + batch_size]
            try:
                stats = Ticker(batch).key_stats
                for sym in batch:
                    if sym in stats and isinstance(stats[sym], dict):
                        float_s = float(stats[sym].get("floatShares") or 15000000.0)
                        short_p = float(stats[sym].get("shortPercentOfFloat") or 0.0) * 100.0
                        # Only keep symbols with float under 15M shares (platform mandate)
                        if float_s <= 15000000.0:
                            stats_map[sym] = {
                                "float_shares_m": float_s / 1000000.0,
                                "short_percent": short_p
                            }
            except Exception:
                pass

        # Use the filtered symbol list
        filtered_symbols = [s for s in train_symbols if s in stats_map] or train_symbols

        # 3. Fetch 12-month history (more data = more positive label samples)
        tickers = Ticker(filtered_symbols)
        df = tickers.history(period="1y")
        if df is None or df.empty:
            print("QuantMLClassifier Error: Could not fetch training data. Keeping model as None.")
            self.model = None
            return

        df = df.reset_index()
        df['date'] = pd.to_datetime(df['date'], utc=True)
        df = df.set_index(['symbol', 'date']).sort_index()

        features_list = []
        labels_list = []

        unique_syms = df.index.get_level_values(0).unique()
        for sym in unique_syms:
            try:
                stock_data = df.loc[sym].copy()
                if len(stock_data) < 25:
                    continue

                # Feature engineering
                stock_data['prev_close'] = stock_data['close'].shift(1)
                stock_data['pct_change'] = (
                    (stock_data['close'] - stock_data['prev_close']) / stock_data['prev_close']
                ) * 100
                stock_data['vol_sma20'] = stock_data['volume'].rolling(20).mean()
                stock_data['rvol'] = stock_data['volume'] / (stock_data['vol_sma20'] + 1e-6)

                stock_data['std_10d'] = stock_data['close'].rolling(10).std()
                stock_data['mean_10d'] = stock_data['close'].rolling(10).mean()
                stock_data['volatility_10d'] = (stock_data['std_10d'] / (stock_data['mean_10d'] + 1e-6)) * 100

                stock_data['prev_rvol'] = stock_data['rvol'].shift(1)
                stock_data['prev_change'] = stock_data['pct_change'].shift(1)

                # IMPROVED LABELING: 30% gain in next 2 trading days high (matches real explosive targets)
                stock_data['next_max_high'] = stock_data['high'].shift(-1).rolling(2, min_periods=1).max()
                stock_data['target_gain'] = (
                    (stock_data['next_max_high'] - stock_data['close']) / (stock_data['close'] + 1e-6)
                ) * 100
                stock_data['label'] = (stock_data['target_gain'] >= 30.0).astype(int)

                stock_data = stock_data.dropna(
                    subset=['rvol', 'volatility_10d', 'prev_rvol', 'prev_change', 'label']
                )

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
            except Exception:
                pass

        if len(features_list) < 100:
            print("QuantMLClassifier: Insufficient data samples. Keeping model as None.")
            self.model = None
            return

        X = np.array(features_list)
        y = np.array(labels_list)

        # Calculate class imbalance ratio for scale_pos_weight
        n_neg = max(int(np.sum(y == 0)), 1)
        n_pos = max(int(np.sum(y == 1)), 1)
        scale_pos_weight = n_neg / n_pos
        print(f"QuantMLClassifier: Label balance — Neg: {n_neg} | Pos: {n_pos} | scale_pos_weight: {scale_pos_weight:.1f}")

        # Train calibrated XGBoost with imbalance correction
        xgb_base = XGBClassifier(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.08,
            scale_pos_weight=scale_pos_weight,  # Corrects for rare positive labels
            min_child_weight=3,                 # Prevents overfitting on rare positives
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss'
        )

        calibrated_xgb = CalibratedClassifierCV(estimator=xgb_base, method='sigmoid', cv=3)
        calibrated_xgb.fit(X, y)

        self.model = calibrated_xgb

        # Save model to disk
        try:
            with open(MODEL_PATH, "wb") as f:
                pickle.dump(self.model, f)
            print(
                f"QuantMLClassifier: Calibrated XGBoost Model trained on {len(X)} samples "
                f"({n_pos} positives / {n_neg} negatives) and saved to {MODEL_PATH}"
            )
        except Exception as e:
            print(f"QuantMLClassifier Warning: Could not save model to disk: {e}")

        except Exception as e:
            print(f"QuantMLClassifier Warning: Could not save model to disk: {e}")

    def predict_probability(self, price, change, rvol, volatility_10d, prev_rvol, prev_change, float_shares_m, short_percent):
        """
        Predict the calibrated probability of a breakout succeeding (0.0 to 100.0) using XGBoost.
        Returns None if no real model is active.
        """
        if self.model is None:
            return None
            
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
            return None
