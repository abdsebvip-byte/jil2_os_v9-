# daily_report.py
"""Generate and send the end‑of‑day summary report to Telegram.

The report includes:
- Total alerts generated today.
- Success / failure counts and win‑rate.
- A markdown table of each alert with entry price, target percent, final price, status, and profit/loss.
- Platform‑level efficiency snapshot.

The function is called from `auto_scanner.py` after the market session ends.
"""

import datetime
from database import QuantDatabase
from notifier import TelegramNotifier
from utils import format_number


def _format_alert_row(alert):
    """Return a markdown table row for a single alert.
    Expected keys in `alert`:
        symbol, sent_at, price, target_percent, max_price_reached, status
    """
    symbol = alert.get("symbol", "-")
    entry = format_number(alert.get("price", 0.0))
    target = f"{format_number(alert.get('target_percent', 0.0))}%"
    final_price = format_number(alert.get("max_price_reached", 0.0))
    status = alert.get("status", "PENDING")
    # Estimate profit %
    if status == "SUCCESS":
        profit = target
    elif status == "FAILED":
        try:
            loss_pct = ((alert.get("max_price_reached", 0.0) - alert.get("price", 0.0)) / alert.get("price", 1.0)) * 100
            profit = f"{format_number(loss_pct)}%"
        except Exception:
            profit = "-"
    else:
        profit = "-"
    return f"| {symbol} | {entry} | {target} | {final_price} | {status} | {profit} |"


def send_daily_closing_report():
    """Collect today's alerts from the DB and push a formatted markdown message to Telegram."""
    db = QuantDatabase()
    notifier = TelegramNotifier()

    today = datetime.date.today().isoformat()
    # Fetch recent alerts and filter by today's date.
    all_alerts = db.get_alerts_history(limit=200)
    todays_alerts = [a for a in all_alerts if a.get("sent_at", "").startswith(today)]

    total = len(todays_alerts)
    success = sum(1 for a in todays_alerts if a.get("status") == "SUCCESS")
    failed = sum(1 for a in todays_alerts if a.get("status") == "FAILED")
    win_rate = (success / total * 100) if total else 0.0

    header = f"📊 *تقرير إغلاق اليوم - {today}*"
    summary = f"\n🟢 إجمالي التنبيهات: {total}\n✅ نجاح: {success}\n❌ فشل: {failed}\n🎯 معدل الربح: {format_number(win_rate)}%"
    table_header = "\n| السهم | سعر الدخول | نسبة الهدف | أعلى سعر | الحالة | الربح/الخسارة |\n|---|---|---|---|---|---|"
    rows = "\n".join(_format_alert_row(a) for a in todays_alerts)

    # Platform performance snapshot
    efficiency = db.calculate_platform_efficiency()
    perf = ("\n\n⚙️ *مؤشرات الأداء*\n" +
            f"- إجمالي التنبيهات: {efficiency.get('total_alerts', 0)}\n" +
            f"- إغلاق: {efficiency.get('closed_alerts', 0)}\n" +
            f"- نجاح: {efficiency.get('success_alerts', 0)}\n" +
            f"- Win Rate: {efficiency.get('win_rate', 0)}%\n" +
            f"- Early Catch Rate: {efficiency.get('early_rate', 0)}%")

    message = header + summary + table_header + ("\n" + rows if rows else "\n| لا توجد تنبيهات اليوم | - | - | - | - | - |") + perf
    return notifier.send_custom_message(message)
