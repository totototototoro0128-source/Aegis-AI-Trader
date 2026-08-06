import plotly.graph_objects as go


def create_candlestick_chart(history, code, company):

    fig = go.Figure()

    # ローソク足
    fig.add_trace(
        go.Candlestick(
            x=history.index,
            open=history["Open"],
            high=history["High"],
            low=history["Low"],
            close=history["Close"],
            name="株価",

            increasing_line_color="#26A69A",
            increasing_fillcolor="#26A69A",

            decreasing_line_color="#EF5350",
            decreasing_fillcolor="#EF5350",
        )
    )

    # 25日MA
    fig.add_trace(
        go.Scatter(
            x=history.index,
            y=history["MA25"],
            mode="lines",
            name="25日MA",
            line=dict(
                color="#2962FF",
                width=2,
            ),
        )
    )

    # 75日MA
    fig.add_trace(
        go.Scatter(
            x=history.index,
            y=history["MA75"],
            mode="lines",
            name="75日MA",
            line=dict(
                color="#FF9800",
                width=2,
            ),
        )
    )

    fig.update_layout(
        title=f"{code} {company}",
        template="plotly_white",
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        height=600,

        xaxis=dict(
            title="日付",
            tickformat="%Y/%m/%d",
            tickangle=-45,
            showgrid=True,
        ),

        yaxis=dict(
            title="株価（円）",
            showgrid=True,
        ),
    )

    return fig