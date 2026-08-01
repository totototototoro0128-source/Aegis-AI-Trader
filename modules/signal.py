from modules.stock import get_stock_price
from modules.technical import get_ma, get_rsi, get_macd


def analyze_stock(code):
    """
    売買シグナルを判定する
    """

    score = 0
    reasons = []

    stock = get_stock_price(code)

    if stock is None:
        return None

    price = stock["price"]

    ma25 = get_ma(code)
    ma75 = get_ma(code, 75)
    rsi = get_rsi(code)
    macd = get_macd(code)

    # 株価 > 25日MA
    if price > ma25:
        score += 30
        reasons.append("株価が25日移動平均より上")

    # 25日MA > 75日MA
    if ma25 > ma75:
        score += 20
        reasons.append("25日MAが75日MAより上")

    # RSI
    if 30 <= rsi <= 70:
        score += 20
        reasons.append("RSIが適正")

    # MACD
    if macd["MACD"].iloc[-1] > macd["Signal"].iloc[-1]:
        score += 30
        reasons.append("MACDが買いシグナル")

    return {
        "score": score,
        "reasons": reasons,
    }