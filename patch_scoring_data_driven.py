import re

with open('intelligence.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define the new data-driven calculate_7_layer_conviction
new_conviction_func = """    def calculate_7_layer_conviction(self, quote, session, anomaly_info, sec_sentiment=None, is_trending=False):
        \"\"\"
        Data-Driven Scoring Engine (Based on missed_gainers_report & historical audit)
        - Removed 35% FOMO block (stocks can go up to 100%+ and still be scored)
        - RVOL accepted down to 2.0x (for silent accumulation detection)
        - No arbitrary 'impossible' constraints. Real supernovas get 95-100%.
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
        return final_score, details, price, price_change, rvol"""

# We need to replace the old calculate_7_layer_conviction completely.
start_idx = content.find('    def calculate_7_layer_conviction')
end_idx = content.find('    def calculate_rules_score', start_idx) 
if end_idx == -1:
    end_idx = content.find('    def calculate_dynamic_target', start_idx)

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_conviction_func + "\n\n" + content[end_idx:]
    with open('intelligence.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("intelligence.py successfully patched with data-driven logic.")
else:
    print("Could not find the function boundaries.")
