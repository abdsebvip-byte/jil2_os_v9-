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

@app.route("/logs")
def view_logs():
    log_path = "auto_scanner.log"
    if not os.path.exists(log_path):
        return "Log file not found.", 404
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "<pre>" + "".join(lines[-200:]) + "</pre>"
    except Exception as e:
        return f"Error reading logs: {e}", 500

@app.route("/trace")
def view_trace():
    import sqlite3
    db_path = "quant_platform.db"
    if not os.path.exists(db_path):
        return "Database file not found.", 404
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evaluation_trace ORDER BY id DESC LIMIT 100")
        rows = cursor.fetchall()
        conn.close()
        
        # Build simple HTML table
        html = """
        <html dir='rtl' lang='ar'>
        <head>
            <meta charset='utf-8'>
            <title>سجل قرارات الاستبعاد والتنقيط</title>
            <style>
                body { font-family: sans-serif; background: #121212; color: #fff; padding: 20px; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { border: 1px solid #333; padding: 10px; text-align: right; }
                th { background: #1e1e1e; color: #00d4ff; }
                tr:nth-child(even) { background: #1a1a1a; }
                .ACCEPTED { color: #00c853; font-weight: bold; }
                .REJECTED { color: #ff5252; }
            </style>
        </head>
        <body>
            <h1>📋 سجل فحص واستبعاد الأسهم (آخر 100 سهم)</h1>
            <p><a href="/" style="color:#00d4ff;">🏠 العودة للرئيسية</a> | <a href="/alerts" style="color:#00d4ff;">🔔 سجل التنبيهات المرسلة</a> | <a href="/logs" style="color:#00d4ff;">📄 السجلات البرمجية</a></p>
            <table>
                <tr>
                    <th>المعرف</th>
                    <th>الرمز</th>
                    <th>الوقت</th>
                    <th>السعر</th>
                    <th>التغير اليومي</th>
                    <th>RVOL</th>
                    <th>النقاء (Score)</th>
                    <th>ML %</th>
                    <th>الحالة</th>
                    <th>سبب الاستبعاد</th>
                </tr>
        """
        for r in rows:
            html += f"""
                <tr>
                    <td>{r['id']}</td>
                    <td><b>{r['symbol']}</b></td>
                    <td>{r['evaluated_at']}</td>
                    <td>${r['price']:.3f}</td>
                    <td>{r['change']:.2f}%</td>
                    <td>{r['rvol']:.2f}x</td>
                    <td>{r['score']}%</td>
                    <td>{r['ml_prob']:.1f}%</td>
                    <td class='{r['status']}'>{r['status']}</td>
                    <td>{r['rejection_reason'] or '-'}</td>
                </tr>
            """
        html += "</table></body></html>"
        return html
    except Exception as e:
        return f"Error reading database: {e}", 500

@app.route("/alerts")
def view_alerts():
    import sqlite3
    db_path = "quant_platform.db"
    if not os.path.exists(db_path):
        return "Database file not found.", 404
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts_history ORDER BY id DESC LIMIT 100")
        rows = cursor.fetchall()
        conn.close()
        
        html = """
        <html dir='rtl' lang='ar'>
        <head>
            <meta charset='utf-8'>
            <title>سجل التنبيهات المرسلة</title>
            <style>
                body { font-family: sans-serif; background: #121212; color: #fff; padding: 20px; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { border: 1px solid #333; padding: 10px; text-align: right; }
                th { background: #1e1e1e; color: #ffab40; }
                tr:nth-child(even) { background: #1a1a1a; }
            </style>
        </head>
        <body>
            <h1>🔔 سجل التنبيهات المرسلة لـ Telegram (آخر 100 تنبيه)</h1>
            <p><a href="/" style="color:#ffab40;">🏠 العودة للرئيسية</a> | <a href="/trace" style="color:#ffab40;">📋 سجل التتبع</a> | <a href="/logs" style="color:#ffab40;">📄 السجلات البرمجية</a></p>
            <table>
                <tr>
                    <th>المعرف</th>
                    <th>الرمز</th>
                    <th>تاريخ الإرسال</th>
                    <th>سعر التنبيه</th>
                    <th>النقاط (Score)</th>
                    <th>النوع</th>
                    <th>الجلسة</th>
                    <th>الهدف المقدر</th>
                    <th>أقصى سعر وصل له</th>
                    <th>الحالة</th>
                </tr>
        """
        for r in rows:
            html += f"""
                <tr>
                    <td>{r['id']}</td>
                    <td><b>{r['symbol']}</b></td>
                    <td>{r['sent_at']}</td>
                    <td>${r['price']:.3f}</td>
                    <td>{r['score']}%</td>
                    <td>{r['alert_type']}</td>
                    <td>{r['session']}</td>
                    <td>+{r['target_percent']}%</td>
                    <td>${r['max_price_reached']:.3f}</td>
                    <td>{r['status']}</td>
                </tr>
            """
        html += "</table></body></html>"
        return html
    except Exception as e:
        return f"Error reading database: {e}", 500

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
