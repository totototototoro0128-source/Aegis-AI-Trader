import sqlite3
from pathlib import Path

# databaseフォルダが無ければ作成
DB_DIR = Path("database")
DB_DIR.mkdir(exist_ok=True)

DB_NAME = DB_DIR / "investment.db"


def get_connection():
    """データベース接続を返す"""
    return sqlite3.connect(DB_NAME)


def init_db():
    """データベース初期化"""

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL,
        company TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()