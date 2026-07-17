# module: app_v10.py
import streamlit as st
import pandas as pd
import asyncio
import logging
import requests
from scanner import FreeMarketScanner
from intelligence import QuantIntelligence
from news_radar import SECNewsRadar
from notifier import TelegramNotifier
from alerts_tracker import get_active_halts, get_sec_filings_sentiment

# إعداد ملف مراقبة الأخطاء المركزي (Centralized Error Logging)
logging.basicConfig(
    filename="radar_errors.log",
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def fetch_stocktwits_trending():
    """
    سحب قائمة الأسهم الأكثر تداولاً وجدلاً حالياً من Stocktwits (Trending Symbols)
    """
    try:
        url = "https://api.stocktwits.com/api/2/trending/symbols.json"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            symbols = [item["symbol"] for item in res.json().get("symbols", [])]
            return set(symbols)
    except Exception as e:
        logging.warning(f"Stocktwits API Error: {e}")
    return set()

# 1. إعداد الصفحة والأنماط البصرية الراقية (Premium Dark Tech Theme)
st.set_page_config(page_title="منظومة رادار السيولة التراكمية v10.0", layout="wide")

# استيراد خطوط Google Fonts وتصميم الواجهة بمؤثرات حديثة
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Cairo:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
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

# تفعيل مشغل الفحص التلقائي الخلفي لإرسال الإشارات لتيليجرام 24 ساعة
@st.cache_resource
def initialize_background_auto_scanner():
    import threading
    from auto_scanner import start_scheduler
    thread = threading.Thread(target=start_scheduler, daemon=True)
    thread.start()
    return "ACTIVE"

auto_status = initialize_background_auto_scanner()

# تفعيل خادم البوت التفاعلي لتلقي أوامر المحفظة والاستشارات بالعربية 24 ساعة
@st.cache_resource
def initialize_interactive_bot():
    import threading
    from bot_listener import start_bot_thread
    thread = threading.Thread(target=start_bot_thread, daemon=True)
    thread.start()
    return "ACTIVE"

bot_status = initialize_interactive_bot()

# 2.1 إعداد شريط جانبي لأدوات التحكم والاختبار
st.sidebar.markdown("### 🛠️ أدوات التحكم والربط")
st.sidebar.write("استخدم هذا الزر لإرسال تنبيه عينة والتأكد من نجاح اتصال بوت تيليجرام بجوالك في أي وقت:")
if st.sidebar.button("📢 إرسال إشارة تجريبية لتيليجرام", key="sidebar_tg_test"):
    notifier = TelegramNotifier()
    success = notifier.send_breakout_alert(
        symbol="TEST",
        price=12.45,
        change=15.8,
        rvol=3.5,
        score=90,
        confidence=8.5
    )
    if success:
        st.sidebar.success("✅ تم إرسال رسالة الاختبار بنجاح!")
    else:
        st.sidebar.error("❌ فشل الإرسال، تحقق من الأسرار.")

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

# عرض بانر إيقاف التداول لحظياً بأعلى الصفحة
active_halts_banner = get_active_halts()
if active_halts_banner:
    halt_symbols_str = ", ".join([f"{sym} ({reason})" for sym, reason in active_halts_banner.items()])
    st.error(f"🚨 *تنبيه إيقاف التداول النشط (Nasdaq Volatility Halts):* الأسهم التالية موقوفة حالياً عن التداول: `{halt_symbols_str}`")

st.write("---")

# 4. علامات التبويب الموزعة للفترات
t1, t2, t3, t4, t5, t6 = st.tabs([
    "🛰️ جلسة ما قبل السوق", 
    "📊 الجلسة الرسمية للسوق", 
    "🌙 جلسة بعد الإغلاق", 
    "📡 رادار الأخبار الفورية (SEC)",
    "🏆 سجل صيد اليقين التراكمي",
    "📊 محرك الاختبار التاريخي"
])

def run_session_pipeline(session_name):
    st.markdown(f"🔬 **حالة المعالجة الحالية:** جاري مسح وتصفية سيولة جلسة `{session_name}`...")
    
    with st.spinner("جاري استخلاص البيانات وتدريب نموذج Isolation Forest ورصد شذوذ الحركة الحجمية..."):
        symbols = scanner.fetch_all_us_symbols()
        if symbols:
            # 1. جلب مؤشرات التعلم الآلي التاريخية ونموذج التنبؤ
            from intraday_tracker import get_historical_features
            from ml_classifier import QuantMLClassifier
            
            hist_features = get_historical_features(symbols)
            ml_classifier = QuantMLClassifier()
            
            # جلب قائمة الأسهم الأكثر شعبية على Stocktwits
            stocktwits_trending = fetch_stocktwits_trending()
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            raw_data = loop.run_until_complete(scanner.scan_entire_market())
            
            if not raw_data:
                st.warning("⚠️ لم يتم استلام أي بيانات أسعار حالياً من ياهو فاينانس.")
                return
            
            # 2. تشغيل Isolation Forest لرصد الشذوذ
            anomaly_map = intel.fit_anomaly_detector(raw_data, session_name)
            
            # 3. جلب حالة الإيقاف المؤقت لجميع الأسهم دفعة واحدة
            active_halts = get_active_halts()
            
            # تصفية وفرز البيانات
            opportunities = []
            for quote in raw_data:
                try:
                    score, details, price, change, rvol = intel.calculate_7_layer_conviction(quote, session_name, anomaly_map)
                    sym = quote.get("symbol")
                    
                    # استبعاد شذوذ التقسيم وأسهم SPACs والخيارات والوحدات الوهمية (أطول من 4 أحرف أو تنتهي بـ U, W, R)
                    if len(sym) > 4 or sym.endswith(("U", "W", "R")):
                        continue
                        
                    if price <= 0.0 or price > 20.0 or change < 3.0 or change > 45.0:
                        continue
                        
                    # تصفية إضافية لمنع عرض الأسهم الخاملة التي لا تتداول في الجلسات الممتدة
                    if session_name == "PRE_MARKET":
                        pre_chg = quote.get("preMarketChangePercent")
                        if pre_chg is None or float(pre_chg) == 0.0:
                            continue
                    elif session_name == "AFTER_HOURS":
                        post_chg = quote.get("postMarketChangePercent")
                        if post_chg is None or float(post_chg) == 0.0:
                            continue
                        
                    anomaly_info = anomaly_map.get(sym, {"is_anomaly": False, "confidence_score": 1.0})
                    
                    # حساب احتمالية الانفجار عبر نموذج التعلم الآلي المطور بـ 8 ميزات (مع الفلوت والبيع المكشوف)
                    f_info = hist_features.get(sym, {
                        "volatility_10d": 5.0, 
                        "prev_rvol": 1.0, 
                        "prev_change": 0.0,
                        "float_shares_m": 10.0,
                        "short_percent": 0.0
                    })
                    
                    ml_prob = ml_classifier.predict_probability(
                        price=price,
                        change=change,
                        rvol=rvol,
                        volatility_10d=f_info["volatility_10d"],
                        prev_rvol=f_info["prev_rvol"],
                        prev_change=f_info["prev_change"],
                        float_shares_m=f_info["float_shares_m"],
                        short_percent=f_info["short_percent"]
                    )
                    
                    # التحقق من شعبية السهم على Stocktwits وحالة الإيقاف
                    is_trending = sym in stocktwits_trending
                    is_halted = sym in active_halts
                    halt_reason = active_halts[sym] if is_halted else ""
                    
                    # فحص الإيداعات والتخفيف والملكية القانونية عبر SEC
                    sec_sentiment = get_sec_filings_sentiment(sym)
                    sec_tags = ", ".join(sec_sentiment["details"]) if sec_sentiment["details"] else "لا يوجد"
                    is_dilution = sec_sentiment["dilution_warning"]
                    
                    opportunities.append({
                        "Symbol": sym,
                        "Price": price,
                        "Change_%": change,
                        "Volume": float(quote.get("regularMarketVolume", 0.0)),
                        "RVOL": rvol,
                        "Conviction_Score": score,
                        "Is_Anomaly": anomaly_info["is_anomaly"],
                        "Confidence_Score": anomaly_info["confidence_score"],
                        "ML_Probability": ml_prob,
                        "Is_Trending": is_trending,
                        "Is_Halted": is_halted,
                        "Halt_Reason": halt_reason,
                        "SEC_Tags": sec_tags,
                        "Is_Dilution": is_dilution,
                        "Matches": details
                    })
                except Exception as e:
                    continue
                    continue
            
            df_opportunities = pd.DataFrame(opportunities)
            if not df_opportunities.empty:
                # ترتيب الفرص حسب قوة الاختراق وثقة الذكاء الاصطناعي
                df_opportunities = df_opportunities.sort_values(by=["Conviction_Score", "Confidence_Score"], ascending=[False, False])
                
                # --- القسم الأول المخصص لرصد شذوذ الحجم (Isolation Forest) ---
                st.markdown("""
                <div class="ai-section">
                    <h3 style="color:#3b82f6;margin:0 0 10px 0;font-size:20px;">🔍 محرك رصد الشذوذ الحجمي (Machine Learning Anomaly Detection)</h3>
                    <p style="color:#94a3b8;font-size:14px;margin-bottom:15px;">
                        خوارزمية <b>Isolation Forest</b> تقوم بفصل وتصنيف الرموز التي تشهد انحرافاً حاداً في الحجم النسبي (RVOL) والتدفقات النقدية اللحظية بنسبة 5% كحد أقصى لاستبعاد الضجيج.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # استخلاص الأسهم الشاذة حجمياً فقط
                df_anomalies = df_opportunities[df_opportunities["Is_Anomaly"] == True].copy()
                
                c_anom1, c_anom2 = st.columns(2)
                with c_anom1:
                    st.metric(label="الأسهم الخاضعة للفحص الكلي", value=f"{len(raw_data)} شركة")
                with c_anom2:
                    st.metric(label="الانفجارات الحجمية المكتشفة بالـ ML", value=f"{len(df_anomalies)} أسهم شاذة", delta=f"{((len(df_anomalies)/len(raw_data))*100):.1f}% من السوق", delta_color="inverse")
                
                if not df_anomalies.empty:
                    st.write("📈 **قائمة الأسهم التي تشهد شذوذاً حجمياً استثنائياً حالياً:**")
                    df_anom_display = df_anomalies[["Symbol", "Price", "Change_%", "Volume", "RVOL", "Confidence_Score"]].copy()
                    df_anom_display.columns = ["رمز السهم", "السعر اللحظي", "التغير المئوي", "الحجم اليومي", "الحجم النسبي RVOL", "مؤشر ثقة الاختراق (0-10)"]
                    st.dataframe(df_anom_display, use_container_width=True, hide_index=True)
                else:
                    st.info("ℹ️ لم يتم العثور على شذوذ حجمي غير طبيعي في فلاتر الأسعار تحت 20$ حالياً.")
                
                # --- القسم الثاني: التوجيه التنفيذي والطبقات السبعة ---
                top_stock = df_opportunities.iloc[0]
                matches = top_stock["Matches"]
                
                st.markdown(f"""
                <div class="signal-card">
                    <h2 style='color:#10b981; margin:0 0 10px 0; font-size:22px; font-weight:700;'>🎯 التوجيه التنفيذي للمركز الأول (أقوى تطابق كمي)</h2>
                    <h3>🔥 رمز السهم: {top_stock['Symbol']} | نسبة تطابق الخوارزمية: {top_stock['Conviction_Score']}%</h3>
                    <p style='font-size:18px;margin:5px 0;'>السعر الحالي: <b>{top_stock['Price']:.4f} $</b> | التغير اليومي: <b>{top_stock['Change_%']:+.2f}%</b> | تسارع الحجم النسبي: <b>{top_stock['RVOL']:.2f}x</b></p>
                    <p style='font-size:15px; color:#3b82f6;margin:0;'><b>مؤشر الثقة الميكروي: {top_stock['Confidence_Score']}/10 وفق خوارزمية الغابة المعزولة (Isolation Forest)</b></p>
                </div>
                """, unsafe_allow_html=True)
                
                # زر إرسال التنبيه الفوري للتيليجرام
                notifier = TelegramNotifier()
                if st.button("📢 إرسال إشارة التنبيه للتيليجرام", key="send_tg_alert"):
                    success = notifier.send_breakout_alert(
                        symbol=top_stock['Symbol'],
                        price=top_stock['Price'],
                        change=top_stock['Change_%'],
                        rvol=top_stock['RVOL'],
                        score=top_stock['Conviction_Score'],
                        confidence=top_stock['Confidence_Score']
                    )
                    if success:
                        st.success("✅ تم إرسال إشارة التنبيه بنجاح إلى هاتفك عبر تيليجرام!")
                    else:
                        st.error("❌ فشل إرسال التنبيه. يرجى التحقق من صحة المفاتيح في config.env أو Streamlit Secrets.")
                
                st.write("#### 🛡️ فحص طبقات اليقين السبعة للسهم المتصدر:")
                cols = st.columns(7)
                layer_names = [
                    ("فلتر السعر", "Price_Filter"),
                    ("درع الفجوة", "Gap_Shield"),
                    ("منطقة الاختراق", "Early_Breakout"),
                    ("تسارع الحجم RVOL", "RVOL_Acceleration"),
                    ("تتبع الحيتان", "Whale_Block"),
                    ("عدم توازن السيولة", "OBI_Imbalance"),
                    ("محفز الأخبار", "News_Catalyst")
                ]
                for i, (name, key) in enumerate(layer_names):
                    val = matches.get(key)
                    is_match = val is True or val in ["IDEAL", "HIGH", "STRONG_POSITIVE"]
                    with cols[i]:
                        if is_match:
                            st.success(f"✅ {name}\n\n({val})")
                        else:
                            st.error(f"❌ {name}\n\n({val})")
                
                # --- القسم الثالث: تقسيم الجداول لحماية رأس المال ---
                st.write("---")
                
                # أ. أسهم المضاربة اللحظية السريعة (Intraday Scalping Radar)
                st.markdown("### 🔥 رادار المضاربة اللحظية السريعة (Intraday Scalping - Target +15% / Stop -7% / Exit Today)")
                st.write("أسهم رخيصة تحت 10$ تشهد اختراقاً حركياً وحجمياً قوياً اليوم، وتستهدف الخروج السريع في نفس اليوم لحماية رأس المال.")
                
                df_scalp = df_opportunities[
                    (df_opportunities["Price"] >= 0.1) & 
                    (df_opportunities["Price"] <= 10.0) & 
                    (df_opportunities["Change_%"] >= 4.0) & 
                    (df_opportunities["RVOL"] >= 2.5)
                ].copy()
                
                if not df_scalp.empty:
                    # ترتيب جدول المضاربة اللحظية حسب احتمالية الانفجار التنبؤية للذكاء الاصطناعي
                    df_scalp = df_scalp.sort_values(by="ML_Probability", ascending=False)
                    
                    df_scalp_display = df_scalp.copy()
                    df_scalp_display["تطابق الخوارزمية"] = df_scalp_display["Conviction_Score"].apply(lambda x: f"🔥 {x}%" if x >= 80 else f"⚡ {x}%")
                    df_scalp_display["مؤشر الثقة"] = df_scalp_display["Confidence_Score"].apply(lambda x: f"⭐ {x}/10")
                    df_scalp_display["حالة الشذوذ"] = df_scalp_display["Is_Anomaly"].apply(lambda x: "🚨 نعم" if x else "لا")
                    df_scalp_display["احتمالية الانفجار (ML)"] = df_scalp_display["ML_Probability"].apply(lambda x: f"🔮 {x:.1f}%")
                    df_scalp_display["التريند العام"] = df_scalp_display["Is_Trending"].apply(lambda x: "🔥 رائج جداً" if x else "لا")
                    df_scalp_display["حالة الإيقاف"] = df_scalp_display.apply(lambda r: f"🚨 موقوف ({r['Halt_Reason']})" if r["Is_Halted"] else "🟢 نشط", axis=1)
                    df_scalp_display["إيداعات SEC"] = df_scalp_display["SEC_Tags"]
                    df_scalp_display["تحذير التخفيف"] = df_scalp_display["Is_Dilution"].apply(lambda x: "🚨 خطر تخفيف (S-1)!" if x else "آمن ✅")
                    
                    df_scalp_table = df_scalp_display[["Symbol", "Price", "Change_%", "Volume", "RVOL", "حالة الإيقاف", "إيداعات SEC", "تحذير التخفيف", "التريند العام", "احتمالية الانفجار (ML)", "تطابق الخوارزمية"]].copy()
                    df_scalp_table.columns = ["رمز السهم", "السعر اللحظي", "التغير المئوي", "الحجم اليومي", "الحجم النسبي RVOL", "حالة التداول", "إيداعات SEC", "التخفيف (Dilution)", "شعبية Stocktwits", "احتمالية الانفجار (ML)", "تطابق الخوارزمية"]
                    st.dataframe(df_scalp_table, use_container_width=True, hide_index=True)
                else:
                    st.info("ℹ️ لا توجد حالياً أسهم مطابقة لشروط المضاربة اللحظية السريعة اليوم.")
                
                st.write("---")
                
                # ب. الأسهم الانفجارية الحقيقية طويلة المدى (Explosive Swing Breakouts)
                st.markdown("### 🚀 رادار الاختراق واليقين طويل المدى (Explosive Swing Breakouts - Target +50%)")
                st.write("أسهم عالية اليقين مطابقة للطبقات السبعة لليقين، تستهدف الاحتفاظ لعدة أيام عمل لتحقيق انفجارات سعرية كبرى تصل لـ 50% فما فوق.")
                
                df_swings = df_opportunities[df_opportunities["Conviction_Score"] >= 80].copy()
                if not df_swings.empty:
                    # ترتيب الاختراقات طويلة المدى حسب احتمالية الانفجار
                    df_swings = df_swings.sort_values(by="ML_Probability", ascending=False)
                    
                    df_swings_display = df_swings.copy()
                    df_swings_display["تطابق الخوارزمية"] = df_swings_display["Conviction_Score"].apply(lambda x: f"🔥 {x}%" if x >= 80 else f"⚡ {x}%")
                    df_swings_display["مؤشر الثقة"] = df_swings_display["Confidence_Score"].apply(lambda x: f"⭐ {x}/10")
                    df_swings_display["حالة الشذوذ"] = df_swings_display["Is_Anomaly"].apply(lambda x: "🚨 نعم" if x else "لا")
                    df_swings_display["احتمالية الانفجار (ML)"] = df_swings_display["ML_Probability"].apply(lambda x: f"🔮 {x:.1f}%")
                    df_swings_display["التريند العام"] = df_swings_display["Is_Trending"].apply(lambda x: "🔥 رائج جداً" if x else "لا")
                    df_swings_display["حالة الإيقاف"] = df_swings_display.apply(lambda r: f"🚨 موقوف ({r['Halt_Reason']})" if r["Is_Halted"] else "🟢 نشط", axis=1)
                    df_swings_display["إيداعات SEC"] = df_swings_display["SEC_Tags"]
                    df_swings_display["تحذير التخفيف"] = df_swings_display["Is_Dilution"].apply(lambda x: "🚨 خطر تخفيف (S-1)!" if x else "آمن ✅")
                    
                    df_swings_table = df_swings_display[["Symbol", "Price", "Change_%", "Volume", "RVOL", "حالة الإيقاف", "إيداعات SEC", "تحذير التخفيف", "التريند العام", "احتمالية الانفجار (ML)", "تطابق الخوارزمية"]].copy()
                    df_swings_table.columns = ["رمز السهم", "السعر اللحظي", "التغير المئوي", "الحجم اليومي", "الحجم النسبي RVOL", "حالة التداول", "إيداعات SEC", "التخفيف (Dilution)", "شعبية Stocktwits", "احتمالية الانفجار (ML)", "تطابق الخوارزمية"]
                    st.dataframe(df_swings_table, use_container_width=True, hide_index=True)
                else:
                    st.info("ℹ️ لا توجد حالياً أسهم مطابقة لطبقات اليقين السبعة لصفقات السوينغ اليوم.")
                
            else:
                st.warning("⚠️ لا توجد حالياً أسهم رخيصة تحقق شروط الانفجار الصارمة ومؤشرات الشذوذ في هذه الجلسة.")
        else:
            st.error("❌ فشل الاتصال بقاعدة بيانات الرموز النشطة.")

with t1:
    st.markdown("### 🛰️ جلسة ما قبل الافتتاح (Pre-Market Scanner)")
    st.write("تركز هذه الجلسة على قياس فجوات الافتتاح وأحجام التداول وشذوذ السيولة قبل انطلاق السوق.")
    if st.button("تفعيل فحص ما قبل السوق"):
        run_session_pipeline("PRE_MARKET")

with t2:
    st.markdown("### 📊 الجلسة الرسمية للسوق (Regular Session Scanner)")
    st.write("تركز الجلسة الرسمية على تسارع السيولة اللحظي واختراق القمم ومؤشرات شذوذ الحجم اللحظية.")
    if st.button("تفعيل فحص الجلسة الرسمية"):
        run_session_pipeline("REGULAR_SESSION")

with t3:
    st.markdown("### 🌙 جلسة بعد الإغلاق (After-Hours Scanner)")
    st.write("تتبع هذه الجلسة استجابات الشركات للنتائج والأخبار وتأثيراتها الحركية بعد جرس الإغلاق.")
    if st.button("تفعيل فحص جلسة الليل"):
        run_session_pipeline("AFTER_HOURS")

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
                    df_trades.columns = ["رمز السهم", "الاستراتيجية", "تاريخ الدخول", "تاريخ الخروج", "سعر الدخول", "سعر الخروج", "الأرباح ($)", "الربح المئوي (%)", "حالة الصفقة"]
                    
                    # تنسيق الأرقام لسهولة القراءة
                    df_trades["سعر الدخول"] = df_trades["سعر الدخول"].apply(lambda x: f"${x:.2f}")
                    df_trades["سعر الخروج"] = df_trades["سعر الخروج"].apply(lambda x: f"${x:.2f}")
                    df_trades["الأرباح ($)"] = df_trades["الأرباح ($)"].apply(lambda x: f"{x:+.2f}$")
                    df_trades["الربح المئوي (%)"] = df_trades["الربح المئوي (%)"].apply(lambda x: f"{x:+.1f}%")
                    
                    st.dataframe(df_trades, use_container_width=True, hide_index=True)
                else:
                    st.info("ℹ️ لم يتم توليد أي صفقات خلال فترة الفحص التاريخية المحددة.")
