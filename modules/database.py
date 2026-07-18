import sqlite3

DB_NAME = "database/investment.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL,
        company TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()