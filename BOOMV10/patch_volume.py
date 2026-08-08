import re

with open('intelligence.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add _session_volume helper method
helper_method = """
    def _session_price_change(self, quote, session):"""

new_helper = """
    def _session_volume(self, quote, session):
        volume = self._safe_float(quote.get("regularMarketVolume"), 0.0)
        
        if session == "PRE_MARKET":
            pre_vol = self._safe_float(quote.get("preMarketVolume"), 0.0)
            if pre_vol > 0: volume = pre_vol
        elif session == "AFTER_HOURS":
            post_vol = self._safe_float(quote.get("postMarketVolume"), 0.0)
            if post_vol > 0: volume = post_vol
            
        return volume

    def _session_price_change(self, quote, session):"""

content = content.replace(helper_method, new_helper)

# 2. Replace hardcoded volume in fit_anomaly_detector
old_fit_vol = 'volume = self._safe_float(q.get("regularMarketVolume"), 0.0)'
new_fit_vol = 'volume = self._session_volume(q, session)'
content = content.replace(old_fit_vol, new_fit_vol)

# 3. Replace hardcoded volume in calculate_ml_score
old_ml_vol = 'volume = self._safe_float(quote.get("regularMarketVolume"), 0.0)'
new_ml_vol = 'volume = self._session_volume(quote, session)'
content = content.replace(old_ml_vol, new_ml_vol)

# 4. Replace hardcoded volume in calculate_7_layer_conviction
# It's identical to the old_ml_vol line, so step 3 might have caught it. Let's make sure.
# Wait, string replace will replace ALL occurrences of old_ml_vol in the file. Which is exactly what we want!

with open('intelligence.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("intelligence.py patched with session-aware volume logic successfully!")
