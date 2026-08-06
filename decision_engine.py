# decision_engine.py
import os
import logging
from dotenv import load_dotenv
from intelligence import QuantIntelligence
from ml_classifier import QuantMLClassifier

class DecisionEngine:
    def __init__(self):
        load_dotenv("config.env", override=True)
        self.intel = QuantIntelligence()
        self.ml_classifier = QuantMLClassifier()
        
    def evaluate_symbol(self, quote, session, anomaly_info, sec_sentiment, is_trending=False, f_info=None):
        """
        Evaluate a single stock symbol and return a decision trace dictionary.
        """
        sym = quote.get("symbol")
        thresholds = self.intel.get_thresholds()
        
        # 1. basic features extraction
        price, change, prev_close = self.intel._session_price_change(quote, session)
        if session == "PRE_MARKET":
            volume = self.intel._safe_float(quote.get("preMarketVolume") or quote.get("regularMarketVolume"), 0.0)
        elif session == "AFTER_HOURS":
            volume = self.intel._safe_float(quote.get("postMarketVolume") or quote.get("regularMarketVolume"), 0.0)
        else:
            volume = self.intel._safe_float(quote.get("regularMarketVolume"), 0.0)
            
        avg_volume = self.intel._safe_float(quote.get("averageDailyVolume3Month"), 100000.0)
        rvol = volume / avg_volume if avg_volume > 0 else 1.0
        
        # Default historical features if not provided
        if f_info is None:
            f_info = {
                "volatility_10d": 5.0,
                "prev_rvol": 1.0,
                "prev_change": 0.0,
                "float_shares_m": 10.0,
                "short_percent": 0.0,
                "squeeze_score": 0
            }
            
        float_shares = quote.get("float_shares_outstanding") or quote.get("floatShares")
        if float_shares is None:
            float_shares = f_info.get("float_shares_m", 10.0) * 1000000.0
        else:
            float_shares = float(float_shares)
            
        short_percent = quote.get("short_percent_of_float") or quote.get("shortPercentOfFloat")
        if short_percent is None:
            short_percent = f_info.get("short_percent", 0.0)
        else:
            short_percent = float(short_percent) * 100.0 if float(short_percent) <= 1.0 else float(short_percent)
            
        # 2. Anomaly status
        is_anomaly = anomaly_info.get("is_anomaly", False)
        anomaly_conf = anomaly_info.get("confidence_score", 1.0)
        
        # 3. SEC catalyst & dilution details
        is_dilution = sec_sentiment.get("dilution_warning", False) if sec_sentiment else False
        has_catalyst = bool(sec_sentiment.get("insider_buy") or sec_sentiment.get("material_news")) if sec_sentiment else False
        
        # 4. Run ML model prediction
        ml_prob = self.ml_classifier.predict_probability(
            price=price,
            change=change,
            rvol=rvol,
            volatility_10d=f_info.get("volatility_10d", 5.0),
            prev_rvol=f_info.get("prev_rvol", 1.0),
            prev_change=f_info.get("prev_change", 0.0),
            float_shares_m=float_shares / 1000000.0,
            short_percent=short_percent
        )
        
        # Fallback if ML model is not trained or returns None
        if ml_prob is None:
            ml_prob = float(anomaly_conf * 10.0)
            
        # 5. Calculate Conviction Score (7 Layers)
        score, details, _, _, _ = self.intel.calculate_7_layer_conviction(
            quote=quote,
            session=session,
            anomaly_info=anomaly_info,
            sec_sentiment=sec_sentiment,
            is_trending=is_trending
        )
        
        # Boost conviction score for positive catalysts
        if sec_sentiment:
            if sec_sentiment.get("insider_buy"):
                score = min(100, score + 15)
            if sec_sentiment.get("material_news"):
                score = min(100, score + 10)
        if is_trending and score >= 70:
            score = min(100, score + 10)
            
        # Build initial trace structure
        trace = {
            "symbol": sym,
            "price": price,
            "change": change,
            "rvol": rvol,
            "score": score,
            "ml_prob": ml_prob,
            "is_dilution": is_dilution,
            "is_anomaly": is_anomaly,
            "status": "ACCEPTED",
            "rejection_reason": "",
            "details": details
        }
        
        # 6. Evaluation Rules
        # Rule A: Symbol structure (Derivatives / SPAC warrants exclusion)
        if not sym or len(sym) > 4 or sym.endswith(("U", "W", "R")):
            trace["status"] = "REJECTED"
            trace["rejection_reason"] = "تعديل الرمز (صكوك، خيارات، أو وحدات SPAC المستبعدة)"
            return trace
            
        # Rule B: Price boundaries (Pre-market/After-hours allow up to $50, Regular up to $20)
        max_price_limit = 50.0 if session in ["PRE_MARKET", "AFTER_HOURS", "NIGHT_CLOSED"] else 20.0
        if price <= 0.1 or price > max_price_limit:
            trace["status"] = "REJECTED"
            trace["rejection_reason"] = f"السعر خارج النطاق الآمن ($0.1 - ${max_price_limit})"
            return trace
            
        # Rule C: Daily Change boundaries (ideal discovery range)
        if change < 3.0:
            trace["status"] = "REJECTED"
            trace["rejection_reason"] = f"نسبة الارتفاع اليومي منخفضة جداً (+{change:.1f}% < +3%)"
            return trace
        if change > 60.0:
            trace["status"] = "REJECTED"
            trace["rejection_reason"] = f"السهم منفجر بالفعل ومتضخم سعرياً (+{change:.1f}% > +60%) — فوات منطقة الدخول الآمنة تجنباً للهبوط الحاد (FOMO)"
            return trace
        if change > 30.0 and not has_catalyst:
            if score < 85 or ml_prob < 75.0:
                trace["status"] = "REJECTED"
                trace["rejection_reason"] = f"ارتفاع مسبق مرتفع (+{change:.1f}%) بدون محفز قوي — يتطلب قناعة فائقة (Score >= 85 & ML >= 75%)"
                return trace
            
        # Rule D: Float shares check
        float_limit = thresholds.get("float_max", 15000000.0)
        if float_shares > float_limit:
            trace["status"] = "REJECTED"
            trace["rejection_reason"] = f"الأسهم الحرة للفلوت كبيرة جداً ({float_shares/1000000.0:.1f}M > {float_limit/1000000.0:.1f}M)"
            return trace
            
        # Rule E: RVOL check
        rvol_limit = thresholds.get("rvol_min", 4.0)
        if session in ["PRE_MARKET", "AFTER_HOURS", "NIGHT_CLOSED"]:
            rvol_limit = 0.05  # lower RVOL for extended sessions
        if rvol < rvol_limit:
            trace["status"] = "REJECTED"
            trace["rejection_reason"] = f"حجم التداول النسبي RVOL منخفض جداً ({rvol:.2f}x < {rvol_limit:.2f}x)"
            return trace
            
        # Rule F: Dilution Protection
        if is_dilution:
            trace["status"] = "REJECTED"
            trace["rejection_reason"] = "مخاطر تخفيف حادة (تم رصد إعلان تسجيل طرح أسهم S-1)"
            return trace
            
        # Rule G: Conviction and ML Classifier decision
        # We accept if score >= 80, OR if Supernova FTAI/Volatility Squeeze detected at score >= 70, OR if ML model probability is high >= 75%
        min_score = 70
        is_supernova_early = bool(details.get("Supernova_FTAI_Early") or details.get("Volatility_Squeeze_Coil"))
        
        if score < min_score:
            if is_supernova_early and score >= 70:
                trace["status"] = "ACCEPTED"
                trace["rejection_reason"] = f"اكتشاف مبكر مؤكد لانفجار خارق في القاع (Supernova FTAI / Volatility Squeeze)"
            elif ml_prob >= 75.0:
                # ML Override: Accept the breakout despite lower manual score!
                trace["status"] = "ACCEPTED"
                trace["rejection_reason"] = f"تم التمرير استثنائياً بقوة الذكاء الاصطناعي (ML: {ml_prob:.1f}%)"
            else:
                trace["status"] = "REJECTED"
                trace["rejection_reason"] = f"قناعة منخفضة (Score: {score}% < 80% | ML: {ml_prob:.1f}% < 75%)"
                return trace

        return trace
