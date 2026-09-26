"""実注文を送らない FX ペーパートレード用デモ。"""

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from modules.yfinance_config import configure_yfinance_cache
from modules.trading.repository import load_state, reset_state, save_state
from modules.trading.risk import calculate_position_notional, may_open_position
from modules.trading.backtest import show_backtest_panel
from modules.trading.execution import (
    PAIR_SPREAD_PIPS,
    estimated_execution_cost,
    execution_price,
    is_trading_time,
    liquidation_price,
)


configure_yfinance_cache()

INITIAL_CAPITAL = 1_000_000.0
FX_PAIRS = {
    "USD/JPY": "JPY=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
}
MODE_CONFIG = {
    "慎重": {
        "risk_per_trade": 0.0025,
        "leverage_cap": 1.0,
        "max_positions": 1,
        "entry_score": 2,
        "stop_loss": 0.004,
        "take_profit": 0.008,
        "daily_loss_limit": 0.01,
        "max_drawdown": 0.03,
        "slippage_pips": 0.05,
        "trading_hours_jst": (8, 22),
    },
    "標準": {
        "risk_per_trade": 0.005,
        "leverage_cap": 2.0,
        "max_positions": 2,
        "entry_score": 1,
        "stop_loss": 0.006,
        "take_profit": 0.012,
        "daily_loss_limit": 0.02,
        "max_drawdown": 0.05,
        "slippage_pips": 0.10,
        "trading_hours_jst": (7, 2),
    },
    "積極": {
        "risk_per_trade": 0.01,
        "leverage_cap": 3.0,
        "max_positions": 3,
        "entry_score": 1,
        "stop_loss": 0.010,
        "take_profit": 0.020,
        "daily_loss_limit": 0.03,
        "max_drawdown": 0.08,
        "slippage_pips": 0.20,
        "trading_hours_jst": (0, 0),
    },
}


def _initial_state():
    return {
        "running": False,
        "initial_capital": INITIAL_CAPITAL,
        "capital": INITIAL_CAPITAL,
        "realized_pnl": 0.0,
        "daily_realized_pnl": 0.0,
        "daily_pnl_date": datetime.now().strftime("%Y-%m-%d"),
        "peak_equity": INITIAL_CAPITAL,
        "mode": "標準",
        "positions": {},
        "trades": [],
        "last_bar": {},
        "equity_history": [
            {"time": datetime.now().isoformat(), "equity": INITIAL_CAPITAL}
        ],
    }


def _state():
    if "paper_trading" not in st.session_state:
        st.session_state.paper_trading = load_state() or _initial_state()
    st.session_state.paper_trading.setdefault(
        "equity_history",
        [{"time": datetime.now().isoformat(), "equity": INITIAL_CAPITAL}],
    )
    today = datetime.now().strftime("%Y-%m-%d")
    if st.session_state.paper_trading.get("daily_pnl_date") != today:
        st.session_state.paper_trading["daily_realized_pnl"] = 0.0
        st.session_state.paper_trading["daily_pnl_date"] = today
    return st.session_state.paper_trading


@st.cache_data(ttl=25, show_spinner=False)
def _market_data(symbol):
    history = yf.Ticker(symbol).history(period="5d", interval="15m").dropna()
    if len(history) < 30:
        return None

    close = history["Close"]
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rsi = 100 - (100 / (1 + gain / loss))
    ema_fast = close.ewm(span=9, adjust=False).mean()
    ema_slow = close.ewm(span=21, adjust=False).mean()

    trend = 1 if ema_fast.iloc[-1] > ema_slow.iloc[-1] else -1
    momentum = 1 if rsi.iloc[-1] < 35 else -1 if rsi.iloc[-1] > 65 else 0
    score = trend + momentum
    return {
        "price": float(close.iloc[-1]),
        "bar": history.index[-1].isoformat(),
        "rsi": float(rsi.iloc[-1]),
        "score": score,
    }


@st.cache_data(ttl=25, show_spinner=False)
def _chart_data(symbol):
    """FXチャート表示用の直近1日分の15分足と移動平均を返す。"""

    history = yf.Ticker(symbol).history(period="5d", interval="15m").dropna()
    if history.empty:
        return history
    history = history.copy()
    history["EMA9"] = history["Close"].ewm(span=9, adjust=False).mean()
    history["EMA21"] = history["Close"].ewm(span=21, adjust=False).mean()
    return history.tail(96)


def _fx_figure(pair):
    history = _chart_data(FX_PAIRS[pair])
    figure = go.Figure()
    if history.empty:
        return figure

    # 週末などデータがない時間帯を詰め、足の間隔を一定にする。
    chart_x = history.index.strftime("%m/%d %H:%M")

    figure.add_trace(
        go.Candlestick(
            x=chart_x,
            open=history["Open"],
            high=history["High"],
            low=history["Low"],
            close=history["Close"],
            name=pair,
            increasing_line_color="#62e6ac",
            decreasing_line_color="#ff7186",
            increasing_line_width=2,
            decreasing_line_width=2,
        )
    )
    figure.add_trace(
        go.Scatter(x=chart_x, y=history["EMA9"], name="EMA9", line={"color": "#74d9ff", "width": 2})
    )
    figure.add_trace(
        go.Scatter(x=chart_x, y=history["EMA21"], name="EMA21", line={"color": "#ffd166", "width": 2})
    )
    figure.update_layout(
        title=f"{pair} / 直近1日・15分足",
        template="plotly_dark",
        height=440,
        margin={"l": 20, "r": 60, "t": 65, "b": 25},
        hovermode="x unified",
        plot_bgcolor="#0b1017",
        paper_bgcolor="#0b1017",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        xaxis={"type": "category", "nticks": 10, "showgrid": False, "rangeslider": {"visible": False}},
        yaxis={"side": "right", "gridcolor": "#26313d", "fixedrange": False},
    )
    return figure


def _equity_figure(state):
    history = pd.DataFrame(state["equity_history"])
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=pd.to_datetime(history["time"]),
            y=history["equity"],
            mode="lines+markers",
            name="純資産",
            line={"color": "#62e6ac", "width": 2},
        )
    )
    figure.add_hline(
        y=INITIAL_CAPITAL,
        line_dash="dot",
        line_color="#74d9ff",
        annotation_text="初期資金",
    )
    figure.update_layout(
        title="純資産推移",
        template="plotly_dark",
        height=390,
        margin={"l": 20, "r": 20, "t": 45, "b": 20},
        yaxis_tickprefix="¥",
        hovermode="x unified",
    )
    return figure


def _record_equity(state, equity):
    now = datetime.now()
    history = state["equity_history"]
    if history and (now - datetime.fromisoformat(history[-1]["time"])).total_seconds() < 25:
        history[-1] = {"time": now.isoformat(), "equity": equity}
    else:
        history.append({"time": now.isoformat(), "equity": equity})
    state["equity_history"] = history[-500:]


def _close_position(state, pair, mid_price, reason, config):
    position = state["positions"].pop(pair)
    direction = 1 if position["side"] == "LONG" else -1
    action = "SELL" if position["side"] == "LONG" else "BUY"
    price, spread_pips = execution_price(
        pair,
        mid_price,
        action,
        config["slippage_pips"],
    )
    execution_cost = estimated_execution_cost(pair, position["units"], config["slippage_pips"])
    pnl = (price - position["entry_price"]) * position["units"] * direction
    state["realized_pnl"] += pnl
    state["daily_realized_pnl"] = state.get("daily_realized_pnl", 0.0) + pnl
    state["trades"].insert(
        0,
        {
            "時刻": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "通貨ペア": pair,
            "売買": f"{position['side']} 決済",
            "価格": round(price, 3),
            "損益": round(pnl),
            "コスト": round(execution_cost),
            "スプレッド": spread_pips,
            "理由": reason,
        },
    )


def _evaluate(state, mode):
    config = MODE_CONFIG[mode]
    trading_time = is_trading_time(config)
    quotes = {}
    for pair, symbol in FX_PAIRS.items():
        data = _market_data(symbol)
        if data is None:
            continue
        quotes[pair] = data

        if not trading_time:
            continue

        if pair in state["positions"]:
            position = state["positions"][pair]
            direction = 1 if position["side"] == "LONG" else -1
            return_rate = (data["price"] / position["entry_price"] - 1) * direction
            if return_rate <= -config["stop_loss"]:
                _close_position(state, pair, data["price"], "ストップロス", config)
            elif return_rate >= config["take_profit"]:
                _close_position(state, pair, data["price"], "利益確定", config)
            elif data["score"] * direction < 0:
                _close_position(state, pair, data["price"], "シグナル反転", config)

        if state["last_bar"].get(pair) == data["bar"]:
            continue
        state["last_bar"][pair] = data["bar"]

        equity = state["initial_capital"] + state["realized_pnl"]
        if trading_time and pair not in state["positions"] and may_open_position(state, config, equity):
            if abs(data["score"]) >= config["entry_score"]:
                notional = calculate_position_notional(equity, config, state["positions"])
                if notional <= 0:
                    continue
                side = "LONG" if data["score"] > 0 else "SHORT"
                action = "BUY" if side == "LONG" else "SELL"
                entry_price, spread_pips = execution_price(
                    pair,
                    data["price"],
                    action,
                    config["slippage_pips"],
                )
                units = notional / entry_price
                execution_cost = estimated_execution_cost(pair, units, config["slippage_pips"])
                state["positions"][pair] = {
                    "side": side,
                    "entry_price": entry_price,
                    "units": units,
                    "notional": notional,
                    "entry_cost": execution_cost,
                }
                state["trades"].insert(
                    0,
                    {
                        "時刻": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "通貨ペア": pair,
                        "売買": side,
                        "価格": round(entry_price, 3),
                        "損益": 0,
                        "コスト": round(execution_cost),
                        "スプレッド": spread_pips,
                        "理由": f"自動シグナル（RSI {data['rsi']:.1f}）",
                    },
                )
    return quotes


@st.fragment(run_every="30s")
def show_paper_trading_demo():
    """FX 自動売買デモの操作画面を表示する。"""

    state = _state()
    st.subheader("FX AUTO TRADER // DEMO")
    st.caption("ペーパートレード専用です。実際の注文・送金・証券口座接続は行いません。")

    control1, control2, control3, control4 = st.columns([2, 1, 1, 1])
    with control1:
        default_index = list(MODE_CONFIG).index(state.get("mode", "標準"))
        mode = st.selectbox("運用モード", list(MODE_CONFIG), index=default_index, key="paper_mode")
        if mode != state.get("mode"):
            state["mode"] = mode
            save_state(state)
    with control2:
        if st.button("▶ 開始", width="stretch"):
            state["running"] = True
            save_state(state)
            st.rerun(scope="fragment")
    with control3:
        if st.button("■ 停止", width="stretch"):
            state["running"] = False
            save_state(state)
            st.rerun(scope="fragment")
    with control4:
        if st.button("↺ リセット", width="stretch"):
            st.session_state.paper_trading = _initial_state()
            reset_state(st.session_state.paper_trading)
            st.rerun(scope="fragment")

    quotes = _evaluate(state, mode) if state["running"] else {}
    unrealized = 0.0
    position_rows = []
    for pair, position in state["positions"].items():
        data = quotes.get(pair) or _market_data(FX_PAIRS[pair])
        mid_price = data["price"] if data else position["entry_price"]
        current = liquidation_price(pair, mid_price, position["side"])
        direction = 1 if position["side"] == "LONG" else -1
        pnl = (current - position["entry_price"]) * position["units"] * direction
        unrealized += pnl
        position_rows.append(
            {
                "通貨ペア": pair,
                "売買": position["side"],
                "建値": round(position["entry_price"], 3),
                "現在値": round(current, 3),
                "想定元本": round(position["notional"]),
                "評価損益": round(pnl),
            }
        )

    equity = state["initial_capital"] + state["realized_pnl"] + unrealized
    state["peak_equity"] = max(state.get("peak_equity", equity), equity)
    if state["running"]:
        _record_equity(state, equity)
        save_state(state)
    total_cost = sum(float(trade.get("コスト", 0.0)) for trade in state["trades"])
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("稼働状態", "RUNNING" if state["running"] else "STOPPED")
    m2.metric("純資産", f"¥{equity:,.0f}", f"¥{equity - INITIAL_CAPITAL:+,.0f}")
    m3.metric("確定損益", f"¥{state['realized_pnl']:+,.0f}")
    m4.metric("保有ポジション", f"{len(state['positions'])} / {MODE_CONFIG[mode]['max_positions']}")
    m5.metric("概算取引コスト", f"¥{total_cost:,.0f}")

    config = MODE_CONFIG[mode]
    session_start, session_end = config["trading_hours_jst"]
    session_label = "平日24時間" if session_start == session_end else f"平日 {session_start:02d}:00–{session_end:02d}:00 JST"
    if is_trading_time(MODE_CONFIG[mode]):
        st.success(f"取引時間内 · {session_label}")
    else:
        st.warning(f"取引時間外のため新規注文を停止中 · {session_label}")

    with st.expander("執行条件"):
        st.dataframe(
            pd.DataFrame(
                [
                    {"通貨ペア": pair, "想定スプレッド": f"{spread:.1f} pips"}
                    for pair, spread in PAIR_SPREAD_PIPS.items()
                ]
            ),
            width="stretch",
            hide_index=True,
        )
        st.write(
            f"モード別スリッページ: {config['slippage_pips']:.2f} pips / "
            f"取引時間: {session_label}"
        )

    chart_pair = st.selectbox(
        "為替チャートを切り替え（USD / EUR / GBP）",
        list(FX_PAIRS),
        key="paper_chart_pair",
    )
    fx_chart, equity_chart = st.columns(2)
    with fx_chart:
        st.plotly_chart(_fx_figure(chart_pair), width="stretch")
    with equity_chart:
        st.plotly_chart(_equity_figure(state), width="stretch")

    with st.expander("現在のポジション", expanded=True):
        if position_rows:
            st.dataframe(pd.DataFrame(position_rows), width="stretch", hide_index=True)
        else:
            st.info("ポジションはありません。")

    with st.expander("取引履歴"):
        if state["trades"]:
            st.dataframe(pd.DataFrame(state["trades"][:50]), width="stretch", hide_index=True)
        else:
            st.info("取引履歴はありません。")

    st.caption(
        f"{mode}: 1取引の許容損失{config['risk_per_trade']:.2%}、"
        f"レバレッジ上限{config['leverage_cap']:.0f}倍、損切り{config['stop_loss']:.1%}、"
        f"利益確定{config['take_profit']:.1%}、日次損失上限{config['daily_loss_limit']:.1%}、"
        f"想定スリッページ{config['slippage_pips']:.2f}pips。"
    )

    show_backtest_panel(FX_PAIRS, MODE_CONFIG)
