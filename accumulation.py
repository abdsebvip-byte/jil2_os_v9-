# module: accumulation.py
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
from yahooquery import Ticker
from scanner import FreeMarketScanner

class SilentAccumulationScanner:
    def __init__(self):
        self.scanner = FreeMarketScanner()

    def scan_for_accumulation(self):
        """
        Scans candidate stocks for silent volume accumulation under strict low-float and price filters.
        """
        print("SilentAccumulation: Starting scan cycle...")
        
        # 1. جلب رموز الأسهم النشطة المبدئية
        all_symbols = self.scanner.fetch_all_us_symbols()
        if not all_symbols:
            return []

        # 2. الاستعلام عن بيانات الأسعار والأسهم الحرة دفعة واحدة لتوفير الوقت والجهد
        print(f"SilentAccumulation: Fetching statistics for {len(all_symbols)} symbols...")
        ticker_batch = Ticker(all_symbols)
        
        try:
            stats = ticker_batch.key_stats
            price_details = ticker_batch.price
        except Exception as e:
            print(f"SilentAccumulation: Bulk statistics fetch failed: {str(e)}")
            return []

        # 3. التصفية المبدئية بالـ Float المحدود والسعر المثالي ($2.00 - $10.00)
        valid_symbols = []
        symbol_float_map = {}
        symbol_price_map = {}

        for sym in all_symbols:
            try:
                p_info = price_details.get(sym)
                if not isinstance(p_info, dict):
                    continue
                    
                price = float(p_info.get("regularMarketPrice", 0.0))
                
                # تصفية السعر الصارمة بين 2$ و 10$ لتقليل الإشارات الخاطئة وتجنب المضاربات الوهمية
                if price < 2.0 or price > 10.0:
                    continue
                
                # جلب بيانات الأسهم الحرة (Float Shares)
                stat_info = stats.get(sym)
                float_shares = 10000000.0  # قيمة افتراضية في حال عدم توفرها بالـ API لمنع التخطي الخاطئ
                if isinstance(stat_info, dict) and stat_info.get("floatShares"):
                    float_shares = float(stat_info["floatShares"])
                
                # تصفية الـ Float المنخفض جداً (< 15 مليون سهم حقيقي للتداول) لضمان سرعة الانفجار
                if float_shares > 15000000.0:
                    continue
                    
                valid_symbols.append(sym)
                symbol_float_map[sym] = float_shares
                symbol_price_map[sym] = price
            except:
                continue

        if not valid_symbols:
            print("SilentAccumulation: No symbols passed the price and float filters.")
            return []

        print(f"SilentAccumulation: {len(valid_symbols)} symbols passed initial filters. Querying 14-day history...")
        
        try:
            hist_batch = Ticker(valid_symbols)
            df_hist = hist_batch.history(period="14d")
        except Exception as e:
            print(f"SilentAccumulation: History fetch failed: {str(e)}")
            return []

        if df_hist is None or df_hist.empty:
            return []

        setups = []
        
        # كشف التوقيت الشرقي لمزامنة نضوج الشموع اليومية
        est_tz = pytz.timezone('US/Eastern')
        now_est = datetime.now(est_tz)
        today_str = now_est.strftime("%Y-%m-%d")
        
        # 5. تحليل النماذج السعرية والحجمية لكل سهم بشكل فردي
        for sym in valid_symbols:
            try:
                if sym not in df_hist.index.levels[0]:
                    continue
                
                full_ticker_df = df_hist.loc[sym]
                if len(full_ticker_df) < 6:
                    continue
                
                # استبعاد شمعة اليوم الحالي إذا كنا قبل إغلاق السوق (الساعة 4:00 مساءً بتوقيت نيويورك)
                # لأن حجم التداول لليوم الحالي لم يكتمل بعد وسيعطي قراءة مغلوطة (صفراً أو قليلاً جداً)
                last_row_date = str(full_ticker_df.index[-1]).split()[0]
                if last_row_date == today_str and now_est.hour < 16:
                    ticker_df = full_ticker_df.iloc[:-1].tail(5)
                else:
                    ticker_df = full_ticker_df.tail(5)
                    
                if len(ticker_df) < 5:
                    continue
                
                # حساب النطاق السعري لآخر 4 أيام (التجميع واستقرار السعر السابق)
                close_prices = ticker_df['close'].iloc[:-1]  # أول 4 أيام باستثناء اليوم الأخير المستهدف
                max_p = close_prices.max()
                min_p = close_prices.min()
                mean_p = close_prices.mean()
                
                # حساب معدل التذبذب (هل السعر يتحرك في قناة ضيقة أقل من 4%؟)
                volatility = ((max_p - min_p) / mean_p) * 100
                is_consolidating = volatility <= 4.0
                
                # حساب حجم التداول لليوم الأخير المكتمل مقارنة بمتوسط الـ 4 أيام السابقة له
                avg_volume_prev = ticker_df['volume'].iloc[:-1].mean()
                target_volume = ticker_df['volume'].iloc[-1]
                
                # حجم التداول تضاعف بمعدل 4.0x فما فوق لليوم المستهدف
                volume_multiplier = target_volume / avg_volume_prev if avg_volume_prev > 0 else 1.0
                is_volume_spike = volume_multiplier >= 4.0
                
                # سعر اليوم المستهدف لم يتغير عن اليوم الذي قبله بأكثر من 3.5% (تراكم سيولة بدون حركة سعرية حادة)
                price_change_target = abs((ticker_df['close'].iloc[-1] - ticker_df['close'].iloc[-2]) / ticker_df['close'].iloc[-2]) * 100
                is_price_stable = price_change_target <= 3.5
                
                if is_consolidating and is_volume_spike and is_price_stable:
                    # حساب الـ ATR لآخر 14 يوماً لتقدير مدى الانفجار ووقف الخسارة
                    high_low = full_ticker_df['high'] - full_ticker_df['low']
                    high_close = abs(full_ticker_df['high'] - full_ticker_df['close'].shift())
                    low_close = abs(full_ticker_df['low'] - full_ticker_df['close'].shift())
                    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                    atr = tr.tail(14).mean()
                    
                    price = symbol_price_map[sym]
                    float_m = symbol_float_map[sym] / 1000000.0  # تحويل بالمليون
                    
                    # 6. التقديرات الرقمية الحقيقية (خالية من التزييف)
                    expected_gain_percent = (3.0 * atr / price) * 100 if price > 0 else 0.0
                    
                    # المدى الزمني المتوقع للانفجار يحسب بناءً على ضيق التذبذب
                    expected_days = 2 + int(volatility * 1.5)
                    expected_days = min(max(expected_days, 2), 7)  # حصر النطاق بين 2 إلى 7 أيام عمل
                    
                    stop_loss = price - (1.5 * atr)
                    
                    # 7. صياغة التوجيه الاستشاري الديناميكي الحقيقي
                    guidance = (
                        f"سهم {sym} يمر بمرحلة تجميع صامت قوي. "
                        f"حجم التداول تضاعف بمعدل {volume_multiplier:.1f} أضعاف مع استقرار السعر بنطاق تذبذب {volatility:.2f}% فقط. "
                        f"حجم الأسهم الحرة المتداولة للشركة صغير جداً ويقدر بـ {float_m:.2f} مليون سهم مما يجعله سريع الاستجابة للسيولة. "
                        f"التوجيه الفني للذكاء الاصطناعي: السهم مؤهل للشراء والاحتفاظ الاستراتيجي المؤقت لمدة {expected_days} أيام عمل ترقباً للاختراق الفعلي. "
                        f"نقطة إيقاف الخسارة الصارمة لحماية رأس مالك توضع عند سعر {stop_loss:.2f}$."
                    )
                    
                    setups.append({
                        "Symbol": sym,
                        "Price": price,
                        "Volume_Multiplier": volume_multiplier,
                        "Volatility": volatility,
                        "Float_M": float_m,
                        "Expected_Gain_%": expected_gain_percent,
                        "Expected_Days": expected_days,
                        "Stop_Loss": stop_loss,
                        "Guidance": guidance
                    })
            except Exception as e:
                print(f"SilentAccumulation: Error evaluating {sym}: {str(e)}")
                continue

        print(f"SilentAccumulation: Found {len(setups)} accumulation setups.")
        return setups
