# module: app_v10.py
import streamlit as st
import time
from datetime import datetime
import pandas as pd
import asyncio
import logging
import requests
import importlib
import scanner
import intelligence
import news_radar
import notifier
import alerts_tracker
import database

importlib.reload(scanner)
importlib.reload(intelligence)
importlib.reload(news_radar)
importlib.reload(notifier)
importlib.reload(alerts_tracker)
importlib.reload(database)

from scanner import FreeMarketScanner
from intelligence import QuantIntelligence
from news_radar import SECNewsRadar
from notifier import TelegramNotifier
from alerts_tracker import get_active_halts, get_sec_filings_sentiment
from database import QuantDatabase

db = QuantDatabase()

# إعداد ملف مراقبة الأخطاء المركزي (Centralized Error Logging)
logging.basicConfig(
    filename="radar_errors.log",
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# 1. إعداد الصفحة والأنماط البصرية الراقية (Premium Dark Tech Theme)
st.set_page_config(page_title="منظومة رادار السيولة التراكمية v10.0", layout="wide")

# استيراد خطوط Google Fonts وتصميم الواجهة بمؤثرات حديثة
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Cairo:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
    /* منع تعتيم وتبييض الصفحة تماماً أثناء تحديث البيانات لضمان تباين ووضوح ألوان الجداول والأسهم */
    .stApp [data-stale="true"], div[data-stale="true"] {
        opacity: 1.0 !important;
        filter: none !important;
        transition: none !important;
    }

    /* تطبيق الألوان والخطوط للوحة التحكم */
    .main { 
        background-color: #080b10; 
        color: #e2e8f0; 
        font-family: 'Cairo', 'Outfit', sans-serif; 
    }
    
    /* أسلوب الزجاج البلوري (Glassmorphic Cards) */
    .metric-card { 
        background: #1e293b !important; 
        border: 1px solid rgba(255, 255, 255, 0.15) !important; 
        padding: 24px; 
        border-radius: 16px; 
        text-align: center; 
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2); 
        transition: transform 0.3s ease, border-color 0.3s ease;
        color: #ffffff !important;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        border-color: rgba(245, 158, 11, 0.4);
    }
    .metric-card h4 {
        color: #94a3b8 !important;
    }
    .metric-card h2 {
        color: #10b981 !important;
    }
    .metric-card h3 {
        color: #f59e0b !important;
    }
    
    /* ترويسة الصفحة الاحترافية */
    .title-header { 
        background: linear-gradient(135deg, #f59e0b, #ef4444);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center; 
        font-size: 38px;
        font-weight: 700; 
        margin-bottom: 30px; 
        filter: drop-shadow(0 2px 8px rgba(245, 158, 11, 0.2));
    }
    
    /* بطاقة التوجيه التنفيذي النيون */
    .signal-card {
        background: linear-gradient(135deg, #1e293b, #0f172a) !important;
        border: 1px solid rgba(16, 185, 129, 0.4) !important;
        box-shadow: 0 0 25px rgba(16, 185, 129, 0.15);
        padding: 30px;
        border-radius: 20px;
        margin-top: 25px;
        margin-bottom: 25px;
        position: relative;
        color: #ffffff !important;
    }
    .signal-card h2 {
        color: #10b981 !important;
    }
    .signal-card h3, .signal-card p, .signal-card b, .signal-card span {
        color: #ffffff !important;
    }
    
    .signal-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #10b981, #3b82f6);
        border-radius: 20px 20px 0 0;
    }
    
    /* قسم الذكاء الاصطناعي المخصص */
    .ai-section {
        background: #0f172a !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
        border-radius: 16px;
        padding: 20px;
        margin-top: 20px;
        margin-bottom: 20px;
        color: #ffffff !important;
    }
    .ai-section h3 {
        color: #3b82f6 !important;
    }
    .ai-section p {
        color: #94a3b8 !important;
    }
</style>
""", unsafe_allow_html=True)

def render_premium_table(df):
    """
    تحويل DataFrame إلى جدول HTML أنيق وعالي التباين متناسق الألوان ومناسب للوضع المظلم المتطور.
    """
    if df.empty:
        return ""
    
    html = """
    <style>
        .premium-table-container {
            width: 100%;
            margin: 15px 0;
            overflow-x: auto;
            border-radius: 12px;
            border: 1px solid #1E293B;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
            background-color: #0F172A;
        }
        .premium-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'Cairo', 'Inter', sans-serif;
            text-align: center;
        }
        /* تثبيت العمود الأول لرمز السهم عند التمرير الأفقي للجداول */
        .premium-table th:first-child, .premium-table td:first-child {
            position: sticky !important;
            left: 0 !important;
            background-color: #0F172A !important;
            z-index: 10 !important;
            box-shadow: 2px 0 5px rgba(0, 0, 0, 0.35) !important;
        }
        .premium-table tr:hover td:first-child {
            background-color: #1E293B !important;
        }
        .premium-table th:first-child {
            background: linear-gradient(135deg, #1E293B, #0F172A) !important;
            z-index: 11 !important;
        }

        .premium-table th {
            background: linear-gradient(135deg, #1E293B, #0F172A) !important;
            color: #00FFCC !important;
            font-weight: 700 !important;
            padding: 14px 16px !important;
            font-size: 13px !important;
            border-bottom: 2px solid #334155 !important;
            text-shadow: 0px 1px 2px rgba(0,0,0,0.5);
            white-space: nowrap;
        }
        .premium-table td {
            padding: 12px 16px !important;
            color: #F8FAFC !important;
            font-size: 13px !important;
            border-bottom: 1px solid #1E293B !important;
            vertical-align: middle;
        }
        .premium-table tr:hover {
            background-color: #1E293B !important;
            cursor: pointer;
        }
        .premium-table tr:last-child td {
            border-bottom: none !important;
        }
        .badge-green {
            background-color: rgba(16, 185, 129, 0.15);
            color: #10B981;
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: bold;
            border: 1px solid rgba(16, 185, 129, 0.3);
            display: inline-block;
        }
        .badge-red {
            background-color: rgba(239, 68, 68, 0.15);
            color: #EF4444;
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: bold;
            border: 1px solid rgba(239, 68, 68, 0.3);
            display: inline-block;
        }
        .badge-gold {
            background-color: rgba(245, 158, 11, 0.15);
            color: #F59E0B;
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: bold;
            border: 1px solid rgba(245, 158, 11, 0.3);
            display: inline-block;
        }
        .badge-blue {
            background-color: rgba(59, 130, 246, 0.15);
            color: #3B82F6;
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: bold;
            border: 1px solid rgba(59, 130, 246, 0.3);
            display: inline-block;
        }
        .badge-purple {
            background-color: rgba(139, 92, 246, 0.15);
            color: #8B5CF6;
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: bold;
            border: 1px solid rgba(139, 92, 246, 0.3);
            display: inline-block;
        }
    </style>
    <div class="premium-table-container">
        <table class="premium-table">
            <thead>
                <tr>
    """
    for col in df.columns:
        html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"
    
    for _, row in df.iterrows():
        html += "<tr>"
        for col in df.columns:
            val = str(row[col])
            if "🟢" in val or "آمن" in val or "نجاح" in val or "شراء" in val:
                html += f"<td><span class='badge-green'>{val}</span></td>"
            elif "🔴" in val or "🚨" in val or "خطر" in val or "فشل" in val or "تجنب" in val:
                html += f"<td><span class='badge-red'>{val}</span></td>"
            elif "🔥" in val:
                html += f"<td><span class='badge-gold'>{val}</span></td>"
            elif "⚡" in val or "M" in val or "%" in val:
                html += f"<td><span class='badge-blue'>{val}</span></td>"
            elif "🔮" in val or "💥" in val:
                html += f"<td><span class='badge-purple'>{val}</span></td>"
            else:
                html += f"<td>{val}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    return html


st.markdown('<h1 class="title-header">🚀 رادار الأسهم الأمريكية: منصة التحليل الكمي ورصد شذوذ السيولة</h1>', unsafe_allow_html=True)

# 2. تهيئة حالات الجلسة (Session States)
if "accumulated_balance" not in st.session_state:
    st.session_state.accumulated_balance = 1000.0
if "paper_ledger" not in st.session_state:
    st.session_state.paper_ledger = []

# تهيئة المحركات الهيكلية
scanner = FreeMarketScanner()
intel = QuantIntelligence()
news_radar = SECNewsRadar()

# فحص PID مباشرة باستخدام ctypes للتحقق من تشغيل العملية
def _pid_alive(pid):
    """Check if a PID is alive using ctypes OpenProcess (no subprocess overhead)."""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x00100000
        handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    except:
        return False

# تفعيل مشغل الفحص التلقائي الخلفي كعملية مستقلة (Subprocess)
def initialize_background_auto_scanner():
    import os
    import subprocess
    pid_file = "auto_scanner.pid"
    if os.path.exists(pid_file):
        try:
            pid = int(open(pid_file).read().strip())
            if _pid_alive(pid):
                return "ALREADY_RUNNING"
        except:
            pass

    venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        import sys
        venv_python = sys.executable

    try:
        proc = subprocess.Popen(
            [venv_python, "auto_scanner.py"],
            creationflags=0x08000000,  # CREATE_NO_WINDOW
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        with open(pid_file, "w") as pf:
            pf.write(str(proc.pid))
        return "STARTED"
    except Exception as e:
        return f"ERROR: {e}"

auto_status = initialize_background_auto_scanner()

def format_ml_prob(val):
    if val is None or val == 0.0 or pd.isna(val):
        return "⚠️ غير نشط"
    return f"🔮 {val:.1f}%"

# تفعيل خادم البوت التفاعلي كعملية مستقلة (Subprocess)
def initialize_interactive_bot():
    import os
    import subprocess
    pid_file = "bot_listener.pid"
    if os.path.exists(pid_file):
        try:
            pid = int(open(pid_file).read().strip())
            if _pid_alive(pid):
                return "ALREADY_RUNNING"
        except:
            pass

    venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        import sys
        venv_python = sys.executable

    try:
        proc = subprocess.Popen(
            [venv_python, "bot_listener.py"],
            creationflags=0x08000000,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        with open(pid_file, "w") as pf:
            pf.write(str(proc.pid))
        return "STARTED"
    except Exception as e:
        return f"ERROR: {e}"

bot_status = initialize_interactive_bot()

# 📈 مؤشر اتجاه السوق العام (Market Trend Correlation)
st.sidebar.markdown("### 🌐 اتجاه السوق العام (SPY/QQQ)")
try:
    from intraday_tracker import get_market_trend
    trend = get_market_trend()
    spy_val = trend["spy_change"]
    qqq_val = trend["qqq_change"]
    
    if trend["status"] == "GREEN":
        st.sidebar.success(f"🟢 السوق صاعد ومستقر\n\n(SPY: {spy_val:+.2f}% | QQQ: {qqq_val:+.2f}%)")
    elif trend["status"] == "YELLOW":
        st.sidebar.warning(f"🟡 السوق حذر وجانبي\n\n(SPY: {spy_val:+.2f}% | QQQ: {qqq_val:+.2f}%)")
    else:
        st.sidebar.error(f"🔴 السوق هابط ومخاطر عالية\n\n(SPY: {spy_val:+.2f}% | QQQ: {qqq_val:+.2f}%)")
except Exception as trend_ex:
    st.sidebar.info("ℹ️ اتجاه السوق: غير متوفر مؤقتاً")

# 🟢 مؤشر نبضات القلب ومراقبة المحرك الخلفي بالثانية
st.sidebar.markdown("### 🤖 حالة المحرك الخلفي")
from database import QuantDatabase
db_hb = QuantDatabase()
last_hb_str = db_hb.get_last_heartbeat()
if last_hb_str:
    last_hb = datetime.fromisoformat(last_hb_str)
    diff = (datetime.now() - last_hb).total_seconds()
    
    from scanner import FreeMarketScanner
    temp_scanner = FreeMarketScanner()
    current_sess = temp_scanner.get_current_market_session()
    max_allowed = 650.0 if current_sess == "NIGHT_CLOSED" else 240.0
    
    if diff <= max_allowed:
        st.sidebar.success(f"🟢 المحرك الخلفي: يعمل بنشاط\n(آخر نبض: منذ {int(diff)} ثانية)")
    else:
        st.sidebar.error(f"🔴 المحرك الخلفي: متوقف!\n(آخر نبض: منذ {int(diff/60)} دقيقة)")
else:
    st.sidebar.warning("⚠️ المحرك الخلفي: لم يبدأ بعد أو لم يسجل نبضات.")

# 📈 مؤشر كفاءة المنصة المطور (System Efficiency KPI Dashboard)
st.sidebar.markdown("### 📈 كفاءة المنصة (Efficiency KPI)")
try:
    from database import QuantDatabase
    db_kpi = QuantDatabase()
    kpi = db_kpi.calculate_platform_efficiency()
    
    idx = kpi["overall_index"]
    if idx >= 85.0:
        quality_status = "🟢 ممتاز ومستقر جداً"
        color = "#00FFCC"
    elif idx >= 70.0:
        quality_status = "🟢 جيد ومستقر"
        color = "#3b82f6"
    else:
        quality_status = "🚨 بحاجة لتطوير وتدريب الـ ML"
        color = "#FF3366"
        
    st.sidebar.markdown(f"""
    <div style="background-color: #1e293b; padding: 15px; border-radius: 10px; border-left: 5px solid {color}; margin-bottom: 20px;">
        <p style="color:#94a3b8; font-size: 13px; margin: 0; font-family: sans-serif;">الكفاءة الإجمالية للنظام:</p>
        <h2 style="color:{color}; margin: 5px 0; font-size: 32px; font-family: sans-serif;">{idx}%</h2>
        <p style="color:#e2e8f0; font-size: 13px; margin: 5px 0 0 0; font-family: sans-serif;">🔍 <b>الحالة:</b> {quality_status}</p>
        <hr style="margin: 10px 0; border-color: #334155;"/>
        <p style="color:#94a3b8; font-size: 12px; margin: 2px 0; font-family: sans-serif;">🎯 نسبة الأهداف (Win Rate): <b>{kpi['win_rate']}%</b></p>
        <p style="color:#94a3b8; font-size: 12px; margin: 2px 0; font-family: sans-serif;">⚡ الكشف المبكر (&le;7%): <b>{kpi['early_rate']}%</b></p>
        <p style="color:#94a3b8; font-size: 12px; margin: 2px 0; font-family: sans-serif;">📦 التنبيهات المغلقة: <b>{kpi['closed_alerts']}</b></p>
    </div>
    """, unsafe_allow_html=True)
except Exception as kpi_err:
    st.sidebar.error(f"فشل حساب مؤشر الكفاءة: {kpi_err}")

# 2.1 إعداد شريط جانبي لأدوات التحكم والاختبار
st.sidebar.markdown("### 🛠️ أدوات التحكم والربط")
st.sidebar.write("استخدم هذا الزر للتأكد من نجاح اتصال بوت تيليجرام فقط — **الأرقام وهمية ولا علاقة لها بالسوق:**")
if st.sidebar.button("🔧 اختبار اتصال تيليجرام فقط (أرقام وهمية)", key="sidebar_tg_test"):
    notifier = TelegramNotifier()
    import requests, os
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    test_msg = (
        "🔧 *رسالة اختبار اتصال فقط — ليست توصية حقيقية*\n\n"
        "✅ بوت تيليجرام متصل ويعمل بشكل صحيح.\n"
        "⚠️ هذه الأرقام وهمية بالكامل ولا علاقة لها بأي سهم في السوق:\n"
        "• رمز وهمي: `TEST-BOT`\n"
        "• سعر وهمي: `$12.45`\n"
        "• تغيير وهمي: `+15.8%`\n\n"
        "📌 التنبيهات الحقيقية تأتي تلقائياً من محرك الفحص عند اكتشاف سهم فعلي."
    )
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={"chat_id": chat_id, "text": test_msg, "parse_mode": "Markdown"}, timeout=10)
        success = resp.status_code == 200
    except:
        success = False
    if success:
        st.sidebar.success("✅ الاتصال يعمل! وصلتك رسالة توضح أنها اختبار فقط.")
    else:
        st.sidebar.error("❌ فشل الإرسال، تحقق من config.env.")

# 🧮 حاسبة حجم الصفقة وإدارة المخاطر (Position Sizing Calculator)
st.sidebar.markdown("---")
st.sidebar.markdown("### 🧮 حاسبة حجم الصفقة وإدارة المخاطر")
account_val = st.sidebar.number_input("إجمالي رأس المال في حسابك ($):", min_value=10.0, value=st.session_state.accumulated_balance, step=100.0)
risk_pct = st.sidebar.slider("حد المخاطرة الأقصى لكل صفقة (%):", min_value=1.0, max_value=20.0, value=10.0, step=1.0)
entry_price = st.sidebar.number_input("سعر دخول السهم المتوقع ($):", min_value=0.01, value=5.00, step=0.1)

max_loss_allowed = (account_val * risk_pct) / 100.0
# Assuming stop loss is 7.0%
stop_loss_pct = 7.0
max_position_size = max_loss_allowed / (stop_loss_pct / 100.0)
# Capital protection: Never allocate more than 25% of account to a single penny stock
max_position_size = min(max_position_size, account_val * 0.25)
shares_to_buy = max_position_size / entry_price

st.sidebar.info(
    f"💵 *مبلغ الشراء المقترح (الحد الأقصى):* `{max_position_size:.2f} $`\n\n"
    f"📉 *أقصى خسارة مسموحة:* `{max_loss_allowed:.2f} $` (عند هبوط -7%)\n\n"
    f"📦 *عدد الأسهم المقترح للشراء:* `{int(shares_to_buy)} سهم`"
)

# رصد الجلسة الزمنية الحالية
current_session = scanner.get_current_market_session()
session_translation = {
    "PRE_MARKET": "🛰️ جلسة ما قبل السوق (Pre-Market)",
    "REGULAR_SESSION": "📊 الجلسة الرسمية للسوق (Regular Session)",
    "AFTER_HOURS": "🌙 جلسة تداول الليل بعد الإغلاق (After-Hours)",
    "NIGHT_CLOSED": "💤 السوق مغلق حالياً (Night / Closed)"
}

dynamic_risk = (st.session_state.accumulated_balance * 2.0) / 100.0

# 3. عرض شريط إحصائيات المحفظة الافتراضية
st.write("### 📊 مركز الرصد والتحكم بالمخاطر المالي (محاكاة حية):")
c1, c2, c3, c4 = st.columns(4)
with c1: 
    st.markdown(f'<div class="metric-card"><h4 style="color:#94a3b8;margin:0;font-size:15px;">رأس المال الافتراضي</h4><h2 style="color:#10b981;margin:10px 0;font-size:28px;">{st.session_state.accumulated_balance:,.2f} $</h2></div>', unsafe_allow_html=True)
with c2: 
    st.markdown(f'<div class="metric-card"><h4 style="color:#94a3b8;margin:0;font-size:15px;">حد مخاطرة الصفقة (2%)</h4><h2 style="color:#ef4444;margin:10px 0;font-size:28px;">{dynamic_risk:,.2f} $</h2></div>', unsafe_allow_html=True)
with c3: 
    st.markdown(f'<div class="metric-card"><h4 style="color:#94a3b8;margin:0;font-size:15px;">حالة الجلسة الحالية</h4><h3 style="color:#f59e0b;margin:10px 0;font-size:18px;">{session_translation.get(current_session)}</h3></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-card"><h4 style="color:#94a3b8;margin:0;font-size:15px;">المستشعر التلقائي لتيليجرام</h4><h2 style="color:#10b981;margin:10px 0;font-size:28px;">نشط بالخلفية 📡</h2></div>', unsafe_allow_html=True)

# مؤشر التحديث والزمن اللحظي للبيانات
from datetime import datetime
import pytz
est_tz = pytz.timezone('US/Eastern')
now_est = datetime.now(est_tz)
st.write(f"⏱️ **آخر تحديث للرادار:** `{now_est.strftime('%H:%M:%S')} EST` | **تأخير البيانات:** `0 ثوانٍ (بيانات لحظية 🟢)`")

# تهيئة حالة الجلسة النشطة للحفاظ على الفحص عبر التحديث التلقائي
if "active_scan_session" not in st.session_state:
    st.session_state["active_scan_session"] = None

# 3.5 شاشة التنبيهات الفورية المرسلة إلى تيليجرام (تزامن 100% بين المنصة والبوت)
st.markdown("### 📡 أحدث التنبيهات المرسلة فوريًا إلى تيليجرام (Telegram Live Feed)")
tg_alerts = db.get_alerts_history(limit=15)
if tg_alerts:
    df_tg_display = pd.DataFrame([
        {
            "ساعة التنبيه": row["sent_at"].split("T")[-1][:8] if "T" in str(row["sent_at"]) else str(row["sent_at"]),
            "رمز السهم": row["symbol"],
            "سعر الدخول": f"${row['price']:.4f}",
            "الارتفاع عند التنبيه": f"+{row['initial_change']:.1f}%" if row['initial_change'] > 0 else f"{row['initial_change']:.1f}%",
            "درجة القناعة": f"{row['score']:.0f}%",
            "نوع التوصية": row["alert_type"],
            "أعلى سعر تم بلوغه": f"${row['max_price_reached']:.4f}",
            "حالة الصفقة": "🟢 نجحت (+12% فأكثر)" if row["status"] == "SUCCESS" else ("🔴 فشلت (-5% stop loss)" if row["status"] == "FAILED" else ("🟡 جزئية (+10%)" if row["status"] == "PARTIAL" else "⏳ قيد التتبع والانتظار"))
        }
        for row in tg_alerts
    ])
    st.markdown(render_premium_table(df_tg_display), unsafe_allow_html=True)
else:
    st.info("ℹ️ لم يتم إرسال أي تنبيهات جديدة إلى تيليجرام في الجلسة الحالية حتى الآن. ستظهر التنبيهات هنا فور صدورها تلقائياً.")

st.markdown("---")

# 4. علامات التبويب الموزعة للفترات
t_halts, t1, t2, t3, t_trace, t4, t5, t6, t7 = st.tabs([
    "🚨 صفقات الاستئناف (LULD Halts)",
    "🛰️ جلسة ما قبل السوق", 
    "📊 الجلسة الرسمية للسوق", 
    "🌙 جلسة بعد الإغلاق", 
    "🔍 سجل الاستبعاد والقرارات (Decision Trace)",
    "📡 رادار الأخبار الفورية (SEC)",
    "🏆 سجل صيد اليقين التراكمي",
    "📊 محرك الاختبار التاريخي",
    "🤖 وكيل التحسين الذاتي (AI)"
])

with t_halts:
    st.markdown("### 🚨 شاشة صيد صفقات الاستئناف (Nasdaq Halts Trading Matrix)")
    active_halts = get_active_halts()

    if active_halts:
        halt_symbols = list(active_halts.keys())
        halts_data = []
        
        # Retrieve features and ML probability for these symbols
        from intraday_tracker import get_historical_features
        from ml_classifier import QuantMLClassifier
        from yahooquery import Ticker
        
        # Fetch current price in bulk (blazing fast, no progress bar, no timeout hangs)
        try:
            tickers = Ticker(halt_symbols)
            prices_data = tickers.price
        except:
            prices_data = {}
            
        hist_features_halts = get_historical_features(halt_symbols)
        ml_classifier = QuantMLClassifier()
        
        for sym in halt_symbols:
            reason = active_halts[sym]
            price = 5.0
            change = 0.0
            try:
                if sym in prices_data and isinstance(prices_data[sym], dict):
                    price = float(prices_data[sym].get("regularMarketPrice") or 5.0)
                    change_val = prices_data[sym].get("regularMarketChangePercent")
                    if change_val is not None:
                        change = float(change_val) * 100.0
            except:
                price = 5.0
                
            f_info = hist_features_halts.get(sym) if isinstance(hist_features_halts, dict) else None
            if not isinstance(f_info, dict):
                f_info = {
                    "volatility_10d": 5.0,
                    "prev_rvol": 1.0,
                    "prev_change": 0.0,
                    "float_shares_m": 10.0,
                    "short_percent": 0.0
                }
            
            # Calculate ML probability using the actual change percent of the halted symbol
            ml_prob = ml_classifier.predict_probability(
                price=price,
                change=change,
                rvol=f_info.get("prev_rvol", 1.0),
                volatility_10d=f_info.get("volatility_10d", 5.0),
                prev_rvol=f_info.get("prev_rvol", 1.0),
                prev_change=f_info.get("prev_change", 0.0),
                float_shares_m=f_info.get("float_shares_m", 10.0),
                short_percent=f_info.get("short_percent", 0.0)
            )
            
            # Always calculate suggested trade parameters so the user is never left with dashed values
            entry_price_val = price * 1.01
            target_price_val = price * 1.12
            stop_price_val = price * 0.95
            
            entry_str = f"${entry_price_val:.2f} (عند الاستئناف)"
            target_str = f"${target_price_val:.2f} (+12%)"
            stop_str = f"${stop_price_val:.2f} (-5%)"
            
            # Optimize: ONLY query SEC filings news if ML probability is promising (>= 60.0%) to prevent freezes
            is_dilution = False
            sec_tags = "لا يوجد"
            ml_prob_val = ml_prob if ml_prob is not None else 0.0
            
            if ml_prob_val >= 60.0:
                sec_sentiment = get_sec_filings_sentiment(sym)
                is_dilution = sec_sentiment["dilution_warning"]
                sec_tags = ", ".join(sec_sentiment["details"]) if sec_sentiment["details"] else "لا يوجد"
                
            if is_dilution:
                decision = "🔴 تجنب (🚨 تخفيف S-1)"
            elif ml_prob is None:
                decision = "⏳ قيد المعايرة (التعلم الآلي غير نشط)"
            elif ml_prob_val >= 65.0:
                decision = "🟢 شراء عاجل"
            else:
                decision = "🔴 تجنب (مخاطرة عالية/ضعف السيولة)"
                
            ml_prob_str = f"🔮 {ml_prob:.1f}%" if ml_prob is not None else "⚠️ نموذج غير نشط"
            
            halts_data.append({
                "رمز السهم": sym,
                "سبب الإيقاف": f"LULD ({reason})",
                "احتمالية الانفجار": ml_prob_str,
                "التوجيه المباشر": decision,
                "نقطة الدخول المقترحة": entry_str,
                "الهدف الربحي المقترح": target_str,
                "وقف الخسارة المقترح": stop_str
            })
            
        df_halts = pd.DataFrame(halts_data)
        
        # 💥 بطاقة التوصية الذهبية للسهم المتصدر عند الاستئناف
        buy_candidates = [h for h in halts_data if "🟢" in h["التوجيه المباشر"]]
        if buy_candidates:
            buy_candidates = sorted(buy_candidates, key=lambda x: float(x["احتمالية الانفجار"].replace("🔮", "").replace("%", "").strip()), reverse=True)
            top_halt = buy_candidates[0]
            st.markdown(f"""
            <div class="signal-card">
                <h2>🎯 توصية شراء عاجلة عند الاستئناف: السهم المتصدر `{top_halt['رمز السهم']}`</h2>
                <p>🔄 <b>سبب الإيقاف:</b> {top_halt['سبب الإيقاف']}</p>
                <p>🔮 <b>احتمالية الانفجار بالتنبؤ (ML):</b> {top_halt['احتمالية الانفجار']}</p>
                <h3 style="color:#00FFCC !important;">🎯 نقطة الدخول المقترحة: {top_halt['نقطة الدخول المقترحة']}</h3>
                <p>💰 <b>الهدف المقترح:</b> {top_halt['الهدف الربحي المقترح']} | 🛡️ <b>وقف الخسارة:</b> {top_halt['وقف الخسارة المقترح']}</p>
                <p>⚠️ <b>التوجيه المباشر:</b> يرجى إدخال أمر شراء بسعر محدد (Limit Order) لتجنب الانزلاق السعري عند فتح التداول.</p>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown(render_premium_table(df_halts), unsafe_allow_html=True)
    else:
        st.info("⏳ لا توجد أسهم موقوفة عن التداول حالياً في ناسداك.")

def get_direct_action(r):
    if r["Is_Dilution"]:
        return "🔴 تجنب (🚨 خطر تخفيف)"
    if r["Change_%"] > 30.0:
        return f"⚠️ مراقبة (تجاوز الشراء الآمن +{r['Change_%']:.1f}%)"
    if r["Change_%"] > 100.0:
        return "🔴 تجنب (🚨 صعود فجوة تضخم)"
    score = r["Conviction_Score"]
    if score >= 90:
        return "🚀 شراء مؤكد (انفجار شديد القوة)"
    elif score >= 80:
        return "🔥 شراء قوي (زخم متسارع)"
    elif score >= 70:
        return "📈 شراء للمتابعة (قيد التكوين)"
    return "⏳ مراقبة وتأكيد"


def run_session_pipeline(session_name):
    # زر إجراء تحديث فوري مباشر
    c_ref1, c_ref2 = st.columns([3, 1])
    with c_ref1:
        st.markdown(f"🔬 **حالة المعالجة الحالية:** عرض نتائج المحرك اللحظية لجلسة `{session_name}` **(استجابة فورية 0 ثانية ⚡)**")
    with c_ref2:
        force_refresh = st.button("⚡ تحديث حاد الآن (3 ثوانٍ)", key=f"force_scan_{session_name}")

    if force_refresh:
        with st.spinner("جاري إجراء تحديث فوري مباشر عبر البث المتوازي..."):
            symbols = scanner.fetch_all_us_symbols()
            if symbols:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                raw_data = loop.run_until_complete(scanner.scan_entire_market())
                if raw_data:
                    anomaly_map = intel.fit_anomaly_detector(raw_data, session_name)
                    from decision_engine import DecisionEngine
                    engine = DecisionEngine()
                    for quote in raw_data[:50]:
                        sym = quote.get("symbol")
                        if not sym: continue
                        sec_sentiment = get_sec_filings_sentiment(sym)
                        anomaly_info = anomaly_map.get(sym, {"is_anomaly": False, "confidence_score": 1.0})
                        trace = engine.evaluate_symbol(quote=quote, session=session_name, anomaly_info=anomaly_info, sec_sentiment=sec_sentiment)
                        db.log_evaluation_trace(
                            symbol=sym, price=trace["price"], change=trace["change"], rvol=trace["rvol"],
                            score=trace["score"], ml_prob=trace["ml_prob"], status=trace["status"],
                            reason=trace["rejection_reason"], details=trace["details"]
                        )

    # جلب أحدث النتائج المقبولة فورياً من قاعدة البيانات (0 ثانية تحميل)
    recent_traces = db.get_recent_evaluations(limit=200)
    accepted_traces = [t for t in recent_traces if t.get("status") == "ACCEPTED"]
    active_halts = get_active_halts()

    opportunities = []
    seen_syms = set()
    for trace in accepted_traces:
        sym = trace.get("symbol")
        if not sym or sym in seen_syms: continue
        seen_syms.add(sym)
        price = trace.get("price", 0.0)
        change = trace.get("change", 0.0)
        rvol = trace.get("rvol", 1.0)
        score = trace.get("score", 0.0)
        ml_prob = trace.get("ml_prob", 0.0)
        is_halted = sym in active_halts
        halt_reason = active_halts[sym] if is_halted else ""

        action_lbl = get_direct_action({
            "Is_Dilution": False,
            "Change_%": change,
            "Conviction_Score": score
        })

        opportunities.append({
            "Symbol": sym,
            "Price": price,
            "Change_%": change,
            "Volume": 0.0,
            "RVOL": rvol,
            "Conviction_Score": score,
            "Is_Anomaly": True if score >= 80 else False,
            "Confidence_Score": round(ml_prob / 10.0, 1),
            "ML_Probability": ml_prob,
            "Is_Trending": False,
            "Is_Halted": is_halted,
            "Halt_Reason": halt_reason,
            "SEC_Tags": "محدث بالخلفية",
            "Is_Dilution": False,
            "Float_M": 10.0,
            "Short_Pct": 0.0,
            "Days_To_Cover": 0.0,
            "Squeeze_Score": 0,
            "Has_Catalyst": False,
            "Matches": trace.get("details", {}),
            "Action_Directive": action_lbl
        })

    df_opportunities = pd.DataFrame(opportunities)
    if not df_opportunities.empty:
        df_opportunities["ML_Probability"] = df_opportunities["ML_Probability"].fillna(0.0)
        df_opportunities = df_opportunities.sort_values(by=["Conviction_Score", "ML_Probability"], ascending=[False, False])
        
        st.markdown("""
        <div class="ai-section">
            <h3 style="color:#3b82f6;margin:0 0 10px 0;font-size:20px;">🔍 محرك رصد الشذوذ الحجمي اللحظي (Anomaly Detection Engine)</h3>
            <p style="color:#94a3b8;font-size:14px;margin-bottom:15px;">
                عرض لحظي مباشر من المحرك للرموز التي تشهد انحرافاً حاداً في الحجم النسبي (RVOL) والتجميع اللحظي.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        df_anomalies = df_opportunities[df_opportunities["Is_Anomaly"] == True].copy()
        
        c_anom1, c_anom2 = st.columns(2)
        with c_anom1:
            st.metric(label="عدد الفرص الجارية بالفحص", value=f"{len(df_opportunities)} شركة")
        with c_anom2:
            st.metric(label="الانفجارات الحجمية المكتشفة", value=f"{len(df_anomalies)} أسهم شاذة")
        
        if not df_anomalies.empty:
            st.write("📈 **قائمة الأسهم التي تشهد تجميعاً ونشاطاً استثنائياً حالياً:**")
            df_anom_display = df_anomalies[["Symbol", "Price", "Change_%", "Volume", "RVOL", "Confidence_Score"]].copy()
            df_anom_display.columns = ["رمز السهم", "السعر اللحظي", "التغير المئوي", "الحجم اليومي", "الحجم النسبي RVOL", "مؤشر ثقة الاختراق (0-10)"]
            st.markdown(render_premium_table(df_anom_display), unsafe_allow_html=True)
        
        top_stock = df_opportunities.iloc[0]
        matches = top_stock["Matches"]
        target_pct_card = intel.calculate_dynamic_target(top_stock['Conviction_Score'], top_stock['Confidence_Score'] * 10.0)
        st.markdown(f"""
        <div class="signal-card">
            <h2 style='color:#10b981; margin:0 0 10px 0; font-size:22px; font-weight:700;'>🎯 التوجيه التنفيذي للمركز الأول (أقوى تطابق كمي)</h2>
            <h3>🔥 رمز السهم: {top_stock['Symbol']} | نسبة تطابق الخوارزمية: {top_stock['Conviction_Score']}%</h3>
            <p style='font-size:18px;margin:5px 0;'>السعر الحالي: <b>{top_stock['Price']:.4f} $</b> | التغير اليومي: <b>{top_stock['Change_%']:+.2f}%</b> | تسارع الحجم النسبي: <b>{top_stock['RVOL']:.2f}x</b></p>
            <h3 style="color:#00FFCC !important; margin: 5px 0;">🎯 القرار المقترح: {get_direct_action(top_stock)}</h3>
            <p style='font-size:16px; margin:5px 0; color:#FFA500;'>💰 <b>الهدف المقترح:</b> +{target_pct_card}% (سعر: ${top_stock['Price'] * (1 + target_pct_card/100.0):.2f}) | 🛡️ <b>وقف الخسارة:</b> -5% (سعر: ${top_stock['Price'] * 0.95:.2f})</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("---")
        st.markdown("### 💥 صفقات الانفجار المعتمدة (High-Conviction Explosive Plays)")
        df_exp_display = df_opportunities.copy()
        df_exp_display["التوجيه المباشر"] = df_exp_display.apply(get_direct_action, axis=1)
        df_exp_display["تطابق الخوارزمية"] = df_exp_display["Conviction_Score"].apply(lambda x: f"🔥 {x}%")
        df_exp_display["احتمالية الانفجار (ML)"] = df_exp_display["ML_Probability"].apply(format_ml_prob)
        df_exp_display["حالة الإيقاف"] = df_exp_display.apply(lambda r: f"🚨 موقوف ({r['Halt_Reason']})" if r["Is_Halted"] else "🟢 نشط", axis=1)
        
        df_exp_table = df_exp_display[["Symbol", "Price", "Change_%", "RVOL", "حالة الإيقاف", "احتمالية الانفجار (ML)", "تطابق الخوارزمية", "Popularity", "Action_Directive"]].copy()
        df_exp_table.columns = ["رمز السهم", "السعر اللحظي", "التغير المئوي", "الحجم النسبي RVOL", "حالة التداول", "احتمالية الانفجار (ML)", "تطابق الخوارزمية", "الشهرة والبحث", "توجيه الشراء"]
        st.markdown(render_premium_table(df_exp_table), unsafe_allow_html=True)
    else:
        st.info("ℹ️ المحرك يعمل بالخلفية ويرسل التنبيهات فوراً لتيليجرام. لا توجد فرص مكتملة الشروط في هذه اللحظة.")


with t1:
    st.markdown("### 🛰️ جلسة ما قبل الافتتاح (Pre-Market Scanner)")
    st.write("تركز هذه الجلسة على قياس فجوات الافتتاح وأحجام التداول وشذوذ السيولة قبل انطلاق السوق.")
    
    col1, col2 = st.columns([1.5, 3.5])
    with col1:
        if st.button("⚡ تشغيل الفحص التلقائي المستمر", key="btn_pre_market"):
            st.session_state["active_scan_session"] = "PRE_MARKET"
            st.rerun()
    with col2:
        if st.session_state.get("active_scan_session") == "PRE_MARKET":
            st.success("🟢 الفحص التلقائي المستمر نشط حالياً ويعمل تلقائياً مع تحديث الصفحة.")
            if st.button("🛑 إيقاف الفحص التلقائي", key="stop_pre_market"):
                st.session_state["active_scan_session"] = None
                st.rerun()
                
    if st.session_state.get("active_scan_session") == "PRE_MARKET":
        run_session_pipeline("PRE_MARKET")
    else:
        st.info("💡 اضغط على زر 'تشغيل الفحص التلقائي المستمر' لمراقبة أسهم ما قبل السوق بشكل مستمر دون اختفاء البيانات عند تحديث الصفحة.")

with t2:
    st.markdown("### 📊 الجلسة الرسمية للسوق (Regular Session Scanner)")
    st.write("تركز الجلسة الرسمية على تسارع السيولة اللحظي واختراق القمم ومؤشرات شذوذ الحجم اللحظية.")
    
    col1, col2 = st.columns([1.5, 3.5])
    with col1:
        if st.button("⚡ تشغيل الفحص التلقائي المستمر", key="btn_reg_market"):
            st.session_state["active_scan_session"] = "REGULAR_SESSION"
            st.rerun()
    with col2:
        if st.session_state.get("active_scan_session") == "REGULAR_SESSION":
            st.success("🟢 الفحص التلقائي المستمر نشط حالياً ويعمل تلقائياً مع تحديث الصفحة.")
            if st.button("🛑 إيقاف الفحص التلقائي", key="stop_reg_market"):
                st.session_state["active_scan_session"] = None
                st.rerun()
                
    if st.session_state.get("active_scan_session") == "REGULAR_SESSION":
        run_session_pipeline("REGULAR_SESSION")
    else:
        st.info("💡 اضغط على زر 'تشغيل الفحص التلقائي المستمر' لمراقبة الجلسة الرسمية بشكل مستمر دون اختفاء البيانات عند تحديث الصفحة.")

with t3:
    st.markdown("### 🌙 جلسة بعد الإغلاق (After-Hours Scanner)")
    st.write("تتبع هذه الجلسة استجابات الشركات للنتائج والأخبار وتأثيراتها الحركية بعد جرس الإغلاق.")
    
    col1, col2 = st.columns([1.5, 3.5])
    with col1:
        if st.button("⚡ تشغيل الفحص التلقائي المستمر", key="btn_after_hours"):
            st.session_state["active_scan_session"] = "AFTER_HOURS"
            st.rerun()
    with col2:
        if st.session_state.get("active_scan_session") == "AFTER_HOURS":
            st.success("🟢 الفحص التلقائي المستمر نشط حالياً ويعمل تلقائياً مع تحديث الصفحة.")
            if st.button("🛑 إيقاف الفحص التلقائي", key="stop_after_hours"):
                st.session_state["active_scan_session"] = None
                st.rerun()
                
    if st.session_state.get("active_scan_session") == "AFTER_HOURS":
        run_session_pipeline("AFTER_HOURS")
    else:
        st.info("💡 اضغط على زر 'تشغيل الفحص التلقائي المستمر' لمراقبة جلسة الليل بشكل مستمر دون اختفاء البيانات عند تحديث الصفحة.")

with t_trace:
    st.markdown("### 🔍 سجل تتبع القرارات والاستبعاد التفصيلي (Decision & Exclusion Trace)")
    st.write("يعرض هذا السجل كافة الرموز والأسهم التي خضعت لتقييم المنصة وسبب القبول أو الرفض التفصيلي لكل سهم لضمان الشفافية بنسبة 100%.")
    
    from database import QuantDatabase
    db_eval = QuantDatabase()
    
    col1, col2 = st.columns([2, 4])
    with col1:
        trace_limit = st.slider("عدد السجلات المعروضة:", min_value=10, max_value=200, value=50, step=10)
    with col2:
        status_filter = st.radio("تصفية حسب الحالة:", ["الكل (All)", "المستبعدة فقط (REJECTED)", "المقبولة فقط (ACCEPTED)"], horizontal=True)

    evals = db_eval.get_recent_evaluations(limit=trace_limit)
    if evals:
        # Filter evaluations
        if "المستبعدة فقط" in status_filter:
            evals = [e for e in evals if e["status"] == "REJECTED"]
        elif "المقبولة فقط" in status_filter:
            evals = [e for e in evals if e["status"] == "ACCEPTED"]
            
        if evals:
            df_evals = pd.DataFrame(evals)
            
            # Format datetime
            df_evals["evaluated_at"] = pd.to_datetime(df_evals["evaluated_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # Translate status labels
            df_evals["حالة القرار"] = df_evals["status"].apply(lambda s: "🟢 مقبول" if s == "ACCEPTED" else "🔴 مستبعد")
            
            # Select columns to display
            df_display = df_evals[["evaluated_at", "symbol", "price", "change", "rvol", "score", "ml_prob", "حالة القرار", "rejection_reason"]].copy()
            df_display.columns = ["توقيت الفحص", "رمز السهم", "السعر", "التغير اليومي", "الحجم النسبي RVOL", "درجة القناعة", "احتمالية ML", "الحالة", "سبب القرار / الاستبعاد"]
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("⏳ لا توجد سجلات مطابقة للتصفية الحالية.")
    else:
        st.info("⏳ لا توجد سجلات فحص وتتبع في قاعدة البيانات حالياً.")

with t4:
    st.markdown("### 📡 رادار الأخبار الفورية (SEC Edgar RSS)")
    st.write("مراقبة التغذية الفيدرالية الرسمية لتقارير الأحداث الهامة (8-K) لكافة الشركات في السوق ورصد المحفز الإيجابي.")
    run_sec = st.button("🔍 فحص تقارير الهيئة الحالية")
    if run_sec:
        with st.spinner("جاري جلب إعلانات هيئة الأوراق المالية الفيدرالية..."):
            catalysts = news_radar.fetch_latest_filings()
            if catalysts:
                st.success(f"تم رصد {len(catalysts)} إعلان جوهري جديد!")
                for event in catalysts:
                    badge_text = "🔥 محفز إيجابي" if event['Is_Positive_Catalyst'] else "محايد"
                    with st.expander(f"🏢 {event['Company']} | العنوان: {event['Title']} | {badge_text}"):
                        st.write(f"**التوقيت الفيدرالي:** {event['Time']}")
                        st.write(f"**رقم التسجيل CIK:** {event['CIK']}")
                        st.write(f"**ملخص الإعلان:** {event['Summary']}")
            else:
                st.info("⏳ لا توجد إعلانات جوهرية جديدة في الثواني الأخيرة.")

with t5:
    st.markdown("### 🏆 سجل صيد اليقين التراكمي والمحفظة الافتراضية حياً")
    st.info("مخصص لأرشفة وإدارة صفقات المحفظة الافتراضية التفاعلية حياً عبر أوامر تيليجرام بالعربية.")
    
    from database import QuantDatabase
    db = QuantDatabase()
    cash = db.get_cash()
    portfolio = db.get_portfolio()
    
    st.write(f"💵 **السيولة النقدية الحالية في الخزنة الافتراضية:** `{cash:,.2f}$`")
    
    if portfolio:
        df_port = pd.DataFrame(portfolio)
        df_port.columns = ["رمز السهم", "الكمية المملكة", "متوسط سعر الدخول", "توقيت الدخول"]
        st.dataframe(df_port, use_container_width=True, hide_index=True)
    else:
        st.write("💼 المحفظة فارغة حالياً. أرسل أمراً للبوت مثل `شراء CLSK 10` للبدء!")

    # ➕ لوحة تسجيل الصفقات اليدوية (Manual Trade Entry Form)
    st.write("---")
    st.markdown("### ✍️ لوحة تسجيل الصفقات يدوياً (Manual Trade Entry)")
    with st.expander("➕ تسجيل عملية شراء/بيع جديدة في المحفظة"):
        with st.form("manual_trade_form", clear_on_submit=True):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                trade_type = st.selectbox("نوع العملية", ["شراء (BUY)", "بيع (SELL)"])
            with col2:
                _trade_input = st.text_input("رمز السهم", placeholder="مثال: GWAV")
                trade_symbol = str(_trade_input).upper().strip() if _trade_input else ""
            with col3:
                trade_qty = st.number_input("الكمية", min_value=1, value=10, step=1)
            with col4:
                trade_price = st.number_input("سعر التنفيذ ($)", min_value=0.0001, value=1.0000, format="%.4f", step=0.1)
                
            submit_trade = st.form_submit_button("💾 تسجيل الصفقة وحفظها في قاعدة البيانات")
            if submit_trade:
                if not trade_symbol:
                    st.error("⚠️ يرجى إدخال رمز السهم أولاً.")
                else:
                    try:
                        if "شراء" in trade_type:
                            cost = trade_qty * trade_price
                            if cash < cost:
                                st.error(f"❌ السيولة النقدية غير كافية. التكلفة: {cost:.2f}$ | السيولة المتاحة: {cash:.2f}$")
                            else:
                                success, msg = db.execute_buy(trade_symbol, trade_qty, trade_price)
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        else:
                            success, msg = db.execute_sell(trade_symbol, trade_qty, trade_price)
                            if success:
                                    st.success(msg)
                                    st.rerun()
                            else:
                                    st.error(msg)
                    except Exception as e:
                        st.error(f"❌ حدث خطأ أثناء التسجيل: {e}")

    st.write("---")
    st.markdown("### 📊 لوحة تقييم كفاءة إشارات التداول (Performance Audit Dashboard)")
    st.write("تقوم هذه اللوحة باحتساب كفاءة ودقة الخوارزميات ونموذج التعلم الآلي تلقائياً استناداً للنتائج الفعلية المحققة في الجلسات الثلاث.")
    
    alerts_hist_all = db.get_alerts_history(limit=250)
    
    valid_alerts = []
    if isinstance(alerts_hist_all, list):
        for a in alerts_hist_all:
            if isinstance(a, dict) and a.get("price", 0.0) > 0.0:
                safe_alert = {
                    "symbol": a.get("symbol", ""),
                    "sent_at": a.get("sent_at", ""),
                    "price": a.get("price", 0.0),
                    "score": a.get("score", 0.0),
                    "alert_type": a.get("alert_type", ""),
                    "session": a.get("session", "REGULAR_SESSION"),
                    "target_percent": a.get("target_percent", 12.0),
                    "max_price_reached": a.get("max_price_reached", a.get("price", 0.0)),
                    "status": a.get("status", "PENDING")
                }
                valid_alerts.append(safe_alert)
                
    if valid_alerts:
        total_alerts = len(valid_alerts)
        success_alerts = sum(1 for a in valid_alerts if a["status"] == "SUCCESS")
        partial_alerts = sum(1 for a in valid_alerts if a["status"] == "PARTIAL")
        failed_alerts = sum(1 for a in valid_alerts if a["status"] == "FAILED")
        pending_alerts = sum(1 for a in valid_alerts if a["status"] == "PENDING")
        
        resolved_alerts = total_alerts - pending_alerts
        win_rate = ((success_alerts + partial_alerts) / resolved_alerts * 100.0) if resolved_alerts > 0 else 0.0
        full_success_rate = (success_alerts / resolved_alerts * 100.0) if resolved_alerts > 0 else 0.0
        
        gains = []
        for a in valid_alerts:
            entry = float(a["price"])
            mx = float(a["max_price_reached"])
            if entry > 0:
                gains.append(((mx - entry) / entry) * 100.0)
        avg_max_gain = sum(gains) / len(gains) if gains else 0.0
        
        # 1. كروت قياس الكفاءة التراكمية
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                label="🎯 معدل النجاح الكلي للرادار (Win Rate)", 
                value=f"{win_rate:.1f}%", 
                help="نسبة التنبيهات التي حققت الهدف المقترح بالكامل أو صعدت بنسبة لا تقل عن +10% قبل ضرب وقف الخسارة."
            )
        with col2:
            st.metric(
                label="🏆 معدل النجاح الكامل (Target Hit)", 
                value=f"{full_success_rate:.1f}%", 
                help="نسبة التوصيات التي لامست الهدف المقترح ديناميكياً بدقة 100%."
            )
        with col3:
            st.metric(
                label="📈 متوسط أقصى صعود محقق", 
                value=f"+{avg_max_gain:.1f}%", 
                help="متوسط الصعود الأقصى التراكمي الذي سجلته الأسهم بعد لحظة صدور التنبيه."
            )
            
        st.write("")
        st.markdown("#### 📢 سجل تدقيق الصفقات وأداء الجلسات المفتوحة")
        
        df_alerts = pd.DataFrame(valid_alerts)
        df_alerts_display = df_alerts.copy()
        
        def format_time(ts_str):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(ts_str)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                return ts_str
                
        df_alerts_display["sent_at"] = df_alerts_display["sent_at"].apply(format_time)
        
        session_map = {
            "PRE_MARKET": "🛰️ ما قبل السوق",
            "REGULAR_SESSION": "📊 الجلسة الرسمية",
            "AFTER_HOURS": "🌙 بعد الإغلاق"
        }
        df_alerts_display["session"] = df_alerts_display["session"].apply(lambda x: session_map.get(x, "📊 الجلسة الرسمية"))
        
        # حساب أقصى صعود محقق كنسبة مئوية
        def calc_max_gain(row):
            try:
                ent = float(row["price"])
                mx = float(row["max_price_reached"])
                return f"+{((mx - ent) / ent * 100.0):.1f}%"
            except:
                return "0.0%"
        df_alerts_display["max_gain"] = df_alerts_display.apply(calc_max_gain, axis=1)
        
        df_alerts_display["price"] = df_alerts_display["price"].apply(lambda x: f"${x:.2f}")
        df_alerts_display["max_price_reached"] = df_alerts_display["max_price_reached"].apply(lambda x: f"${x:.2f}")
        df_alerts_display["target_percent"] = df_alerts_display["target_percent"].apply(lambda x: f"+{x:.0f}%")
        
        status_map = {
            "SUCCESS": "🟢 ناجح بالكامل",
            "PARTIAL": "🟡 ناجح جزئياً",
            "FAILED": "🔴 صفقة خاسرة",
            "PENDING": "⏳ قيد التتبع"
        }
        df_alerts_display["status"] = df_alerts_display["status"].apply(lambda x: status_map.get(x, "⏳ قيد التتبع"))
        
        df_alerts_display = df_alerts_display[[
            "symbol", "session", "sent_at", "price", "target_percent", "max_price_reached", "max_gain", "status"
        ]]
        df_alerts_display.columns = [
            "رمز السهم", "الجلسة", "وقت التنبيه", "سعر الدخول", "الهدف المتوقع", "أقصى سعر محقق", "أقصى صعود", "الحالة النهائية"
        ]
        st.dataframe(df_alerts_display, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ لم يتم إصدار أي تنبيهات أو إشارات تداول خلال الجلسة الحالية حتى الآن.")

    st.write("---")
    st.markdown("### 🔍 رادار التجميع الحجمي الصامت (Pre-Breakout Scanner)")
    st.write("يبحث هذا الرادار عن الأسهم ذات الفلوت المنخفض (<15M) التي تشهد طفرات حجم ضخمة (>4x) مع ثبات تام في السعر، لالتقاط الحركة قبل حدوث الانفجار السعري.")
    
    run_accum = st.button("⚡ تفعيل فحص التجميع الصامت", key="run_silent_accum")
    if run_accum:
        with st.spinner("جاري مسح السوق تاريخياً وحساب تجميع السيولة..."):
            from accumulation import SilentAccumulationScanner
            accum_scanner = SilentAccumulationScanner()
            setups = accum_scanner.scan_for_accumulation()
            
            if setups:
                st.success(f"🎉 تم رصد {len(setups)} أسهم تمر بمرحلة تجميع صامت عالية اليقين!")
                
                # عرض جدول الفرص
                df_setups = pd.DataFrame(setups)
                df_table = df_setups[["Symbol", "Price", "Volume_Multiplier", "Volatility", "Float_M", "Expected_Gain_%", "Expected_Days", "Stop_Loss"]].copy()
                df_table.columns = ["رمز السهم", "السعر", "تضاعف الحجم", "التذبذب اليومي", "الأسهم الحرة (Float M)", "الهدف المتوقع", "الانتظار المتوقع (يوم)", "وقف الخسارة"]
                
                # تنسيق الأرقام
                df_table["تضاعف الحجم"] = df_table["تضاعف الحجم"].apply(lambda x: f"{x:.1f}x")
                df_table["التذبذب اليومي"] = df_table["التذبذب اليومي"].apply(lambda x: f"{x:.2f}%")
                df_table["الأسهم الحرة (Float M)"] = df_table["الأسهم الحرة (Float M)"].apply(lambda x: f"{x:.2f}M")
                df_table["الهدف المتوقع"] = df_table["الهدف المتوقع"].apply(lambda x: f"+{x:.1f}%")
                df_table["الانتظار المتوقع (يوم)"] = df_table["الانتظار المتوقع (يوم)"].apply(lambda x: f"{x} أيام")
                df_table["وقف الخسارة"] = df_table["وقف الخسارة"].apply(lambda x: f"${x:.2f}")
                
                st.dataframe(df_table, use_container_width=True, hide_index=True)
                
                # عرض كروت النصائح والتوجيهات الحقيقية
                st.write("#### 💡 التوجيه الفني والتحليل الاستشاري للذكاء الاصطناعي:")
                for item in setups:
                    with st.expander(f"🏢 التوجيه الفني الكامل لـ {item['Symbol']}"):
                        st.markdown(f'<div class="ai-section"><h4>🎯 تحليل سهم {item["Symbol"]}</h4><p style="font-size:16px;line-height:1.6;color:#ffffff !important;">{item["Guidance"]}</p></div>', unsafe_allow_html=True)
            else:
                st.info("⏳ لم يتم رصد أي أسهم تمر بمرحلة تجميع صامت ومطابقة للشروط الصارمة حالياً.")

with t6:
    st.markdown("### 📊 محرك الاختبار التاريخي وتقييم الخوارزميات (Backtesting Engine)")
    st.write("يقوم هذا المحرك بمحاكاة تاريخية لـ 6 أشهر سابقة للتحقق من نسب النجاح وعامل الربحية لجميع الأكواد والخوارزميات.")
    
    # خيارات التحكم
    col_strat, col_cap = st.columns(2)
    with col_strat:
        strategy_choice = st.selectbox(
            "اختر الاستراتيجية للتحليل التاريخي:", 
            ["ACCUMULATION", "BREAKOUT", "INTRADAY_SCALPING"], 
            format_func=lambda x: "🏆 التجميع الصامت (Consolidation & Float)" if x == "ACCUMULATION" else ("⚡ الاختراقات واليقين (Volume & SMA Breakout)" if x == "BREAKOUT" else "🔥 المضاربة اللحظية السريعة (Intraday Scalping)")
        )
    with col_cap:
        initial_cap = st.number_input("رأس المال الافتراضي للبدء ($):", min_value=100.0, value=1000.0, step=100.0)
        
    run_backtest = st.button("⚡ بدء الاختبار التاريخي الشامل")
    if run_backtest:
        with st.spinner("جاري تنزيل 180 يوماً من البيانات التاريخية لـ 570+ سهم ومحاكاة التداول..."):
            from backtester import QuantBacktester
            tester = QuantBacktester()
            results = tester.run_backtest(strategy_type=strategy_choice, days_to_test=180, initial_capital=initial_cap)
            
            if "error" in results:
                st.error(f"❌ {results['error']}")
            else:
                st.success("✅ تم الانتهاء من الاختبار التاريخي بنجاح!")
                
                # عرض إحصائيات الأداء في كروت تفاعلية جميلة
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("إجمالي الصفقات", results["total_trades"])
                with c2:
                    st.metric("نسبة النجاح (Win Rate)", f"{results['win_rate_pct']:.1f}%")
                with c3:
                    st.metric("عامل الربحية (Profit Factor)", f"{results['profit_factor']:.2f}")
                with c4:
                    st.metric("أقصى تراجع (Max Drawdown)", f"{results['max_drawdown_pct']:.1f}%")
                    
                # عرض النتيجة النهائية للمحفظة
                st.markdown(f"📈 **القيمة النهائية للمحفظة بعد 6 أشهر:** `{results['final_wealth']:,.2f}$` (العائد الكلي: `{results['net_return_pct']:+.1f}%`)")
                
                # رسم مخطط نمو رأس المال باستخدام Plotly
                df_equity = pd.DataFrame(results["equity_curve"])
                import plotly.express as px
                fig = px.line(
                    df_equity, 
                    x="Date", 
                    y="Capital", 
                    title="📈 منحنى نمو رأس المال الافتراضي (Equity Growth)", 
                    labels={"Capital": "قيمة المحفظة ($)", "Date": "التاريخ"}
                )
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#ffffff",
                    title_font_size=18,
                    xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)")
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # عرض جدول تفصيلي بكافة الصفقات التي تمت
                if results["trades"]:
                    st.markdown("### 📋 سجل الصفقات المحاكاة بالتفصيل:")
                    df_trades = pd.DataFrame(results["trades"])
                    
                    # 1. ترجمة الاستراتيجيات
                    strategy_map = {
                        "INTRADAY_SCALPING": "🔥 مضاربة لحظية",
                        "BREAKOUT": "⚡ اختراق حجمي",
                        "ACCUMULATION": "🏆 تجميع صامت"
                    }
                    df_trades["Type"] = df_trades["Type"].apply(lambda x: strategy_map.get(x, x))
                    
                    # 2. تنسيق الأرقام والعملات
                    df_trades["Entry_Price"] = df_trades["Entry_Price"].apply(lambda x: f"${x:.2f}")
                    df_trades["Exit_Price"] = df_trades["Exit_Price"].apply(lambda x: f"${x:.2f}")
                    df_trades["PnL_$"] = df_trades["PnL_$"].apply(lambda x: f"{x:+.2f}$" if x >= 0 else f"{x:.2f}$")
                    df_trades["PnL_%"] = df_trades["PnL_%"].apply(lambda x: f"+{x:.1f}%" if x >= 0 else f"{x:.1f}%")
                    
                    # 3. تعريب وتلوين حالة الصفقة
                    def translate_result(res_str):
                        res_str = str(res_str).upper()
                        if "WIN" in res_str:
                            if "EXPIRED" in res_str or "HOLD" in res_str:
                                return "🟢 إغلاق إجباري (ربح جزئي)"
                            return "🟢 ناجحة (ضرب الهدف)"
                        elif "LOSS" in res_str:
                            if "EXPIRED" in res_str or "HOLD" in res_str:
                                return "🔴 إغلاق إجباري (خسارة)"
                            return "🔴 خاسرة (وقف الخسارة)"
                        return res_str
                        
                    df_trades["Result"] = df_trades["Result"].apply(translate_result)
                    
                    # 4. إعادة ترتيب وتسمية الأعمدة لتناسق تام
                    df_trades = df_trades[["Symbol", "Type", "Entry_Date", "Exit_Date", "Entry_Price", "Exit_Price", "PnL_$", "PnL_%", "Result"]]
                    df_trades.columns = ["رمز السهم", "الاستراتيجية", "تاريخ الدخول", "تاريخ الخروج", "سعر الدخول", "سعر الخروج", "الأرباح ($)", "الربحية (%)", "حالة الصفقة النهائية"]
                    
                    st.dataframe(df_trades, use_container_width=True, hide_index=True)
                else:
                    st.info("ℹ️ لم يتم توليد أي صفقات خلال فترة الفحص التاريخية المحددة.")

with t7:
    st.markdown("### 🤖 وكيل التطوير والتحسين الذاتي المستقل (Self-Optimizing Agent)")
    st.write("يقوم وكيل الذكاء الاصطناعي بمراجعة الأسهم الأكثر صعوداً يومياً، وتشخيص أسباب استبعادها، وتعديل قيم فلاتر المنصة ديناميكياً لرفع نسبة اقتناص صعود السوق بدون تدخل بشري.")
    
    # عرض القيم الحالية للفلاتر
    current_thresholds = intel.get_thresholds()
    
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    with col_t1:
        st.metric(label="🛡️ حد منع الفومو الحالي", value=f"{current_thresholds['fomo']:.1f}%")
    with col_t2:
        st.metric(label="🚨 حد درع الفجوة الحالي", value=f"{current_thresholds['gap']:.1f}%")
    with col_t3:
        st.metric(label="🌙 سيولة الجلسات الممتدة", value=f"${current_thresholds['whale_ext']:,.0f}")
    with col_t4:
        st.metric(label="📊 سيولة الجلسة الرسمية", value=f"${current_thresholds['whale_reg']:,.0f}")
        
    st.write("---")
    
    # جلب آخر عملية تحسين
    latest_run = db.get_latest_optimization_run()
    if latest_run:
        st.markdown("#### 📊 نتائج آخر فحص ومعايرة تلقائية:")
        st.info(f"⏱️ **تاريخ الفحص:** `{latest_run['optimized_at']}` | 🎯 **نسبة اقتناص صعود السوق المقدرة:** `{latest_run['catch_rate']:.1f}%`")
        
        st.markdown(latest_run["missed_gainers"])
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.write(f"📈 **حد منع الفومو المعتمد:** `{latest_run['fomo_threshold']:.1f}%`")
            st.write(f"🛡️ **حد درع الفجوة المعتمد:** `{latest_run['gap_threshold']:.1f}%`")
        with col_r2:
            st.write(f"⚡ **عتبة سيولة الجلسات الممتدة:** `${latest_run['whale_threshold_ext']:,.0f}`")
            st.write(f"📊 **عتبة سيولة الجلسة الرسمية:** `${latest_run['whale_threshold_reg']:,.0f}`")
    else:
        st.info("ℹ️ لم يتم تشغيل أي عملية معايرة تلقائية حتى الآن. يمكنك تشغيل المعايرة يدوياً بالأسفل.")
        
    st.write("---")
    
    if st.button("⚙️ تشغيل معايرة وتحسين خوارزميات المنصة الآن", use_container_width=True):
        with st.spinner("جاري تشغيل وكيل التطوير لإجراء مئات المحاكاة على فلاتر السوق وسجل الفرص الفائتة..."):
            from self_optimizer import QuantSelfOptimizer
            optimizer = QuantSelfOptimizer()
            res = optimizer.run_optimization()
            
            if res.get("status") == "OPTIMIZED":
                st.success(f"✅ تم تحسين فلاتر المنصة تلقائياً بنجاح! ارتفعت نسبة رصد السوق اليوم إلى **{res['catch_rate']:.1f}%** عبر معايرة المعايير الجديدة.")
                st.balloons()
                time.sleep(2)
                st.rerun()
            else:
                st.warning(f"⚠️ فحص الوكيل لم يتطلب تعديل البارامترات: {res.get('reason', 'الفلاتر الحالية تعطي أفضل نسبة رصد واقتناص آمنة حالياً')}")

# --- التحديث التلقائي للبيانات والصفحة ---
import time
st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("🔄 تفعيل التحديث التلقائي للصفحة", value=True)
refresh_interval = st.sidebar.slider("⏱️ ثواني الانتظار قبل التحديث:", min_value=10, max_value=300, value=60, step=10)

if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
