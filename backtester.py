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
        from ml_classifier import QuantMLClassifier
        ml_classifier = QuantMLClassifier()
        
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

        # التأكد من إعادة بناء الفهرس المتعدد وتوحيد التواريخ
        try:
            df_hist = df_hist.reset_index()
            if 'symbol' not in df_hist.columns or 'date' not in df_hist.columns:
                return {"error": "فشل تنسيق البيانات التاريخية المسترجعة."}
            df_hist['date'] = pd.to_datetime(df_hist['date'], utc=True)
            df_hist = df_hist.set_index(['symbol', 'date']).sort_index()
        except Exception as e:
            print(f"Backtester: MultiIndex alignment warning: {str(e)}")

        # 3. استخلاص الفلوت ونسبة الشورت لكل سهم
        print("Backtester: Fetching float & short stats...")
        float_map = {}
        short_map = {}
        try:
            stats = ticker_batch.key_stats
            for sym in symbols:
                stat_info = stats.get(sym)
                float_shares = 10000000.0 # افتراضي 10 مليون في حال الغياب
                short_pct = 0.0
                if isinstance(stat_info, dict):
                    if stat_info.get("floatShares"):
                        float_shares = float(stat_info["floatShares"])
                    if stat_info.get("shortPercentOfFloat"):
                        short_pct = float(stat_info["shortPercentOfFloat"]) * 100.0
                float_map[sym] = float_shares
                short_map[sym] = short_pct
        except:
            for sym in symbols:
                float_map[sym] = 10000000.0
                short_map[sym] = 0.0

        # ترتيب البيانات حسب التواريخ
        try:
            if isinstance(df_hist.index, pd.MultiIndex):
                available_symbols = df_hist.index.levels[0]
                all_dates = sorted(list(set(df_hist.index.levels[1])))
            else:
                available_symbols = [symbols[0]] if symbols else []
                all_dates = sorted(list(set(df_hist.index)))
        except Exception as e:
            return {"error": f"فشل استخراج التواريخ ورموز الأسهم للاختبار: {str(e)}"}
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
                strat = pos["strategy"]
                target_pct = pos.get("target_percent", 12.0)
                target_mult = 1.0 + (target_pct / 100.0)
                
                # أ. قوانين خروج صفقات المضاربة اللحظية السريعة (تصفية نفس اليوم)
                if strat == "INTRADAY_SCALPING":
                    if high_t >= entry_p * target_mult:
                        exit_price = entry_p * target_mult
                        pnl = (exit_price - entry_p) * qty
                        current_capital += (exit_price * qty)
                        trades.append({
                            "Symbol": sym,
                            "Type": strat,
                            "Entry_Date": pos["entry_date"],
                            "Exit_Date": current_date_str,
                            "Entry_Price": entry_p,
                            "Exit_Price": exit_price,
                            "PnL_$": pnl,
                            "PnL_%": target_pct,
                            "Result": f"WIN (TP {target_pct}% Intraday)"
                        })
                    elif low_t <= entry_p * 0.95:
                        exit_price = entry_p * 0.95
                        pnl = (exit_price - entry_p) * qty
                        current_capital += (exit_price * qty)
                        trades.append({
                            "Symbol": sym,
                            "Type": strat,
                            "Entry_Date": pos["entry_date"],
                            "Exit_Date": current_date_str,
                            "Entry_Price": entry_p,
                            "Exit_Price": exit_price,
                            "PnL_$": pnl,
                            "PnL_%": -5.0,
                            "Result": "LOSS (SL 5% Intraday)"
                        })
                    else:
                        # إغلاق إجباري نهاية اليوم لمنع المخاطرة الليلية
                        exit_price = close_t
                        pnl = (exit_price - entry_p) * qty
                        current_capital += (exit_price * qty)
                        pnl_pct = ((exit_price - entry_p) / entry_p) * 100
                        is_win = exit_price >= entry_p * target_mult
                        trades.append({
                            "Symbol": sym,
                            "Type": strat,
                            "Entry_Date": pos["entry_date"],
                            "Exit_Date": current_date_str,
                            "Entry_Price": entry_p,
                            "Exit_Price": exit_price,
                            "PnL_$": pnl,
                            "PnL_%": pnl_pct,
                            "Result": f"CLOSE EXPIRED ({'WIN' if is_win else 'LOSS'})"
                        })
                
                # ب. قوانين صفقات سوينغ الاختراقات والتجميع (تحتاج لعدة أيام)
                else:
                    if high_t >= entry_p * target_mult:
                        exit_price = entry_p * target_mult
                        pnl = (exit_price - entry_p) * qty
                        current_capital += (exit_price * qty)
                        trades.append({
                            "Symbol": sym,
                            "Type": strat,
                            "Entry_Date": pos["entry_date"],
                            "Exit_Date": current_date_str,
                            "Entry_Price": entry_p,
                            "Exit_Price": exit_price,
                            "PnL_$": pnl,
                            "PnL_%": target_pct,
                            "Result": f"WIN (TP {target_pct}%)"
                        })
                    elif low_t <= entry_p * 0.95:
                        exit_price = entry_p * 0.95
                        pnl = (exit_price - entry_p) * qty
                        current_capital += (exit_price * qty)
                        trades.append({
                            "Symbol": sym,
                            "Type": strat,
                            "Entry_Date": pos["entry_date"],
                            "Exit_Date": current_date_str,
                            "Entry_Price": entry_p,
                            "Exit_Price": exit_price,
                            "PnL_$": pnl,
                            "PnL_%": -5.0,
                            "Result": "LOSS (SL 5%)"
                        })
                    elif pos["days_held"] >= 9: # اليوم العاشر
                        exit_price = close_t
                        pnl = (exit_price - entry_p) * qty
                        current_capital += (exit_price * qty)
                        pnl_pct = ((exit_price - entry_p) / entry_p) * 100
                        is_win = exit_price >= entry_p * target_mult
                        trades.append({
                            "Symbol": sym,
                            "Type": strat,
                            "Entry_Date": pos["entry_date"],
                            "Exit_Date": current_date_str,
                            "Entry_Price": entry_p,
                            "Exit_Price": exit_price,
                            "PnL_$": pnl,
                            "PnL_%": pnl_pct,
                            "Result": f"HOLD EXPIRED ({'WIN' if is_win else 'LOSS'})"
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
                    try:
                        # تطبيق خوارزمية التجميع الصامت التاريخية المحدثة
                        if strategy_type == "ACCUMULATION":
                            ticker_df = stock_hist.tail(10) # فحص تماسك 10 أيام
                            close_prev = ticker_df['close'].iloc[:-1]
                            max_p = close_prev.max()
                            min_p = close_prev.min()
                            mean_p = close_prev.mean()
                            
                            volatility = ((max_p - min_p) / mean_p) * 100
                            is_consolidating = volatility <= 6.0 # تذبذب تجميع ضيق
                            
                            avg_vol_20 = stock_hist['volume'].tail(20).mean()
                            today_vol = float(stock_hist['volume'].iloc[-1])
                            volume_multiplier = today_vol / avg_vol_20 if avg_vol_20 > 0 else 1.0
                            is_vol_spike = volume_multiplier >= 4.0 # زيادة حجم التداول التاريخية المحدثة (4 أضعاف)
                            
                            pct_change = ((price_today - float(stock_hist['close'].iloc[-2])) / float(stock_hist['close'].iloc[-2])) * 100
                            is_price_stable = abs(pct_change) <= 3.5 # استقرار السعر اليوم للتجميع الصامت
                            
                            if is_consolidating and is_vol_spike and is_price_stable:
                                try:
                                    close_tail = stock_hist['close'].tail(10)
                                    volatility_10d = (close_tail.std() / close_tail.mean() * 100.0) if close_tail.mean() > 0 else 0.0
                                    
                                    prev_vol_avg = stock_hist['volume'].iloc[-21:-1].mean()
                                    prev_rvol = (stock_hist['volume'].iloc[-2] / prev_vol_avg) if prev_vol_avg > 0 else 1.0
                                    
                                    prev_price = float(stock_hist['close'].iloc[-2])
                                    prev_prev_price = float(stock_hist['close'].iloc[-3]) if len(stock_hist) >= 3 else prev_price
                                    prev_change = ((prev_price - prev_prev_price) / prev_prev_price * 100.0) if prev_prev_price > 0 else 0.0
                                    
                                    f_shares_m = float_map.get(sym, 10000000.0) / 1000000.0
                                    short_pct = short_map.get(sym, 0.0)
                                    
                                    prob = ml_classifier.predict_probability(
                                        price_today, pct_change, volume_multiplier, volatility_10d, 
                                        prev_rvol, prev_change, f_shares_m, short_pct
                                    )
                                    if prob >= 60.0:
                                        signals_today.append((sym, price_today, prob))
                                except:
                                    pass
                                
                        # تطبيق خوارزمية الاختراق واليقين المحدثة (مع فلتر مقاومة الذيول المصيدة)
                        elif strategy_type in ["BREAKOUT", "INTRADAY_SCALPING"]:
                            if len(stock_hist) < 21:
                                continue
                            sma_20 = stock_hist['close'].tail(20).mean()
                            vol_avg_20 = stock_hist['volume'].tail(20).mean()
                            price_prev = float(stock_hist['close'].iloc[-2])
                            vol_today = float(stock_hist['volume'].iloc[-1])
                            
                            is_above_sma = price_today > sma_20
                            is_vol_breakout = vol_today >= vol_avg_20 * 4.0 # اختراق حجم قوي محدث (4 أضعاف)
                            pct_change = ((price_today - price_prev) / price_prev) * 100
                            is_price_surge = pct_change >= 4.0 # صعود حقيقي
                            
                            # فلتر الإغلاق قرب القمة للتخلص من شمعة الذيل العلوي الطويل (المصيدة البينية)
                            high_today = float(stock_hist['high'].iloc[-1])
                            low_today = float(stock_hist['low'].iloc[-1])
                            range_today = high_today - low_today
                            close_from_high = high_today - price_today
                            is_close_near_high = (close_from_high <= range_today * 0.20) if range_today > 0 else False
                            
                            if is_above_sma and is_vol_breakout and is_price_surge and is_close_near_high:
                                try:
                                    close_tail = stock_hist['close'].tail(10)
                                    volatility_10d = (close_tail.std() / close_tail.mean() * 100.0) if close_tail.mean() > 0 else 0.0
                                    
                                    rvol = vol_today / vol_avg_20 if vol_avg_20 > 0 else 1.0
                                    prev_vol_avg = stock_hist['volume'].iloc[-21:-1].mean()
                                    prev_rvol = (stock_hist['volume'].iloc[-2] / prev_vol_avg) if prev_vol_avg > 0 else 1.0
                                    
                                    prev_price = float(stock_hist['close'].iloc[-2])
                                    prev_prev_price = float(stock_hist['close'].iloc[-3]) if len(stock_hist) >= 3 else prev_price
                                    prev_change = ((prev_price - prev_prev_price) / prev_prev_price * 100.0) if prev_prev_price > 0 else 0.0
                                    
                                    f_shares_m = float_map.get(sym, 10000000.0) / 1000000.0
                                    short_pct = short_map.get(sym, 0.0)
                                    
                                    prob = ml_classifier.predict_probability(
                                        price_today, pct_change, rvol, volatility_10d, 
                                        prev_rvol, prev_change, f_shares_m, short_pct
                                    )
                                    if prob >= 60.0:
                                        signals_today.append((sym, price_today, prob))
                                except:
                                    pass
                    except:
                        continue
 
            # ج. تنفيذ الدخول في الصفقات الجديدة
            # نقسم القيمة الكلية الحالية للمحفظة بالتساوي للحصول على حجم صفقة موحد
            if signals_today and available_slots > 0:
                signals_today = signals_today[:available_slots]
                
                # حساب القيمة الإجمالية للمحفظة لإعادة الاستثمار الكامل
                portfolio_value = current_capital
                for pos in active_positions:
                    sym_pos = pos["symbol"]
                    try:
                        current_price = float(df_hist.loc[sym_pos].loc[current_date]["close"])
                    except:
                        current_price = pos["entry_price"]
                    portfolio_value += (current_price * pos["qty"])
                
                allocation_per_trade = portfolio_value / max_simultaneous_positions
                
                from intelligence import QuantIntelligence
                intel = QuantIntelligence()
                
                for sym, price, prob in signals_today:
                    if current_capital >= allocation_per_trade:
                        qty = allocation_per_trade / price
                        current_capital -= allocation_per_trade
                        
                        # حساب الهدف ديناميكياً بناءً على نقاط التطابق التاريخية لليوم الحالي
                        try:
                            day_candle = df_hist.loc[sym].loc[current_date]
                            quote_dict = {
                                "regularMarketPrice": price,
                                "regularMarketChangePercent": 10.0, 
                                "regularMarketOpen": float(day_candle.get("open") or price),
                                "regularMarketPreviousClose": float(day_candle.get("close") or price) / 1.10,
                                "regularMarketVolume": float(day_candle.get("volume") or 100000.0),
                                "averageDailyVolume3Month": float(day_candle.get("volume") or 100000.0) / 2.0
                            }
                            score, _, _, _, _ = intel.calculate_7_layer_conviction(quote_dict, "REGULAR_SESSION", {})
                            target_pct = intel.calculate_dynamic_target(score, prob)
                        except:
                            target_pct = 12.0
                            
                        active_positions.append({
                            "symbol": sym,
                            "entry_price": price,
                            "qty": qty,
                            "entry_date": current_date_str,
                            "days_held": 0,
                            "strategy": strategy_type,
                            "target_percent": target_pct
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
