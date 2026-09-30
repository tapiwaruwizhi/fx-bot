"""Daily FX rates from Frankfurter (European Central Bank reference rates).

Free, no API key, and not blocked on cloud hosts like Render.
Limitation: one rate per business day (published ~16:00 CET), so this is
fine for daily-bar signals but NOT for intraday trading. Swap this module
for a broker feed (e.g. OANDA) when you need live prices.
"""
from __future__ import annotations
import time
from datetime import date, timedelta

import httpx
import pandas as pd

from config import settings

BASE_URLS = ["https://api.frankfurter.dev/v1", "https://api.frankfurter.app"]
CACHE_TTL_SECS = 3600  # ECB publishes once a day; hourly re-fetch is plenty

_cache: dict = {"ts": 0.0, "df": None}


def _currencies() -> list[str]:
    cur: set[str] = set()
    for p in settings.fx_pairs:
        cur.update({p[:3], p[3:]})
    cur.discard("USD")
    return sorted(cur)


def usd_history(days: int = 270) -> pd.DataFrame:
    """DataFrame indexed by date; column X = units of X per 1 USD (USD column = 1)."""
    if _cache["df"] is not None and time.time() - _cache["ts"] < CACHE_TTL_SECS:
        return _cache["df"]

    start = (date.today() - timedelta(days=days)).isoformat()
    params = {"from": "USD", "to": ",".join(_currencies())}
    last_err: Exception | None = None
    for base in BASE_URLS:
        try:
            r = httpx.get(f"{base}/{start}..", params=params, timeout=20.0, follow_redirects=True)
            r.raise_for_status()
            df = pd.DataFrame.from_dict(r.json()["rates"], orient="index")
            df.index = pd.to_datetime(df.index)
            df = df.sort_index().astype(float)
            df["USD"] = 1.0
            _cache.update(ts=time.time(), df=df)
            return df
        except Exception as e:  # try next mirror
            last_err = e
            print(f"[market_data] {base} failed: {e}")

    if _cache["df"] is not None:  # serve stale data rather than nothing
        print("[market_data] using stale cache")
        return _cache["df"]
    raise RuntimeError(f"all rate sources failed: {last_err}")


def pair_series(pair: str, usd_df: pd.DataFrame) -> pd.Series:
    """Close series for e.g. 'EURUSD' = quote units per 1 base unit."""
    base, quote = pair[:3], pair[3:]
    return (usd_df[quote] / usd_df[base]).dropna()
