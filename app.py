import streamlit as st
import plotly.graph_objects as go
from modules.charts import create_candlestick_chart

from modules.technical import (
    get_history,
    get_ma,
    get_rsi,
    get_macd,
)

from modules.database import init_db

from modules.watchlist import (
    add_stock,
    get_stocks,
    delete_stock,
)

from modules.stock import get_stock_price

from modules.signal import analyze_stock

from modules.company import get_company_name

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

# -----------------------------
# 選択中の銘柄
# -----------------------------

if "selected_code" not in st.session_state:
    st.session_state.selected_code = "7203"

if "selected_company" not in st.session_state:
    st.session_state.selected_company = "トヨタ"
st.divider()

# -----------------------------
# 銘柄追加
# -----------------------------

st.subheader("➕ 銘柄追加")

code = st.text_input("銘柄コード")

company = ""

if code:

    company = get_company_name(code)

if company:

    st.text_input(
        "会社名",
        value=company,
        disabled=True,
    )

else:

    st.text_input(
        "会社名",
        value="",
    )

if st.button("追加"):

    if code and company:

        add_stock(code, company)

        st.success("追加しました")

        st.rerun()

    else:

        st.warning("正しい銘柄コードを入力してください")

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
        
        if st.button(f"📈 {code} {company}", key=f"select_{stock_id}"):

            st.session_state.selected_code = code

            st.session_state.selected_company = company

            st.rerun()

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

            if st.button("🗑", key=f"delete_{stock_id}"):

                delete_stock(stock_id)

                st.rerun()

        st.divider()

# -----------------------------
# テクニカル分析
# -----------------------------

st.subheader("🧪 テクニカルテスト")

history = get_history(
    st.session_state.selected_code
)

history["MA25"] = history["Close"].rolling(25).mean()
history["MA75"] = history["Close"].rolling(75).mean()

st.dataframe(history.tail())

fig = create_candlestick_chart(
    history,
    st.session_state.selected_code,
    st.session_state.selected_company,
)

st.plotly_chart(
    fig,
    use_container_width=True,
)

ma25 = get_ma(st.session_state.selected_code)
ma75 = get_ma(st.session_state.selected_code, 75)
rsi = get_rsi(st.session_state.selected_code)
macd_history = get_macd(st.session_state.selected_code)

st.subheader("📊 MACD")

fig_macd = go.Figure()

# MACD
fig_macd.add_trace(
    go.Scatter(
        x=macd_history.index,
        y=macd_history["MACD"],
        mode="lines",
        name="MACD",
        line=dict(
            color="#2962FF",
            width=2,
        ),
    )
)

# Signal
fig_macd.add_trace(
    go.Scatter(
        x=macd_history.index,
        y=macd_history["Signal"],
        mode="lines",
        name="Signal",
        line=dict(
            color="#FF9800",
            width=2,
        ),
    )
)

# Histogram
fig_macd.add_trace(
    go.Bar(
        x=macd_history.index,
        y=macd_history["Histogram"],
        name="Histogram",
        marker_color=[
            "#26A69A" if x >= 0 else "#EF5350"
            for x in macd_history["Histogram"]
        ],
    )
)

fig_macd.update_layout(
    title="MACD",
    height=300,
    template="plotly_white",
    hovermode="x unified",
    xaxis=dict(
        title="日付",
        tickformat="%Y/%m/%d",
        tickangle=-45,
        showgrid=True,
    ),
    yaxis=dict(
        title="MACD",
        showgrid=True,
    ),
)

st.plotly_chart(fig_macd, use_container_width=True)

macd_value = macd_history["MACD"].iloc[-1]
signal_value = macd_history["Signal"].iloc[-1]

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("25日移動平均", f"{ma25:.2f} 円")

with col2:
    st.metric("75日移動平均", f"{ma75:.2f} 円")

with col3:
    st.metric("RSI", f"{rsi:.2f}")

    if rsi >= 70:
        st.error("買われすぎ")
    elif rsi <= 30:
        st.success("売られすぎ")
    else:
        st.info("中立")

with col4:
    st.metric("MACD", f"{macd_value:.2f}")

    st.divider()

st.subheader("🤖 AI売買シグナル")

signal = analyze_stock(st.session_state.selected_code)

if signal:

    st.metric("総合スコア", f"{signal['score']} 点")

    if signal["score"] >= 80:
        st.success("★★★★★　強い買い")

    elif signal["score"] >= 60:
        st.info("★★★★☆　買い")

    elif signal["score"] >= 40:
        st.warning("★★★☆☆　様子見")

    else:
        st.error("★★☆☆☆　弱い")

    st.write("### 判定理由")

    for reason in signal["reasons"]:

        st.write("✅", reason)