"""MetaTrader 5 connection (ADS Securities demo, or any MT5 broker).

Requirements:
  * Windows, with the MT5 terminal installed on the same machine
  * `pip install MetaTrader5`
  * MT5_ENABLED=true plus MT5_LOGIN / MT5_PASSWORD / MT5_SERVER in .env

The MetaTrader5 package talks to one terminal through a global connection
and is not thread-safe, so every call goes through `_lock`.
"""
from __future__ import annotations
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd

from config import settings

try:
    import MetaTrader5 as mt5
except ImportError:  # non-Windows host, or package not installed
    mt5 = None

_lock = threading.RLock()
_connected = False

TIMEFRAMES = {
    "M5": "TIMEFRAME_M5",
    "M15": "TIMEFRAME_M15",
    "M30": "TIMEFRAME_M30",
    "H1": "TIMEFRAME_H1",
    "H4": "TIMEFRAME_H4",
    "D1": "TIMEFRAME_D1",
}


def enabled() -> bool:
    return settings.mt5_enabled and mt5 is not None


def connect() -> bool:
    """Initialise the terminal and log in. Safe to call repeatedly."""
    global _connected
    if not enabled():
        return False
    with _lock:
        if _connected and mt5.terminal_info() is not None:
            return True
        # No password in .env -> attach to whatever account the terminal is
        # already logged into (needs "Save password" ticked in the terminal).
        kwargs: dict = dict(timeout=20_000)
        if settings.mt5_password:
            kwargs.update(
                login=settings.mt5_login,
                password=settings.mt5_password,
                server=settings.mt5_server,
            )
        if settings.mt5_path:
            kwargs["path"] = settings.mt5_path
        if not mt5.initialize(**kwargs):
            print(f"[mt5] initialize failed: {mt5.last_error()}")
            _connected = False
            return False
        info = mt5.account_info()
        if info is None:
            print(f"[mt5] terminal started but no account is logged in: {mt5.last_error()}")
            mt5.shutdown()
            _connected = False
            return False
        _connected = True
        print(f"[mt5] connected: login={info.login} server={info.server} demo={is_demo()}")
        return True


def shutdown() -> None:
    global _connected
    if mt5 is not None:
        with _lock:
            mt5.shutdown()
            _connected = False


def is_demo() -> bool:
    with _lock:
        info = mt5.account_info()
    return info is not None and info.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO


def symbol(pair: str) -> str:
    """Broker symbol for a pair, e.g. 'EURUSD' -> 'EURUSD.r' if a suffix is set."""
    return f"{pair}{settings.mt5_symbol_suffix}"


def _ensure_symbol(sym: str) -> None:
    if not mt5.symbol_select(sym, True):
        raise RuntimeError(f"symbol {sym} not available: {mt5.last_error()}")


def rates(pair: str, count: int = 300, timeframe: Optional[str] = None) -> pd.DataFrame:
    """OHLC bars, oldest first, indexed by UTC time. Columns: Open/High/Low/Close."""
    if not connect():
        raise RuntimeError("MT5 not connected")
    tf = getattr(mt5, TIMEFRAMES[timeframe or settings.mt5_timeframe])
    sym = symbol(pair)
    with _lock:
        _ensure_symbol(sym)
        data = mt5.copy_rates_from_pos(sym, tf, 0, count)
    if data is None or len(data) == 0:
        raise RuntimeError(f"no rates for {sym}: {mt5.last_error()}")
    df = pd.DataFrame(data)
    df.index = pd.to_datetime(df["time"], unit="s", utc=True)
    return df.rename(columns=str.capitalize)[["Open", "High", "Low", "Close"]]


def tick(pair: str):
    if not connect():
        raise RuntimeError("MT5 not connected")
    sym = symbol(pair)
    with _lock:
        _ensure_symbol(sym)
        t = mt5.symbol_info_tick(sym)
    if t is None:
        raise RuntimeError(f"no tick for {sym}: {mt5.last_error()}")
    return t


def account() -> Optional[dict]:
    if not connect():
        return None
    with _lock:
        info = mt5.account_info()
    if info is None:
        return None
    return {
        "login": info.login,
        "server": info.server,
        "name": info.name,
        "currency": info.currency,
        "balance": info.balance,
        "equity": info.equity,
        "margin": info.margin,
        "margin_free": info.margin_free,
        "profit": info.profit,
        "leverage": info.leverage,
        "demo": info.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO,
        "trade_allowed": bool(info.trade_allowed),
    }


def positions(bot_only: bool = False) -> list[dict]:
    if not connect():
        return []
    with _lock:
        raw = mt5.positions_get() or ()
    out = []
    for p in raw:
        if bot_only and p.magic != settings.mt5_magic:
            continue
        out.append({
            "ticket": p.ticket,
            "symbol": p.symbol,
            "type": "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
            "volume": p.volume,
            "price_open": p.price_open,
            "sl": p.sl,
            "tp": p.tp,
            "profit": p.profit,
            "magic": p.magic,
            "comment": p.comment,
        })
    return out


def _filling_mode(info) -> int:
    # symbol_info.filling_mode is a bitmask: 1 = FOK allowed, 2 = IOC allowed
    if info.filling_mode & 1:
        return mt5.ORDER_FILLING_FOK
    if info.filling_mode & 2:
        return mt5.ORDER_FILLING_IOC
    return mt5.ORDER_FILLING_RETURN


def _pip(info) -> float:
    return info.point * 10 if info.digits in (3, 5) else info.point


def open_market(pair: str, direction: str, volume: float,
                sl_pips: float, tp_pips: float, comment: str) -> dict:
    """Send a market order. Caller is responsible for the demo-only check."""
    if not connect():
        raise RuntimeError("MT5 not connected")
    sym = symbol(pair)
    with _lock:
        _ensure_symbol(sym)
        info = mt5.symbol_info(sym)
        t = mt5.symbol_info_tick(sym)
        pip = _pip(info)
        if direction == "BUY":
            order_type, price = mt5.ORDER_TYPE_BUY, t.ask
            sl, tp = price - sl_pips * pip, price + tp_pips * pip
        else:
            order_type, price = mt5.ORDER_TYPE_SELL, t.bid
            sl, tp = price + sl_pips * pip, price - tp_pips * pip
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": sym,
            "volume": float(volume),
            "type": order_type,
            "price": price,
            "sl": round(sl, info.digits) if sl_pips else 0.0,
            "tp": round(tp, info.digits) if tp_pips else 0.0,
            "deviation": settings.mt5_deviation_points,
            "magic": settings.mt5_magic,
            "comment": comment[:31],  # MT5 comment limit
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": _filling_mode(info),
        }
        result = mt5.order_send(request)
    return _result(result)


def close_position(ticket: int) -> dict:
    if not connect():
        raise RuntimeError("MT5 not connected")
    with _lock:
        found = mt5.positions_get(ticket=ticket)
        if not found:
            raise RuntimeError(f"position {ticket} not found")
        p = found[0]
        info = mt5.symbol_info(p.symbol)
        t = mt5.symbol_info_tick(p.symbol)
        is_buy = p.type == mt5.POSITION_TYPE_BUY
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": p.symbol,
            "volume": p.volume,
            "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
            "position": p.ticket,
            "price": t.bid if is_buy else t.ask,
            "deviation": settings.mt5_deviation_points,
            "magic": settings.mt5_magic,
            "comment": "fx-bot close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": _filling_mode(info),
        }
        result = mt5.order_send(request)
    return _result(result)


def _result(result) -> dict:
    if result is None:
        return {"ok": False, "retcode": None, "comment": str(mt5.last_error())}
    return {
        "ok": result.retcode == mt5.TRADE_RETCODE_DONE,
        "retcode": result.retcode,
        "comment": result.comment,
        "order": result.order,
        "price": result.price,
        "volume": result.volume,
    }


# --- history (backtesting and trade stats) ---------------------------------

def history(pair: str, timeframe: str, count: int) -> tuple[pd.DataFrame, dict]:
    """Bars for backtesting, oldest first, plus facts about the symbol.

    The index is the broker's *server* time; MT5 doesn't say which timezone
    that is, so backtest.py works it out. Columns: Open/High/Low/Close and
    Spread (in price units, e.g. 0.00012).
    """
    if not connect():
        raise RuntimeError("MT5 not connected")
    tf = getattr(mt5, TIMEFRAMES[timeframe])
    sym = symbol(pair)
    with _lock:
        _ensure_symbol(sym)
        info = mt5.symbol_info(sym)
        data = mt5.copy_rates_from_pos(sym, tf, 0, count)
        t = mt5.symbol_info_tick(sym)
        pip = _pip(info)
        price = t.bid if t is not None and t.bid else None
        per_pip = (mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, sym, 1.0, price, price + pip)
                   if price else None)
    if data is None or len(data) == 0:
        raise RuntimeError(f"no history for {sym}: {mt5.last_error()}")
    df = pd.DataFrame(data)
    df.index = pd.to_datetime(df["time"], unit="s")  # naive = broker server time
    df = df.rename(columns=str.capitalize)
    df["Spread"] = df["Spread"] * info.point
    meta = {"symbol": sym, "pip": pip, "digits": info.digits,
            "profit_per_pip_per_lot": per_pip}  # in the account currency
    return df[["Open", "High", "Low", "Close", "Spread"]], meta


def bot_deals(days: int = 30) -> list[dict]:
    """The bot's closed trades (positions opened with MT5_MAGIC) from the last `days`."""
    if not connect():
        return []
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    # Deal times are broker server time, which can run ahead of UTC: pad the range,
    # and look further back for the opening deals of positions closed in range.
    with _lock:
        deals = mt5.history_deals_get(start - timedelta(days=30), now + timedelta(days=1)) or ()
    opened = {d.position_id: d for d in deals
              if d.magic == settings.mt5_magic and d.entry == mt5.DEAL_ENTRY_IN}
    reasons = {}
    for name in ("SL", "TP", "SO", "EXPERT", "CLIENT", "MOBILE", "WEB"):
        code = getattr(mt5, f"DEAL_REASON_{name}", None)
        if code is not None:
            reasons[code] = {"SO": "stop_out", "EXPERT": "bot"}.get(name, name.lower())

    out = []
    for d in deals:
        if d.position_id not in opened or d.entry not in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY):
            continue
        if d.time < start.timestamp():
            continue
        o = opened[d.position_id]
        profit = (d.profit + d.swap + d.commission + getattr(d, "fee", 0.0)
                  + o.commission + getattr(o, "fee", 0.0))
        out.append({
            "position": d.position_id,
            "symbol": d.symbol,
            "direction": "BUY" if o.type == mt5.DEAL_TYPE_BUY else "SELL",
            "volume": d.volume,
            "open_price": o.price,
            "close_price": d.price,
            "opened_server_time": datetime.utcfromtimestamp(o.time).isoformat(),
            "closed_server_time": datetime.utcfromtimestamp(d.time).isoformat(),
            "profit": round(profit, 2),
            "close_reason": reasons.get(d.reason, str(d.reason)),
        })
    return sorted(out, key=lambda t: t["closed_server_time"])
