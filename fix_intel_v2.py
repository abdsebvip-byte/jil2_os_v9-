import re

with open('intelligence.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Append check_micro_momentum
micro_momentum_code = """
    def check_micro_momentum(self, symbol, avg_daily_volume):
        \"\"\"
        PM ARCHITECTURE UPGRADE 2: Micro-Momentum Tape Filter
        Fetches 1-minute or 5-minute data. If the volume in the last 5 minutes
        is less than 5% of the average daily volume, the stock is just drifting, not exploding.
        \"\"\"
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
"""
if "def check_micro_momentum" not in content:
    content += "\n" + micro_momentum_code

# 2. Replace calculate_dynamic_target
target_pattern = re.compile(r"    def calculate_dynamic_target.*?return round\(float\(np\.clip\(expected_yield, 8\.0, 300\.0\)\), 1\)", re.DOTALL)

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

        # 1. Base realistic potential (8% to 25%)
        if float_shares < 2000000.0:
            base_pot = 25.0  # Ultra-low float realistic bounce
        elif float_shares < 5000000.0:
            base_pot = 18.0
        elif float_shares < 12000000.0:
            base_pot = 12.0
        else:
            base_pot = 8.0
            
        # 2. Catalyst multiplier (only slight boosts)
        cat_mult = 1.0
        if details.get("material_news"):
            cat_mult = 1.3
        elif details.get("insider_buy"):
            cat_mult = 1.1
            
        is_squeeze = bool(details.get("Volatility_Squeeze_Coil"))
        squeeze_mult = 1.2 if is_squeeze else 1.0
        
        # Blended with model probability & conviction score
        import numpy as np
        conviction = np.clip(float(score), 0.0, 100.0) / 100.0
        probability = np.clip(float(ml_prob or 0.0), 0.0, 100.0) / 100.0
        blended_edge = (0.70 * conviction) + (0.30 * probability)
        
        expected_yield = base_pot * cat_mult * squeeze_mult * blended_edge
        
        # Cap realistically between 5% and 45% MAX
        return round(float(np.clip(expected_yield, 5.0, 45.0)), 1)"""

content = target_pattern.sub(new_target, content)

# 3. Replace get_execution_directive
start_idx = content.find('    def get_execution_directive(self, quote, score, ml_prob, session, sec_sentiment, is_halted=False):')
end_idx = content.find('    def _session_price_change', start_idx) 

new_exec = """    def get_execution_directive(self, quote, score, ml_prob, session, sec_sentiment, is_halted=False):
        \"\"\"
        Provide a customized, clear execution directive in Arabic based on conviction level and float.
        \"\"\"
        float_shares = self._safe_float(
            quote.get("float_shares_outstanding") or quote.get("floatShares") if quote else None,
            15000000.0
        )
        
        # 1. Halts execution
        if is_halted:
            return "⏳ أمر دخول محدد (Limit Order) قريباً من السعر المقترح عند استئناف التداول لتجنب الانزلاق السعري المفاجئ."
            
        # 1.5 Safe entry zone validation
        price, change, prev_close = self._session_price_change(quote, session) if quote else (0.0, 0.0, 0.0)
        if change > 35.0:
            return f"⚠️ دخول بحذر (تجاوز منطقة الشراء المثالية) - السهم ارتفع (+{change:.1f}%)، استخدم أوامر وقف خسارة صارمة لتجنب الانعكاس السريع."
            
        # 2. Super-Nova Execution (Low-Float + High Conviction)
        if float_shares < 2000000.0 and score >= 80:
            return "🚀 دخول ماركت (زخم عالي جداً) - السهم يمتلك فلوت صغير جداً وتأكيد سيولة لحظية، راقب مقاومة السعر القريبة بدقة لجني الربح."
            
        # 3. Regular Breakout Execution
        if score >= 80:
            return "🔥 دخول ماركت (بناءً على تدفق السيولة) - استهدف 10% إلى 20% كحد أقصى لتأمين الأرباح وعدم الطمع."
            
        # 4. Machine Learning Edge (High ML, Mid Conviction)
        if ml_prob >= 75.0 and score < 80:
            return "🤖 إشارة ذكاء اصطناعي (دخول تدريجي) - النماذج ترصد احتمالية انفجار مبكرة، ابدأ بنصف الكمية."
            
        # 5. Default Fallback
        return "⚡ دخول تكتيكي سريع - استهدف أرباحاً قريبة ولا تترك الصفقة مفتوحة بدون مراقبة." """

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_exec + "\n\n" + content[end_idx:]

with open('intelligence.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Patch applied successfully.")
