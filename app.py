import streamlit as st

from modules.database import init_db

from modules.watchlist import (
    add_stock,
    get_stocks,
    delete_stock,
)

from modules.stock import get_stock_price

from modules.technical import (
    get_history,
    get_ma,
    get_rsi,
)

# -----------------------------
# 初期設定
# -----------------------------

init_db()

st.set_page_config(
    page_title="AI Investment Assistant",
    page_icon="📈",
    layout="wide",
)

st.title("📈 AI Investment Assistant")

st.divider()

# -----------------------------
# 銘柄追加
# -----------------------------

st.subheader("➕ 銘柄追加")

code = st.text_input("銘柄コード")

company = st.text_input("会社名")

if st.button("追加"):

    if code and company:

        add_stock(code, company)

        st.success("追加しました")

        st.rerun()

    else:

        st.warning("銘柄コードと会社名を入力してください")

st.divider()

# -----------------------------
# 監視銘柄
# -----------------------------

st.subheader("📋 監視銘柄")

stocks = get_stocks()

if len(stocks) == 0:

    st.info("まだ登録されていません")

else:

    for stock in stocks:

        stock_id, code, company = stock

        stock_info = get_stock_price(code)

        col1, col2 = st.columns([8, 1])

        with col1:

            st.subheader(f"{code}　{company}")

            if stock_info:

                price = stock_info["price"]

                previous = stock_info["previous_close"]

                if price and previous:

                    diff = price - previous

                    rate = diff / previous * 100

                    st.write(f"現在価格：{price:.2f} 円")

                    if diff >= 0:

                        st.success(
                            f"前日比：+{diff:.2f} 円 ({rate:.2f}%)"
                        )

                    else:

                        st.error(
                            f"前日比：{diff:.2f} 円 ({rate:.2f}%)"
                        )

                else:

                    st.warning("株価取得失敗")

            else:

                st.warning("株価取得失敗")

        with col2:

            if st.button("🗑", key=stock_id):

                delete_stock(stock_id)

                st.rerun()

        st.divider()

# -----------------------------
# テクニカル分析
# -----------------------------

st.subheader("🧪 テクニカルテスト")

history = get_history("7203")

st.dataframe(history.tail())

ma25 = get_ma("7203")

ma75 = get_ma("7203", 75)

rsi = get_rsi("7203")

col1, col2, col3 = st.columns(3)

with col1:

    if ma25 is None:

        st.metric("25日移動平均", "データ不足")

    else:

        st.metric(
            "25日移動平均",
            f"{ma25:.2f} 円"
        )

with col2:

    if ma75 is None:

        st.metric("75日移動平均", "データ不足")

    else:

        st.metric(
            "75日移動平均",
            f"{ma75:.2f} 円"
        )

with col3:

    if rsi is None:

        st.metric("RSI", "データ不足")

    else:

        st.metric(
            "RSI",
            f"{rsi:.2f}"
        )

        if rsi >= 70:

            st.error("🔴 買われすぎ")

        elif rsi <= 30:

            st.success("🟢 売られすぎ")

        else:

            st.info("🟡 中立")