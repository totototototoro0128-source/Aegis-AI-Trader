from modules.database import get_connection


def add_stock(code: str, company: str):
    """監視銘柄を追加"""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO watchlist (code, company)
        VALUES (?, ?)
        """,
        (code, company),
    )

    conn.commit()
    conn.close()


def get_stocks():
    """監視銘柄一覧を取得"""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, code, company
        FROM watchlist
        ORDER BY code
        """
    )

    rows = cur.fetchall()

    conn.close()

    return rows


def delete_stock(stock_id: int):
    """監視銘柄を削除"""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        DELETE FROM watchlist
        WHERE id = ?
        """,
        (stock_id,),
    )

    conn.commit()
    conn.close()