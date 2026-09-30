"""Economic calendar from ForexFactory's public weekly JSON feed.

No API key. The feed only includes the current week and doesn't carry
'actual' values, so those show as empty. It is rate-limited, so we refresh
every 30 min (see calendar_refresh_secs in config.py).
"""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from typing import List

import httpx

from models import CalendarEvent

FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
VALID_IMPACT = {"low", "medium", "high"}


async def fetch_calendar() -> List[CalendarEvent]:
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (compatible; fx-bot/0.1)"}, timeout=15.0
        ) as client:
            r = await client.get(FF_URL, follow_redirects=True)
            r.raise_for_status()
            rows = r.json()
    except Exception as e:
        print(f"[calendar] fetch failed: {e}")
        return []

    events: List[CalendarEvent] = []
    for row in rows:
        try:
            dt = datetime.fromisoformat(row["date"]).astimezone(timezone.utc)
            impact = str(row.get("impact", "low")).lower()
            if impact not in VALID_IMPACT:  # e.g. "Holiday"
                impact = "low"
            currency = row.get("country", "")
            title = row.get("title", "")
            events.append(
                CalendarEvent(
                    id=hashlib.sha1(f"{row['date']}{currency}{title}".encode()).hexdigest()[:12],
                    time=dt,
                    currency=currency,
                    title=title,
                    impact=impact,
                    actual=row.get("actual") or None,
                    forecast=row.get("forecast") or None,
                    previous=row.get("previous") or None,
                )
            )
        except Exception as e:
            print(f"[calendar] row skipped: {e}")
    return sorted(events, key=lambda e: e.time)