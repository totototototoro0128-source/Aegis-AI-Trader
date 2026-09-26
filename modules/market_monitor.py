"""日本株を中心に為替・コモディティを一覧する市場モニター。"""

import yfinance as yf
import streamlit as st

from modules.yfinance_config import configure_yfinance_cache


configure_yfinance_cache()


MARKETS = {
    "日本市場": [
        ("日経平均", "^N225", "JPY"),
        ("TOPIX連動ETF", "1306.T", "JPY"),
    ],
    "為替": [
        ("USD/JPY", "JPY=X", "JPY"),
        ("EUR/JPY", "EURJPY=X", "JPY"),
    ],
    "金属・商品": [
        ("金", "GC=F", "USD"),
        ("銀", "SI=F", "USD"),
        ("銅", "HG=F", "USD"),
    ],
}


@st.cache_data(ttl=55, show_spinner=False)
def get_market_snapshot():
    """主要市場の直近価格と前日比を取得する。"""

    snapshot = {}
    for group, instruments in MARKETS.items():
        snapshot[group] = []
        for name, ticker_symbol, currency in instruments:
            try:
                info = yf.Ticker(ticker_symbol).fast_info
                price = info.get("lastPrice") or info.get("last_price")
                previous = info.get("previousClose") or info.get("previous_close")
                if price is None or previous in (None, 0):
                    continue
                change = price - previous
                change_percent = change / previous * 100
                snapshot[group].append(
                    {
                        "name": name,
                        "price": float(price),
                        "change": float(change),
                        "change_percent": float(change_percent),
                        "currency": currency,
                    }
                )
            except Exception:
                continue
    return snapshot


@st.fragment(run_every="60s")
def show_market_monitor():
    """1分ごとに更新する市場モニターを表示する。"""

    st.subheader("GLOBAL MARKET MONITOR")
    st.caption("更新間隔: 60秒（データ提供元の配信遅延が発生する場合があります）")

    snapshot = get_market_snapshot()
    for group, instruments in snapshot.items():
        if not instruments:
            continue

        st.markdown(f"##### {group}")
        columns = st.columns(len(instruments))
        for column, instrument in zip(columns, instruments):
            with column:
                st.metric(
                    instrument["name"],
                    f"{instrument['price']:,.2f} {instrument['currency']}",
                    f"{instrument['change']:+,.2f} ({instrument['change_percent']:+.2f}%)",
                )

    if not any(snapshot.values()):
        st.warning("市場データを取得できませんでした。しばらくしてから再読み込みしてください。")
