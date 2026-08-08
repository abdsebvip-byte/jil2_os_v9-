# test_scanner.py
import asyncio
from yahoo_scanner import FreeMarketScanner

async def test():
    scanner = FreeMarketScanner()
    print("--- STEP 1: Fetching symbols from SEC ---")
    symbols = scanner.fetch_all_us_symbols()
    print(f"Total symbols returned: {len(symbols)}")
    if len(symbols) > 50:
        print(f"Sample symbols: {symbols[:20]}")
    else:
        print(f"Symbols list: {symbols}")
        
    print("\n--- STEP 2: Running parallel market scan ---")
    # نختبر مسح أول 1000 سهم لتوفير الوقت ومعرفة سرعة الاستجابة
    test_symbols = symbols[:1000]
    raw_data = await scanner.scan_entire_market(test_symbols)
    print(f"Total raw quotes received from Yahoo Finance: {len(raw_data)}")
    
    print("\n--- STEP 3: Filtering breakout opportunities ---")
    df_ops = scanner.filter_breakout_opportunities(raw_data)
    print(f"Total opportunities found matching filters: {len(df_ops)}")
    if not df_ops.empty:
        print(df_ops.head(15).to_string(index=False))

if __name__ == "__main__":
    asyncio.run(test())
