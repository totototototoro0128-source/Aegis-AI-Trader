"""日本株の自動取引ペーパーデモ。"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from modules.trading.repository import (
    load_state,
    load_symbol_settings,
    reset_state,
    save_state,
    save_symbol_settings,
)
from modules.trading.risk import calculate_position_notional, may_open_position
from modules.yfinance_config import configure_yfinance_cache


configure_yfinance_cache()

ACCOUNT_ID = "jp_stock_demo"
INITIAL_CAPITAL = 1_000_000.0
STOCKS = {
    "7203 トヨタ": "7203.T",
    "6758 ソニーG": "6758.T",
    "9984 ソフトバンクG": "9984.T",
    "8306 三菱UFJ": "8306.T",
}
STOCK_MODES = {
    "慎重": {"risk_per_trade": 0.0025, "leverage_cap": 1.0, "max_positions": 1, "entry_score": 2, "stop_loss": 0.010, "take_profit": 0.020, "daily_loss_limit": 0.01, "max_drawdown": 0.03, "slippage_bps": 2},
    "標準": {"risk_per_trade": 0.0050, "leverage_cap": 1.0, "max_positions": 2, "entry_score": 1, "stop_loss": 0.015, "take_profit": 0.030, "daily_loss_limit": 0.02, "max_drawdown": 0.05, "slippage_bps": 4},
    "積極": {"risk_per_trade": 0.0100, "leverage_cap": 1.0, "max_positions": 3, "entry_score": 1, "stop_loss": 0.020, "take_profit": 0.040, "daily_loss_limit": 0.03, "max_drawdown": 0.08, "slippage_bps": 8},
}


def _initial_state():
    now = datetime.now()
    return {
        "running": False,
        "initial_capital": INITIAL_CAPITAL,
        "capital": INITIAL_CAPITAL,
        "realized_pnl": 0.0,
        "daily_realized_pnl": 0.0,
        "daily_pnl_date": now.strftime("%Y-%m-%d"),
        "peak_equity": INITIAL_CAPITAL,
        "mode": "標準",
        "positions": {},
        "trades": [],
        "last_bar": {},
        "equity_history": [{"time": now.isoformat(), "equity": INITIAL_CAPITAL}],
    }


def _state():
    if "stock_paper_trading" not in st.session_state:
        st.session_state.stock_paper_trading = load_state(ACCOUNT_ID) or _initial_state()
    state = st.session_state.stock_paper_trading
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("daily_pnl_date") != today:
        state["daily_realized_pnl"] = 0.0
        state["daily_pnl_date"] = today
    return state


def _market_open():
    now = datetime.now(ZoneInfo("Asia/Tokyo"))
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 9 * 60 <= minutes < 11 * 60 + 30 or 12 * 60 + 30 <= minutes < 15 * 60 + 30


@st.cache_data(ttl=55, show_spinner=False)
def _stock_data(symbol):
    history = yf.Ticker(symbol).history(period="1mo", interval="15m").dropna()
    if len(history) < 30:
        return None
    close = history["Close"]
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rsi = 100 - (100 / (1 + gain / loss))
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    trend = 1 if ema9.iloc[-1] > ema21.iloc[-1] else -1
    momentum = 1 if rsi.iloc[-1] < 35 else -1 if rsi.iloc[-1] > 65 else 0
    return {"price": float(close.iloc[-1]), "bar": history.index[-1].isoformat(), "rsi": float(rsi.iloc[-1]), "score": trend + momentum}


@st.cache_data(ttl=300, show_spinner=False)
def _lookup_stock(code):
    """東証コードを検証し、画面表示用の会社名を返す。"""

    symbol = f"{code}.T"
    ticker = yf.Ticker(symbol)
    history = ticker.history(period="5d", interval="1d").dropna()
    if history.empty:
        return None
    try:
        info = ticker.info
        name = info.get("shortName") or info.get("longName") or code
    except Exception:
        name = code
    return f"{code} {name}", symbol


@st.cache_data(ttl=55, show_spinner=False)
def _stock_chart_data(symbol):
    history = yf.Ticker(symbol).history(period="1mo", interval="15m").dropna()
    if history.empty:
        return history
    history = history.copy()
    history["EMA9"] = history["Close"].ewm(span=9, adjust=False).mean()
    history["EMA21"] = history["Close"].ewm(span=21, adjust=False).mean()
    return history.tail(130)


def _stock_figure(label, symbol, position=None, sessions=1):
    history = _stock_chart_data(symbol)
    figure = go.Figure()
    if not history.empty:
        trading_dates = pd.Index(history.index.date)
        visible_dates = set(pd.unique(trading_dates)[-sessions:])
        history = history[[date in visible_dates for date in trading_dates]]
        # 休場時間を詰めてローソク足を等間隔にする。
        chart_x = history.index.strftime("%m/%d %H:%M")
        figure.add_trace(go.Candlestick(
            x=chart_x, open=history["Open"], high=history["High"],
            low=history["Low"], close=history["Close"], name=label,
            increasing_line_color="#62e6ac", decreasing_line_color="#ff7186",
            increasing_line_width=2, decreasing_line_width=2,
        ))
        figure.add_trace(go.Scatter(x=chart_x, y=history["EMA9"], name="EMA9", line={"color": "#53c7f0", "width": 2}))
        figure.add_trace(go.Scatter(x=chart_x, y=history["EMA21"], name="EMA21", line={"color": "#f2c94c", "width": 2}))
        last_price = float(history["Close"].iloc[-1])
        figure.add_hline(
            y=last_price,
            line_dash="dot",
            line_color="#8b98a5",
            annotation_text=f"現在 ¥{last_price:,.1f}",
            annotation_position="bottom right",
        )
    if position:
        figure.add_hline(y=position["entry_price"], line_dash="dot", line_color="#f2c94c", annotation_text="建値")
    figure.update_layout(
        title=f"{label} / 15分足・直近{sessions}営業日", template="plotly_dark", height=500,
        margin={"l": 20, "r": 70, "t": 70, "b": 30},
        hovermode="x unified",
        plot_bgcolor="#0b1017",
        paper_bgcolor="#0b1017",
        font={"color": "#e6edf3", "size": 13},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        xaxis={
            "type": "category",
            "nticks": 12,
            "showgrid": False,
            "rangeslider": {"visible": False},
            "title": "取引時刻（休場時間を除外）",
        },
        yaxis={
            "side": "right",
            "tickprefix": "¥",
            "tickformat": ",.1f",
            "gridcolor": "#26313d",
            "fixedrange": False,
        },
    )
    return figure


def _symbols():
    if "stock_auto_symbols" not in st.session_state:
        catalog, enabled = load_symbol_settings(ACCOUNT_ID)
        if not catalog:
            catalog, enabled = dict(STOCKS), list(STOCKS)
            save_symbol_settings(ACCOUNT_ID, catalog, enabled)
        st.session_state.stock_auto_symbols = catalog
        st.session_state.stock_universe = enabled
    return st.session_state.stock_auto_symbols


def _execution_price(mid_price, action, slippage_bps):
    adjustment = mid_price * slippage_bps / 10_000
    return mid_price + adjustment if action == "BUY" else mid_price - adjustment


def _close(state, key, mid_price, reason, config):
    position = state["positions"].pop(key)
    price = _execution_price(mid_price, "SELL", config["slippage_bps"])
    pnl = (price - position["entry_price"]) * position["shares"]
    cost = mid_price * config["slippage_bps"] / 10_000 * position["shares"]
    state["realized_pnl"] += pnl
    state["daily_realized_pnl"] += pnl
    state["trades"].insert(0, {"時刻": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "銘柄": key, "売買": "SELL", "株数": position["shares"], "価格": round(price, 1), "損益": round(pnl), "コスト": round(cost), "理由": reason})


def _evaluate(state, mode, universe, symbols):
    config = STOCK_MODES[mode]
    quotes = {}
    market_open = _market_open()
    # 選択解除後も、既に保有している銘柄の決済監視は継続する。
    monitored = list(dict.fromkeys([*universe, *state["positions"].keys()]))
    for key in monitored:
        data = _stock_data(symbols[key])
        if data is None:
            continue
        quotes[key] = data
        if not market_open:
            continue
        if key in state["positions"]:
            position = state["positions"][key]
            return_rate = data["price"] / position["entry_price"] - 1
            if return_rate <= -config["stop_loss"]:
                _close(state, key, data["price"], "ストップロス", config)
            elif return_rate >= config["take_profit"]:
                _close(state, key, data["price"], "利益確定", config)
            elif data["score"] < 0:
                _close(state, key, data["price"], "シグナル反転", config)
        if state["last_bar"].get(key) == data["bar"]:
            continue
        state["last_bar"][key] = data["bar"]
        equity = state["initial_capital"] + state["realized_pnl"]
        if key in universe and key not in state["positions"] and may_open_position(state, config, equity) and data["score"] >= config["entry_score"]:
            notional = calculate_position_notional(equity, config, state["positions"])
            entry = _execution_price(data["price"], "BUY", config["slippage_bps"])
            shares = int(notional / entry / 100) * 100
            if shares < 100:
                continue
            actual_notional = shares * entry
            cost = data["price"] * config["slippage_bps"] / 10_000 * shares
            state["positions"][key] = {"side": "LONG", "entry_price": entry, "shares": shares, "units": shares, "notional": actual_notional}
            state["trades"].insert(0, {"時刻": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "銘柄": key, "売買": "BUY", "株数": shares, "価格": round(entry, 1), "損益": 0, "コスト": round(cost), "理由": f"自動シグナル（RSI {data['rsi']:.1f}）"})
    return quotes


@st.fragment(run_every="60s")
def show_stock_paper_trading_demo():
    state = _state()
    symbols = _symbols()
    st.subheader("JP STOCK AUTO TRADER // DEMO")
    st.caption("日本株のペーパートレード専用です。100株単位・買いのみで、実注文は行いません。")

    add_code, add_button = st.columns([4, 1])
    code = add_code.text_input(
        "自動取引する日本株を追加",
        placeholder="4桁の銘柄コード（例: 9432）",
        max_chars=4,
        key="stock_add_code",
    ).strip().upper()
    if add_button.button("銘柄を追加", width="stretch"):
        if len(code) != 4 or not code.isalnum():
            st.error("4桁の銘柄コードを入力してください。")
        else:
            result = _lookup_stock(code)
            if result is None:
                st.error("株価データを確認できませんでした。コードを確認してください。")
            else:
                label, symbol = result
                symbols[label] = symbol
                selected = list(st.session_state.get("stock_universe", []))
                if label not in selected:
                    selected.append(label)
                st.session_state.stock_universe = selected
                save_symbol_settings(ACCOUNT_ID, symbols, selected)
                st.success(f"{label} を自動取引対象へ追加しました。")
                st.rerun(scope="fragment")

    c1, c2 = st.columns(2)
    previous_mode = state.get("mode", "標準")
    mode = c1.selectbox("株式運用モード", list(STOCK_MODES), index=list(STOCK_MODES).index(previous_mode), key="stock_mode")
    universe = c2.multiselect("自動取引対象", list(symbols), key="stock_universe")
    if universe != load_symbol_settings(ACCOUNT_ID)[1]:
        save_symbol_settings(ACCOUNT_ID, symbols, universe)
    state["mode"] = mode
    if mode != previous_mode:
        save_state(state, ACCOUNT_ID)

    b1, b2, b3 = st.columns(3)
    if b1.button("▶ 株式デモ開始", width="stretch"):
        state["running"] = True
        save_state(state, ACCOUNT_ID)
        st.rerun(scope="fragment")
    if b2.button("■ 株式デモ停止", width="stretch"):
        state["running"] = False
        save_state(state, ACCOUNT_ID)
        st.rerun(scope="fragment")
    if b3.button("↺ 株式口座リセット", width="stretch"):
        st.session_state.stock_paper_trading = _initial_state()
        reset_state(st.session_state.stock_paper_trading, ACCOUNT_ID)
        st.rerun(scope="fragment")

    quotes = _evaluate(state, mode, universe, symbols) if state["running"] else {}
    unrealized = 0.0
    rows = []
    for key, position in state["positions"].items():
        data = quotes.get(key) or _stock_data(symbols[key])
        current = data["price"] if data else position["entry_price"]
        pnl = (current - position["entry_price"]) * position["shares"]
        unrealized += pnl
        rows.append({"銘柄": key, "株数": position["shares"], "建値": round(position["entry_price"], 1), "現在値": round(current, 1), "評価損益": round(pnl)})

    equity = state["initial_capital"] + state["realized_pnl"] + unrealized
    state["peak_equity"] = max(state.get("peak_equity", equity), equity)
    if state["running"]:
        state["equity_history"].append({"time": datetime.now().isoformat(), "equity": equity})
        state["equity_history"] = state["equity_history"][-500:]
        save_state(state, ACCOUNT_ID)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("稼働状態", "RUNNING" if state["running"] else "STOPPED")
    m2.metric("株式口座純資産", f"¥{equity:,.0f}", f"¥{equity - INITIAL_CAPITAL:+,.0f}")
    m3.metric("確定損益", f"¥{state['realized_pnl']:+,.0f}")
    m4.metric("市場", "OPEN" if _market_open() else "CLOSED")

    chart_symbols = list(dict.fromkeys([*state["positions"].keys(), *universe]))
    if chart_symbols:
        chart_choice, period_choice = st.columns([3, 1])
        chart_key = chart_choice.selectbox(
            "表示する株価チャート（保有中・自動取引対象）",
            chart_symbols,
            key="stock_chart_symbol",
        )
        period_label = period_choice.selectbox(
            "表示期間",
            ["1日", "3日", "5日"],
            key="stock_chart_period",
        )
        sessions = {"1日": 1, "3日": 3, "5日": 5}[period_label]
        st.plotly_chart(
            _stock_figure(
                chart_key,
                symbols[chart_key],
                state["positions"].get(chart_key),
                sessions,
            ),
            width="stretch",
            config={"displaylogo": False, "scrollZoom": True},
        )
    else:
        st.info("自動取引対象を追加すると、ここに株価チャートが表示されます。")

    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    with st.expander("株式取引履歴"):
        if state["trades"]:
            st.dataframe(pd.DataFrame(state["trades"][:100]), width="stretch", hide_index=True)
        else:
            st.info("株式取引履歴はありません。")

    config = STOCK_MODES[mode]
    st.caption(f"{mode}: 許容損失{config['risk_per_trade']:.2%}、損切り{config['stop_loss']:.1%}、利益確定{config['take_profit']:.1%}、想定スリッページ{config['slippage_bps']}bps。")
