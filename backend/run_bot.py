"""Run the backend for unattended use (no auto-reload).

All output (prints, uvicorn logs, errors) is appended to
logs/bot-YYYY-MM-DD.log next to this file. Used by scripts/start-bot.ps1,
which the "FX Bot" scheduled task starts at Windows logon.

Manual use:  .venv\\Scripts\\python.exe run_bot.py
"""
import os
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
sys.path.insert(0, str(HERE))

log_dir = HERE / "logs"
log_dir.mkdir(exist_ok=True)
log_file = open(log_dir / f"bot-{date.today():%Y-%m-%d}.log", "a", encoding="utf-8", buffering=1)
sys.stdout = sys.stderr = log_file

import uvicorn  # noqa: E402  (imported after redirect so its logs go to the file)
from config import settings  # noqa: E402

if __name__ == "__main__":
    print(f"[run_bot] starting backend on http://127.0.0.1:{settings.port}")
    # 127.0.0.1 = only reachable from this PC, not from other devices on the network
    uvicorn.run("main:app", host="127.0.0.1", port=settings.port)
