# test_yq.py
from yahooquery import Screener

def test():
    print("Testing yahooquery Screener API...")
    try:
        s = Screener()
        # البارامتر الصحيح هو screen_ids وليس scr_ids
        data = s.get_screeners(screen_ids=['day_gainers', 'most_actives'], count=150)
        
        print("\n--- Day Gainers ---")
        gainers = data.get('day_gainers', {}).get('quotes', [])
        print(f"Total gainers retrieved: {len(gainers)}")
        for stock in gainers[:10]:
            symbol = stock.get('symbol')
            price = stock.get('regularMarketPrice')
            change = stock.get('regularMarketChangePercent')
            volume = stock.get('regularMarketVolume')
            print(f" Gainer: {symbol} | Price: {price} | Change: {change:+.2f}% | Volume: {volume}")
            
        print("\n--- Most Active ---")
        active = data.get('most_actives', {}).get('quotes', [])
        print(f"Total active retrieved: {len(active)}")
        for stock in active[:10]:
            symbol = stock.get('symbol')
            price = stock.get('regularMarketPrice')
            change = stock.get('regularMarketChangePercent')
            volume = stock.get('regularMarketVolume')
            print(f" Active: {symbol} | Price: {price} | Change: {change:+.2f}% | Volume: {volume}")
            
    except Exception as e:
        print(f"yahooquery failed: {e}")

if __name__ == "__main__":
    test()
