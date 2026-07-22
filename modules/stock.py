import yfinance as yf


def get_stock_price(code):
    """
    日本株の現在価格を取得
    例: 7203 → 7203.T
    """

    ticker = yf.Ticker(f"{code}.T")

    try:
        info = ticker.fast_info

        return {
            "price": info.get("lastPrice"),
            "previous_close": info.get("previousClose"),
        }

    except Exception:
        return None