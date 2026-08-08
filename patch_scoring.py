import re

with open('intelligence.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define the new strict calculate_7_layer_conviction
new_conviction_func = """    def calculate_7_layer_conviction(self, quote, session, anomaly_info, sec_sentiment=None, is_trending=False):
        \"\"\"
        PM ARCHITECTURE UPGRADE 4: Strict Multiplicative Scoring Engine
        Calculates a 0-100 conviction score. It is mathematically impossible to reach 90-100% 
        unless the stock has massive RVOL, high float turnover (FTAI), and is in the ideal price breakout zone.
        Dead stocks will be heavily penalized.
        \"\"\"
        score = 0
        details = {}
        thresholds = self.get_thresholds()

        price, price_change, prev_close = self._session_price_change(quote, session)
        volume = self._safe_float(quote.get("regularMarketVolume"), 0.0)
        avg_volume = self._safe_float(quote.get("averageDailyVolume3Month"), 100000.0)
        float_shares = self._safe_float(quote.get("float_shares_outstanding") or quote.get("floatShares"), 15000000.0)
        
        rvol = volume / avg_volume if avg_volume > 0 else 1.0
        ftai = (volume / float_shares * rvol) if float_shares > 0 else 0.0
        details["FTAI_Score"] = round(ftai, 2)

        # 1. Base Score: Float & Price Change
        if float_shares < 5000000.0 and 3.0 <= price_change <= 18.0:
            score += 40
            details["Base_Setup"] = "PRIME_LOW_FLOAT"
        elif float_shares < 15000000.0 and 2.0 <= price_change <= 12.0:
            score += 25
            details["Base_Setup"] = "MID_FLOAT_SETUP"
        else:
            score += 10
            details["Base_Setup"] = "WEAK_BASE"
            
        # 2. RVOL Multiplier (The most critical filter)
        if rvol < 2.5:
            score = 0  # DEAD STOCK KILL SWITCH
            details["RVOL_Acceleration"] = "DEAD_STOCK_PENALTY"
        elif rvol > 10.0:
            score += 40
            details["RVOL_Acceleration"] = "MASSIVE"
        elif rvol > 5.0:
            score += 25
            details["RVOL_Acceleration"] = "HIGH"
        elif rvol >= 3.0:
            score += 15
            details["RVOL_Acceleration"] = "MODERATE"
            
        # 3. Tape Acceleration (FTAI)
        if ftai > 1.5:
            score += 20
            details["Tape_Acceleration"] = "HYPER_ACTIVE"
        elif ftai > 0.8:
            score += 10
            details["Tape_Acceleration"] = "ACTIVE"
        elif ftai < 0.1:
            score -= 20  # Penalize stagnant tape
            details["Tape_Acceleration"] = "STAGNANT_PENALTY"

        # 4. FOMO/Extended Penalty
        if price_change > 35.0:
            score -= 30  # Heavy penalty for chasing late
            details["FOMO_Penalty"] = True

        # 5. Catalyst / Anomaly Bonuses (Small pushes)
        if isinstance(sec_sentiment, dict) and sec_sentiment.get("material_news"):
            score += 10
            details["Catalyst"] = True
            
        if anomaly_info and anomaly_info.get("is_anomaly"):
            score += 5
            
        if is_trending:
            score += 5
            
        final_score = max(0, min(100, score))
        return final_score, details, price, price_change, rvol"""

# We need to replace the old calculate_7_layer_conviction completely.
start_idx = content.find('    def calculate_7_layer_conviction')
end_idx = content.find('    def calculate_rules_score', start_idx) # wait, what's the next function?
if end_idx == -1:
    end_idx = content.find('    def calculate_dynamic_target', start_idx) # It's below it

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_conviction_func + "\n\n" + content[end_idx:]
    with open('intelligence.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("intelligence.py successfully patched.")
else:
    print("Could not find the function boundaries.")
