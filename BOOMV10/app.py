import os
import sqlite3
import pandas as pd
from flask import Flask, render_template, jsonify
from pattern_detector import PatternDetector
import yfinance as yf

app = Flask(__name__)
DB_PATH = r"C:\Users\sahar\.gemini\antigravity\scratch\jil2_os_v9\quant_platform.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/stocks/<session_type>")
def get_stocks(session_type):
    try:
        conn = get_db_connection()
        # نستدعي أحدث الإشارات من الجدول الفعلي signals
        query = """
        SELECT symbol, ts_utc as discovery_time, score as final_score 
        FROM signals 
        ORDER BY ts_utc DESC LIMIT 15
        """
        stocks = conn.execute(query).fetchall()
        conn.close()
        
        result = []
        for row in stocks:
            result.append({
                "symbol": row["symbol"],
                "time": row["discovery_time"],
                "state": "ACTIVE",
                "score": round(row["final_score"] * 100, 1) if row["final_score"] else 0
            })
            
        # Fallback for testing if DB is empty (should not happen on prod)
        if not result:
             mock = ["NVDA", "TSLA", "AAPL", "AMD", "SMCI"]
             for i, s in enumerate(mock):
                 result.append({"symbol": s, "time": "now", "state": "ACTIVE", "score": 90 - i*5})
                 
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/pattern/<symbol>")
def get_pattern(symbol):
    try:
        df = yf.download(symbol, period="1mo", interval="15m", progress=False)
        if df.empty:
            return jsonify({"status": "no_data"})
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel('Ticker')
            
        detector = PatternDetector(df, order=4)
        pattern = detector.detect_patterns()
        
        if pattern:
            return jsonify({"status": "found", "pattern": pattern})
        else:
            return jsonify({"status": "none"})
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/api/whales")
def get_whales():
    try:
        conn = get_db_connection()
        query = """
        SELECT symbol, ts, reason, change_pct 
        FROM whale_alerts 
        ORDER BY ts DESC LIMIT 5
        """
        whales = conn.execute(query).fetchall()
        conn.close()
        
        result = []
        for row in whales:
            result.append({
                "symbol": row["symbol"],
                "time": row["ts"],
                "reason": row["reason"],
                "impact": round(row["change_pct"], 2) if row["change_pct"] else 0
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/global_patterns")
def get_global_patterns():
    try:
        conn = get_db_connection()
        query = """
        SELECT symbol, pattern_name, pattern_type, probability, details, ts_utc
        FROM global_patterns 
        ORDER BY probability DESC LIMIT 50
        """
        patterns = conn.execute(query).fetchall()
        conn.close()
        
        result = []
        for row in patterns:
            result.append({
                "symbol": row["symbol"],
                "pattern": row["pattern_name"],
                "type": row["pattern_type"],
                "probability": row["probability"],
                "details": row["details"],
                "time": row["ts_utc"]
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/deep_analysis/<symbol>")
def get_deep_analysis(symbol):
    try:
        conn = get_db_connection()
        # 1. Check if our V9 explosive algorithm caught it recently
        signal_query = "SELECT score FROM signals WHERE symbol = ? ORDER BY ts_utc DESC LIMIT 1"
        signal_res = conn.execute(signal_query, (symbol,)).fetchone()
        
        # 2. Check for recent whale activity
        whale_query = "SELECT reason, change_pct FROM whale_alerts WHERE symbol = ? ORDER BY ts DESC LIMIT 1"
        whale_res = conn.execute(whale_query, (symbol,)).fetchone()
        conn.close()
        
        # 3. Quick liquidity check via yfinance
        df = yf.download(symbol, period="5d", interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel('Ticker')
            
        buying_pressure = "عادية"
        liquidity = "غير متوفرة"
        if not df.empty and len(df) >= 2:
            vol_today = df['Volume'].iloc[-1]
            vol_prev = df['Volume'].iloc[-2]
            if vol_today > vol_prev * 1.5:
                liquidity = "عالية جداً (ارتفاع في الفوليوم)"
            else:
                liquidity = "مستقرة"
                
            close_today = df['Close'].iloc[-1]
            open_today = df['Open'].iloc[-1]
            if close_today > open_today:
                buying_pressure = "إيجابية (سيطرة المشترين)"
            else:
                buying_pressure = "سلبية (سيطرة البائعين)"
                
        return jsonify({
            "v9_condition": "محقق (سبق رصده كلاسيكياً)" if signal_res else "غير محقق (لم يلتقطه رادار الانفجار السريع)",
            "v9_score": round(signal_res["score"] * 100, 1) if signal_res else 0,
            "whale_activity": whale_res["reason"] if whale_res else "لا توجد سيولة خفية مرصودة مؤخراً",
            "liquidity": liquidity,
            "buying_pressure": buying_pressure
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/chart_data/<symbol>")
def get_chart_data(symbol):
    try:
        df = yf.download(symbol, period="1mo", interval="1h", progress=False)
        if df.empty:
            return jsonify({"status": "no_data"})
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel('Ticker')
            
        df = df.dropna()
        df = df[~df.index.duplicated(keep='first')]
        df = df.sort_index()
        
        # Prepare OHLC for lightweight-charts
        candles = []
        for index, row in df.iterrows():
            candles.append({
                "time": int(index.timestamp()),
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"]
            })
            
        # Get Pattern Lines
        detector = PatternDetector(df, order=4)
        pattern = detector.detect_patterns()
        
        return jsonify({
            "status": "success", 
            "candles": candles,
            "pattern": pattern
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    app.run(port=8502, debug=True)
