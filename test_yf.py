# test_yf.py
import yfinance as yf

def test():
    print("Testing yfinance library access...")
    try:
        # نختبر جلب بيانات 3 رموز رئيسية
        data = yf.download(tickers="AAPL MSFT NVDA", period="1d", interval="1m", group_by="ticker", auto_adjust=True, prepost=True, threads=True)
        print("Download completed successfully!")
        print("Data columns:")
        print(data.columns)
        print("\nData head:")
        print(data.head(2))
    except Exception as e:
        print(f"yfinance failed: {e}")

if __name__ == "__main__":
    test()
