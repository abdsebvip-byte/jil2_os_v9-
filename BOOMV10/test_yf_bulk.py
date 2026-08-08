# test_yf_bulk.py
import yfinance as yf
import time
from yahoo_scanner import FreeMarketScanner

def test():
    scanner = FreeMarketScanner()
    print("Fetching symbols from SEC...")
    symbols = scanner.fetch_all_us_symbols()
    test_symbols = symbols[:1000] # نختبر أول 1000 سهم
    
    print(f"Downloading daily data for {len(test_symbols)} symbols via yfinance...")
    start_time = time.time()
    
    # yfinance يتيح جلب البيانات بالتوازي باستخدام threads=True
    # نطلب بيانات آخر يومين (للحصول على سعر الإغلاق السابق والسعر الحالي)
    # prepost=True يجلب تداولات ما قبل وما بعد السوق
    data = yf.download(
        tickers=test_symbols,
        period="2d",
        interval="1d",
        group_by="ticker",
        threads=True,
        progress=False,
        prepost=True
    )
    
    end_time = time.time()
    print(f"Download finished in {end_time - start_time:.2f} seconds.")
    
    # استخراج البيانات وتصفيتها
    valid_quotes = 0
    for symbol in test_symbols:
        try:
            if symbol not in data:
                continue
            symbol_df = data[symbol]
            if len(symbol_df) < 2:
                continue
            
            # سعر الإغلاق السابق وسعر الإغلاق الحالي
            prev_close = symbol_df['Close'].iloc[0]
            current_price = symbol_df['Close'].iloc[1]
            volume = symbol_df['Volume'].iloc[1]
            
            # احتساب التغير المئوي
            if prev_close > 0:
                change = ((current_price - prev_close) / prev_close) * 100
                valid_quotes += 1
                if change > 5:
                    print(f"Breakout found: {symbol} | Price: {current_price:.2f} | Change: {change:+.2f}% | Volume: {volume}")
        except Exception as e:
            continue
            
    print(f"\nTotal valid quotes parsed: {valid_quotes}")

if __name__ == "__main__":
    test()
