# debug_filter.py
import asyncio
from yahoo_scanner import FreeMarketScanner

async def debug():
    scanner = FreeMarketScanner()
    symbols = scanner.fetch_all_us_symbols()
    raw_data = await scanner.scan_entire_market(symbols)
    
    print("\n--- STEP-BY-STEP FILTER EVALUATION ---")
    skipped_by_price = 0
    skipped_by_change = 0
    accepted = []
    
    for quote in raw_data:
        symbol = quote.get("symbol")
        price = float(quote.get("regularMarketPrice", 0.0))
        price_change = float(quote.get("regularMarketChangePercent", 0.0))
        
        market_state = quote.get("marketState", "")
        # طباعة البيانات الخام لبعض الرموز مثل RGC أو أي رمز رخيص
        is_interesting = price < 30.0 and abs(price_change) > 3.0
        
        # تطبيق نفس منطق التحويل
        if market_state in ["PRE", "PREPRE"] and quote.get("preMarketPrice") is not None:
            price = float(quote.get("preMarketPrice"))
            price_change = float(quote.get("preMarketChangePercent", 0.0))
        elif market_state in ["POST", "POSTPOST"] and quote.get("postMarketPrice") is not None:
            price = float(quote.get("postMarketPrice"))
            price_change = float(quote.get("postMarketChangePercent", 0.0))
            
        if is_interesting:
            print(f"Ticker: {symbol} | Price (Evaluated): {price} | Change: {price_change}% | State: {market_state}")
            
        if price <= 0.0 or price > 20.0:
            skipped_by_price += 1
            if is_interesting:
                print(f"  -> Skipped by price (>20 or <=0)")
            continue
            
        if not (5.0 <= price_change <= 40.0):
            skipped_by_change += 1
            if is_interesting:
                print(f"  -> Skipped by change percentage ({price_change}%)")
            continue
            
        accepted.append({
            "Symbol": symbol,
            "Price": price,
            "Change_%": price_change
        })
        print(f"  -> ACCEPTED! Symbol: {symbol}")
        
    print(f"\nEvaluation summary:")
    print(f"Total Tickers: {len(raw_data)}")
    print(f"Skipped by price: {skipped_by_price}")
    print(f"Skipped by change percent: {skipped_by_change}")
    print(f"Total Accepted: {len(accepted)}")

if __name__ == "__main__":
    asyncio.run(debug())
