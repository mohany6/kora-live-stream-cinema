"""Development launcher for the live score API."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "live_score.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        app_dir=str(SRC),
    )
