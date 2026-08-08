# test_decision_engine.py
import unittest
import os
from decision_engine import DecisionEngine
from database import QuantDatabase

class TestDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = DecisionEngine()
        self.db = QuantDatabase()
        
    def test_evaluate_accepted_stock(self):
        # A low-float stock with positive catalysts and reasonable change
        quote = {
            "symbol": "TEST",
            "regularMarketPrice": 5.2,
            "regularMarketPreviousClose": 4.8,
            "regularMarketVolume": 500000.0,
            "averageDailyVolume3Month": 100000.0, # RVOL = 5.0
            "float_shares_outstanding": 3000000.0 # Low float = 3M
        }
        sec_sentiment = {
            "insider_buy": True,
            "material_news": False,
            "dilution_warning": False,
            "details": []
        }
        anomaly_info = {"is_anomaly": True, "confidence_score": 8.0}
        
        trace = self.engine.evaluate_symbol(
            quote=quote,
            session="REGULAR_SESSION",
            anomaly_info=anomaly_info,
            sec_sentiment=sec_sentiment,
            is_trending=True
        )
        
        self.assertEqual(trace["symbol"], "TEST")
        self.assertEqual(trace["status"], "ACCEPTED")
        self.assertTrue(trace["score"] >= 80)
        
    def test_evaluate_rejected_dilution(self):
        quote = {
            "symbol": "DILS",
            "regularMarketPrice": 2.5,
            "regularMarketPreviousClose": 2.2,
            "regularMarketVolume": 1000000.0,
            "averageDailyVolume3Month": 200000.0,
            "float_shares_outstanding": 5000000.0
        }
        sec_sentiment = {
            "insider_buy": False,
            "material_news": False,
            "dilution_warning": True, # Diluted!
            "details": ["Form S-1 detected"]
        }
        anomaly_info = {"is_anomaly": False, "confidence_score": 2.0}
        
        trace = self.engine.evaluate_symbol(
            quote=quote,
            session="REGULAR_SESSION",
            anomaly_info=anomaly_info,
            sec_sentiment=sec_sentiment
        )
        
        self.assertEqual(trace["status"], "REJECTED")
        self.assertIn("تخفيف", trace["rejection_reason"])
        
    def test_database_logging(self):
        # Log a test trace to SQLite
        self.db.log_evaluation_trace(
            symbol="MOCK",
            price=10.0,
            change=15.0,
            rvol=6.2,
            score=85.0,
            ml_prob=80.0,
            status="ACCEPTED",
            reason="AI pass",
            details={"test": True}
        )
        
        recent = self.db.get_recent_evaluations(limit=5)
        self.assertTrue(len(recent) > 0)
        mock_record = [r for r in recent if r["symbol"] == "MOCK"]
        self.assertTrue(len(mock_record) > 0)
        self.assertEqual(mock_record[0]["status"], "ACCEPTED")
        self.assertEqual(mock_record[0]["price"], 10.0)

if __name__ == "__main__":
    unittest.main()
