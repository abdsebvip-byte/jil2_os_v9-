# module: database.py
import sqlite3
from datetime import datetime

class QuantDatabase:
    def __init__(self, db_path="quant_platform.db"):
        self.db_path = db_path
        self.initialize_tables()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

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
