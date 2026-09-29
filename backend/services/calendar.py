"""Economic calendar.

Uses Investing.com's public economic-calendar JSON via a simple scrape.
Swap in ForexFactory or a paid API later — the returned schema stays the same.
For MVP, if scraping fails we return an empty list rather than crashing.
"""
from __future__ import annotations
import hashlib
import re
from datetime import datetime, timezone, timedelta
from typing import List

import httpx
from bs4 import BeautifulSoup

from models import CalendarEvent


IMPACT_MAP = {"grayFullBullishIcon": "low", "grayFullBullishIcon2": "medium", "grayFullBullishIcon3": "high"}


async def fetch_calendar() -> List[CalendarEvent]:
    """Best-effort scrape of investing.com economic calendar (today + tomorrow)."""
    events: List[CalendarEvent] = []
    url = "https://www.investing.com/economic-calendar/"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; fx-bot/0.1)",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
            r = await client.get(url, follow_redirects=True)
            r.raise_for_status()
    except Exception as e:
        print(f"[calendar] fetch failed: {e}")
        return events

    soup = BeautifulSoup(r.text, "html.parser")
    rows = soup.select("tr.js-event-item")
    now = datetime.now(timezone.utc)
    for row in rows:
        try:
            time_str = row.get("data-event-datetime", "")
            if not time_str:
                continue
            try:
                dt = datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if dt < now - timedelta(hours=6) or dt > now + timedelta(days=2):
                continue
            currency = row.select_one("td.flagCur")
            currency = currency.get_text(strip=True) if currency else ""
            title_el = row.select_one("td.event a")
            title = title_el.get_text(strip=True) if title_el else ""
            impact_el = row.select_one("td.sentiment")
            impact = "low"
            if impact_el:
                bulls = len(impact_el.select("i.grayFullBullishIcon"))
                impact = {1: "low", 2: "medium", 3: "high"}.get(bulls, "low")
            actual = _cell(row, "td.act")
            forecast = _cell(row, "td.fore")
            previous = _cell(row, "td.prev")
            events.append(
                CalendarEvent(
                    id=hashlib.sha1(f"{time_str}{currency}{title}".encode()).hexdigest()[:12],
                    time=dt,
                    currency=currency,
                    title=title,
                    impact=impact,
                    actual=actual or None,
                    forecast=forecast or None,
                    previous=previous or None,
                )
            )
        except Exception as e:
            print(f"[calendar] row skipped: {e}")
            continue
    return events


def _cell(row, selector: str) -> str:
    el = row.select_one(selector)
    if not el:
        return ""
    return re.sub(r"\s+", " ", el.get_text(strip=True))
