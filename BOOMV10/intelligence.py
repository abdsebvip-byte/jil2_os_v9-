# module: intelligence.py
import os

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.ensemble import IsolationForest


class QuantIntelligence:
    def __init__(self):
        self.iso_forest = IsolationForest(contamination=0.05, random_state=42)
        load_dotenv("config.env")

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            if value is None or pd.isna(value):
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def get_thresholds(self):
        """
        Load tunable thresholds with defaults aligned to the explosive-stock mandate.
        """
        load_dotenv("config.env", override=True)
        return {
            "fomo": float(os.getenv("FOMO_THRESHOLD", 45.0)),
            "gap": float(os.getenv("GAP_THRESHOLD", 15.0)),
            "whale_ext": float(os.getenv("WHALE_THRESHOLD_EXT", 500000.0)),
            "whale_reg": float(os.getenv("WHALE_THRESHOLD_REG", 1500000.0)),
            "rvol_min": float(os.getenv("RVOL_MIN", 4.0)),
            "float_max": float(os.getenv("FLOAT_MAX", 15000000.0)),
            "max_spread_bps": float(os.getenv("MAX_SPREAD_BPS", 250.0)),
            "min_value_traded": float(os.getenv("MIN_VALUE_TRADED", 250000.0)),
        }

    def _session_volume(self, quote, session):
        volume = self._safe_float(quote.get("regularMarketVolume"), 0.0)
        
        if session == "PRE_MARKET":
            pre_vol = self._safe_float(quote.get("preMarketVolume"), 0.0)
            if pre_vol > 0: volume = pre_vol
        elif session == "AFTER_HOURS":
            post_vol = self._safe_float(quote.get("postMarketVolume"), 0.0)
            if post_vol > 0: volume = post_vol
            
        return volume

    def _session_price_change(self, quote, session):
        price = self._safe_float(quote.get("regularMarketPrice"), 0.0)
        prev_close = self._safe_float(quote.get("regularMarketPreviousClose"), price)
        change = ((price - prev_close) / prev_close) * 100.0 if prev_close > 0 else 0.0

        if session == "PRE_MARKET" and quote.get("preMarketPrice") is not None:
            price = self._safe_float(quote.get("preMarketPrice"), price)
            change = ((price - prev_close) / prev_close) * 100.0 if prev_close > 0 else change
        elif session == "AFTER_HOURS" and quote.get("postMarketPrice") is not None:
            price = self._safe_float(quote.get("postMarketPrice"), price)
            change = ((price - prev_close) / prev_close) * 100.0 if prev_close > 0 else change

        return price, change, prev_close

    def fit_anomaly_detector(self, raw_quotes, session):
        """
        Fit Isolation Forest on market snapshots and return anomaly confidence by symbol.
        """
        features = []
        valid_quotes = []

        for q in raw_quotes:
            try:
                price, change, _ = self._session_price_change(q, session)
                volume = self._session_volume(q, session)
                avg_vol = self._safe_float(q.get("averageDailyVolume3Month"), 100000.0)
                float_shares = self._safe_float(q.get("float_shares_outstanding"), 15000000.0)
                rvol = volume / avg_vol if avg_vol > 0 else 1.0

                if price <= 0.0:
                    continue

                features.append([price, change, rvol, np.log10(max(float_shares, 1.0))])
                valid_quotes.append(q)
            except Exception:
                continue

        if len(features) < 10:
            return {}

        X = np.array(features)
        self.iso_forest.fit(X)
        predictions = self.iso_forest.predict(X)
        anomaly_scores = self.iso_forest.decision_function(X)

        anomaly_map = {}
        for idx, q in enumerate(valid_quotes):
            sym = q.get("symbol")
            raw_score = anomaly_scores[idx]
            confidence = float(np.clip(((-raw_score + 0.5) / 1.0) * 10.0, 0.0, 10.0))
            anomaly_map[sym] = {
                "is_anomaly": predictions[idx] == -1,
                "confidence_score": round(confidence, 1),
            }

        return anomaly_map

    def calculate_supply_pressure(self, quote, rvol):
        """
        Quantify low-float + relative-volume pressure.
        A high value means less tradable supply is absorbing unusually high demand.
        """
        thresholds = self.get_thresholds()
        float_shares = self._safe_float(
            quote.get("float_shares_outstanding") or quote.get("floatShares"),
            thresholds["float_max"],
        )
        value_traded = self._safe_float(quote.get("value_traded"), 0.0)

        float_ratio = thresholds["float_max"] / max(float_shares, 1.0)
        rvol_ratio = rvol / max(thresholds["rvol_min"], 0.1)
        pressure_index = np.sqrt(max(float_ratio, 0.0) * max(rvol_ratio, 0.0))

        score = 0
        if float_shares <= thresholds["float_max"]:
            score += 12
        if rvol >= thresholds["rvol_min"]:
            score += 10
        elif rvol >= thresholds["rvol_min"] * 0.75:
            score += 5
        if value_traded >= thresholds["min_value_traded"]:
            score += 3

        return min(score, 25), {
            "Float_Shield": float_shares <= thresholds["float_max"],
            "Float_Shares": round(float_shares, 0),
            "Supply_Pressure_Index": round(float(pressure_index), 2),
        }

    def calculate_ml_score(self, quote, session, anomaly_info):
        try:
            from database import QuantDatabase
            db = QuantDatabase()
            weights, bias = db.load_latest_model_weights(num_features=6)
            
            price, price_change, prev_close = self._session_price_change(quote, session)
            volume = self._session_volume(quote, session)
            bid = self._safe_float(quote.get("bid"), price)
            ask = self._safe_float(quote.get("ask"), price)
            
            mid = (bid + ask) / 2.0
            spread = (ask - bid) / (mid + 1e-6) if mid > 0 else 0.0
            idp = volume / (spread + 1e-6)
            
            high = self._safe_float(quote.get("regularMarketDayHigh"), price)
            low = self._safe_float(quote.get("regularMarketDayLow"), price)
            atr = max(high - low, 1e-6) if high > low else 0.1
            
            eta = 0.2
            if price > mid + eta * spread:
                sgn = 1.0
            elif price < mid - eta * spread:
                sgn = -1.0
            else:
                sgn = 0.0
                
            ofip = sgn
            
            thresholds = self.get_thresholds()
            lai = idp - thresholds["min_value_traded"]
            
            r = np.log(price / prev_close) if prev_close > 0 and price > 0 else 0.0
            pi = abs(r) / (np.sqrt(volume) + 1e-6)
            
            features = np.array([idp, ofip, lai, pi, spread, atr], dtype=np.float32)
            
            z = np.dot(weights, features) + bias
            score = 1.0 / (1.0 + np.exp(-np.clip(z, -20.0, 20.0)))
            
            return float(score) * 100.0, features
        except Exception as e:
            conf = float(anomaly_info.get("confidence_score", 5.0) if anomaly_info else 5.0)
            return conf * 10.0, np.zeros(6, dtype=np.float32)

    def calculate_7_layer_conviction(self, quote, session, anomaly_info, sec_sentiment=None, is_trending=False, is_consolidating=False):
        """
        Data-Driven Scoring Engine (Based on missed_gainers_report & historical audit)
        - Removed 35% FOMO block (stocks can go up to 100%+ and still be scored)
        - RVOL accepted down to 2.0x (for silent accumulation detection)
        - No arbitrary 'impossible' constraints. Real supernovas get 95-100%.
        """
        score = 0
        details = {}
        thresholds = self.get_thresholds()

        price, price_change, prev_close = self._session_price_change(quote, session)
        volume = self._session_volume(quote, session)
        avg_volume = self._safe_float(quote.get("averageDailyVolume3Month"), 100000.0)
        float_shares = self._safe_float(quote.get("float_shares_outstanding") or quote.get("floatShares"), 15000000.0)
        
        rvol = volume / avg_volume if avg_volume > 0 else 1.0
        ftai = (volume / float_shares * rvol) if float_shares > 0 else 0.0
        details["FTAI_Score"] = round(ftai, 2)

        # 1. Base Setup Score
        if float_shares < 10000000.0 and 2.0 <= price_change <= 20.0:
            score += 35
            details["Base_Setup"] = "PRIME_LOW_FLOAT"
        elif float_shares < 20000000.0 and 1.5 <= price_change <= 50.0:
            score += 25
            details["Base_Setup"] = "MID_FLOAT_OR_RUNNING"
        else:
            score += 15
            details["Base_Setup"] = "STANDARD_BASE"
            
        # 2. RVOL Multiplier (Data-Driven: 2.0x is minimum for accumulation)
        if rvol < 2.0:
            score -= 20  # Only penalize if completely dead (<2.0x)
            details["RVOL_Acceleration"] = "DEAD_STOCK_PENALTY"
        elif rvol > 5.0:
            score += 35
            details["RVOL_Acceleration"] = "MASSIVE"
        elif rvol > 3.0:
            score += 25
            details["RVOL_Acceleration"] = "HIGH"
        elif rvol >= 2.0:
            score += 15
            details["RVOL_Acceleration"] = "ACCUMULATION_MODERATE"
            
        # 3. Tape Acceleration (FTAI)
        if ftai > 1.0:
            score += 20
            details["Tape_Acceleration"] = "HYPER_ACTIVE"
        elif ftai > 0.4:
            score += 10
            details["Tape_Acceleration"] = "ACTIVE"

        # 4. FOMO/Extended Price (Removed 35% harsh penalty based on audit)
        if price_change > 150.0:
            score -= 10  # Only penalize extreme 150%+ chasing
            details["FOMO_Penalty"] = True

        # 5. Catalyst / Gap Shield Logic
        open_price = self._safe_float(quote.get("regularMarketOpen"), price)
        gap = ((open_price - prev_close) / prev_close) * 100.0 if prev_close > 0 else 0.0
        gap_limit = 20.0
        has_catalyst = isinstance(sec_sentiment, dict) and sec_sentiment.get("material_news")
        
        if has_catalyst:
            gap_limit = 100.0  # Dynamic gap shield from missed_gainers_report
            score += 10
            details["Catalyst"] = True
            
        if abs(gap) > gap_limit:
            score -= 15
            details["Gap_Penalty"] = True
            
        if anomaly_info and anomaly_info.get("is_anomaly"):
            score += 5
            
        if is_trending:
            score += 5
            
        final_score = max(0, min(100, score))
        return final_score, details, price, price_change, rvol

    def calculate_dynamic_target(self, score, ml_prob=0.0, quote=None):
        """
        Return a continuous target between +8% and +120% depending on Low-Float status.
        It blends rules-based conviction with model/anomaly probability.
        """
        conviction = np.clip(float(score), 0.0, 100.0) / 100.0
        probability = np.clip(float(ml_prob or 0.0), 0.0, 100.0) / 100.0
        blended_edge = (0.70 * conviction) + (0.30 * probability)
        base_target = 8.0 + (42.0 * (blended_edge ** 1.7))
        
        # Check for Ultra-Low Float boost (Super-Nova Setup)
        float_shares = 15000000.0
        if isinstance(quote, dict):
            float_shares = self._safe_float(
                quote.get("float_shares_outstanding") or quote.get("floatShares"),
                15000000.0
            )
            
        if float_shares < 2000000.0:  # Float less than 2 million shares
            target = base_target * 2.4
            return round(float(np.clip(target, 15.0, 120.0)), 1)
        elif float_shares < 5000000.0:  # Float less than 5 million shares
            target = base_target * 1.6
            return round(float(np.clip(target, 12.0, 75.0)), 1)
            
        return round(float(np.clip(base_target, 8.0, 50.0)), 1)

    def get_execution_directive(self, quote, score, ml_prob, session, sec_sentiment, is_halted=False):
        """
        Provide a customized, clear execution directive in Arabic based on conviction level and float.
        """
        float_shares = self._safe_float(
            quote.get("float_shares_outstanding") or quote.get("floatShares") if quote else None,
            15000000.0
        )
        
        # 1. Halts execution
        if is_halted:
            return "⏳ أمر دخول محدد (Limit Order) قريباً من السعر المقترح عند استئناف التداول لتجنب الانزلاق السعري الفجائي."
            
        # 1.5 Safe entry zone validation
        price, change, prev_close = self._session_price_change(quote, session) if quote else (0.0, 0.0, 0.0)
        if change > 30.0:
            return f"⚠️ مراقبة فقط (تجاوز منطقة الشراء الآمنة) - السهم ارتفع بنسبة كبيرة (+{change:.1f}%) والدخول الفوري ينطوي على مخاطرة تراجع عالية (FOMO)."
            
        # 2. Super-Nova Execution (Low-Float + High Conviction)
        if float_shares < 2000000.0 and score >= 80:
            return "🚀 دخول فوري ماركت بسعر السوق (شديد القوة) - تأكيد سيولة متفجرة مع فلوت صغير جداً يدعم انفجاراً خارقاً (+100%)."
            
        # 3. Regular Breakout Execution
        if score >= 80:
            return "🔥 دخول ماركت (بسعر السوق الحالي) أو انتظار تراجع طفيف بنسبة 1-2% للدخول مع شمعة تأكيد الاتجاه."
            
        # 4. Silent Accumulation / Cautious Entry
        if score >= 70:
            return "📈 شراء تدريجي بأمر محدد السعر (Limit) - السهم في مرحلة تجميع سيولة هادئة ولم يبدأ انفجاره الرئيسي بعد."
            
        return "⏳ مراقبة وتأكيد - لا ينصح بالدخول الفوري لعدم اكتمال شروط تسارع السيولة."

    def get_exit_strategy(self, target_pct):
        """
        Generate exits guidance based on the size of target_pct.
        """
        if target_pct >= 80.0:
            return "🎯 استراتيجية التأمين: بع 40% من الكمية عند تحقيق +30% لتأمين الأرباح، و40% عند تحقيق +60%، واترك 20% حرة للوصول إلى القمة النهائية (+100% إلى +120%)."
        elif target_pct >= 50.0:
            return "🎯 استراتيجية التأمين: بع 50% من الكمية عند تحقيق +25% لتأمين رأس المال، واترك الباقي ليصل إلى الهدف المستهدف (+50% إلى +75%)."
        else:
            return f"🎯 استراتيجية التأمين: ضع أمر بيع محدد (Take Profit) لكامل الكمية عند السعر المستهدف (+{target_pct}%)."

    def calculate_predictive_yield_tier(self, quote, score, details=None):
        """
        Return the dynamic predictive expected yield tier based on Float, FTAI, Squeeze, and Conviction.
        Returns tuple: (tier_code, tier_label, tier_color, target_range_str)
        """
        if isinstance(details, str):
            try:
                import json
                details = json.loads(details)
            except Exception:
                details = {}
        elif not isinstance(details, dict):
            details = {}

        float_shares = self._safe_float(
            quote.get("float_shares_outstanding") or quote.get("floatShares") if quote else None,
            15000000.0
        )
        ftai = self._safe_float(details.get("FTAI_Score"), 0.0)
        is_squeeze = bool(details.get("Volatility_Squeeze_Coil"))
        is_ftai_early = bool(details.get("Supernova_FTAI_Early"))

        # 🚀 1. فئة الانفجار الخارق (+80% إلى +100%+)
        if (float_shares < 5000000.0 and (is_ftai_early or is_squeeze or ftai >= 0.8) and score >= 75) or (float_shares < 3000000.0 and score >= 85):
            return "TIER_1_SUPERNOVA", "🚀 فئة الانفجار الخارق المتوقع (+80% إلى +100%+)", "#00FFCC", "+80% إلى +120%"

        # 💥 2. فئة الصعود العالي (+40% إلى +75%)
        if (float_shares < 15000000.0 and score >= 75) or (score >= 85):
            return "TIER_2_HIGH_YIELD", "💥 فئة الصعود العالي المتوقع (+40% إلى +75%)", "#FFA500", "+40% إلى +75%"

        # 📈 3. فئة الزخم اللحظي السريع (+15% إلى +35%)
        return "TIER_3_MOMENTUM", "📈 فئة الزخم اللحظي السريع (+15% إلى +35%)", "#3B82F6", "+15% إلى +35%"

    def calculate_liquidity_rating(self, quote):
        """
        Return the dollar-volume liquidity rating indicator.
        Returns tuple: (liq_code, liq_label, dollar_vol_formatted)
        """
        if not isinstance(quote, dict):
            return "LIQ_MEDIUM", "💧 سيولة نقدية متوسطة", "$1.0M"

        price = self._safe_float(quote.get("regularMarketPrice"), 0.0)
        volume = self._session_volume(quote, session)
        dollar_vol = price * volume

        formatted_vol = f"${dollar_vol/1000000.0:.2f}M" if dollar_vol >= 1000000.0 else f"${dollar_vol/1000.0:.0f}K"

        if dollar_vol >= 5000000.0:
            return "LIQ_HEAVY", f"🌊 سيولة نقدية ضخمة ({formatted_vol}) 🟢", formatted_vol
        elif dollar_vol >= 1000000.0:
            return "LIQ_MEDIUM", f"💧 سيولة نقدية متوسطة ({formatted_vol}) 🟡", formatted_vol
        else:
            return "LIQ_THIN", f"⚠️ سيولة خفيفة ({formatted_vol}) 🔴 (يفضل الدخول بمبلغ صغير)", formatted_vol

    def calculate_dynamic_stop_loss(self, rvol, max_loss=5.0):
        """
        Keep loss protection strict; tighten to -4% when volume confirmation is weak.
        """
        if rvol < self.get_thresholds()["rvol_min"]:
            return -4.0
        return -abs(float(max_loss))


    def check_micro_momentum(self, symbol, avg_daily_volume):
        """
        PM ARCHITECTURE UPGRADE 2: Micro-Momentum Tape Filter
        Fetches 1-minute or 5-minute data. If the volume in the last 5 minutes
        is less than 5% of the average daily volume, the stock is just drifting, not exploding.
        """
        import time
        import yfinance as yf
        
        try:
            # We want an actual tape reading, so we don't cache this. We fetch live.
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d", interval="5m")
            if hist.empty:
                return True # Fallback if no 5m data
                
            last_5m_vol = hist['Volume'].iloc[-1]
            # If the stock traded > 1% of its daily volume in just 5 minutes, it's a massive squeeze.
            min_required_vol = avg_daily_volume * 0.01 
            
            # Additional check: minimum absolute volume (e.g. 10k shares in 5 mins)
            if last_5m_vol < min_required_vol and last_5m_vol < 20000:
                return False
                
            return True
        except Exception as e:
            return True # Fallback on error
