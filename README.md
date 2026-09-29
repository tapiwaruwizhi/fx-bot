# FX Bot — starter

Backend (Python / FastAPI) that pulls FX news, prices, technical signals, and an economic calendar; Flutter web app that renders it live over WebSocket.

## Structure

```
fx-bot/
├── backend/
│   ├── main.py              FastAPI app (REST + /ws)
│   ├── config.py            pairs, feeds, refresh cadence
│   ├── models.py            Pydantic schemas
│   ├── services/
│   │   ├── news.py          RSS aggregation + naive sentiment
│   │   ├── prices.py        yfinance FX ticks
│   │   ├── signals.py       SMA cross + RSI
│   │   └── calendar.py      Investing.com economic calendar
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── pubspec.yaml
    ├── lib/
    │   ├── main.dart
    │   ├── api.dart         REST + WS client
    │   ├── models.dart
    │   ├── screens/dashboard.dart
    │   └── widgets/         price grid, news, signals, calendar
    └── web/index.html
```

## Run

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # optional keys
python main.py             # http://localhost:8000
```

Endpoints: `/api/snapshot`, `/api/news`, `/api/prices`, `/api/signals`, `/api/calendar`, `/ws`.

### Frontend

```bash
cd frontend
flutter create . --platforms=web    # first time only, generates web/ scaffolding
flutter pub get
flutter run -d chrome
```

If `flutter create` overwrites `web/index.html` and `lib/main.dart`, keep the versions in this repo.

## Notes

- **News sentiment** is a keyword lexicon — plug in VADER, FinBERT, or an LLM call later. Same `NewsItem.sentiment` field.
- **Signals** are placeholders (SMA cross, RSI). Add MACD, ATR breakouts, price action, etc. in `services/signals.py`.
- **Calendar** scrapes investing.com; if it breaks, swap to ForexFactory's JSON or a paid API — the `CalendarEvent` schema stays.
- **Prices** are delayed via yfinance. For live pricing, wire OANDA / IG / Dukascopy.
- **WebSocket** pushes typed messages (`snapshot`, `news`, `prices`, `signals`, `calendar`) each time a refresh job runs.

## Next steps

1. Add real sentiment (FinBERT or LLM).
2. Wire live prices (OANDA streaming).
3. Add pair filtering + watchlist persistence.
4. Layer strategy backtests, then paper trading, then broker execution.
