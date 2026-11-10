"""Live results of the bot's demo trades, read from MT5's deal history.

Used by GET /api/stats. Only positions the bot opened (MT5_MAGIC) count;
profit includes swap and commission.
"""
from __future__ import annotations

from services import mt5_client


def summarize(trades: list[dict], days: int) -> dict:
    profits = [t["profit"] for t in trades]
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]
    gross_profit, gross_loss = sum(wins), -sum(losses)
    n = len(profits)

    by_pair: dict[str, dict] = {}
    by_reason: dict[str, int] = {}
    for t in trades:
        bp = by_pair.setdefault(t["symbol"], {"trades": 0, "wins": 0, "net_profit": 0.0})
        bp["trades"] += 1
        bp["wins"] += t["profit"] > 0
        bp["net_profit"] = round(bp["net_profit"] + t["profit"], 2)
        by_reason[t["close_reason"]] = by_reason.get(t["close_reason"], 0) + 1

    return {
        "days": days,
        "trades": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(len(wins) / n * 100, 1) if n else None,
        "net_profit": round(sum(profits), 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        # > 1 means winners made more than losers lost
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss else None,
        "avg_win": round(gross_profit / len(wins), 2) if wins else None,
        "avg_loss": round(-gross_loss / len(losses), 2) if losses else None,
        "by_pair": dict(sorted(by_pair.items(), key=lambda kv: kv[1]["net_profit"])),
        "by_close_reason": by_reason,
        "recent": list(reversed(trades[-20:])),
    }


def bot_trade_stats(days: int = 30) -> dict:
    connected = mt5_client.connect()
    trades = mt5_client.bot_deals(days) if connected else []
    return {"connected": connected, **summarize(trades, days)}
