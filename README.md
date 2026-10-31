# FX Bot

Backend (Python / FastAPI) that pulls FX news, prices, technical signals and an economic calendar, and can trade a demo MT5 account; Flutter web app that shows it live over WebSocket.

- **Backend:** Render (`backend/`), auto-deploys on push to `main`
- **Frontend:** Vercel (`frontend/`), auto-deploys on push to `main`

## Structure

```
fx-bot/
├── .gitattributes             keeps *.sh files with LF line endings
├── backend/
│   ├── main.py                FastAPI app (REST + /ws) and refresh scheduler
│   ├── config.py              pairs, feeds, refresh cadence, MT5 / auto-trade settings
│   ├── models.py              Pydantic schemas
│   ├── services/
│   │   ├── news.py            RSS aggregation + naive sentiment
│   │   ├── market_data.py     daily ECB rates via Frankfurter (fallback data source)
│   │   ├── prices.py          live MT5 ticks, else Frankfurter
│   │   ├── signals.py         SMA(20/50) cross + RSI(14)
│   │   ├── calendar.py        ForexFactory weekly economic calendar
│   │   ├── mt5_client.py      MetaTrader 5 connection, rates, orders
│   │   └── trader.py          signals -> demo-only MT5 orders
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── pubspec.yaml
    ├── vercel.json            Vercel build settings
    ├── vercel-build.sh        downloads Flutter and builds the web app on Vercel
    ├── lib/
    │   ├── main.dart
    │   ├── api.dart           REST + WS client (backend URL from --dart-define=API_URL)
    │   ├── models.dart
    │   ├── screens/dashboard.dart
    │   └── widgets/           price grid, news, signals, calendar
    └── web/index.html
```

## Data sources

| Data | Source | Notes |
|---|---|---|
| News | Investing.com, FXStreet, DailyFX, ForexLive RSS | free, no key |
| Prices | MT5 live ticks when connected, else Frankfurter (ECB) | ECB is one rate per business day |
| Signals | computed locally from MT5 bars or ECB daily history | |
| Calendar | ForexFactory weekly JSON (`nfs.faireconomy.media`) | current week only, no "actual" values |

## Run locally

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python main.py             # http://localhost:8000
```

Endpoints: `/health`, `/api/snapshot`, `/api/news`, `/api/prices`, `/api/signals`, `/api/calendar`, `/api/account`, `/ws`. `/health` reports how many items each source has, which is the quickest way to spot a broken source.

### MetaTrader 5 (optional, Windows only)

With an MT5 terminal (e.g. ADS Securities) installed on the same machine, set in `backend/.env`:

```
MT5_ENABLED=true
MT5_LOGIN=<demo account number>
MT5_PASSWORD=<demo password>
MT5_SERVER=<server name from the MT5 login dialog>
MT5_PATH=C:\Program Files\ADS Securities MT5 Terminal\terminal64.exe
```

Prices then come from live MT5 ticks and signals from MT5 bars (`MT5_TIMEFRAME`, default H1). `/api/account` shows balance, equity and open positions.

Auto-trading (`AUTO_TRADE_ENABLED=true`) is off by default and **only trades on demo accounts** — it refuses to send orders if the logged-in account isn't a demo. It also needs **Algo Trading** switched on in the MT5 toolbar. Orders are tagged with `MT5_MAGIC`, one position per pair. See `services/trader.py` for the rules.

This can't run on Render/Linux: the MetaTrader5 package needs the Windows terminal next to it. Without MT5 the backend falls back to Frankfurter.

### Frontend

```powershell
cd frontend
flutter pub get
flutter run -d chrome --dart-define=API_URL=http://localhost:8000
```

Without `API_URL` the app defaults to `http://localhost:8000`.

## Deploy

**Render (backend):** Web Service, root directory `backend`, build `pip install -r requirements.txt`, start `uvicorn main:app --host 0.0.0.0 --port $PORT`, env var `PYTHON_VERSION=3.11.9`. Optionally set `CORS_ORIGINS=["https://<your-app>.vercel.app"]`. MT5 is skipped automatically on Render (Linux).

**Vercel (frontend):** root directory `frontend`, framework preset "Other". Env vars `API_URL` (the Render URL, no trailing slash) and `FLUTTER_VERSION` (e.g. `3.47.2`). Settings come from `vercel.json`.

## Notes

- **News sentiment** is a keyword lexicon. Plug in VADER, FinBERT or an LLM call later behind the same `NewsItem.sentiment` field.
- **Signals** are placeholders (SMA cross, RSI). Add MACD, ATR breakouts, price action etc. in `services/signals.py`.
- **WebSocket** pushes typed messages (`snapshot`, `news`, `prices`, `signals`, `calendar`, `trades`) each time a refresh job runs.

## Next steps

1. Show MT5 account, positions and auto-trades in the dashboard (`/api/account` and the `trades` WebSocket message already exist).
2. Add real sentiment (FinBERT or LLM).
3. Pair filtering + watchlist persistence.
4. Backtest strategies before trusting the auto-trader.
