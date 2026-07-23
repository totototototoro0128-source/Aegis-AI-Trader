import yfinance as yf


def get_history(code, period="6mo"):
    """
    株価履歴を取得する
    """

    ticker = yf.Ticker(f"{code}.T")

    history = ticker.history(period=period)

    return history.dropna()


def get_ma(code, days=25):
    """
    移動平均線を取得
    """

    history = get_history(code)

    if len(history) < days:
        return None

    ma = history["Close"].rolling(days).mean().dropna()

    if ma.empty:
        return None

    return float(ma.iloc[-1])


def get_rsi(code, period=14):
    """
    RSIを取得
    """

    history = get_history(code)

    if len(history) < period:
        return None

    close = history["Close"]

    delta = close.diff()

    gain = delta.where(delta > 0, 0)

    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(period).mean()

    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    rsi = rsi.dropna()

    if rsi.empty:
        return None

    return float(rsi.iloc[-1])