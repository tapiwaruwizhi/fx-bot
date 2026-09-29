"""News aggregation from FX-focused RSS feeds.

Fetches headlines, tags them with currency pairs mentioned, and applies a
simple lexicon-based sentiment score. Real sentiment (LLM / VADER / FinBERT)
can drop in later behind the same interface.
"""
from __future__ import annotations
import hashlib
import re
from datetime import datetime, timezone
from typing import List

import feedparser
import httpx

from config import settings
from models import NewsItem


# Currencies and common tickers that appear in headlines
CURRENCY_ALIASES = {
    "USD": ["USD", "dollar", "greenback", "buck"],
    "EUR": ["EUR", "euro"],
    "GBP": ["GBP", "sterling", "pound", "cable"],
    "JPY": ["JPY", "yen"],
    "AUD": ["AUD", "aussie"],
    "CAD": ["CAD", "loonie"],
    "CHF": ["CHF", "swiss franc", "franc"],
    "NZD": ["NZD", "kiwi"],
}

BULLISH_WORDS = {
    "surge", "rally", "gain", "jump", "rise", "climb", "strengthen",
    "boost", "soar", "beat", "outperform", "upgrade", "hawkish", "strong",
}
BEARISH_WORDS = {
    "fall", "drop", "plunge", "decline", "weaken", "slump", "tumble",
    "miss", "underperform", "downgrade", "dovish", "weak", "crash", "sell-off",
}


def _detect_pairs(text: str) -> List[str]:
    """Return list of pairs like 'EURUSD' inferred from text."""
    text_l = text.lower()
    found = set()
    for code, aliases in CURRENCY_ALIASES.items():
        for a in aliases:
            if re.search(rf"\b{re.escape(a.lower())}\b", text_l):
                found.add(code)
                break
    # Build pairs against USD if USD or another currency is present
    codes = list(found)
    pairs = []
    for i, a in enumerate(codes):
        for b in codes[i + 1 :]:
            pair = f"{a}{b}" if a == "USD" or b != "USD" else f"{b}{a}"
            # Normalize to conventional quote order
            if a == "USD" and b in {"JPY", "CAD", "CHF"}:
                pair = f"USD{b}"
            elif b == "USD" and a in {"EUR", "GBP", "AUD", "NZD"}:
                pair = f"{a}USD"
            pairs.append(pair)
    # Also emit single-currency tag so UI can filter
    return sorted(set(pairs)) or sorted(found)


def _score_sentiment(text: str) -> tuple[str, float]:
    """Very simple bag-of-words score in [-1, 1]."""
    tokens = re.findall(r"\b[a-zA-Z-]+\b", text.lower())
    if not tokens:
        return "neutral", 0.0
    pos = sum(1 for t in tokens if t in BULLISH_WORDS)
    neg = sum(1 for t in tokens if t in BEARISH_WORDS)
    if pos == 0 and neg == 0:
        return "neutral", 0.0
    score = (pos - neg) / max(pos + neg, 1)
    label = "bullish" if score > 0.15 else "bearish" if score < -0.15 else "neutral"
    return label, round(score, 3)


def _make_id(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:12]


async def _fetch_feed(client: httpx.AsyncClient, url: str) -> List[NewsItem]:
    try:
        r = await client.get(url, timeout=15.0, follow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        print(f"[news] {url} failed: {e}")
        return []

    parsed = feedparser.parse(r.text)
    source = parsed.feed.get("title", url)
    items: List[NewsItem] = []
    for entry in parsed.entries[:30]:
        title = entry.get("title", "").strip()
        summary = re.sub(r"<[^>]+>", "", entry.get("summary", ""))[:400].strip()
        link = entry.get("link", "")
        if not (title and link):
            continue
        published = _parse_time(entry)
        text = f"{title}. {summary}"
        label, score = _score_sentiment(text)
        items.append(
            NewsItem(
                id=_make_id(link),
                title=title,
                summary=summary,
                url=link,
                source=source,
                published=published,
                sentiment=label,
                sentiment_score=score,
                pairs=_detect_pairs(text),
            )
        )
    return items


def _parse_time(entry) -> datetime:
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            return datetime(*val[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


async def fetch_all_news() -> List[NewsItem]:
    """Fetch every configured feed in parallel, dedupe by URL, newest first."""
    async with httpx.AsyncClient(headers={"User-Agent": "fx-bot/0.1"}) as client:
        results: List[NewsItem] = []
        for feed in settings.news_feeds:
            results.extend(await _fetch_feed(client, feed))

    seen = set()
    unique: List[NewsItem] = []
    for item in sorted(results, key=lambda i: i.published, reverse=True):
        if item.url in seen:
            continue
        seen.add(item.url)
        unique.append(item)
    return unique[:100]
