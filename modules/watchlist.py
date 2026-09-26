from modules.database import get_connection
from modules.runtime_mode import is_public_site
import streamlit as st


def add_stock(code: str, company: str):
    """監視銘柄を追加"""
    if is_public_site():
        stocks = st.session_state.setdefault("public_watchlist", [])
        next_id = max((stock[0] for stock in stocks), default=0) + 1
        stocks.append((next_id, code, company))
        return
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
    if is_public_site():
        return sorted(st.session_state.setdefault("public_watchlist", []), key=lambda stock: stock[1])
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
    if is_public_site():
        st.session_state.public_watchlist = [
            stock for stock in st.session_state.setdefault("public_watchlist", [])
            if stock[0] != stock_id
        ]
        return
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
