import sqlite3

def add_whale_table():
    conn = sqlite3.connect('quant_platform.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS whale_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            ts TEXT NOT NULL,
            price REAL,
            change_pct REAL,
            rvol REAL,
            market_cap REAL,
            reason TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("Whale table created successfully.")

if __name__ == "__main__":
    add_whale_table()
