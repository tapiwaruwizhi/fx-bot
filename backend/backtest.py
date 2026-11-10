"""Backtest the auto-trader's rules on MT5 price history.

Replays exactly what services/trader.py does, bar by bar:
  * the same SMA(20/50) + RSI(14) signals and net score per pair
  * the same entry rule (score >= min score -> BUY, <= -min score -> SELL),
    closing an opposite position first, one position per pair, max positions
  * the same trading window (no new trades on the weekend or in the first /
    last hours of the week, see services/market_hours.py)
  * stop loss / take profit, and the broker's spread on every entry and exit

Run it on the PC with MT5 (the terminal must be open and logged in):

    cd backend
    .venv\\Scripts\\python.exe backtest.py                      # default sweep, 1 year
    .venv\\Scripts\\python.exe backtest.py --days 730           # 2 years
    .venv\\Scripts\\python.exe backtest.py --timeframes H1 --scores 0.1 --sl-tp 30/60

It only reads price history; it never places orders. Price data is cached
in backend/data/, so --offline re-runs without MT5. Results are printed and
saved to backend/backtests/.

Assumptions (all on the cautious side):
  * signals are evaluated at each bar open on closed bars; live, the bot
    checks every 15 minutes, so its entries can be a little earlier or later
  * if a bar touches both the stop loss and the take profit, the stop loss
    is assumed to have been hit first
  * the spread is MT5's recorded spread for each bar, plus --extra-spread
  * profit per pip is converted at today's exchange rate
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from config import settings  # noqa: E402
from services import market_hours, mt5_client  # noqa: E402
from services.signals import _rsi  # noqa: E402  (same RSI as the live bot)

DATA_DIR = HERE / "data"
OUT_DIR = HERE / "backtests"
TF_MINUTES = {"M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}
MIN_BARS_SMA, MIN_BARS_RSI = 55, 20  # same minimums as services/signals.py


# --- data ---------------------------------------------------------------------

def load_history(pair: str, tf: str, days: int, offline: bool) -> tuple[pd.DataFrame, dict]:
    cache, meta_file = DATA_DIR / f"{pair}_{tf}.csv", DATA_DIR / f"{pair}_{tf}.json"
    count = int(days * 1440 / TF_MINUTES[tf] * 5 / 7) + 200  # trading bars + warm-up
    if not offline:
        df, meta = mt5_client.history(pair, tf, count)
        DATA_DIR.mkdir(exist_ok=True)
        df.to_csv(cache)
        meta_file.write_text(json.dumps(meta))
    elif cache.exists() and meta_file.exists():
        df = pd.read_csv(cache, index_col=0)
        df.index = pd.to_datetime(df.index)
        meta = json.loads(meta_file.read_text())
    else:
        raise SystemExit(f"--offline: no cached data for {pair} {tf}; run once with MT5 open first")
    return df.iloc[-count:], meta


def server_to_utc(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """MT5 bar times are broker server time. Work out the offset from the data:
    the first bar after each weekend gap is the real weekly open (Sunday 17:00
    New York), whose UTC time market_hours knows."""
    times = index.to_pydatetime()
    offsets = np.full(len(times), np.nan)
    gaps = np.flatnonzero(np.diff(index.values) > np.timedelta64(36, "h")) + 1
    for g in gaps:
        t = times[g].replace(tzinfo=timezone.utc)
        week_open = market_hours.week_bounds(t)[0]
        true_open = min((week_open, week_open + timedelta(days=7)), key=lambda c: abs(t - c))
        offsets[g] = round((t - true_open).total_seconds() / 3600)
    s = pd.Series(offsets).ffill().bfill()
    hours = s.fillna(0).to_numpy()
    return pd.DatetimeIndex(index - pd.to_timedelta(hours, unit="h")).tz_localize("UTC")


def net_scores(close: pd.Series) -> pd.Series:
    """Vectorised copy of signals._sma_cross + signals._rsi_signal, summed like trader._net_scores.
    Value at bar i = net score computed from bars 0..i."""
    n = np.arange(1, len(close) + 1)
    diff = close.rolling(20).mean() - close.rolling(50).mean()
    sma_strength = np.round(np.minimum(diff.abs() / close * 100, 1.0), 3)
    sma = np.where(diff > 0, sma_strength, -sma_strength)
    sma = np.where((n >= MIN_BARS_SMA) & diff.notna(), sma, 0.0)

    rsi = _rsi(close)
    buy, sell = rsi < 30, rsi > 70
    rs = np.where(buy, (30 - rsi) / 30, np.where(sell, (rsi - 70) / 30, 0.0))
    rs = np.round(np.minimum(rs, 1.0), 3)
    rsi_score = np.where(buy, rs, np.where(sell, -rs, 0.0))
    rsi_score = np.where((n >= MIN_BARS_RSI) & rsi.notna(), rsi_score, 0.0)
    return pd.Series(sma + rsi_score, index=close.index)


def prepare(pairs: list[str], tf: str, days: int, offline: bool) -> dict:
    """Align all pairs on one timeline; score[i] uses only bars closed before bar i."""
    frames, metas = {}, {}
    for pair in pairs:
        df, meta = load_history(pair, tf, days, offline)
        df.index = server_to_utc(df.index)
        df = df[~df.index.duplicated()]
        df["Score"] = net_scores(df["Close"]).shift(1)  # live bot drops the forming bar
        frames[pair], metas[pair] = df, meta
    times = sorted(set().union(*(f.index for f in frames.values())))
    idx = pd.DatetimeIndex(times)
    cols = {p: {c: f[c].reindex(idx).tolist() for c in ("Open", "High", "Low", "Close", "Spread", "Score")}
            for p, f in frames.items()}
    allowed = [market_hours.trading_window(t.to_pydatetime())[0] for t in idx]
    start = max(f.index[MIN_BARS_SMA] for f in frames.values())  # skip indicator warm-up
    return {"tf": tf, "times": idx, "cols": cols, "metas": metas, "allowed": allowed,
            "first": int(idx.searchsorted(start))}


# --- simulation ---------------------------------------------------------------

def simulate(data: dict, min_score: float, sl_pips: float, tp_pips: float,
             max_positions: int, volume: float, extra_spread_pips: float,
             commission_per_lot: float) -> list[dict]:
    times, cols, metas, allowed = data["times"], data["cols"], data["metas"], data["allowed"]
    pairs = list(cols)
    pos: dict[str, dict] = {}
    trades: list[dict] = []

    def close(pair: str, i: int, price: float, reason: str) -> None:
        p = pos.pop(pair)
        pip = metas[pair]["pip"]
        pips = (price - p["entry"]) / pip if p["dir"] == "BUY" else (p["entry"] - price) / pip
        per_pip = metas[pair]["profit_per_pip_per_lot"] or 10.0
        trades.append({
            "pair": pair, "direction": p["dir"], "opened": times[p["i"]], "closed": times[i],
            "entry": p["entry"], "exit": price, "reason": reason, "pips": round(pips, 1),
            "profit": round(pips * per_pip * volume - commission_per_lot * volume, 2),
        })

    for i in range(data["first"], len(times)):
        bars = {}
        for pair in pairs:
            c = cols[pair]
            o = c["Open"][i]
            if o == o:  # not NaN: this pair has a bar now
                spread = (c["Spread"][i] if c["Spread"][i] == c["Spread"][i] else 0.0) \
                    + extra_spread_pips * metas[pair]["pip"]
                bars[pair] = (o, c["High"][i], c["Low"][i], c["Close"][i], spread, c["Score"][i])

        # 1) price gapped through SL/TP at the open (e.g. Monday open)
        for pair in list(pos):
            if pair not in bars:
                continue
            o, _, _, _, spread, _ = bars[pair]
            p = pos[pair]
            px = o if p["dir"] == "BUY" else o + spread  # BUY exits at bid, SELL at ask
            if (p["dir"] == "BUY" and (px <= p["sl"] or px >= p["tp"])) or \
               (p["dir"] == "SELL" and (px >= p["sl"] or px <= p["tp"])):
                close(pair, i, px, "gap")

        # 2) the trader's decision at the bar open (same rules as trader.run)
        if allowed[i]:
            for pair in pairs:
                if pair not in bars:
                    continue
                o, _, _, _, spread, score = bars[pair]
                if score != score:
                    continue
                if score >= min_score:
                    want = "BUY"
                elif score <= -min_score:
                    want = "SELL"
                else:
                    continue
                existing = pos.get(pair)
                if existing and existing["dir"] == want:
                    continue
                if existing:
                    close(pair, i, o if existing["dir"] == "BUY" else o + spread, "signal")
                elif len(pos) >= max_positions:
                    continue
                pip = metas[pair]["pip"]
                if want == "BUY":
                    entry = o + spread
                    pos[pair] = {"dir": want, "entry": entry, "i": i,
                                 "sl": entry - sl_pips * pip, "tp": entry + tp_pips * pip}
                else:
                    entry = o
                    pos[pair] = {"dir": want, "entry": entry, "i": i,
                                 "sl": entry + sl_pips * pip, "tp": entry - tp_pips * pip}

        # 3) stop loss / take profit during the bar (stop loss first if both)
        for pair in list(pos):
            if pair not in bars:
                continue
            _, h, l, _, spread, _ = bars[pair]
            p = pos[pair]
            if p["dir"] == "BUY":
                if l <= p["sl"]:
                    close(pair, i, p["sl"], "sl")
                elif h >= p["tp"]:
                    close(pair, i, p["tp"], "tp")
            else:
                if h + spread >= p["sl"]:
                    close(pair, i, p["sl"], "sl")
                elif l + spread <= p["tp"]:
                    close(pair, i, p["tp"], "tp")

    # still open at the end: close at the last price
    for pair in list(pos):
        c = cols[pair]
        last = max(j for j in range(len(times)) if c["Close"][j] == c["Close"][j])
        spread = c["Spread"][last] if c["Spread"][last] == c["Spread"][last] else 0.0
        close(pair, last, c["Close"][last] if pos[pair]["dir"] == "BUY" else c["Close"][last] + spread, "end")
    return trades


def metrics(trades: list[dict], start: datetime, end: datetime) -> dict:
    if not trades:
        return {"trades": 0}
    df = pd.DataFrame(trades).sort_values("closed")
    wins, losses = df[df.profit > 0], df[df.profit < 0]
    equity = df.profit.cumsum()
    mid = start + (end - start) / 2
    gross_loss = -losses.profit.sum()
    return {
        "trades": len(df),
        "win_rate_%": round(len(wins) / len(df) * 100, 1),
        "avg_win_pips": round(wins.pips.mean(), 1) if len(wins) else 0.0,
        "avg_loss_pips": round(losses.pips.mean(), 1) if len(losses) else 0.0,
        "profit_factor": round(wins.profit.sum() / gross_loss, 2) if gross_loss else float("inf"),
        "net_pips": round(df.pips.sum(), 1),
        "net_profit": round(df.profit.sum(), 2),
        "max_drawdown": round((equity.cummax().clip(lower=0) - equity).max(), 2),
        "1st_half": round(df[df.closed < mid].profit.sum(), 2),
        "2nd_half": round(df[df.closed >= mid].profit.sum(), 2),
    }


# --- command line -------------------------------------------------------------

def parse_sl_tp(text: str) -> list[tuple[float, float]]:
    out = []
    for part in text.split(","):
        sl, tp = part.split("/")
        out.append((float(sl), float(tp)))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Backtest the FX bot's auto-trading rules on MT5 history.")
    ap.add_argument("--days", type=int, default=365, help="history to test (default 365)")
    ap.add_argument("--timeframes", default="H1,M15,H4", help="comma list, e.g. H1,M15 (default H1,M15,H4)")
    ap.add_argument("--scores", default="0.05,0.1,0.2", help="min scores to try (default 0.05,0.1,0.2)")
    ap.add_argument("--sl-tp", default="20/40,30/60,50/100", help="stop/target pips (default 20/40,30/60,50/100)")
    ap.add_argument("--pairs", default=",".join(settings.fx_pairs), help="comma list (default: config pairs)")
    ap.add_argument("--volume", type=float, default=settings.auto_trade_volume, help="lots per trade")
    ap.add_argument("--max-positions", type=int, default=settings.auto_trade_max_positions)
    ap.add_argument("--extra-spread", type=float, default=0.0, help="extra pips of cost per trade")
    ap.add_argument("--commission", type=float, default=0.0, help="round-trip commission per lot")
    ap.add_argument("--offline", action="store_true", help="use cached data in backend/data/, no MT5")
    args = ap.parse_args()

    pairs = [p.strip().upper() for p in args.pairs.split(",") if p.strip()]
    tfs = [t.strip().upper() for t in args.timeframes.split(",") if t.strip()]
    scores = [float(s) for s in args.scores.split(",")]
    sl_tps = parse_sl_tp(args.sl_tp)
    for tf in tfs:
        if tf not in TF_MINUTES or tf not in mt5_client.TIMEFRAMES:
            raise SystemExit(f"unknown timeframe {tf}; use one of {', '.join(mt5_client.TIMEFRAMES)}")
    if not args.offline and not mt5_client.connect():
        raise SystemExit("Can't connect to MT5. Open the terminal and log in, check MT5_ENABLED/MT5_* "
                         "in .env, or use --offline with cached data.")

    current = (settings.mt5_timeframe.upper(), settings.auto_trade_min_score,
               settings.auto_trade_sl_pips, settings.auto_trade_tp_pips)
    rows, all_trades = [], {}
    t0 = time.time()
    for tf in tfs:
        print(f"Loading {tf} history for {len(pairs)} pairs ...", flush=True)
        data = prepare(pairs, tf, args.days, args.offline)
        start, end = data["times"][data["first"]].to_pydatetime(), data["times"][-1].to_pydatetime()
        for score in scores:
            for sl, tp in sl_tps:
                trades = simulate(data, score, sl, tp, args.max_positions, args.volume,
                                  args.extra_spread, args.commission)
                key = (tf, score, sl, tp)
                all_trades[key] = trades
                rows.append({"timeframe": tf, "min_score": score, "sl/tp": f"{sl:g}/{tp:g}",
                             "now": "<-" if key == current else "", **metrics(trades, start, end)})
        print(f"  tested {start:%d %b %Y} to {end:%d %b %Y}", flush=True)

    table = pd.DataFrame(rows).sort_values("net_profit", ascending=False, na_position="last")
    OUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    table.to_csv(OUT_DIR / f"{stamp}_summary.csv", index=False)
    best = table.iloc[0]
    best_key = (best["timeframe"], best["min_score"], *map(float, best["sl/tp"].split("/")))
    for name, key in (("best", best_key), ("current", current)):
        if key in all_trades:
            pd.DataFrame(all_trades[key]).to_csv(OUT_DIR / f"{stamp}_trades_{name}.csv", index=False)

    pd.set_option("display.width", 200)
    print(f"\nResults at {args.volume:g} lots, profit in account currency "
          f"({len(rows)} runs in {time.time() - t0:.0f}s; '<-' = your current .env settings):\n")
    print(table.to_string(index=False))
    print(f"\nSaved to {OUT_DIR}\\{stamp}_summary.csv (+ trade lists for the best and current settings)")
    print("Look for profit_factor > 1.2 in BOTH halves before trusting a setting; "
          "the best row of a sweep is usually partly luck.")


if __name__ == "__main__":
    main()
