import streamlit as st
import plotly.graph_objects as go


def show_macd(macd_history):
    """
    MACDを表示するWidget
    """

    st.subheader("MACD")

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