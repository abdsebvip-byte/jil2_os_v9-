import os
import sys

def audit_codebase():
    errors = []
    
    # 1. Check ML Model
    if not os.path.exists("breakout_xgb.pkl"):
        errors.append("?? CARNAGE: breakout_xgb.pkl is MISSING. The ML classifier is running on empty fallbacks!")
    
    # 2. Check Database Size
    try:
        import sqlite3
        conn = sqlite3.connect("quant_platform.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM signals")
        sig_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM alerts")
        alert_count = c.fetchone()[0]
        if sig_count == 0:
            errors.append("?? WARNING: 'signals' table is empty. The intelligence module might not be logging.")
    except Exception as e:
        errors.append(f"DB Error: {e}")
        
    # 3. Check for fake logic
    with open('decision_engine.py', 'r', encoding='utf-8') as f:
        de_code = f.read()
        if 'random' in de_code and 'predict' not in de_code:
            errors.append("?? FAKE LOGIC: decision_engine.py is using random instead of real ML predictions.")
            
    with open('auto_scanner.py', 'r', encoding='utf-8') as f:
        sc_code = f.read()
        if 'time.sleep(60)' in sc_code and not 'async' in sc_code:
            errors.append("?? BOTTLENECK: auto_scanner.py uses synchronous time.sleep(60), which freezes the entire scanner loop!")
            
    if errors:
        print("--- DIAGNOSTIC ERRORS FOUND ---")
        for e in errors:
            print(e)
    else:
        print("SYSTEM CLEAN. No obvious catastrophic logic bombs found.")

audit_codebase()
