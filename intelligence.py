# module: intelligence.py
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

class QuantIntelligence:
    def __init__(self):
        # نضبط الـ contamination عند 0.05 (5% شذوذ حجمي) لتقليل إشارات الضجيج
        self.iso_forest = IsolationForest(contamination=0.05, random_state=42)

    def fit_anomaly_detector(self, raw_quotes, session):
        """
        Fit Isolation Forest dynamically on the currently retrieved market snapshots.
        Passes data as NumPy array (.values) to avoid scikit-learn Feature Name Warnings.
        """
        features = []
        valid_quotes = []
        
        for q in raw_quotes:
            try:
                price = float(q.get("regularMarketPrice", 0.0))
                change = float(q.get("regularMarketChangePercent", 0.0))
                volume = float(q.get("regularMarketVolume", 0.0))
                avg_vol = float(q.get("averageDailyVolume3Month", 100000.0))
                rvol = volume / avg_vol if avg_vol > 0 else 1.0
                
                prev_close = float(q.get("regularMarketPreviousClose", price))
                
                # مواءمة الأسعار والنسب المئوية بحسب الجلسة
                if session == "PRE_MARKET" and q.get("preMarketPrice") is not None:
                    price = float(q.get("preMarketPrice"))
                    if prev_close > 0:
                        change = ((price - prev_close) / prev_close) * 100
                elif session == "AFTER_HOURS" and q.get("postMarketPrice") is not None:
                    price = float(q.get("postMarketPrice"))
                    if prev_close > 0:
                        change = ((price - prev_close) / prev_close) * 100

                if price <= 0.0:
                    continue
                    
                features.append([price, change, rvol])
                valid_quotes.append(q)
            except:
                continue

        if len(features) < 10:
            # عينات غير كافية لتدريب Isolation Forest بشكل مستقر
            return {}

        # تحويل المصفوفة لـ NumPy لتفادي تحذيرات أسماء الخصائص
        X = np.array(features)
        
        # تدريب النموذج وتصنيف الشذوذ
        self.iso_forest.fit(X)
        predictions = self.iso_forest.predict(X) # 1 للنمط الطبيعي، -1 للنمط الشاذ (الانفجاري)
        anomaly_scores = self.iso_forest.decision_function(X) # النتيجة الخام للشذوذ

        anomaly_map = {}
        for idx, q in enumerate(valid_quotes):
            sym = q.get("symbol")
            is_anomaly = predictions[idx] == -1
            score = anomaly_scores[idx]
            
            # تحويل قيمة الشذوذ لمؤشر ثقة (Confidence Score) من 0 إلى 10
            # النتيجة الخام decision_function تكون سالبة للشذوذ وموجبة للمستقر
            # نقوم بمعادلتها وتطبيعها
            confidence = float(np.clip(((-score + 0.5) / 1.0) * 10, 0, 10))
            
            anomaly_map[sym] = {
                "is_anomaly": is_anomaly,
                "confidence_score": round(confidence, 1)
            }
            
        return anomaly_map

    def calculate_7_layer_conviction(self, quote, session, anomaly_info):
        """
        Calculate Abu Faisal's 7-Layer Conviction Matching Score (0 - 100%).
        """
        score = 0
        details = {}
        
        price = float(quote.get("regularMarketPrice", 0.0))
        price_change = float(quote.get("regularMarketChangePercent", 0.0))
        open_price = float(quote.get("regularMarketOpen", price))
        prev_close = float(quote.get("regularMarketPreviousClose", price))
        
        # مواءمة الأسعار والنسب المئوية بناءً على الجلسة الحالية
        if session == "PRE_MARKET" and quote.get("preMarketPrice") is not None:
            price = float(quote.get("preMarketPrice"))
            if prev_close > 0:
                price_change = ((price - prev_close) / prev_close) * 100
        elif session == "AFTER_HOURS" and quote.get("postMarketPrice") is not None:
            price = float(quote.get("postMarketPrice"))
            if prev_close > 0:
                price_change = ((price - prev_close) / prev_close) * 100

        # الطبقة 1: فلتر السعر (<= 20$)
        if 0.0 < price <= 20.0:
            score += 15
            details["Price_Filter"] = True
        else:
            details["Price_Filter"] = False

        # الطبقة 2: درع الفجوة الافتتاحية (أقل من 15%)
        gap = ((open_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
        if abs(gap) <= 15.0:
            score += 15
            details["Gap_Shield"] = True
        else:
            details["Gap_Shield"] = False

        # الطبقة 3: صعود الاختراق المبكر (+5% إلى +15%)
        # الصعود فوق 40% يخصم نقاط (مضاد الـ FOMO)
        if 5.0 <= price_change <= 15.0:
            score += 20
            details["Early_Breakout"] = "IDEAL"
        elif 15.0 < price_change <= 40.0:
            score += 10
            details["Early_Breakout"] = "HIGH"
        elif price_change > 40.0:
            score -= 10
            details["Early_Breakout"] = "FOMO_BLOCKED"
        else:
            details["Early_Breakout"] = "LOW_CHANGE"

        # الطبقة 4: تسارع السيولة RVOL (RVOL >= 1.2x)
        volume = float(quote.get("regularMarketVolume", 0.0))
        avg_volume = float(quote.get("averageDailyVolume3Month", 100000.0))
        rvol = volume / avg_volume if avg_volume > 0 else 1.0
        if rvol >= 1.2:
            score += 20
            details["RVOL_Acceleration"] = True
        else:
            details["RVOL_Acceleration"] = False

        # الطبقة 5: تدفق كتل الحيتان الافتراضي (RVOL >= 2.5x)
        if rvol >= 2.5:
            score += 15
            details["Whale_Block"] = True
        else:
            details["Whale_Block"] = False

        # الطبقة 6: عدم توازن السيولة OBI (تحقق الشراء التراكمي)
        bid_size = float(quote.get("bidSize", 0.0))
        ask_size = float(quote.get("askSize", 0.0))
        obi = (bid_size - ask_size) / (bid_size + ask_size) if (bid_size + ask_size) > 0 else 0.0
        if obi >= 0.3:
            score += 10
            details["OBI_Imbalance"] = True
        else:
            details["OBI_Imbalance"] = False

        # الطبقة 7: المحفز الإخباري الذكي بالتحليل التراكمي لـ SEC
        if price_change > 10.0 and rvol >= 1.5:
            score += 5
            details["News_Catalyst"] = "STRONG_POSITIVE"
        else:
            details["News_Catalyst"] = "NEUTRAL"

        final_score = max(0, min(100, score))
        return final_score, details, price, price_change, rvol
