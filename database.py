# module: database.py
import sqlite3
from datetime import datetime, timedelta

class QuantDatabase:
    def __init__(self, db_path="quant_platform.db"):
        self.db_path = db_path
        self.initialize_tables()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = OFF")
        conn.execute("PRAGMA temp_store = MEMORY")
        return conn

    def initialize_tables(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # جدول المحفظة الافتراضية (المراكز المفتوحة)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio (
                    symbol TEXT PRIMARY KEY,
                    quantity REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    entry_time TEXT NOT NULL
                )
            """)
            
            # جدول سجل العمليات والصفقات المنفذة
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL, -- BUY / SELL
                    symbol TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            # جدول الرصيد النقدي الافتراضي (Cash)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account_balance (
                    id INTEGER PRIMARY KEY,
                    cash REAL NOT NULL
                )
            """)
            
            # جدول منع تكرار الإشعارات والتنبيهات
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sent_alerts (
                    symbol TEXT PRIMARY KEY,
                    sent_at TEXT NOT NULL
                )
            """)
            
            # جدول أرشيف التنبيهات التاريخية للتداول
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    sent_at TEXT NOT NULL,
                    price REAL NOT NULL,
                    score REAL NOT NULL,
                    alert_type TEXT NOT NULL,
                    session TEXT,
                    target_percent REAL,
                    max_price_reached REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'PENDING'
                )
            """)
            
            # محاولة إضافة الأعمدة الجديدة في حال وجود الجدول مسبقاً لمنع أخطاء SQLite
            try:
                cursor.execute("ALTER TABLE alerts_history ADD COLUMN session TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE alerts_history ADD COLUMN target_percent REAL")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE alerts_history ADD COLUMN max_price_reached REAL DEFAULT 0.0")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE alerts_history ADD COLUMN status TEXT DEFAULT 'PENDING'")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE alerts_history ADD COLUMN initial_change REAL DEFAULT 0.0")
            except:
                pass
            
            # الجداول الجديدة لتدقيق وتعميق الذكاء الاصطناعي
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_utc TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    features BLOB NOT NULL,
                    score REAL NOT NULL,
                    persisted INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS labels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER NOT NULL,
                    ts_label TEXT NOT NULL,
                    outcome INTEGER NOT NULL,
                    price_start REAL,
                    price_end REAL,
                    FOREIGN KEY(signal_id) REFERENCES signals(id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS models (
                    version INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    weights BLOB NOT NULL,
                    bias REAL,
                    n_samples INTEGER,
                    val_precision_topk REAL,
                    notes TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics_daily (
                    day TEXT PRIMARY KEY,
                    signals_total INTEGER,
                    signals_tp INTEGER,
                    precision_topk REAL,
                    avg_lead_time_days REAL,
                    avg_slippage REAL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    level TEXT,
                    message TEXT
                )
            """)

            # جدول سجلات أداء التحسين الذاتي للذكاء الاصطناعي
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS optimization_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    optimized_at TEXT NOT NULL,
                    missed_gainers TEXT,
                    fomo_threshold REAL,
                    gap_threshold REAL,
                    whale_threshold_ext REAL,
                    whale_threshold_reg REAL,
                    catch_rate REAL
                )
            """)
            
            # تهيئة الرصيد الافتراضي بـ 1000 دولار إذا لم يكن موجوداً
            cursor.execute("SELECT COUNT(*) FROM account_balance")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO account_balance (id, cash) VALUES (1, 1000.0)")
                
            conn.commit()

    def get_cash(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cash FROM account_balance WHERE id = 1")
            return cursor.fetchone()[0]

    def update_cash(self, amount):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE account_balance SET cash = ? WHERE id = 1", (amount,))
            conn.commit()

    def execute_buy(self, symbol, quantity, price):
        symbol = symbol.upper()
        cash = self.get_cash()
        cost = quantity * price
        
        if cost > cash:
            return False, f"⚠️ الرصيد النقدي غير كافٍ. التكلفة: {cost:.2f}$ | الرصيد المتاح: {cash:.2f}$"
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # التحقق مما إذا كان هناك مركز مفتوح مسبقاً في السهم
            cursor.execute("SELECT quantity, entry_price FROM portfolio WHERE symbol = ?", (symbol,))
            row = cursor.fetchone()
            
            if row:
                existing_qty, existing_price = row
                new_qty = existing_qty + quantity
                # متوسط سعر الدخول الجديد
                new_price = ((existing_qty * existing_price) + cost) / new_qty
                cursor.execute("""
                    UPDATE portfolio 
                    SET quantity = ?, entry_price = ?, entry_time = ? 
                    WHERE symbol = ?
                """, (new_qty, new_price, datetime.now().isoformat(), symbol))
            else:
                cursor.execute("""
                    INSERT INTO portfolio (symbol, quantity, entry_price, entry_time)
                    VALUES (?, ?, ?, ?)
                """, (symbol, quantity, price, datetime.now().isoformat()))
                
            # تسجيل العملية
            cursor.execute("""
                INSERT INTO transactions (type, symbol, quantity, price, timestamp)
                VALUES ('BUY', ?, ?, ?, ?)
            """, (symbol, quantity, price, datetime.now().isoformat()))
            
            conn.commit()
            
        self.update_cash(cash - cost)
        return True, f"✅ تم شراء {quantity} سهم من {symbol} بنجاح بسعر {price:.4f}$ للسهم."

    def execute_sell(self, symbol, quantity, price):
        symbol = symbol.upper()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT quantity, entry_price FROM portfolio WHERE symbol = ?", (symbol,))
            row = cursor.fetchone()
            
            if not row or row[0] < quantity:
                qty_owned = row[0] if row else 0.0
                return False, f"⚠️ لا تملك كمية كافية للبيع. الكمية المملوكة من {symbol}: {qty_owned} سهم."
                
            existing_qty, entry_price = row
            new_qty = existing_qty - quantity
            
            if new_qty == 0:
                cursor.execute("DELETE FROM portfolio WHERE symbol = ?", (symbol,))
            else:
                cursor.execute("UPDATE portfolio SET quantity = ? WHERE symbol = ?", (new_qty, symbol))
                
            # تسجيل العملية
            cursor.execute("""
                INSERT INTO transactions (type, symbol, quantity, price, timestamp)
                VALUES ('SELL', ?, ?, ?, ?)
            """, (symbol, quantity, price, datetime.now().isoformat()))
            
            conn.commit()
            
        cash = self.get_cash()
        revenue = quantity * price
        self.update_cash(cash + revenue)
        
        pnl = (price - entry_price) * quantity
        pnl_percent = ((price - entry_price) / entry_price) * 100 if entry_price > 0 else 0.0
        pnl_icon = "🟢 ربح" if pnl >= 0 else "🔴 خسارة"
        
        return True, f"✅ تم بيع {quantity} سهم من {symbol} بسعر {price:.4f}$.\n💸 العائد النقدي: {revenue:.2f}$\n📊 النتيجة: {pnl_icon} بقيمة {pnl:+.2f}$ ({pnl_percent:+.2f}%)"

    def get_portfolio(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT symbol, quantity, entry_price, entry_time FROM portfolio")
            rows = cursor.fetchall()
            portfolio_list = []
            for r in rows:
                portfolio_list.append({
                    "symbol": r[0],
                    "quantity": r[1],
                    "entry_price": r[2],
                    "entry_time": r[3]
                })
            return portfolio_list

    def check_alert_sent_recently(self, symbol, hours=3):
        symbol = symbol.upper().strip()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sent_at FROM sent_alerts WHERE symbol = ?", (symbol,))
            row = cursor.fetchone()
            if not row:
                return False
            
            try:
                sent_time = datetime.fromisoformat(row[0])
                if datetime.now() - sent_time < timedelta(hours=hours):
                    return True
            except:
                pass
            return False

    def log_sent_alert(self, symbol):
        symbol = symbol.upper().strip()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sent_alerts (symbol, sent_at)
                VALUES (?, ?)
            """, (symbol, datetime.now().isoformat()))
            conn.commit()

    def log_alert_history(self, symbol, price, score, alert_type, session="REGULAR_SESSION", target_percent=12.0, status="PENDING", initial_change=0.0):
        symbol = symbol.upper().strip()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO alerts_history (symbol, sent_at, price, score, alert_type, session, target_percent, max_price_reached, status, initial_change)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, datetime.now().isoformat(), float(price), float(score), str(alert_type), str(session), float(target_percent), float(price), str(status), float(initial_change)))
            conn.commit()

    def get_alerts_history(self, limit=50):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT symbol, sent_at, price, score, alert_type, session, target_percent, max_price_reached, status, initial_change
                FROM alerts_history 
                ORDER BY sent_at DESC 
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [{
                "symbol": r[0],
                "sent_at": r[1],
                "price": r[2],
                "score": r[3],
                "alert_type": r[4],
                "session": r[5] if r[5] else "REGULAR_SESSION",
                "target_percent": r[6] if r[6] is not None else 12.0,
                "max_price_reached": r[7] if r[7] is not None else r[2],
                "status": r[8] if r[8] else "PENDING",
                "initial_change": r[9] if r[9] is not None else 0.0
            } for r in rows]

    def get_pending_alerts(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, symbol, price, target_percent, max_price_reached, status 
                FROM alerts_history 
                WHERE status = 'PENDING'
            """)
            rows = cursor.fetchall()
            return [{
                "id": r[0],
                "symbol": r[1],
                "price": r[2],
                "target_percent": r[3],
                "max_price_reached": r[4],
                "status": r[5]
            } for r in rows]

    def update_alert_status(self, alert_id, max_price, status):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE alerts_history 
                SET max_price_reached = ?, status = ? 
                WHERE id = ?
            """, (float(max_price), str(status), int(alert_id)))
            conn.commit()

    def save_model_weights(self, weights, bias, n_samples=0, val_precision=0.0, notes=""):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            blob = weights.astype('float32').tobytes()
            cursor.execute(
                "INSERT INTO models (created_at, weights, bias, n_samples, val_precision_topk, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), blob, float(bias), int(n_samples), float(val_precision), notes)
            )
            conn.commit()

    def load_latest_model_weights(self, num_features=6):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT weights, bias FROM models ORDER BY version DESC LIMIT 1")
                row = cursor.fetchone()
                if row:
                    import numpy as np
                    weights = np.frombuffer(row[0], dtype=np.float32)
                    bias = float(row[1])
                    return weights, bias
        except Exception as e:
            print(f"Error loading model weights: {e}")
        import numpy as np
        return np.zeros(num_features, dtype=np.float32), 0.0

    def calculate_platform_efficiency(self):
        """
        Calculate platform's overall win rate and early catch efficiency over closed alerts.
        - Win Rate: (SUCCESS alerts / closed alerts) * 100
        - Early Catch Rate: (alerts caught with initial_change <= 7.0% / total alerts) * 100
        - Overall Index: 0.6 * Win_Rate + 0.4 * Early_Catch_Rate
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get total closed alerts (SUCCESS or FAILED)
            cursor.execute("SELECT COUNT(*) FROM alerts_history WHERE status IN ('SUCCESS', 'FAILED')")
            closed_count = cursor.fetchone()[0]
            
            # Get success alerts
            cursor.execute("SELECT COUNT(*) FROM alerts_history WHERE status = 'SUCCESS'")
            success_count = cursor.fetchone()[0]
            
            # Get total alerts
            cursor.execute("SELECT COUNT(*) FROM alerts_history")
            total_count = cursor.fetchone()[0]
            
            # Get early catch count (caught when change <= 7.0% and > 0.0)
            cursor.execute("SELECT COUNT(*) FROM alerts_history WHERE initial_change <= 7.0 AND initial_change > 0.0")
            early_count = cursor.fetchone()[0]
            
            win_rate = (success_count / closed_count * 100.0) if closed_count > 0 else 0.0
            early_rate = (early_count / total_count * 100.0) if total_count > 0 else 0.0
            
            # If no data exists yet, we default to 0.0 to show accurate performance
            if total_count == 0:
                win_rate = 0.0
                early_rate = 0.0
                
            overall_index = 0.6 * win_rate + 0.4 * early_rate
            
            return {
                "total_alerts": total_count,
                "closed_alerts": closed_count,
                "success_alerts": success_count,
                "early_alerts": early_count,
                "win_rate": round(win_rate, 1),
                "early_rate": round(early_rate, 1),
                "overall_index": round(overall_index, 1)
            }

    def log_optimization_run(self, missed_gainers, fomo, gap, whale_ext, whale_reg, catch_rate):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO optimization_logs (optimized_at, missed_gainers, fomo_threshold, gap_threshold, whale_threshold_ext, whale_threshold_reg, catch_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (datetime.now().isoformat(), missed_gainers, fomo, gap, whale_ext, whale_reg, catch_rate))
            conn.commit()

    def update_heartbeat(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS system_status (key TEXT PRIMARY KEY, value TEXT)")
            cursor.execute("INSERT OR REPLACE INTO system_status (key, value) VALUES ('last_heartbeat', ?)", (datetime.now().isoformat(),))
            conn.commit()

    def get_last_heartbeat(self):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM system_status WHERE key = 'last_heartbeat'")
                row = cursor.fetchone()
                return row[0] if row else None
        except:
            return None

    def get_latest_optimization_run(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM optimization_logs ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "optimized_at": row[1],
                    "missed_gainers": row[2],
                    "fomo_threshold": row[3],
                    "gap_threshold": row[4],
                    "whale_threshold_ext": row[5],
                    "whale_threshold_reg": row[6],
                    "catch_rate": row[7]
                }
            return None


