"""Latest FX prices: live MT5 ticks when connected, else daily ECB rates via Frankfurter."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import List

from config import settings
from models import PriceTick
from services import mt5_client
from services.market_data import usd_history, pair_series


def _mt5_prices() -> List[PriceTick]:
    """Live bid from MT5; change % is vs. the previous daily close."""
    ticks: List[PriceTick] = []
    for pair in settings.fx_pairs:
        try:
            t = mt5_client.tick(pair)
            daily = mt5_client.rates(pair, count=2, timeframe="D1")
            prev = float(daily["Close"].iloc[0])
            change_pct = (t.bid - prev) / prev * 100 if prev else 0.0
            ticks.append(
                PriceTick(
                    pair=pair,
                    price=round(t.bid, 5),
                    change_pct=round(change_pct, 3),
                    # tick.time is in the broker's server timezone, not UTC
                    timestamp=datetime.now(timezone.utc),
                )
            )
        except Exception as e:
            print(f"[prices] {pair} (mt5) failed: {e}")
    return ticks


def fetch_prices() -> List[PriceTick]:
    if mt5_client.connect():
        ticks = _mt5_prices()
        if ticks:
            return ticks
        print("[prices] MT5 returned no prices (check MT5_SYMBOL_SUFFIX); falling back to Frankfurter")
    try:
        df = usd_history()
    except Exception as e:
        print(f"[prices] failed: {e}")
        return []

    ticks: List[PriceTick] = []
    for pair in settings.fx_pairs:
        try:
            s = pair_series(pair, df)
            if s.empty:
                continue
            last = float(s.iloc[-1])
            prev = float(s.iloc[-2]) if len(s) > 1 else last
            change_pct = (last - prev) / prev * 100 if prev else 0.0
            ts = s.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
            ticks.append(
                PriceTick(
                    pair=pair,
                    price=round(last, 5),
                    change_pct=round(change_pct, 3),
                    timestamp=ts,
                )
            )
        except Exception as e:
            print(f"[prices] {pair} failed: {e}")
    return ticks
