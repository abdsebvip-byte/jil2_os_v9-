# module: backtester.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from yahooquery import Ticker
from scanner import FreeMarketScanner

class QuantBacktester:
    def __init__(self):
        self.scanner = FreeMarketScanner()

    def run_backtest(self, strategy_type="ACCUMULATION", days_to_test=180, initial_capital=1000.0):
        """
        Runs a historical backtest over the last 180 days for active candidate symbols.
        Target Exit: Profit Target +50%, Stop Loss -15%, or Max Hold of 10 trading days.
        """
        print(f"Backtester: Initializing backtest for {strategy_type} over {days_to_test} days...")
        
        # 1. جلب قائمة الأسهم المرشحة النشطة
        symbols = self.scanner.fetch_all_us_symbols()
        if not symbols:
            return {"error": "لم يتم العثور على رموز أسهم نشطة للتحليل التاريخي."}

        # 2. تحميل البيانات التاريخية دفعة واحدة لجميع الأسهم لتفادي تعليق السيرفر
        # نقوم بتحميل فترة إضافية قدرها 20 يوماً لحساب المتوسطات التاريخية بدقة لليوم الأول من الاختبار
        period_str = f"{days_to_test + 20}d"
        print(f"Backtester: Fetching {period_str} history for {len(symbols)} symbols in bulk...")
        
        try:
            ticker_batch = Ticker(symbols)
            df_hist = ticker_batch.history(period=period_str)
        except Exception as e:
            return {"error": f"فشل تحميل البيانات التاريخية من خوادم ياهو: {str(e)}"}

        if df_hist is None or df_hist.empty:
            return {"error": "البيانات التاريخية المسترجعة فارغة."}

        # توحيد نوع التواريخ في الفهرس لتفادي أخطاء مقارنة الأنواع المختلفة من التواريخ (mixed types)
        try:
            df_hist.index = df_hist.index.set_levels(pd.to_datetime(df_hist.index.levels[1]), level=1)
        except Exception as e:
            print(f"Backtester: Date alignment warning: {str(e)}")

        # 3. استخلاص الفلوت لكل سهم لتطبيقه في تصفية الأسهم الحرة
        print("Backtester: Fetching float details...")
        float_map = {}
        try:
            stats = ticker_batch.key_stats
            for sym in symbols:
                stat_info = stats.get(sym)
                float_shares = 10000000.0 # افتراضي 10 مليون في حال الغياب
                if isinstance(stat_info, dict) and stat_info.get("floatShares"):
                    float_shares = float(stat_info["floatShares"])
                float_map[sym] = float_shares
        except:
            for sym in symbols:
                float_map[sym] = 10000000.0

        # ترتيب البيانات حسب التواريخ
        available_symbols = df_hist.index.levels[0]
        
        # استخراج جميع التواريخ الفريدة المتاحة في البيانات وجدولة نطاق الاختبار الفعلي
        all_dates = sorted(list(set(df_hist.index.levels[1])))
        if len(all_dates) < 25:
            return {"error": "البيانات التاريخية المتاحة غير كافية لإجراء الاختبار."}
            
        test_dates = all_dates[20:] # استبعاد أول 20 يوماً لتأمين حساب المتوسطات
        
        trades = []
        equity_curve = [{"Date": str(test_dates[0]).split()[0], "Capital": initial_capital}]
        current_capital = initial_capital
        
        # تتبع حالة رأس المال والصفقات الجارية
        active_positions = [] # عناصرها: {"symbol": str, "entry_price": float, "qty": float, "entry_date": datetime, "days_held": int}

        # 4. محاكاة التداول يوماً بيوم (أثر رجعي دون تداخل مستقبلي)
        for date_idx, current_date in enumerate(test_dates):
            current_date_str = str(current_date).split()[0]
            
            # أ. مراجعة وتصفية الصفقات المفتوحة جارية التداول بناء على الشروط المعتمدة
            still_active = []
            for pos in active_positions:
                sym = pos["symbol"]
                # جلب شمعة تداول اليوم الحالي للسهم
                try:
                    day_candle = df_hist.loc[sym].loc[current_date]
                    high_t = float(day_candle["high"])
                    low_t = float(day_candle["low"])
                    close_t = float(day_candle["close"])
                except:
                    # في حال لم يتداول السهم في هذا اليوم، نستمر بالاحتفاظ
                    pos["days_held"] += 1
                    still_active.append(pos)
                    continue

                entry_p = pos["entry_price"]
                qty = pos["qty"]
                
                # شرط الخروج 1: تحقيق جني الأرباح المستهدف (>= 50% من سعر الدخول)
                if high_t >= entry_p * 1.50:
                    exit_price = entry_p * 1.50
                    pnl = (exit_price - entry_p) * qty
                    current_capital += (exit_price * qty)
                    trades.append({
                        "Symbol": sym,
                        "Type": pos["strategy"],
                        "Entry_Date": pos["entry_date"],
                        "Exit_Date": current_date_str,
                        "Entry_Price": entry_p,
                        "Exit_Price": exit_price,
                        "PnL_$": pnl,
                        "PnL_%": 50.0,
                        "Result": "WIN (TP 50%)"
                    })
                # شرط الخروج 2: تفعيل وقف الخسارة لحماية رأس المال (<= -15%)
                elif low_t <= entry_p * 0.85:
                    exit_price = entry_p * 0.85
                    pnl = (exit_price - entry_p) * qty
                    current_capital += (exit_price * qty)
                    trades.append({
                        "Symbol": sym,
                        "Type": pos["strategy"],
                        "Entry_Date": pos["entry_date"],
                        "Exit_Date": current_date_str,
                        "Entry_Price": entry_p,
                        "Exit_Price": exit_price,
                        "PnL_$": pnl,
                        "PnL_%": -15.0,
                        "Result": "LOSS (SL 15%)"
                    })
                # شرط الخروج 3: انتهاء المدة القصوى للاحتفاظ (10 أيام تداول)
                elif pos["days_held"] >= 9: # اليوم العاشر
                    exit_price = close_t
                    pnl = (exit_price - entry_p) * qty
                    current_capital += (exit_price * qty)
                    pnl_pct = ((exit_price - entry_p) / entry_p) * 100
                    trades.append({
                        "Symbol": sym,
                        "Type": pos["strategy"],
                        "Entry_Date": pos["entry_date"],
                        "Exit_Date": current_date_str,
                        "Entry_Price": entry_p,
                        "Exit_Price": exit_price,
                        "PnL_$": pnl,
                        "PnL_%": pnl_pct,
                        "Result": f"HOLD EXPIRED ({'WIN' if pnl >= 0 else 'LOSS'})"
                    })
                else:
                    pos["days_held"] += 1
                    still_active.append(pos)
            
            active_positions = still_active

            # ب. البحث عن إشارات دخول جديدة اليوم
            # للتبسيط وعدم توزيع رأس المال بشكل مفرط، نخصص حد أقصى 3 صفقات متزامنة في المحفظة
            max_simultaneous_positions = 3
            available_slots = max_simultaneous_positions - len(active_positions)
            
            signals_today = []
            
            if available_slots > 0:
                for sym in available_symbols:
                    # تجنب تكرار شراء سهم نمتلكه بالفعل
                    if any(p["symbol"] == sym for p in active_positions):
                        continue
                        
                    try:
                        # جلب تاريخ السهم حتى اليوم الحالي فقط لمنع الانحياز المستقبلي
                        stock_hist = df_hist.loc[sym].loc[:current_date]
                        if len(stock_hist) < 6:
                            continue
                            
                        # تصفية الفلوت والسعر
                        price_today = float(stock_hist['close'].iloc[-1])
                        # تضمين الأسهم الرخيصة جداً بناءً على طلب أبو فيصل المحدث (0.1$ - 10$)
                        if price_today < 0.1 or price_today > 10.0:
                            continue
                            
                        f_shares = float_map.get(sym, 10000000.0)
                        if f_shares > 15000000.0: # فلوت منخفض
                            continue

                        # تطبيق خوارزمية التجميع الصامت التاريخية
                        if strategy_type == "ACCUMULATION":
                            ticker_df = stock_hist.tail(5)
                            close_prev = ticker_df['close'].iloc[:-1]
                            max_p = close_prev.max()
                            min_p = close_prev.min()
                            mean_p = close_prev.mean()
                            
                            volatility = ((max_p - min_p) / mean_p) * 100
                            is_consolidating = volatility <= 4.0
                            
                            avg_vol = ticker_df['volume'].iloc[:-1].mean()
                            today_vol = ticker_df['volume'].iloc[-1]
                            volume_multiplier = today_vol / avg_vol if avg_vol > 0 else 1.0
                            is_vol_spike = volume_multiplier >= 4.0
                            
                            change_target = abs((ticker_df['close'].iloc[-1] - ticker_df['close'].iloc[-2]) / ticker_df['close'].iloc[-2]) * 100
                            is_price_stable = change_target <= 3.5
                            
                            if is_consolidating and is_vol_spike and is_price_stable:
                                signals_today.append((sym, price_today))
                                
                        # تطبيق خوارزمية الاختراق واليقين التاريخية (مبسطة للشموع اليومية)
                        elif strategy_type == "BREAKOUT":
                            # نتحقق من شروط الاختراق الأساسية لليقين:
                            # 1. السعر أعلى من متوسط 20 يوم
                            # 2. حجم التداول اليوم أعلى من متوسط 20 يوم بمعدل 2.0x فما فوق
                            # 3. السعر صعد اليوم بأكثر من 4%
                            if len(stock_hist) < 21:
                                continue
                            sma_20 = stock_hist['close'].tail(20).mean()
                            vol_avg_20 = stock_hist['volume'].tail(20).mean()
                            price_today = float(stock_hist['close'].iloc[-1])
                            price_prev = float(stock_hist['close'].iloc[-2])
                            vol_today = float(stock_hist['volume'].iloc[-1])
                            
                            is_above_sma = price_today > sma_20
                            is_vol_breakout = vol_today >= vol_avg_20 * 2.0
                            is_price_surge = ((price_today - price_prev) / price_prev) * 100 >= 4.0
                            
                            if is_above_sma and is_vol_breakout and is_price_surge:
                                signals_today.append((sym, price_today))
                    except:
                        continue

            # ج. تنفيذ الدخول في الصفقات الجديدة
            # نقسم الكاش المتاح للفرع بالتساوي بين عدد الصفقات المتاحة
            if signals_today and available_slots > 0:
                # نأخذ أفضل الفرص بناء على حجم السيولة اليوم
                signals_today = signals_today[:available_slots]
                allocation_per_trade = current_capital / max_simultaneous_positions
                
                for sym, price in signals_today:
                    if current_capital >= allocation_per_trade:
                        qty = allocation_per_trade / price
                        current_capital -= allocation_per_trade
                        active_positions.append({
                            "symbol": sym,
                            "entry_price": price,
                            "qty": qty,
                            "entry_date": current_date_str,
                            "days_held": 0,
                            "strategy": strategy_type
                        })
            
            # د. حساب تقييم المحفظة نهاية اليوم (السيولة + القيمة السوقية للأسهم المفتوحة)
            portfolio_value = current_capital
            for pos in active_positions:
                sym = pos["symbol"]
                try:
                    current_price = float(df_hist.loc[sym].loc[current_date]["close"])
                except:
                    current_price = pos["entry_price"]
                portfolio_value += (current_price * pos["qty"])
                
            equity_curve.append({
                "Date": current_date_str,
                "Capital": portfolio_value
            })

        # 5. حساب الإحصائيات الإجمالية للاختبار التاريخي
        total_trades = len(trades)
        if total_trades > 0:
            winning_trades = [t for t in trades if t["PnL_$"] > 0]
            losing_trades = [t for t in trades if t["PnL_$"] <= 0]
            win_rate = (len(winning_trades) / total_trades) * 100
            
            total_gains = sum([t["PnL_$"] for t in winning_trades])
            total_losses = abs(sum([t["PnL_$"] for t in losing_trades]))
            profit_factor = total_gains / total_losses if total_losses > 0 else total_gains
            
            # حساب أقصى تراجع (Max Drawdown)
            cap_series = pd.Series([e["Capital"] for e in equity_curve])
            cum_max = cap_series.cummax()
            drawdowns = (cap_series - cum_max) / cum_max * 100
            max_drawdown = drawdowns.min()
            
            final_wealth = equity_curve[-1]["Capital"]
            net_return_pct = ((final_wealth - initial_capital) / initial_capital) * 100
        else:
            win_rate = 0.0
            profit_factor = 1.0
            max_drawdown = 0.0
            final_wealth = initial_capital
            net_return_pct = 0.0

        return {
            "total_trades": total_trades,
            "win_rate_pct": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown_pct": max_drawdown,
            "initial_capital": initial_capital,
            "final_wealth": final_wealth,
            "net_return_pct": net_return_pct,
            "trades": trades,
            "equity_curve": equity_curve
        }
