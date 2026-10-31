"""Auto-trading: turn signals into MT5 market orders.

OFF by default (AUTO_TRADE_ENABLED=false). Even when on, it refuses to
trade unless the connected MT5 account is a DEMO account.

Rule per pair:
  * net score = sum(strength for BUY signals) - sum(strength for SELL signals)
  * net >=  AUTO_TRADE_MIN_SCORE  -> want LONG
  * net <= -AUTO_TRADE_MIN_SCORE  -> want SHORT
  * otherwise                     -> do nothing
  * no new trades on the weekend, or just after the Sunday open / before
    the Friday close (see services/market_hours.py)
  * at most one bot position per pair (identified by the magic number);
    an opposite position is closed before the new one is opened.
"""
from __future__ import annotations
from collections import defaultdict
from typing import List

from config import settings
from models import Signal
from services import market_hours, mt5_client


def _net_scores(signals: List[Signal]) -> dict[str, float]:
    net: dict[str, float] = defaultdict(float)
    for s in signals:
        if s.direction == "BUY":
            net[s.pair] += s.strength
        elif s.direction == "SELL":
            net[s.pair] -= s.strength
    return net


def run(signals: List[Signal]) -> list[dict]:
    """Act on the latest signals. Returns a log of actions taken."""
    if not settings.auto_trade_enabled:
        return []
    allowed, reason = market_hours.trading_window()
    if not allowed:
        print(f"[trader] not trading: {reason}")
        return []
    if not mt5_client.connect():
        print("[trader] MT5 not connected; skipping")
        return []
    if not mt5_client.is_demo():
        print("[trader] REFUSING to trade: connected account is not a demo account")
        return []

    open_by_symbol = {p["symbol"]: p for p in mt5_client.positions(bot_only=True)}
    actions: list[dict] = []

    for pair, score in _net_scores(signals).items():
        if score >= settings.auto_trade_min_score:
            want = "BUY"
        elif score <= -settings.auto_trade_min_score:
            want = "SELL"
        else:
            continue

        sym = mt5_client.symbol(pair)
        existing = open_by_symbol.get(sym)
        try:
            if existing and existing["type"] == want:
                continue  # already positioned
            if existing:
                res = mt5_client.close_position(existing["ticket"])
                actions.append({"pair": pair, "action": "CLOSE", "ticket": existing["ticket"], **res})
                if not res["ok"]:
                    continue
                open_by_symbol.pop(sym, None)
            elif len(open_by_symbol) >= settings.auto_trade_max_positions:
                continue

            res = mt5_client.open_market(
                pair,
                want,
                volume=settings.auto_trade_volume,
                sl_pips=settings.auto_trade_sl_pips,
                tp_pips=settings.auto_trade_tp_pips,
                comment=f"fx-bot {score:+.2f}",
            )
            actions.append({"pair": pair, "action": want, "score": round(score, 3), **res})
            if res["ok"]:
                open_by_symbol[sym] = {"type": want, "ticket": res.get("order")}
        except Exception as e:
            actions.append({"pair": pair, "action": want, "ok": False, "comment": str(e)})

    for a in actions:
        print(f"[trader] {a}")
    return actions
