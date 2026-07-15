# module: app_v10.py
import streamlit as st
import pandas as pd
import asyncio
from scanner import FreeMarketScanner
from intelligence import QuantIntelligence
from news_radar import SECNewsRadar
from notifier import TelegramNotifier

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

st.write("---")

# 4. علامات التبويب الموزعة للفترات
t1, t2, t3, t4, t5 = st.tabs([
    "🛰️ جلسة ما قبل السوق", 
    "📊 الجلسة الرسمية للسوق", 
    "🌙 جلسة بعد الإغلاق", 
    "📡 رادار الأخبار الفورية (SEC)",
    "🏆 سجل صيد اليقين التراكمي"
])

def run_session_pipeline(session_name):
    st.markdown(f"🔬 **حالة المعالجة الحالية:** جاري مسح وتصفية سيولة جلسة `{session_name}`...")
    
    with st.spinner("جاري استخلاص البيانات وتدريب نموذج Isolation Forest لرصد شذوذ الحركة الحجمية..."):
        symbols = scanner.fetch_all_us_symbols()
        if symbols:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            raw_data = loop.run_until_complete(scanner.scan_entire_market())
            
            if not raw_data:
                st.warning("⚠️ لم يتم استلام أي بيانات أسعار حالياً من ياهو فاينانس.")
                return
            
            # 1. تشغيل Isolation Forest لرصد الشذوذ
            anomaly_map = intel.fit_anomaly_detector(raw_data, session_name)
            
            # 2. تصفية وفرز البيانات
            opportunities = []
            for quote in raw_data:
                try:
                    score, details, price, change, rvol = intel.calculate_7_layer_conviction(quote, session_name, anomaly_map)
                    sym = quote.get("symbol")
                    
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
                    
                    opportunities.append({
                        "Symbol": sym,
                        "Price": price,
                        "Change_%": change,
                        "Volume": float(quote.get("regularMarketVolume", 0.0)),
                        "RVOL": rvol,
                        "Conviction_Score": score,
                        "Is_Anomaly": anomaly_info["is_anomaly"],
                        "Confidence_Score": anomaly_info["confidence_score"],
                        "Matches": details
                    })
                except Exception as e:
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
                
                # --- القسم الثالث: مصفوفة الفحص الشاملة المرتبة ---
                st.write("---")
                st.write("### 📊 مصفوفة الفحص الشاملة المرتبة تناسقياً:")
                df_all_display = df_opportunities.copy()
                df_all_display["تطابق الخوارزمية"] = df_all_display["Conviction_Score"].apply(lambda x: f"🔥 {x}%" if x >= 80 else f"⚡ {x}%")
                df_all_display["مؤشر الثقة"] = df_all_display["Confidence_Score"].apply(lambda x: f"⭐ {x}/10")
                df_all_display["حالة الشذوذ"] = df_all_display["Is_Anomaly"].apply(lambda x: "🚨 نعم" if x else "لا")
                
                df_table = df_all_display[["Symbol", "Price", "Change_%", "Volume", "RVOL", "حالة الشذوذ", "مؤشر الثقة", "تطابق الخوارزمية"]].copy()
                df_table.columns = ["رمز السهم", "السعر اللحظي", "التغير المئوي", "الحجم اليومي", "الحجم النسبي RVOL", "انحراف حجمي حاد", "مؤشر الثقة (ML)", "تطابق الخوارزمية"]
                st.dataframe(df_table, use_container_width=True, hide_index=True)
                
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
    st.markdown("### 🏆 سجل صيد اليقين التراكمي")
    st.info("مخصص لأرشفة ومحاكاة الصفقات الافتراضية عالية التأكيد لرصد معدل نمو المحفظة التراكمية.")
    if st.session_state.paper_ledger:
        st.dataframe(pd.DataFrame(st.session_state.paper_ledger), use_container_width=True)
    else:
        st.write("السجل فارغ حالياً. قم بإجراء الفحوصات لتسجيل البيانات عند مطابقة الصفقات.")
