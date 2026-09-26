"""ペーパートレード状態のSQLite永続化。"""

import json
from datetime import datetime

from modules.database import get_connection


ACCOUNT_ID = "fx_demo"


def init_repository():
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS paper_accounts (
            account_id TEXT PRIMARY KEY,
            initial_capital REAL NOT NULL,
            realized_pnl REAL NOT NULL,
            daily_realized_pnl REAL NOT NULL,
            peak_equity REAL NOT NULL,
            running INTEGER NOT NULL,
            mode TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS paper_positions (
            account_id TEXT NOT NULL,
            pair TEXT NOT NULL,
            payload TEXT NOT NULL,
            PRIMARY KEY (account_id, pair)
        );
        CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS paper_equity_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT NOT NULL,
            time TEXT NOT NULL,
            equity REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS paper_runtime (
            account_id TEXT PRIMARY KEY,
            last_bar_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS paper_symbols (
            account_id TEXT NOT NULL,
            label TEXT NOT NULL,
            symbol TEXT NOT NULL,
            enabled INTEGER NOT NULL,
            PRIMARY KEY (account_id, label)
        );
        """
    )
    conn.commit()
    conn.close()


def load_state(account_id=ACCOUNT_ID):
    init_repository()
    conn = get_connection()
    cur = conn.cursor()
    account = cur.execute(
        "SELECT initial_capital, realized_pnl, daily_realized_pnl, peak_equity, running, mode "
        "FROM paper_accounts WHERE account_id = ?",
        (account_id,),
    ).fetchone()
    if account is None:
        conn.close()
        return None

    positions = {
        pair: json.loads(payload)
        for pair, payload in cur.execute(
            "SELECT pair, payload FROM paper_positions WHERE account_id = ?",
            (account_id,),
        ).fetchall()
    }
    trades = [
        json.loads(row[0])
        for row in cur.execute(
            "SELECT payload FROM paper_trades WHERE account_id = ? ORDER BY id DESC LIMIT 500",
            (account_id,),
        ).fetchall()
    ]
    equity_history = [
        {"time": row[0], "equity": row[1]}
        for row in cur.execute(
            "SELECT time, equity FROM paper_equity_history WHERE account_id = ? ORDER BY id LIMIT 500",
            (account_id,),
        ).fetchall()
    ]
    runtime = cur.execute(
        "SELECT last_bar_json FROM paper_runtime WHERE account_id = ?",
        (account_id,),
    ).fetchone()
    conn.close()
    today = datetime.now().strftime("%Y-%m-%d")
    daily_realized_pnl = sum(
        trade.get("損益", 0.0)
        for trade in trades
        if trade.get("時刻", "").startswith(today)
    )
    return {
        "running": bool(account[4]),
        "initial_capital": account[0],
        "capital": account[0],
        "realized_pnl": account[1],
        "daily_realized_pnl": daily_realized_pnl,
        "daily_pnl_date": today,
        "peak_equity": account[3],
        "mode": account[5],
        "positions": positions,
        "trades": trades,
        "equity_history": equity_history,
        "last_bar": json.loads(runtime[0]) if runtime else {},
    }


def save_state(state, account_id=ACCOUNT_ID):
    init_repository()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO paper_accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(account_id) DO UPDATE SET
            initial_capital=excluded.initial_capital,
            realized_pnl=excluded.realized_pnl,
            daily_realized_pnl=excluded.daily_realized_pnl,
            peak_equity=excluded.peak_equity,
            running=excluded.running,
            mode=excluded.mode,
            updated_at=excluded.updated_at
        """,
        (
            account_id,
            state["initial_capital"],
            state["realized_pnl"],
            state.get("daily_realized_pnl", 0.0),
            state.get("peak_equity", state["initial_capital"]),
            int(state["running"]),
            state.get("mode", "標準"),
            datetime.now().isoformat(),
        ),
    )
    cur.execute("DELETE FROM paper_positions WHERE account_id = ?", (account_id,))
    cur.executemany(
        "INSERT INTO paper_positions VALUES (?, ?, ?)",
        [(account_id, pair, json.dumps(position, ensure_ascii=False)) for pair, position in state["positions"].items()],
    )
    cur.execute("DELETE FROM paper_trades WHERE account_id = ?", (account_id,))
    cur.executemany(
        "INSERT INTO paper_trades(account_id, payload) VALUES (?, ?)",
        [(account_id, json.dumps(trade, ensure_ascii=False)) for trade in reversed(state["trades"][-500:])],
    )
    cur.execute("DELETE FROM paper_equity_history WHERE account_id = ?", (account_id,))
    cur.executemany(
        "INSERT INTO paper_equity_history(account_id, time, equity) VALUES (?, ?, ?)",
        [(account_id, item["time"], item["equity"]) for item in state["equity_history"][-500:]],
    )
    cur.execute(
        "INSERT INTO paper_runtime VALUES (?, ?) ON CONFLICT(account_id) DO UPDATE SET last_bar_json=excluded.last_bar_json",
        (account_id, json.dumps(state["last_bar"])),
    )
    conn.commit()
    conn.close()


def reset_state(state, account_id=ACCOUNT_ID):
    conn = get_connection()
    cur = conn.cursor()
    for table in ("paper_accounts", "paper_positions", "paper_trades", "paper_equity_history", "paper_runtime"):
        cur.execute(f"DELETE FROM {table} WHERE account_id = ?", (account_id,))
    conn.commit()
    conn.close()
    save_state(state, account_id)


def load_symbol_settings(account_id):
    """口座ごとの監視銘柄と自動取引の有効状態を読み込む。"""

    init_repository()
    conn = get_connection()
    rows = conn.execute(
        "SELECT label, symbol, enabled FROM paper_symbols WHERE account_id = ? ORDER BY rowid",
        (account_id,),
    ).fetchall()
    conn.close()
    return ({label: symbol for label, symbol, _ in rows}, [label for label, _, enabled in rows if enabled])


def save_symbol_settings(account_id, symbols, enabled_labels):
    """監視銘柄カタログと自動取引対象をまとめて保存する。"""

    init_repository()
    enabled = set(enabled_labels)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM paper_symbols WHERE account_id = ?", (account_id,))
    cur.executemany(
        "INSERT INTO paper_symbols(account_id, label, symbol, enabled) VALUES (?, ?, ?, ?)",
        [(account_id, label, symbol, int(label in enabled)) for label, symbol in symbols.items()],
    )
    conn.commit()
    conn.close()
