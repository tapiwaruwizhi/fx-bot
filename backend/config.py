"""Configuration for the FX bot backend."""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # API
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["*"]  # tighten in production

    # Major pairs we track by default
    fx_pairs: List[str] = [
        "EURUSD",
        "GBPUSD",
        "USDJPY",
        "AUDUSD",
        "USDCAD",
        "USDCHF",
        "NZDUSD",
        "EURJPY",
        "GBPJPY",
        "EURGBP",
    ]

    # News sources (RSS)
    news_feeds: List[str] = [
        "https://www.investing.com/rss/news_1.rss",              # forex news
        "https://www.investing.com/rss/news_285.rss",            # forex analysis
        "https://www.fxstreet.com/rss/news",                     # FXStreet
        "https://www.dailyfx.com/feeds/market-news",             # DailyFX
        "https://www.forexlive.com/feed/news",                   # ForexLive
    ]

    # Refresh cadence (seconds)
    news_refresh_secs: int = 300      # 5 min
    signals_refresh_secs: int = 900   # 15 min
    prices_refresh_secs: int = 600    # 10 min (source is daily ECB rates)
    calendar_refresh_secs: int = 1800 # 30 min (be polite to ForexFactory feed)

    # Optional API keys (set in .env)
    newsapi_key: str = ""
    finnhub_key: str = ""

    # MetaTrader 5 (Windows only; terminal must be installed on this machine)
    mt5_enabled: bool = False
    mt5_login: int = 0
    mt5_password: str = ""
    mt5_server: str = ""              # exactly as shown in the MT5 login dialog
    mt5_path: str = ""                # optional: full path to terminal64.exe
    mt5_symbol_suffix: str = ""       # e.g. ".r" if the broker's symbols are EURUSD.r
    mt5_timeframe: str = "H1"         # bars used for signals: M15, M30, H1, H4, D1
    mt5_magic: int = 20260930         # tags orders placed by this bot
    mt5_deviation_points: int = 20    # max slippage

    # Auto-trading (demo accounts only; see services/trader.py)
    auto_trade_enabled: bool = False
    auto_trade_volume: float = 0.01   # lots
    auto_trade_sl_pips: float = 30
    auto_trade_tp_pips: float = 60
    auto_trade_min_score: float = 0.5
    auto_trade_max_positions: int = 3
    auto_trade_skip_after_open_hours: float = 2    # no new trades for this long after the Sunday open
    auto_trade_stop_before_close_hours: float = 2  # no new trades this close to the Friday close

    class Config:
        env_file = ".env"


settings = Settings()
