import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import yfinance as yf
from pattern_detector import PatternDetector

# -------------------------------------------------------------
# إعداد الصفحة لتكون واسعة بالكامل (Terminal Mode)
# -------------------------------------------------------------
st.set_page_config(
    page_title="BOOM V10 - Advanced Terminal",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------------------
# CSS مخصص لتحويل Streamlit إلى منصة تداول احترافية 
# -------------------------------------------------------------
st.markdown("""
<style>
    /* إزالة الحواف وجعل الشاشة ممتلئة تماماً */
    .block-container {
        padding: 0.5rem 1rem 0.5rem 1rem !important;
        max-width: 100% !important;
    }
    /* خلفية داكنة احترافية جداً */
    .stApp {
        background-color: #0b0e14;
        color: #d1d5db;
    }
    /* تنسيق الكروت الجانبية لتبدو فاخرة */
    div[data-testid="stVerticalBlock"] > div {
        background-color: #151924;
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #1f2937;
    }
    /* إخفاء شريط Streamlit العلوي */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* تنسيق العناوين والتابات */
    h1, h2, h3, h4 {
        color: #f3f4f6 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background-color: #151924;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1f2937;
        border-radius: 5px 5px 0 0;
        padding: 10px 15px;
        color: white;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# شريط الحالة العلوي (System Health Bar)
# -------------------------------------------------------------
st.markdown("""
<div style="background-color: #111827; padding: 10px; border-radius: 5px; border-bottom: 2px solid #3b82f6; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
    <div style="color: #60a5fa; font-weight: bold; font-size: 18px;">🚀 BOOM V10 Terminal</div>
    <div style="color: #10b981; font-size: 14px;">🟢 الرادار متصل بالسوق الحي | الجلسة الحالية: ما بعد الإغلاق (After-Hours)</div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# دالة لعرض شارت TradingView الاحترافي
# -------------------------------------------------------------
def render_advanced_tradingview(symbol):
    html_code = f"""
    <!-- TradingView Widget BEGIN -->
    <div class="tradingview-widget-container" style="height:100%;width:100%">
      <div id="tradingview_advanced" style="height:700px;width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
      "autosize": true,
      "symbol": "{symbol}",
      "interval": "15",
      "timezone": "Etc/UTC",
      "theme": "dark",
      "style": "1",
      "locale": "ar_AE",
      "enable_publishing": false,
      "backgroundColor": "#0b0e14",
      "gridColor": "#1f2937",
      "hide_top_toolbar": false,
      "hide_legend": false,
      "save_image": false,
      "container_id": "tradingview_advanced",
      "toolbar_bg": "#0b0e14",
      "studies": [
        "Volume@tv-basicstudies",
        "RSI@tv-basicstudies"
      ]
    }}
      );
      </script>
    </div>
    <!-- TradingView Widget END -->
    """
    components.html(html_code, height=700)

# -------------------------------------------------------------
# دالة تحليل النماذج الفنية باستخدام المحرك الرياضي
# -------------------------------------------------------------
@st.cache_data(ttl=60)
def analyze_stock_pattern(symbol):
    try:
        df = yf.download(symbol, period="1mo", interval="15m", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel('Ticker')
        detector = PatternDetector(df, order=4)
        return detector.detect_patterns()
    except:
        return None

# -------------------------------------------------------------
# تقسيم الشاشة إلى 3 أقسام رئيسية 
# -------------------------------------------------------------
# اليسار: الرادار (20%) | الوسط: الشارت (60%) | اليمين: النماذج والذكاء (20%)
col_radar, col_chart, col_ai = st.columns([2, 6, 2])

# ==========================================
# 1. القسم الأيسر: رادار الانفجارات الحي
# ==========================================
with col_radar:
    st.markdown("#### 📡 صائد الانفجارات")
    
    # تابات الجلسات كما اقترحت
    tab_ah, tab_reg, tab_pre = st.tabs(["🌙 المسائية", "☀️ الرسمية", "🌅 ما قبل السوق"])
    
    with tab_ah:
        mock_ah_stocks = ["NVDA", "MSTR", "PLTR", "SOUN", "SMCI"]
        selected_stock = st.radio("الأسهم المرصودة الآن (انقر للتحليل):", mock_ah_stocks, index=0)
        st.info("🔥 السيولة تتركز هنا حالياً.")
        
    with tab_reg:
        st.warning("الجلسة الرسمية مغلقة حالياً. ستظهر الأسهم غداً الساعة 9:30.")
        
    with tab_pre:
        st.warning("ما قبل السوق مغلق. سيعمل غداً 4:00 فجراً.")

# ==========================================
# 2. القسم الأوسط: الشارت الاحترافي العملاق
# ==========================================
with col_chart:
    st.markdown(f"### 📊 مراقبة السهم: {selected_stock}")
    render_advanced_tradingview(selected_stock)

# ==========================================
# 3. القسم الأيمن: عقل الذكاء الاصطناعي (النماذج الفنية)
# ==========================================
with col_ai:
    st.markdown("#### 🤖 النماذج الفنية (AI)")
    st.markdown(f"**يتم تحليل {selected_stock} رياضياً...**")
    
    pattern = analyze_stock_pattern(selected_stock)
    
    if pattern:
        color = "#10b981" if pattern['type'] == "BULLISH" else "#f59e0b"
        st.markdown(f"""
        <div style="background-color: #1f2937; padding: 15px; border-radius: 8px; border-left: 4px solid {color}; margin-bottom: 10px;">
            <div style="font-size: 18px; color: white;">📐 {pattern['pattern']}</div>
            <div style="font-size: 14px; color: #9ca3af; margin-top: 5px;">{pattern['details']}</div>
            <div style="margin-top: 10px; display:flex; align-items:center;">
                <div style="flex-grow:1; background-color:#374151; height:8px; border-radius:4px;">
                    <div style="width:{pattern['probability']}%; background-color:{color}; height:100%; border-radius:4px;"></div>
                </div>
                <div style="margin-left:10px; font-weight:bold; color:{color};">{pattern['probability']}% الدقة</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info(f"⏳ لا توجد نماذج انفجارية واضحة تشكلت على سهم {selected_stock} حتى هذه اللحظة. المحرك مستمر في المراقبة.")
        
    st.markdown("---")
    st.markdown("#### 🐋 رادار الحيتان (مباشر)")
    st.markdown("""
    <div style="background-color: #1f2937; padding: 10px; border-radius: 5px; margin-bottom: 5px;">
        <span style="color:#ef4444;">▼</span> TSLA: حائط بيع ضخم عند 320$
    </div>
    <div style="background-color: #1f2937; padding: 10px; border-radius: 5px;">
        <span style="color:#10b981;">▲</span> AAPL: شراء مخفي مستمر بـ 5M$
    </div>
    """, unsafe_allow_html=True)
