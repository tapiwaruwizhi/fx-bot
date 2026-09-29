"""FX price ticks via yfinance (delayed, free)."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import List

import yfinance as yf

from config import settings
from models import PriceTick


def fetch_prices() -> List[PriceTick]:
    ticks: List[PriceTick] = []
    tickers = yf.Tickers(" ".join(settings.fx_pairs))
    for symbol in settings.fx_pairs:
        try:
            t = tickers.tickers[symbol]
            hist = t.history(period="2d", interval="1d")
            if hist.empty:
                continue
            last = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last
            change_pct = ((last - prev) / prev) * 100 if prev else 0.0
            ticks.append(
                PriceTick(
                    pair=symbol.replace("=X", ""),
                    price=round(last, 5),
                    change_pct=round(change_pct, 3),
                    timestamp=datetime.now(timezone.utc),
                )
            )
        except Exception as e:
            print(f"[prices] {symbol} failed: {e}")
    return ticks
