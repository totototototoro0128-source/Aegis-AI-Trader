import streamlit as st
import plotly.graph_objects as go
from modules.charts import create_candlestick_chart

from modules.technical import (
    get_history,
    get_ma,
    get_rsi,
    get_macd,
)

from modules.widgets import (
    show_macd,
    show_rsi,
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

st.title("AI Investment Assistant")

# -----------------------------
# 選択中の銘柄
# -----------------------------

if "selected_code" not in st.session_state:
    st.session_state.selected_code = "7203"

if "selected_company" not in st.session_state:
    st.session_state.selected_company = "トヨタ"
st.divider()

# -----------------------------
# 銘柄検索・追加
# -----------------------------

col_search, col_button = st.columns([8, 1])

with col_search:

    search_code = st.text_input(
        "銘柄検索",
        placeholder="銘柄コードを入力（例：7203）",
        label_visibility="collapsed",
    )

with col_button:

    search_button = st.button(
        "追加",
        use_container_width=True,
    )

if search_button:

    if search_code:

        company_name = get_company_name(search_code)

        if company_name:

            add_stock(search_code, company_name)

            st.success(
                f"{search_code} {company_name} を追加しました"
            )

            st.rerun()

        else:

            st.warning(
                "銘柄が見つかりませんでした"
            )

    else:

        st.warning(
            "銘柄コードを入力してください"
        )

st.divider()

# -----------------------------
# 監視銘柄
# -----------------------------

st.subheader("監視銘柄")

stocks = get_stocks()

if len(stocks) == 0:

    st.info("監視銘柄がありません")

else:

    columns = st.columns(len(stocks))

    for index, stock in enumerate(stocks):

        stock_id, code, company = stock

        with columns[index]:

            stock_info = get_stock_price(code)

            if st.button(
                f"{code}  {company}",
                key=f"select_{stock_id}",
                use_container_width=True,
            ):

                st.session_state.selected_code = code
                st.session_state.selected_company = company

                st.rerun()

            if stock_info:

                price = stock_info["price"]
                previous = stock_info["previous_close"]

                if price and previous:

                    diff = price - previous
                    rate = diff / previous * 100

                    st.metric(
                        "株価",
                        f"{price:.2f} 円",
                        f"{diff:+.2f} ({rate:+.2f}%)",
                    )

            if st.button(
                "削除",
                key=f"delete_{stock_id}",
                use_container_width=True,
            ):

                delete_stock(stock_id)

                st.rerun()

st.divider()

# -----------------------------
# 表示設定
# -----------------------------

st.subheader("表示")

display_col1, display_col2, display_col3, display_col4 = st.columns(4)

with display_col1:

    show_chart = st.toggle(
        "株価チャート",
        value=True,
    )

with display_col2:

    show_macd_widget = st.toggle(
    "MACD",
    value=True,
)

with display_col3:

    show_rsi_widget = st.toggle(
    "RSI",
    value=True,
)

with display_col4:

    show_ai = st.toggle(
        "AI分析",
        value=True,
    )
    
# -----------------------------
# テクニカル分析
# -----------------------------

st.subheader(
    f"{st.session_state.selected_code} "
    f"{st.session_state.selected_company}"
)

history = get_history(
    st.session_state.selected_code
)

history["MA25"] = history["Close"].rolling(25).mean()
history["MA75"] = history["Close"].rolling(75).mean()


if show_chart:

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

if show_macd_widget:

    show_macd(macd_history)

macd_value = macd_history["MACD"].iloc[-1]
signal_value = macd_history["Signal"].iloc[-1]

if show_macd:

    macd_col1, macd_col2 = st.columns(2)

    with macd_col1:

        st.metric(
            "MACD",
            f"{macd_value:.2f}"
        )

    with macd_col2:

        st.metric(
            "Signal",
            f"{signal_value:.2f}"
        )

if show_rsi:

    show_rsi(rsi)

if show_ai:

    st.subheader("AI売買シグナル")

    signal = analyze_stock(
        st.session_state.selected_code
    )

    if signal:

        st.metric(
            "総合スコア",
            f"{signal['score']} 点"
        )

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

            st.write(reason)