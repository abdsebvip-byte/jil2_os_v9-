import logging
logging.basicConfig(level=logging.INFO)

try:
    from intelligence import QuantIntelligence
    from decision_engine import DecisionEngine

    intel = QuantIntelligence()
    engine = DecisionEngine()

    fake_quote = {
        "symbol": "TEST",
        "regularMarketPrice": 10.5,
        "regularMarketPreviousClose": 10.0,
        "regularMarketVolume": 5000000,
        "averageDailyVolume3Month": 1000000,
        "floatShares": 8000000,
        "regularMarketOpen": 10.2
    }

    print("Running evaluate_symbol test...")
    trace = engine.evaluate_symbol(
        quote=fake_quote,
        session="REGULAR",
        anomaly_info={"is_anomaly": True, "confidence_score": 8.0},
        sec_sentiment={"material_news": True},
        is_trending=True,
        is_consolidating=False
    )
    
    print("Test passed! Result status:", trace["status"])
    print("Score:", trace["score"])
    print("Details:", trace["details"])
except Exception as e:
    print("TEST FAILED WITH ERROR:", e)
    import traceback
    traceback.print_exc()
