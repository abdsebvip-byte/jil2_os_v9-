import os
import time
import sqlite3
import datetime
import yfinance as yf
import pandas as pd
from pattern_detector import PatternDetector

DB_PATH = r"C:\Users\sahar\.gemini\antigravity\scratch\jil2_os_v9\quant_platform.db"

# Dynamically fetch 800 high-liquidity stocks (S&P 500 + Top Nasdaq)
def get_800_symbols():
    try:
        # Fetch S&P 500
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        # Clean symbols (e.g. BRK.B -> BRK-B for yfinance)
        sp500 = [s.replace('.', '-') for s in sp500]
        
        # We need 300 more to reach 800. We can just append some large ETFs and popular NASDAQ stocks
        extra = ["QQQ", "SPY", "IWM", "DIA", "ARKK", "TSLA", "PLTR", "SOFI", "RIVN", "LCID", "NIO", "COIN", "MARA", "RIOT", "HOOD", "UBER", "LYFT", "DASH", "ABNB", "SNOW", "DDOG", "NET", "CRWD", "ZS", "PANW", "FTNT", "MDB", "TEAM", "WDAY", "NOW", "CRM", "ADBE", "INTU", "ADSK", "ANSS", "CDNS", "SNPS", "KLAC", "LRCX", "AMAT", "ASML", "TSM", "AMD", "INTC", "QCOM", "TXN", "AVGO", "MU", "NXPI", "MCHP", "ADI", "SWKS", "QRVO", "MRVL", "GFS", "WDC", "STX", "HPQ", "HPE", "DELL", "SMCI", "FSLR", "ENPH", "SEDG", "RUN", "SPWR", "NOVA", "BE", "PLUG", "FCEL", "BLDP", "SQ", "PYPL", "AFRM", "UPST", "MQ", "TOST", "SOFI", "LMND", "PINS", "SNAP", "MTCH", "BMBL", "ROKU", "NFLX", "DIS", "WBD", "PARA", "FOXA", "CMCSA", "CHTR", "SIRI", "SPOT", "WMG", "LYV", "EA", "TTWO", "RBLX", "U", "APP", "MTLS", "DKNG", "PENN", "CZR", "MGM", "WYNN", "LVS", "CHDN", "RCL", "CCL", "NCLH", "DAL", "UAL", "AAL", "LUV", "ALK", "JBLU", "HA", "SAVE", "BA", "LMT", "GD", "NOC", "RTX", "LHX", "HWM", "TDG", "TXT", "SPR", "BAH", "LDOS", "SAIC", "CACI", "MANH", "PTC", "NTNX", "FIVN", "ZEN", "PD", "SMAR", "ASAN", "MOND", "NCNO", "DT", "ESTC", "NEWR", "SPLK", "DOCN", "FSLY", "AKAM", "CHKP", "CYBR", "TENB", "VRNS", "RPD", "QLYS", "OKTA", "PING", "FORG", "SAIL"]
        
        combined = list(set(sp500 + extra))
        return combined[:800]
    except Exception as e:
        print(f"Error fetching symbols: {e}")
        # Fallback to a hardcoded massive list if Wikipedia parsing fails
        return ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "TSM", "BRK-B", "LLY", "V", "JPM", "WMT", "UNH", "MA", "XOM", "PG", "JNJ", "HD", "ORCL", "COST", "MRK", "ABBV", "CVX", "CRM", "BAC", "AMD", "NFLX", "PEP", "TMO", "KO", "WFC", "LIN", "QCOM", "DIS", "CSCO", "INTC", "ADBE", "ABT", "DHR", "MCD", "GE", "INTU", "VZ", "CAT", "PFE", "IBM", "NOW", "AMAT", "UBER", "CMCSA", "AXP", "TXN", "NKE", "PM", "COP", "HON", "BA", "SYK", "SPGI", "UNP", "AMGN", "RTX", "LMT", "LOW", "BKNG", "ISRG", "ELV", "C", "MDT", "PLD", "BLK", "GS", "PGR", "TJX", "T", "VRTX", "GILD", "REGN", "ZTS", "MDLZ", "CVS", "ADP", "SCHW", "LRCX", "ADI", "CB", "MMC", "SO", "BSX", "DE", "BMY", "CI", "PANW", "DUK", "SNPS", "FI", "KLAC", "CDNS", "ICE", "SHW", "WM", "EQIX", "MU", "CME"]

MEGA_CAPS = get_800_symbols()

def get_db_connection():
    return sqlite3.connect(DB_PATH, timeout=10)

def scan_market():
    print(f"[{datetime.datetime.now()}] Starting Global Pattern Scan for {len(MEGA_CAPS)} stocks...")
    
    # Download data in bulk to minimize API calls and avoid bans
    try:
        # Fetch data in bulk for all 800 stocks at once (fastest way for yfinance)
        # Using threads internally in yf
        print(f"[{datetime.datetime.now()}] جلب بيانات {len(MEGA_CAPS)} سهم لتحديث النماذج...")
        data = yf.download(MEGA_CAPS, period="1mo", interval="1h", progress=False, group_by="ticker")
    except Exception as e:
        print(f"Yahoo Download Error: {e}")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clear old patterns
    cursor.execute("DELETE FROM global_patterns")
    
    detected_count = 0
    for symbol in MEGA_CAPS:
        try:
            # If only 1 symbol passed somehow (unlikely), yf returns single level
            if isinstance(data.columns, pd.MultiIndex):
                if symbol not in data.columns.levels[0]:
                    continue
                stock_data = data[symbol].copy()
            else:
                stock_data = data.copy()
                
            stock_data = stock_data.dropna()
            stock_data = stock_data[~stock_data.index.duplicated(keep='first')]
            stock_data = stock_data.sort_index()

            if len(stock_data) < 20: continue
            
            detector = PatternDetector(stock_data, order=4)
            pattern = detector.detect_patterns()
            
            if pattern:
                cursor.execute("""
                    INSERT INTO global_patterns (symbol, pattern_name, pattern_type, probability, details, ts_utc)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    symbol, 
                    pattern['pattern'], 
                    pattern['type'], 
                    pattern['probability'], 
                    pattern['details'], 
                    datetime.datetime.utcnow().isoformat()
                ))
                detected_count += 1
                print(f"✅ Found {pattern['pattern']} on {symbol}!")
                
        except Exception as e:
            pass # Skip stock if error
            
    conn.commit()
    conn.close()
    print(f"[{datetime.datetime.now()}] Scan Complete. Found {detected_count} patterns.")

if __name__ == "__main__":
    while True:
        scan_market()
        # مسح كل 15 دقيقة لتجنب الحظر ولأن فريم 1 ساعة يتحدث ببطء
        time.sleep(900) 
