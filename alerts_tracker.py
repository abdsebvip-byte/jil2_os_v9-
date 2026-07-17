# alerts_tracker.py
import requests
import re
import yfinance as yf
import logging

def get_active_halts():
    """
    Fetch and parse the official Nasdaq Trading Halts RSS feed.
    Returns a dictionary of symbols currently halted: {SYMBOL: REASON_CODE}
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    url = "https://www.nasdaqtrader.com/rss.aspx?feed=tradehalts"
    halted_symbols = {}
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            items = re.findall(r"<item>(.*?)</item>", res.text, re.DOTALL)
            for item in items:
                title_match = re.search(r"<title>(.*?)</title>", item, re.DOTALL)
                desc_match = re.search(r"<description>(.*?)</description>", item, re.DOTALL)
                
                if title_match and desc_match:
                    sym = title_match.group(1).replace("<![CDATA[", "").replace("]]>", "").strip()
                    desc = desc_match.group(1).replace("<![CDATA[", "").replace("]]>", "").strip()
                    
                    # Parse TD elements
                    tds = re.findall(r"<td[^>]*>(.*?)</td>", desc, re.DOTALL)
                    if len(tds) >= 10:
                        reason = tds[5].strip()
                        res_trade_time = tds[9].strip()
                        
                        # If resumption trade time is empty, TBD, or equals quote time without trade execution, it is currently halted
                        if not res_trade_time or "TBD" in res_trade_time or res_trade_time == "":
                            halted_symbols[sym] = reason
    except Exception as e:
        logging.warning(f"HaltsTracker Error: {e}")
        
    return halted_symbols

def get_sec_filings_sentiment(symbol):
    """
    Fetch the latest news for a symbol via yfinance, and scan titles/summaries
    for SEC Form 4 (insider buy), Form 8-K (material event), and Form S-1 (dilution warning).
    """
    sentiment = {
        "insider_buy": False,
        "material_news": False,
        "dilution_warning": False,
        "details": []
    }
    
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news
        if not news:
            return sentiment
            
        for article in news[:5]:
            title = article.get("title", "").upper()
            summary = article.get("summary", "").upper()
            text_to_scan = f"{title} {summary}"
            
            # 1. Insider buying (Form 4)
            if any(k in text_to_scan for k in ["FORM 4", "INSIDER BUY", "INSIDER ACQUISITION", "DIRECTOR PURCHASE"]):
                sentiment["insider_buy"] = True
                sentiment["details"].append("Form 4 (Insider Buy)")
                
            # 2. Material event (Form 8-K)
            if any(k in text_to_scan for k in ["FORM 8-K", "FORM 8K", "MATERIAL EVENT", "MERGER", "ACQUISITION", "PARTNERSHIP"]):
                sentiment["material_news"] = True
                sentiment["details"].append("Form 8-K (Material Event)")
                
            # 3. Dilution Warning (Form S-1 / Offering)
            if any(k in text_to_scan for k in ["FORM S-1", "FORM S1", "SHELF REGISTRATION", "STOCK OFFERING", "DILUTION", "PUBLIC OFFERING"]):
                sentiment["dilution_warning"] = True
                sentiment["details"].append("Form S-1 (Dilution Alert)")
    except Exception as e:
        logging.warning(f"SECFilingsTracker Error for {symbol}: {e}")
        
    return sentiment
