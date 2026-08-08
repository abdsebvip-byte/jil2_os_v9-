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
        
    def evaluate_symbol(self, quote, session, anomaly_info, sec_sentiment, is_trending=False, f_info=None, is_consolidating=False):
        """
        Evaluate a single stock symbol and return a decision trace dictionary.
        """
        sym = quote.get("symbol")
        thresholds = self.intel.get_thresholds()
        
        # 1. basic features extraction
        price, change, prev_close = self.intel._session_price_change(quote, session)
        if session == "PRE_MARKET":
            volume = self.intel._safe_float(quote.get("preMarketVolume") if quote.get("preMarketVolume") is not None else 0.0, 0.0)
        elif session == "AFTER_HOURS":
            volume = self.intel._safe_float(quote.get("postMarketVolume") if quote.get("postMarketVolume") is not None else 0.0, 0.0)
        else:
            volume = self.intel._safe_float(quote.get("regularMarketVolume"), 0.0)
            
        avg_volume = self.intel._safe_float(quote.get("averageDailyVolume3Month"), 100000.0)
        
        # Calculate Time-Adjusted RVOL
        if session == "REGULAR_SESSION":
            elapsed_fraction = self.intel._get_regular_market_elapsed_fraction()
            expected_avg_vol = avg_volume * elapsed_fraction
            rvol = volume / expected_avg_vol if expected_avg_vol > 0 else 1.0
        elif session in ["PRE_MARKET", "AFTER_HOURS", "NIGHT_CLOSED"]:
            expected_ext_vol = avg_volume * 0.05
            rvol = volume / expected_ext_vol if expected_ext_vol > 0 else 1.0
        else:
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
            is_trending=is_trending,
            is_consolidating=is_consolidating
        )
        # NOTE: SEC catalyst bonuses (insider_buy +10, material_news +15) are already applied
        # inside calculate_7_layer_conviction in intelligence.py — do NOT re-apply them here.
        # Only apply the is_trending boost which is a decision_engine-level context signal.
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
            
        # Rule B2: Liquidity Floor Check
        value_traded = self.intel._safe_float(quote.get("value_traded"), 0.0)
        if value_traded <= 0.0:
            value_traded = price * volume
            
        if session in ["PRE_MARKET", "AFTER_HOURS", "NIGHT_CLOSED"]:
            min_volume = 50000.0
            min_value_traded = 100000.0
        else:
            min_volume = 150000.0
            min_value_traded = 250000.0
            
        if volume < min_volume or value_traded < min_value_traded:
            trace["status"] = "REJECTED"
            trace["rejection_reason"] = f"شح السيولة وحجم التداول (الحجم: {volume:,.0f} < {min_volume:,.0f} | القيمة: ${value_traded:,.0f} < ${min_value_traded:,.0f})"
            return trace
            
        # Rule C: Daily Change boundaries (ideal discovery range)
        min_change_limit = 5.0 if session == "REGULAR_SESSION" else 4.0
        if change < min_change_limit:
            trace["status"] = "REJECTED"
            trace["rejection_reason"] = f"نسبة الارتفاع اليومي منخفضة جداً (+{change:.1f}% < +{min_change_limit}%)"
            return trace
        if change > 60.0:
            trace["status"] = "REJECTED"
            trace["rejection_reason"] = f"السهم منفجر بالفعل ومتضخم سعرياً (+{change:.1f}% > +60%) — فوات منطقة الدخول الآمنة تجنباً للهبوط الحاد (FOMO)"
            return trace
        if change > 20.0 and not has_catalyst:
            if score < 85 or ml_prob < 15.0:
                trace["status"] = "REJECTED"
                trace["rejection_reason"] = f"ارتفاع مسبق مرتفع (+{change:.1f}%) بدون محفز قوي — يتطلب قناعة فائقة (Score >= 85 & ML >= 15%)"
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
            rvol_limit = 0.15  # raise RVOL limit from 0.05 to 0.15 for extended sessions
        if rvol < rvol_limit:
            trace["status"] = "REJECTED"
            trace["rejection_reason"] = f"حجم التداول النسبي RVOL منخفض جداً ({rvol:.2f}x < {rvol_limit:.2f}x)"
            return trace
            
        # Rule F: Dilution Protection
        if is_dilution:
            trace["status"] = "REJECTED"
            trace["rejection_reason"] = "مخاطر تخفيف حادة (تم رصد إعلان تسجيل طرح أسهم S-1)"
            return trace
            
        # --- PM ARCHITECTURE UPGRADE 2: Micro-Momentum Tape Filter ---
        # We run this live tick request only for final candidates to save API hits.
        is_exploding = self.intel.check_micro_momentum(sym, avg_volume)
        if not is_exploding:
            trace["status"] = "REJECTED"
            trace["rejection_reason"] = "شح السيولة اللحظية (Micro-Momentum): لا يوجد هجوم شرائي في آخر 5 دقائق، السهم يتحرك ببطء."
            return trace

        # Rule T: Daily Trend Alignment Guard
        # We only run the yfinance HTTP request for final candidates to prevent rate limits!
        is_daily_aligned = self.intel.check_daily_trend_alignment(sym, price)
        if not is_daily_aligned:
            # Apply a strict penalty of -30 unless we have Tier-1 material news news catalyst
            is_material_news = isinstance(sec_sentiment, dict) and bool(sec_sentiment.get("material_news"))
            if not is_material_news:
                score -= 30
                details["Daily_Trend_Alignment"] = False
            else:
                score += 5  # Small boost for fighting trend with news catalyst
                details["Daily_Trend_Alignment"] = "FIGHTING_WITH_CATALYST"
        else:
            score += 10  # Boost for matching daily trend
            details["Daily_Trend_Alignment"] = True
            
        score = max(0, min(100, score))
        trace["score"] = score
        trace["details"] = details

        # Rule G: Conviction and ML Classifier decision
        # Smart flexible thresholds — not a rigid 80-point cliff:
        # - Base minimum: 80 points (no catalyst)
        # - Catalyst reduction: 75 points if backed by confirmed news (material_news or insider_buy)
        # - Supernova exception: 75 points if FTAI/Volatility Squeeze detected
        # - ML Override: 65% ML probability can lower the threshold by 5 more points
        has_news_catalyst = bool(
            isinstance(sec_sentiment, dict) and
            (sec_sentiment.get("material_news") or sec_sentiment.get("insider_buy"))
        )
        is_supernova_early = bool(details.get("Supernova_FTAI_Early") or details.get("Volatility_Squeeze_Coil"))

        # Determine effective minimum score based on context
        if has_news_catalyst or is_supernova_early:
            effective_min_score = 75  # News or squeeze lowers the bar slightly
        else:
            effective_min_score = 80  # No catalyst: strict 80 required

        # ML high confidence can lower the bar by 5 more points
        if ml_prob >= 65.0:
            effective_min_score = max(70, effective_min_score - 5)

        if score < effective_min_score:
            # Hard floor: Even if ML is confident, don't accept garbage (score < 65)
            if ml_prob >= 80.0 and score >= 65:
                # ML Override: strong model confidence overrides manual score
                trace["status"] = "ACCEPTED"
                trace["rejection_reason"] = f"تم التمرير بقوة الذكاء الاصطناعي (ML: {ml_prob:.1f}%) رغم قناعة متوسطة"
            else:
                context = "مع محفز" if has_news_catalyst else ("مع انفجار صامت" if is_supernova_early else "بدون محفز")
                trace["status"] = "REJECTED"
                trace["rejection_reason"] = (
                    f"قناعة منخفضة ({context}) — Score: {score} < {effective_min_score} | ML: {ml_prob:.1f}%"
                )
                return trace

        return trace

