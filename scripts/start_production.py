"""
Production High-Concurrency Server Launcher for the Arabic Football Platform.

Configures Uvicorn with multiple asynchronous workers, socket backlog tuning,
keep-alive timeouts, and production logging to handle 10,000 concurrent online users.
"""

from __future__ import annotations

import multiprocessing
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import uvicorn


def get_worker_count() -> int:
    env_workers = os.getenv("WEB_CONCURRENCY")
    if env_workers:
        try:
            return max(1, int(env_workers))
        except ValueError:
            pass
    cores = multiprocessing.cpu_count()
    # 2 workers per core, bounded between 2 and 8
    return min(8, max(2, cores * 2))


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    workers = get_worker_count()

    print("=" * 65)
    print("PRODUCTION SERVER INITIALIZATION")
    print(f"Host: {host}:{port}")
    print(f"Workers: {workers} multi-worker processes")
    print("Micro-Caching: Enabled (10s TTL, ETag 304 Validation)")
    print("Database: SQLite WAL Mode (Async Batch Telemetry)")
    print("Rate Limiting: Sliding-Window (120 req/min public, 15m brute-force jail)")
    print("Security: OWASP Headers & 64KB Payload Size Guard")
    print("=" * 65)

    uvicorn.run(
        "live_score.api.main:app",
        host=host,
        port=port,
        workers=workers,
        timeout_keep_alive=30,
        backlog=2048,
        access_log=True,
    )


if __name__ == "__main__":
    main()
