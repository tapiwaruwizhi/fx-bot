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

    class Config:
        env_file = ".env"


settings = Settings()
