"""ブラウザ内で Widget を自由配置する分析ダッシュボード。"""

import json

import plotly.io as pio
import streamlit.components.v1 as components

from modules.widgets import create_macd_chart, create_stock_chart


DEFAULT_LAYOUT = {
    "stock_chart": {"x": 0, "y": 0, "w": 8, "h": 12},
    "macd": {"x": 8, "y": 0, "w": 4, "h": 8},
    "rsi": {"x": 8, "y": 8, "w": 4, "h": 4},
    "ai_signal": {"x": 0, "y": 12, "w": 6, "h": 6},
}


def _grid_item(widget_id, title, content):
    layout = DEFAULT_LAYOUT[widget_id]
    return f"""
        <div class="grid-stack-item" gs-id="{widget_id}"
             gs-x="{layout['x']}" gs-y="{layout['y']}"
             gs-w="{layout['w']}" gs-h="{layout['h']}">
          <div class="grid-stack-item-content widget-card">
            <div class="widget-header">⠿ {title}</div>
            <div class="widget-content">{content}</div>
          </div>
        </div>
    """


def _status(rsi):
    if rsi >= 70:
        return "買われすぎ", "danger"
    if rsi <= 30:
        return "売られすぎ", "success"
    return "中立", "info"


def _signal_summary(signal):
    if signal is None:
        return "シグナルを取得できませんでした。", "danger", []

    score = signal["score"]
    if score >= 80:
        label, tone = "★★★★★ 強い買い", "success"
    elif score >= 60:
        label, tone = "★★★★☆ 買い", "info"
    elif score >= 40:
        label, tone = "★★★☆☆ 様子見", "warning"
    else:
        label, tone = "★★☆☆☆ 弱い", "danger"
    return f"総合スコア: {score} 点 — {label}", tone, signal["reasons"]


def show_layout_dashboard(history, code, company, macd_history, rsi, signal, visibility):
    """ドラッグ・リサイズ可能な Widget ダッシュボードを表示する。"""

    items = []
    scripts = []

    if visibility["stock_chart"]:
        items.append(_grid_item("stock_chart", "株価チャート", '<div id="stock-chart" class="plot"></div>'))
        figure = create_stock_chart(history, code, company)
        scripts.append(f"renderPlot('stock-chart', {pio.to_json(figure)});")

    if visibility["macd"]:
        items.append(_grid_item("macd", "MACD", '<div id="macd-chart" class="plot"></div>'))
        figure = create_macd_chart(macd_history)
        scripts.append(f"renderPlot('macd-chart', {pio.to_json(figure)});")

    if visibility["rsi"]:
        status, tone = _status(rsi)
        items.append(
            _grid_item(
                "rsi",
                "RSI",
                f'<div class="metric">{rsi:.2f}</div><div class="status {tone}">{status}</div>',
            )
        )

    if visibility["ai_signal"]:
        summary, tone, reasons = _signal_summary(signal)
        reason_items = "".join(f"<li>{reason}</li>" for reason in reasons)
        items.append(
            _grid_item(
                "ai_signal",
                "AI売買シグナル",
                f'<div class="status {tone}">{summary}</div><h4>判定理由</h4><ul>{reason_items}</ul>',
            )
        )

    html = f"""
    <!doctype html>
    <html lang="ja">
      <head>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gridstack@10.1.2/dist/gridstack.min.css">
        <script src="https://cdn.jsdelivr.net/npm/gridstack@10.1.2/dist/gridstack-all.js"></script>
        <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
        <style>
          body {{ margin: 0; font-family: Consolas, "Courier New", monospace; background: #05080d; color: #d8e1ea; }}
          .widget-card {{ background: #0a111a; border: 1px solid #1d4658; border-radius: 2px; overflow: hidden; height: 100%; box-sizing: border-box; box-shadow: inset 0 0 0 1px #081017; }}
          .widget-header {{ cursor: move; padding: 9px 12px; font-weight: 700; letter-spacing: .05em; color: #74d9ff; background: #0d1a25; border-bottom: 1px solid #1d4658; user-select: none; }}
          .widget-content {{ height: calc(100% - 42px); padding: 12px; box-sizing: border-box; overflow: auto; }}
          .plot {{ width: 100%; height: 100%; }}
          .metric {{ font-size: 42px; font-weight: 700; color: #e8f1f8; }}
          .status {{ font-weight: 700; margin-top: 10px; }}
          .success {{ color: #62e6ac; }} .info {{ color: #74d9ff; }} .warning {{ color: #ffd166; }} .danger {{ color: #ff7186; }}
          h4 {{ margin-bottom: 6px; }} ul {{ margin-top: 0; padding-left: 20px; }}
        </style>
      </head>
      <body>
        <div class="grid-stack">{''.join(items)}</div>
        <script>
          const storageKey = 'aegis-ai-trader-layout-v1';
          const grid = GridStack.init({{column: 12, cellHeight: 34, margin: 8, float: true, draggable: {{handle: '.widget-header'}}, resizable: {{handles: 'all'}}}});
          const savedLayout = localStorage.getItem(storageKey);
          if (savedLayout) grid.load(JSON.parse(savedLayout));

          const resizePlots = () => document.querySelectorAll('.plot').forEach((plot) => Plotly.Plots.resize(plot));
          grid.on('change', () => {{
            localStorage.setItem(storageKey, JSON.stringify(grid.save()));
            resizePlots();
          }});
          function renderPlot(id, figure) {{
            const element = document.getElementById(id);
            Plotly.newPlot(element, figure.data, figure.layout, {{responsive: true, displaylogo: false}});
          }}
          {''.join(scripts)}
          setTimeout(resizePlots, 150);
        </script>
      </body>
    </html>
    """

    components.html(html, height=760, scrolling=True)
