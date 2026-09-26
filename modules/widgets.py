import streamlit as st
import plotly.graph_objects as go

from modules.charts import create_candlestick_chart


def show_stock_chart(history, code, company):
    """株価チャート Widget を表示する。"""

    fig = create_stock_chart(history, code, company)

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


def create_stock_chart(history, code, company):
    """株価チャート Widget 用の Figure を作成する。"""

    return create_candlestick_chart(history, code, company)


def show_macd(macd_history):
    """
    MACDを表示するWidget
    """

    st.subheader("MACD")

    fig_macd = create_macd_chart(macd_history)

    st.plotly_chart(
        fig_macd,
        use_container_width=True,
    )

    # 現在値
    macd_value = macd_history["MACD"].iloc[-1]
    signal_value = macd_history["Signal"].iloc[-1]

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "MACD",
            f"{macd_value:.2f}",
        )

    with col2:

        st.metric(
            "Signal",
            f"{signal_value:.2f}",
        )


def create_macd_chart(macd_history):
    """MACD Widget 用の Figure を作成する。"""

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
        template="plotly_dark",
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

    return fig_macd

def show_rsi(rsi):
    """
    RSIを表示するWidget
    """

    st.subheader("RSI")

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "RSI",
            f"{rsi:.2f}",
        )

    with col2:

        if rsi >= 70:

            st.error("買われすぎ")

        elif rsi <= 30:

            st.success("売られすぎ")

        else:

            st.info("中立")


def show_ai_signal(signal):
    """AI 売買シグナル Widget を表示する。"""

    st.subheader("AI売買シグナル")

    if signal is None:
        return

    st.metric(
        "総合スコア",
        f"{signal['score']} 点",
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
