import re

with open('intelligence.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Append check_micro_momentum
micro_momentum_code = """
    def check_micro_momentum(self, symbol, avg_daily_volume):
        \"\"\"
        PM ARCHITECTURE UPGRADE 2: Micro-Momentum Tape Filter
        \"\"\"
        import time
        import yfinance as yf
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d", interval="5m")
            if hist.empty:
                return True
            last_5m_vol = hist['Volume'].iloc[-1]
            min_required_vol = avg_daily_volume * 0.01 
            if last_5m_vol < min_required_vol and last_5m_vol < 20000:
                return False
            return True
        except Exception as e:
            return True
"""
if "def check_micro_momentum" not in content:
    content += "\n" + micro_momentum_code

# 2. Replace calculate_dynamic_target
target_pattern = re.compile(r"    def calculate_dynamic_target\(self, score, ml_prob=0\.0, quote=None, details=None\):.*?return round\(float\(np\.clip\(expected_yield, 8\.0, 300\.0\)\), 1\)", re.DOTALL)

new_target = """    def calculate_dynamic_target(self, score, ml_prob=0.0, quote=None, details=None):
        \"\"\"
        PM ARCHITECTURE UPGRADE 3: Precise Targets
        Returns a highly realistic, precise target between +5% and +45% depending on setup.
        Removes the dangerous 150%+ goals that trap traders.
        \"\"\"
        if not isinstance(details, dict):
            details = {}

        float_shares = 15000000.0
        if isinstance(quote, dict):
            float_shares = self._safe_float(
                quote.get("float_shares_outstanding") or quote.get("floatShares"),
                15000000.0
            )

        if float_shares < 2000000.0:
            base_pot = 25.0
        elif float_shares < 5000000.0:
            base_pot = 18.0
        elif float_shares < 12000000.0:
            base_pot = 12.0
        else:
            base_pot = 8.0
            
        cat_mult = 1.0
        if details.get("material_news"):
            cat_mult = 1.3
        elif details.get("insider_buy"):
            cat_mult = 1.1
            
        import numpy as np
        is_squeeze = bool(details.get("Volatility_Squeeze_Coil"))
        squeeze_mult = 1.2 if is_squeeze else 1.0
        
        conviction = np.clip(float(score), 0.0, 100.0) / 100.0
        probability = np.clip(float(ml_prob or 0.0), 0.0, 100.0) / 100.0
        blended_edge = (0.70 * conviction) + (0.30 * probability)
        
        expected_yield = base_pot * cat_mult * squeeze_mult * blended_edge
        return round(float(np.clip(expected_yield, 5.0, 45.0)), 1)"""

content = target_pattern.sub(new_target, content)

# 3. Replace get_execution_directive
exec_pattern = re.compile(r"    def get_execution_directive\(self, quote, score, ml_prob, session, sec_sentiment, is_halted=False\):.*?        # 5\. Default Fallback\n        return [^\n]+", re.DOTALL)

new_exec = """    def get_execution_directive(self, quote, score, ml_prob, session, sec_sentiment, is_halted=False):
        float_shares = self._safe_float(quote.get("float_shares_outstanding") or quote.get("floatShares") if quote else None, 15000000.0)
        if is_halted:
            return "? ÃãÑ ÏÎæá ãÍÏÏ (Limit Order) ŞÑíÈÇğ ãä ÇáÓÚÑ ÇáãŞÊÑÍ áÊÌäÈ ÇáÇäÒáÇŞ."
        price, change, prev_close = self._session_price_change(quote, session) if quote else (0.0, 0.0, 0.0)
        if change > 35.0:
            return f"?? ãÑÇŞÈÉ İŞØ (ÊÌÇæÒ ãäØŞÉ ÇáÔÑÇÁ ÇáãËÇáíÉ) - ÇáÓåã ÇÑÊİÚ (+{change:.1f}%) æÇáÏÎæá ÇáÂä íäØæí Úáì ãÎÇØÑÉ ÊÑÇÌÚ (FOMO)."
        if float_shares < 2000000.0 and score >= 80:
            return "?? ÏÎæá ãÇÑßÊ (ÒÎã ÚÇáí ÌÏÇğ) - ÓíæáÉ ãÊİÌÑÉ æİáæÊ ÕÛíÑ¡ ÇÓÊåÏİ ÑÈÍ 15-30% ßÍÏ ÃŞÕì."
        if score >= 80:
            return "?? ÏÎæá ãÇÑßÊ (ÒÎã ãÄßÏ) - ÇÓÊåÏİ ÑÈÍ 10-20% ßÍÏ ÃŞÕì áÊÃãíä ÃÑÈÇÍß."
        if ml_prob >= 75.0 and score < 80:
            return "?? ÅÔÇÑÉ ĞßÇÁ ÇÕØäÇÚí (ÊãÑßÒ ÇÓÊÈÇŞí) - ÏÎæá ÈäÕİ ÇáßãíÉ."
        return "? ÏÎæá ÊßÊíßí ÓÑíÚ - ÇÓÊåÏİ ÃÑÈÇÍÇğ ŞÑíÈÉ æáÇ ÊØãÚ." """

content = exec_pattern.sub(new_exec, content)

with open('intelligence.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
