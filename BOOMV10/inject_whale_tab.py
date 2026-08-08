import re

with open('app_v10.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add t_whale to the tabs array
old_tabs = """t_halts, t1, t2, t3, t_trace, t4, t5, t6, t7 = st.tabs([
    "🚨 صفقات الاستئناف (LULD Halts)",
    "🛩️ جلسة ما قبل السوق", 
    "📊 الجلسة الرسمية للسوق", 
    "🌙 جلسة بعد الإغلاق", 
    "🔍 سجل الاستبعاد والقرارات (Decision Trace)",
    "📡 رادار الأخبار الفورية (SEC)",
    "🏆 سجل صيد اليقين التراكمي",
    "📊 محرك الاختبار التاريخي",
    "🤖 وكيل التحسين الذاتي (AI)"
])"""
new_tabs = """t_halts, t1, t2, t3, t_whale, t_trace, t4, t5, t6, t7 = st.tabs([
    "🚨 صفقات الاستئناف (LULD Halts)",
    "🛩️ جلسة ما قبل السوق", 
    "📊 الجلسة الرسمية للسوق", 
    "🌙 جلسة بعد الإغلاق", 
    "🐳 رادار الحيتان (قائمة توقعات الغد)",
    "🔍 سجل الاستبعاد والقرارات (Decision Trace)",
    "📡 رادار الأخبار الفورية (SEC)",
    "🏆 سجل صيد اليقين التراكمي",
    "📊 محرك الاختبار التاريخي",
    "🤖 وكيل التحسين الذاتي (AI)"
])"""
content = content.replace(old_tabs, new_tabs)

# 2. Add the UI for t_whale
whale_ui = """
with t_whale:
    st.markdown("### 🐳 رادار الحيتان: التمركز الاستباقي (Pre-Breakout Predictor)")
    st.write("يقوم هذا الرادار بمسح سيولة ما قبل الافتتاح والساعة الأخيرة من السوق لاصطياد المحافظ الكبيرة التي تجمع بهدوء في أسهم صغيرة، تحضيراً لرفعها في الجلسة القادمة.")
    
    conn = get_db_connection()
    whale_alerts = pd.read_sql_query("SELECT symbol, price, change_pct, rvol, market_cap, reason FROM whale_alerts ORDER BY rvol DESC", conn)
    conn.close()
    
    if not whale_alerts.empty:
        st.warning("⚠️ **تنبيه:** هذه الأسهم لقائمة المراقبة والتمركز المبكر (Watchlist). احذر من فخاخ الهوامير الوهمية (Fakeouts).")
        st.dataframe(whale_alerts.rename(columns={
            "symbol": "رمز السهم",
            "price": "السعر اللحظي",
            "change_pct": "التغير (%)",
            "rvol": "مضاعف السيولة (RVOL)",
            "market_cap": "القيمة السوقية",
            "reason": "سبب الترشيح (السر)"
        }), use_container_width=True, hide_index=True)
    else:
        st.info("هدوء تام.. لم يرصد رادار الحيتان أي نشاط تجميعي مريب للتحضير للجلسة القادمة.")

with t_trace:
"""
content = content.replace("with t_trace:", whale_ui)

with open('app_v10.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Whale tab injected successfully.")
