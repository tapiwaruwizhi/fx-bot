"""When the auto-trader is allowed to open trades.

Spot FX trades from Sunday 17:00 to Friday 17:00 New York time. The trader
skips:
  * the weekend, when the market is closed
  * the first AUTO_TRADE_SKIP_AFTER_OPEN_HOURS after the Sunday open
    (thin liquidity, wide spreads, price gaps from Friday's close)
  * the last AUTO_TRADE_STOP_BEFORE_CLOSE_HOURS before the Friday close
    (so new trades aren't left open over the weekend gap)

New York daylight saving is handled here (2nd Sunday of March to 1st Sunday
of November), so no timezone package is needed. Bank holidays aren't
covered; MT5 rejects orders on those days anyway ("Market closed").
"""
from __future__ import annotations
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, Tuple

from config import settings

OPEN_HOUR_NY = 17  # Sunday open and Friday close, New York local time


def _nth_sunday(year: int, month: int, n: int) -> date:
    first = date(year, month, 1)
    first_sunday = first + timedelta(days=(6 - first.weekday()) % 7)
    return first_sunday + timedelta(weeks=n - 1)


def _ny_offset(utc_dt: datetime) -> timedelta:
    """New York's UTC offset at a UTC moment (-4h in summer, -5h in winter)."""
    y = utc_dt.year
    dst_start = datetime.combine(_nth_sunday(y, 3, 2), time(7), timezone.utc)   # 02:00 EST
    dst_end = datetime.combine(_nth_sunday(y, 11, 1), time(6), timezone.utc)    # 02:00 EDT
    return timedelta(hours=-4) if dst_start <= utc_dt < dst_end else timedelta(hours=-5)


def _ny_to_utc(ny_naive: datetime) -> datetime:
    guess = ny_naive.replace(tzinfo=timezone.utc) + timedelta(hours=5)
    return ny_naive.replace(tzinfo=timezone.utc) - _ny_offset(guess)


def week_bounds(now: Optional[datetime] = None) -> Tuple[datetime, datetime, datetime]:
    """(this week's open, this week's close, next week's open), all in UTC."""
    now = now or datetime.now(timezone.utc)
    now_ny = (now + _ny_offset(now)).replace(tzinfo=None)
    days_since_sunday = (now_ny.weekday() + 1) % 7  # Mon=1 ... Sun=0
    open_ny = (now_ny - timedelta(days=days_since_sunday)).replace(
        hour=OPEN_HOUR_NY, minute=0, second=0, microsecond=0
    )
    if open_ny > now_ny:  # Sunday before 17:00 -> week started last Sunday
        open_ny -= timedelta(days=7)
    week_open = _ny_to_utc(open_ny)
    week_close = _ny_to_utc(open_ny + timedelta(days=5))
    next_open = _ny_to_utc(open_ny + timedelta(days=7))
    return week_open, week_close, next_open


def _fmt(dt: datetime) -> str:
    """Show times in this computer's local timezone."""
    return dt.astimezone().strftime("%a %d %b %H:%M")


def trading_window(now: Optional[datetime] = None) -> Tuple[bool, str]:
    """(allowed, reason) for opening new auto-trades right now."""
    now = now or datetime.now(timezone.utc)
    week_open, week_close, next_open = week_bounds(now)
    skip_open = timedelta(hours=settings.auto_trade_skip_after_open_hours)
    stop_close = timedelta(hours=settings.auto_trade_stop_before_close_hours)
    resume = next_open + skip_open

    if now >= week_close:
        return False, f"weekend: market closed, trading resumes {_fmt(resume)}"
    if now < week_open + skip_open:
        return False, f"first {settings.auto_trade_skip_after_open_hours:g}h after weekly open, trading resumes {_fmt(week_open + skip_open)}"
    if now >= week_close - stop_close:
        return False, f"last {settings.auto_trade_stop_before_close_hours:g}h before weekly close, trading resumes {_fmt(resume)}"
    return True, f"open until {_fmt(week_close - stop_close)}"
