"""FastAPI entrypoint for the FX bot.

Endpoints
---------
GET  /health              — liveness
GET  /api/news            — latest headlines
GET  /api/signals         — current signals
GET  /api/prices          — latest FX prices
GET  /api/calendar        — economic calendar
GET  /api/snapshot        — everything in one call (used by dashboard on load)
WS   /ws                  — pushes snapshots as they refresh
"""
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Set

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models import DashboardSnapshot, NewsItem, PriceTick, Signal, CalendarEvent
from services.news import fetch_all_news
from services.prices import fetch_prices
from services.signals import generate_signals
from services.calendar import fetch_calendar


# --- in-memory cache -------------------------------------------------------

class Cache:
    news: List[NewsItem] = []
    prices: List[PriceTick] = []
    signals: List[Signal] = []
    calendar: List[CalendarEvent] = []
    updated_at: datetime = datetime.now(timezone.utc)

    @classmethod
    def snapshot(cls) -> DashboardSnapshot:
        return DashboardSnapshot(
            prices=cls.prices,
            news=cls.news,
            signals=cls.signals,
            calendar=cls.calendar,
            generated_at=cls.updated_at,
        )


# --- websocket hub ---------------------------------------------------------

class Hub:
    def __init__(self) -> None:
        self.clients: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.clients.discard(ws)

    async def broadcast(self, payload: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self.clients:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


hub = Hub()


# --- refresh jobs ----------------------------------------------------------

async def refresh_news() -> None:
    Cache.news = await fetch_all_news()
    Cache.updated_at = datetime.now(timezone.utc)
    await hub.broadcast({"type": "news", "data": [n.model_dump(mode="json") for n in Cache.news]})


async def refresh_prices() -> None:
    Cache.prices = await asyncio.to_thread(fetch_prices)
    Cache.updated_at = datetime.now(timezone.utc)
    await hub.broadcast({"type": "prices", "data": [p.model_dump(mode="json") for p in Cache.prices]})


async def refresh_signals() -> None:
    Cache.signals = await asyncio.to_thread(generate_signals)
    Cache.updated_at = datetime.now(timezone.utc)
    await hub.broadcast({"type": "signals", "data": [s.model_dump(mode="json") for s in Cache.signals]})


async def refresh_calendar() -> None:
    Cache.calendar = await fetch_calendar()
    Cache.updated_at = datetime.now(timezone.utc)
    await hub.broadcast({"type": "calendar", "data": [c.model_dump(mode="json") for c in Cache.calendar]})


# --- lifespan --------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Prime the cache
    await asyncio.gather(
        refresh_news(),
        refresh_prices(),
        refresh_signals(),
        refresh_calendar(),
        return_exceptions=True,
    )

    scheduler = AsyncIOScheduler()
    scheduler.add_job(refresh_news, "interval", seconds=settings.news_refresh_secs)
    scheduler.add_job(refresh_prices, "interval", seconds=settings.prices_refresh_secs)
    scheduler.add_job(refresh_signals, "interval", seconds=settings.signals_refresh_secs)
    scheduler.add_job(refresh_calendar, "interval", seconds=settings.news_refresh_secs)
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="FX Bot", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- routes ----------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {"ok": True, "updated_at": Cache.updated_at.isoformat()}


@app.get("/api/news", response_model=List[NewsItem])
def get_news() -> List[NewsItem]:
    return Cache.news


@app.get("/api/prices", response_model=List[PriceTick])
def get_prices() -> List[PriceTick]:
    return Cache.prices


@app.get("/api/signals", response_model=List[Signal])
def get_signals() -> List[Signal]:
    return Cache.signals


@app.get("/api/calendar", response_model=List[CalendarEvent])
def get_calendar() -> List[CalendarEvent]:
    return Cache.calendar


@app.get("/api/snapshot", response_model=DashboardSnapshot)
def get_snapshot() -> DashboardSnapshot:
    return Cache.snapshot()


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await hub.connect(ws)
    try:
        # Send initial snapshot on connect
        await ws.send_json({"type": "snapshot", "data": Cache.snapshot().model_dump(mode="json")})
        while True:
            await ws.receive_text()  # keepalive / ignore client msgs
    except WebSocketDisconnect:
        hub.disconnect(ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
