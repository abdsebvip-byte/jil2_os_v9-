# app.py — Flask web server + background scanner
import os
import threading
from flask import Flask, jsonify
from datetime import datetime
import pytz

app = Flask(__name__)

from state import scanner_status

@app.route("/")
def index():
    est_tz = pytz.timezone('US/Eastern')
    now_est = datetime.now(est_tz).strftime("%Y-%m-%d %H:%M:%S EST")
    return f"""
    <html dir='rtl' lang='ar'>
    <head>
        <meta charset='utf-8'>
        <title>BoomMarkt - منصة رصد الأسهم الانفجارية</title>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: 'Segoe UI', Tahoma, sans-serif;
                background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
                color: #e0e0e0;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .container {{
                text-align: center;
                padding: 40px;
                background: rgba(255,255,255,0.05);
                border-radius: 20px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.1);
                max-width: 600px;
                width: 90%;
            }}
            h1 {{ font-size: 2em; margin-bottom: 10px; color: #00d4ff; }}
            .status {{ 
                display: inline-block;
                padding: 8px 20px;
                border-radius: 50px;
                font-weight: bold;
                margin: 15px 0;
            }}
            .running {{ background: rgba(0,200,83,0.2); color: #00c853; border: 1px solid #00c853; }}
            .stopped {{ background: rgba(255,82,82,0.2); color: #ff5252; border: 1px solid #ff5252; }}
            .info {{ color: #aaa; margin: 8px 0; font-size: 0.9em; }}
            .time {{ color: #ffab40; font-size: 1.1em; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class='container'>
            <h1>🚀 BoomMarkt</h1>
            <p style='font-size:1.2em; color:#ccc;'>منصة رصد الأسهم الانفجارية</p>
            <div class='status {"running" if scanner_status["is_running"] else "stopped"}'>
                {"🟢 الماسح يعمل الآن" if scanner_status["is_running"] else "🔴 الماسح متوقف"}
            </div>
            <p class='info'>عدد دورات المسح المكتملة: {scanner_status["scans_completed"]}</p>
            <p class='info'>آخر مسح: {scanner_status["last_scan"] or "لم يبدأ بعد"}</p>
            <p class='time'>🕐 {now_est}</p>
            <p class='info' style='margin-top:20px; color:#666;'>التنبيهات تُرسل تلقائياً عبر Telegram</p>
        </div>
    </body>
    </html>
    """

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "scanner_running": scanner_status["is_running"],
        "scans_completed": scanner_status["scans_completed"],
        "last_scan": scanner_status["last_scan"]
    })

@app.route("/api/status")
def api_status():
    return jsonify(scanner_status)

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


def run_scanner_background():
    """Run the auto scanner in a background thread."""
    scanner_status["is_running"] = True
    scanner_status["started_at"] = datetime.utcnow().isoformat()
    try:
        from auto_scanner import start_scheduler
        start_scheduler()
    except Exception as e:
        scanner_status["is_running"] = False
        scanner_status["errors"].append(str(e))
        print(f"Scanner crashed: {e}")


if __name__ == "__main__":
    # Start scanner in background thread
    scanner_thread = threading.Thread(target=run_scanner_background, daemon=True)
    scanner_thread.start()
    print("Scanner background thread started.")
    
    # Start Flask web server
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
