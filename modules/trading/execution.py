"""FXデモ注文の約定価格・取引時間シミュレーション。"""

from datetime import datetime
from zoneinfo import ZoneInfo


PAIR_SPREAD_PIPS = {
    "USD/JPY": 0.2,
    "EUR/JPY": 0.5,
    "GBP/JPY": 0.8,
}
JPY_PIP_SIZE = 0.01


def is_trading_time(config, now=None):
    """日本時間を基準に、モードで許可された取引時間か判定する。"""

    current = now or datetime.now(ZoneInfo("Asia/Tokyo"))
    if current.tzinfo is None:
        current = current.replace(tzinfo=ZoneInfo("Asia/Tokyo"))
    else:
        current = current.astimezone(ZoneInfo("Asia/Tokyo"))
    if current.weekday() >= 5:
        return False

    start_hour, end_hour = config["trading_hours_jst"]
    if start_hour == end_hour:
        return True
    if start_hour < end_hour:
        return start_hour <= current.hour < end_hour
    return current.hour >= start_hour or current.hour < end_hour


def execution_price(pair, mid_price, action, slippage_pips):
    """BUY/SELLに応じて不利なスプレッドとスリッページを加える。"""

    spread_pips = PAIR_SPREAD_PIPS[pair]
    half_spread = spread_pips * JPY_PIP_SIZE / 2
    slippage = slippage_pips * JPY_PIP_SIZE
    adjustment = half_spread + slippage
    price = mid_price + adjustment if action == "BUY" else mid_price - adjustment
    return price, spread_pips


def estimated_execution_cost(pair, units, slippage_pips):
    """ミッド価格約定との差を円換算した概算コスト。"""

    spread_pips = PAIR_SPREAD_PIPS[pair]
    return units * (spread_pips / 2 + slippage_pips) * JPY_PIP_SIZE


def liquidation_price(pair, mid_price, position_side):
    """保有ポジションを即時決済した場合のスプレッド込み評価価格。"""

    half_spread = PAIR_SPREAD_PIPS[pair] * JPY_PIP_SIZE / 2
    return mid_price - half_spread if position_side == "LONG" else mid_price + half_spread
