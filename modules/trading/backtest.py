"""FXデモ戦略のバックテストと高速リプレイ。"""

from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from modules.trading.execution import (
    estimated_execution_cost,
    execution_price,
    is_trading_time,
    liquidation_price,
)
from modules.trading.risk import calculate_position_notional


@dataclass
class BacktestResult:
    data: pd.DataFrame
    equity: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict


@st.cache_data(ttl=900, show_spinner=False)
def _historical_data(symbol, days):
    history = yf.Ticker(symbol).history(period="1mo", interval="15m").dropna()
    if history.empty:
        return history
    cutoff = history.index.max() - pd.Timedelta(days=days)
    return history.loc[history.index >= cutoff].copy()


def _prepare(history):
    data = history.copy()
    close = data["Close"]
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    data["RSI"] = 100 - (100 / (1 + gain / loss))
    data["EMA9"] = close.ewm(span=9, adjust=False).mean()
    data["EMA21"] = close.ewm(span=21, adjust=False).mean()
    data["Score"] = (data["EMA9"] > data["EMA21"]).map({True: 1, False: -1})
    data.loc[data["RSI"] < 35, "Score"] += 1
    data.loc[data["RSI"] > 65, "Score"] -= 1
    return data.dropna()


def run_backtest(pair, symbol, config, days, initial_capital=1_000_000.0):
    data = _prepare(_historical_data(symbol, days))
    if data.empty:
        return None

    realized = 0.0
    daily_realized = 0.0
    trading_date = None
    peak = initial_capital
    position = None
    trades = []
    equity_points = []

    def close_position(timestamp, mid_price, reason):
        nonlocal realized, daily_realized, position
        action = "SELL" if position["side"] == "LONG" else "BUY"
        exit_price, spread = execution_price(pair, mid_price, action, config["slippage_pips"])
        direction = 1 if position["side"] == "LONG" else -1
        pnl = (exit_price - position["entry_price"]) * position["units"] * direction
        exit_cost = estimated_execution_cost(pair, position["units"], config["slippage_pips"])
        realized += pnl
        daily_realized += pnl
        trades.append(
            {
                "entry_time": position["entry_time"],
                "exit_time": timestamp,
                "side": position["side"],
                "entry_price": position["entry_price"],
                "exit_price": exit_price,
                "pnl": pnl,
                "cost": position["entry_cost"] + exit_cost,
                "spread": spread,
                "reason": reason,
            }
        )
        position = None

    for timestamp, row in data.iterrows():
        current_date = timestamp.tz_convert("Asia/Tokyo").date() if timestamp.tzinfo else timestamp.date()
        if current_date != trading_date:
            trading_date = current_date
            daily_realized = 0.0
        mid_price = float(row["Close"])
        score = int(row["Score"])

        if position is not None and is_trading_time(config, timestamp.to_pydatetime()):
            direction = 1 if position["side"] == "LONG" else -1
            return_rate = (mid_price / position["entry_price"] - 1) * direction
            if return_rate <= -config["stop_loss"]:
                close_position(timestamp, mid_price, "ストップロス")
            elif return_rate >= config["take_profit"]:
                close_position(timestamp, mid_price, "利益確定")
            elif score * direction < 0:
                close_position(timestamp, mid_price, "シグナル反転")

        current_equity = initial_capital + realized
        drawdown = (peak - current_equity) / peak if peak else 0.0
        if (
            position is None
            and is_trading_time(config, timestamp.to_pydatetime())
            and abs(score) >= config["entry_score"]
            and drawdown < config["max_drawdown"]
            and abs(min(0.0, daily_realized)) < initial_capital * config["daily_loss_limit"]
        ):
            notional = calculate_position_notional(current_equity, config, {})
            side = "LONG" if score > 0 else "SHORT"
            action = "BUY" if side == "LONG" else "SELL"
            entry_price, _ = execution_price(pair, mid_price, action, config["slippage_pips"])
            units = notional / entry_price if entry_price else 0.0
            position = {
                "side": side,
                "entry_time": timestamp,
                "entry_price": entry_price,
                "units": units,
                "entry_cost": estimated_execution_cost(pair, units, config["slippage_pips"]),
            }

        unrealized = 0.0
        if position is not None:
            mark = liquidation_price(pair, mid_price, position["side"])
            direction = 1 if position["side"] == "LONG" else -1
            unrealized = (mark - position["entry_price"]) * position["units"] * direction
        equity = initial_capital + realized + unrealized
        peak = max(peak, equity)
        equity_points.append({"time": timestamp, "equity": equity, "price": mid_price})

    if position is not None:
        close_position(data.index[-1], float(data["Close"].iloc[-1]), "期間終了")
        equity_points[-1]["equity"] = initial_capital + realized

    equity = pd.DataFrame(equity_points)
    trade_frame = pd.DataFrame(trades)
    running_peak = equity["equity"].cummax()
    drawdowns = (running_peak - equity["equity"]) / running_peak
    wins = trade_frame[trade_frame["pnl"] > 0] if not trade_frame.empty else trade_frame
    losses = trade_frame[trade_frame["pnl"] < 0] if not trade_frame.empty else trade_frame
    gross_profit = wins["pnl"].sum() if not wins.empty else 0.0
    gross_loss = abs(losses["pnl"].sum()) if not losses.empty else 0.0
    metrics = {
        "return": (equity["equity"].iloc[-1] / initial_capital - 1),
        "net_profit": equity["equity"].iloc[-1] - initial_capital,
        "max_drawdown": drawdowns.max(),
        "trade_count": len(trade_frame),
        "win_rate": len(wins) / len(trade_frame) if len(trade_frame) else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss else None,
        "total_cost": trade_frame["cost"].sum() if not trade_frame.empty else 0.0,
    }
    return BacktestResult(data=data, equity=equity, trades=trade_frame, metrics=metrics)


def _equity_chart(result):
    figure = go.Figure(
        go.Scatter(
            x=result.equity["time"],
            y=result.equity["equity"],
            mode="lines",
            name="純資産",
            line={"color": "#62e6ac", "width": 2},
        )
    )
    figure.add_hline(y=1_000_000, line_dash="dot", line_color="#74d9ff")
    figure.update_layout(template="plotly_dark", height=330, title="バックテスト資産推移", yaxis_tickprefix="¥")
    return figure


def _replay_chart(result, end_index):
    view = result.data.iloc[:end_index]
    figure = go.Figure(
        go.Candlestick(
            x=view.index,
            open=view["Open"],
            high=view["High"],
            low=view["Low"],
            close=view["Close"],
            increasing_line_color="#62e6ac",
            decreasing_line_color="#ff7186",
            name="価格",
        )
    )
    figure.add_trace(go.Scatter(x=view.index, y=view["EMA9"], name="EMA9", line={"color": "#74d9ff"}))
    figure.add_trace(go.Scatter(x=view.index, y=view["EMA21"], name="EMA21", line={"color": "#ffd166"}))
    if not result.trades.empty:
        visible_trades = result.trades[result.trades["entry_time"] <= view.index[-1]]
        figure.add_trace(
            go.Scatter(
                x=visible_trades["entry_time"],
                y=visible_trades["entry_price"],
                mode="markers",
                marker={"symbol": "triangle-up", "size": 10, "color": "#74d9ff"},
                name="エントリー",
            )
        )
        closed = visible_trades[visible_trades["exit_time"] <= view.index[-1]]
        figure.add_trace(
            go.Scatter(
                x=closed["exit_time"],
                y=closed["exit_price"],
                mode="markers",
                marker={"symbol": "x", "size": 9, "color": "#ffd166"},
                name="決済",
            )
        )
    figure.update_layout(
        template="plotly_dark",
        height=440,
        title="高速リプレイ",
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )
    return figure


def show_backtest_panel(fx_pairs, mode_config):
    """バックテスト設定・結果・高速リプレイを表示する。"""

    with st.expander("BACKTEST / 高速リプレイ", expanded=False):
        c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
        pair = c1.selectbox("通貨ペア", list(fx_pairs), key="backtest_pair")
        mode = c2.selectbox("検証モード", list(mode_config), index=1, key="backtest_mode")
        days = c3.selectbox("期間", [5, 10, 20, 30], index=1, format_func=lambda value: f"{value}日")
        run = c4.button("検証実行", width="stretch")

        if run:
            with st.spinner("過去データを検証中..."):
                st.session_state.backtest_result = run_backtest(
                    pair,
                    fx_pairs[pair],
                    mode_config[mode],
                    days,
                )

        result = st.session_state.get("backtest_result")
        if result is None:
            st.info("条件を選び、「検証実行」を押してください。")
            return

        metrics = result.metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("損益", f"¥{metrics['net_profit']:+,.0f}", f"{metrics['return']:+.2%}")
        m2.metric("最大DD", f"{metrics['max_drawdown']:.2%}")
        m3.metric("取引回数", f"{metrics['trade_count']}")
        m4.metric("勝率", f"{metrics['win_rate']:.1%}")
        pf = "—" if metrics["profit_factor"] is None else f"{metrics['profit_factor']:.2f}"
        m5.metric("PF / コスト", f"{pf} / ¥{metrics['total_cost']:,.0f}")
        st.plotly_chart(_equity_chart(result), width="stretch")

        minimum = min(30, len(result.data))
        replay_end = st.slider(
            "リプレイ位置",
            min_value=minimum,
            max_value=len(result.data),
            value=len(result.data),
            step=max(1, len(result.data) // 200),
        )
        st.plotly_chart(_replay_chart(result, replay_end), width="stretch")
        if not result.trades.empty:
            display = result.trades.copy()
            display["entry_time"] = display["entry_time"].astype(str)
            display["exit_time"] = display["exit_time"].astype(str)
            st.dataframe(display.tail(100), width="stretch", hide_index=True)

        st.caption("過去の結果は将来の成績を保証しません。デモ検証専用です。")
