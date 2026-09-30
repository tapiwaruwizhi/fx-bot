"""Latest FX prices (daily ECB reference rates via Frankfurter)."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import List

from config import settings
from models import PriceTick
from services.market_data import usd_history, pair_series


def fetch_prices() -> List[PriceTick]:
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
