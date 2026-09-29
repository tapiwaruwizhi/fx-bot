"""Technical signal generation.

Starter strategies:
  * SMA(20) vs SMA(50) crossover on daily bars
  * RSI(14) overbought/oversold

Replace / extend with your own strategies. Each returns a Signal object
with strength in [0, 1].
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

from config import settings
from models import Signal


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _sma_cross(df: pd.DataFrame, pair: str) -> Optional[Signal]:
    if len(df) < 55:
        return None
    close = df["Close"]
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    prev_diff = sma20.iloc[-2] - sma50.iloc[-2]
    curr_diff = sma20.iloc[-1] - sma50.iloc[-1]
    if prev_diff <= 0 < curr_diff:
        direction, reason = "BUY", "SMA(20) crossed above SMA(50)"
    elif prev_diff >= 0 > curr_diff:
        direction, reason = "SELL", "SMA(20) crossed below SMA(50)"
    else:
        direction = "BUY" if curr_diff > 0 else "SELL"
        reason = f"SMA(20) {'above' if curr_diff > 0 else 'below'} SMA(50)"
    strength = float(min(abs(curr_diff) / close.iloc[-1] * 100, 1.0))
    return Signal(
        pair=pair,
        direction=direction,
        strength=round(strength, 3),
        strategy="SMA_20_50_cross",
        reason=reason,
        generated_at=datetime.now(timezone.utc),
    )


def _rsi_signal(df: pd.DataFrame, pair: str) -> Optional[Signal]:
    if len(df) < 20:
        return None
    rsi = _rsi(df["Close"])
    val = float(rsi.iloc[-1])
    if np.isnan(val):
        return None
    if val < 30:
        direction, reason, strength = "BUY", f"RSI={val:.1f} (oversold)", (30 - val) / 30
    elif val > 70:
        direction, reason, strength = "SELL", f"RSI={val:.1f} (overbought)", (val - 70) / 30
    else:
        direction, reason, strength = "HOLD", f"RSI={val:.1f}", 0.0
    return Signal(
        pair=pair,
        direction=direction,
        strength=round(min(strength, 1.0), 3),
        strategy="RSI_14",
        reason=reason,
        generated_at=datetime.now(timezone.utc),
    )


def generate_signals() -> List[Signal]:
    signals: List[Signal] = []
    for symbol in settings.fx_pairs:
        try:
            df = yf.download(symbol, period="6mo", interval="1d", progress=False, auto_adjust=True)
            if df.empty:
                continue
            # yfinance sometimes returns MultiIndex columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            pair = symbol.replace("=X", "")
            for fn in (_sma_cross, _rsi_signal):
                sig = fn(df, pair)
                if sig:
                    signals.append(sig)
        except Exception as e:
            print(f"[signals] {symbol} failed: {e}")
    return signals
