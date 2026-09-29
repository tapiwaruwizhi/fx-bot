"""Pydantic schemas shared by services and API."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class NewsItem(BaseModel):
    id: str
    title: str
    summary: str
    url: str
    source: str
    published: datetime
    sentiment: Optional[str] = None   # "bullish" | "bearish" | "neutral"
    sentiment_score: Optional[float] = None
    pairs: List[str] = []             # e.g. ["EURUSD", "USDJPY"]


class PriceTick(BaseModel):
    pair: str
    price: float
    change_pct: float
    timestamp: datetime


class Signal(BaseModel):
    pair: str
    direction: str        # "BUY" | "SELL" | "HOLD"
    strength: float       # 0..1
    strategy: str         # e.g. "SMA_20_50_cross"
    reason: str
    generated_at: datetime


class CalendarEvent(BaseModel):
    id: str
    time: datetime
    currency: str
    title: str
    impact: str           # "low" | "medium" | "high"
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None


class DashboardSnapshot(BaseModel):
    prices: List[PriceTick]
    news: List[NewsItem]
    signals: List[Signal]
    calendar: List[CalendarEvent]
    generated_at: datetime
