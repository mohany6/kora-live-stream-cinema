"""
Persistent supervisor for Uvicorn server.
Automatically restarts the server if the process is terminated or interrupted.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

PYTHON = sys.executable
CMD = [
    PYTHON,
    "-m",
    "uvicorn",
    "live_score.api.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    "8000",
]
ENV = os.environ.copy()
ENV["PYTHONPATH"] = "src"

print("[*] Starting persistent Uvicorn supervisor on port 8000...", flush=True)

while True:
    try:
        proc = subprocess.Popen(CMD, env=ENV)
        proc.wait()
        print(f"[*] Uvicorn exited with code {proc.returncode}. Restarting in 2s...", flush=True)
        time.sleep(2)
    except KeyboardInterrupt:
        print("[*] Supervisor stopped.")
        break
    except Exception as exc:
        print(f"[!] Supervisor error: {exc}. Retrying in 5s...", flush=True)
        time.sleep(5)
