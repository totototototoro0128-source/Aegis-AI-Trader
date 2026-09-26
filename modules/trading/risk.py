"""注文前リスク管理。"""


def calculate_position_notional(equity, config, open_positions):
    """許容損失と損切り幅から想定元本を計算する。"""

    if equity <= 0 or config["stop_loss"] <= 0:
        return 0.0

    risk_budget = equity * config["risk_per_trade"]
    risk_based_notional = risk_budget / config["stop_loss"]
    total_cap = equity * config["leverage_cap"]
    used_notional = sum(position["notional"] for position in open_positions.values())
    return max(0.0, min(risk_based_notional, total_cap - used_notional))


def may_open_position(state, config, equity):
    """新規ポジションを許可できるか判定する。"""

    if equity <= 0 or len(state["positions"]) >= config["max_positions"]:
        return False

    daily_loss = min(0.0, state.get("daily_realized_pnl", 0.0))
    if abs(daily_loss) >= state["initial_capital"] * config["daily_loss_limit"]:
        return False

    peak_equity = max(state.get("peak_equity", equity), equity)
    drawdown = (peak_equity - equity) / peak_equity if peak_equity else 0.0
    return drawdown < config["max_drawdown"]
