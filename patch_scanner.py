import re

with open('auto_scanner.py', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to replace the sequential loop with a concurrent one.
start_str = "                accepted_candidates = []\n                for quote in raw_data:"
# find the exact end of the loop
end_str = "                        continue\n                        \n                # --- طابور الترتيب والمفاضلة اللحظي (Binned Ranking Queue) ---"

start_idx = content.find(start_str)
end_idx = content.find(end_str)

if start_idx == -1 or end_idx == -1:
    print("Could not find loop bounds!")
    print(start_idx, end_idx)
    import sys; sys.exit(1)

end_idx += len("                        continue\n                        \n")

new_loop_code = """                def process_candidate(quote):
                    try:
                        sym = quote.get("symbol")
                        price = _safe_float(quote.get("regularMarketPrice"), 0.0)
                        if price <= 0.0: return None
                        
                        price, change, prev_close = intel._session_price_change(quote, session)
                        
                        max_price_limit = 50.0 if session in ["PRE_MARKET", "AFTER_HOURS", "NIGHT_CLOSED"] else 20.0
                        if not (0.1 <= price <= max_price_limit): return None
                        if not (1.5 <= change <= 60.0): return None
                            
                        float_shares = _safe_float(quote.get("float_shares_outstanding") or quote.get("floatShares"), 10000000.0)
                        thresholds = intel.get_thresholds()
                        if float_shares > thresholds.get("float_max", 30000000.0): return None
                            
                        if session == "PRE_MARKET":
                            volume = _safe_float(quote.get("preMarketVolume") or quote.get("regularMarketVolume"), 0.0)
                        elif session == "AFTER_HOURS":
                            volume = _safe_float(quote.get("postMarketVolume") or quote.get("regularMarketVolume"), 0.0)
                        else:
                            volume = _safe_float(quote.get("regularMarketVolume"), 0.0)
                            
                        value_traded = _safe_float(quote.get("value_traded"), 0.0)
                        if value_traded <= 0.0:
                            value_traded = price * volume
                            
                        if session in ["PRE_MARKET", "AFTER_HOURS", "NIGHT_CLOSED"]:
                            min_vol, min_val, rvol_limit = 50000.0, 100000.0, 0.15
                        else:
                            min_vol, min_val, rvol_limit = 150000.0, 250000.0, thresholds.get("rvol_min", 3.0)
                            
                        if volume < min_vol or value_traded < min_val: return None
                            
                        avg_volume = _safe_float(quote.get("averageDailyVolume3Month"), 100000.0)
                        rvol = volume / avg_volume if avg_volume > 0 else 1.0
                        if rvol < rvol_limit: return None

                        # --- SLOW NETWORK CALLS START HERE (Now running in parallel!) ---
                        sec_sentiment = get_sec_filings_sentiment(sym)
                        anomaly_info = anomaly_map.get(sym, {"is_anomaly": False, "confidence_score": 1.0})
                        
                        is_yahoo = sym in yahoo_trending
                        is_reddit = sym in reddit_trending
                        
                        price_check, change_check, _ = intel._session_price_change(quote, session)
                        internal_trending = rvol >= 3.0 and change_check >= 3.0
                        is_trending = (is_yahoo or is_reddit) and internal_trending
                        
                        is_consolidating = intel.calculate_volatility_squeeze(sym)
                        engine = DecisionEngine()
                        trace = engine.evaluate_symbol(
                            quote=quote, session=session, anomaly_info=anomaly_info,
                            sec_sentiment=sec_sentiment, is_trending=is_trending,
                            is_consolidating=is_consolidating
                        )
                        
                        accepted_dict = None
                        if trace["status"] == "ACCEPTED":
                            accepted_dict = {
                                "symbol": sym, "trace": trace, "quote": quote,
                                "anomaly_info": anomaly_info, "sec_sentiment": sec_sentiment,
                                "is_trending": is_trending, "price": price, "change": change
                            }
                        return (sym, trace, accepted_dict)
                    except Exception as e:
                        logging.warning(f"Background Scanner Symbol Processing Error: {e}")
                        return None

                accepted_candidates = []
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                    results = list(executor.map(process_candidate, raw_data))
                    
                for res in results:
                    if res:
                        sym, trace, accepted_dict = res
                        db.log_evaluation_trace(
                            symbol=sym, price=trace["price"], change=trace["change"],
                            rvol=trace["rvol"], score=trace["score"], ml_prob=trace["ml_prob"],
                            status=trace["status"], reason=trace["rejection_reason"], details=trace["details"]
                        )
                        if accepted_dict:
                            accepted_candidates.append(accepted_dict)
                """

new_content = content[:start_idx] + new_loop_code + "\n                # --- طابور الترتيب والمفاضلة اللحظي (Binned Ranking Queue) ---" + content[end_idx:]

with open('auto_scanner.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
print("auto_scanner.py successfully patched.")
