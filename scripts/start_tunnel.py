"""
Automated Cloudflare Quick Tunnel Launcher for the Arabic Football Platform.

Checks for `cloudflared.exe` (or automatically downloads it into `.tools/` if missing),
spawns a public HTTPS tunnel pointing to http://127.0.0.1:8000, and captures the
generated public URL so anyone worldwide can access the website.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / ".tools"
CLOUDFLARED_BIN = TOOLS_DIR / "cloudflared.exe"
DOWNLOAD_URL = (
    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
)


def ensure_cloudflared() -> Path:
    """Ensures cloudflared.exe is available; downloads it if missing."""
    # 1. Check system PATH
    system_bin = shutil.which("cloudflared")
    if system_bin:
        return Path(system_bin)

    # 2. Check local .tools directory
    if CLOUDFLARED_BIN.exists() and CLOUDFLARED_BIN.stat().st_size > 10_000_000:
        return CLOUDFLARED_BIN

    # 3. Download official binary
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[*] Downloading official cloudflared binary from Cloudflare...")
    print(f"    URL: {DOWNLOAD_URL}")
    print(f"    Target: {CLOUDFLARED_BIN}")

    def progress(blocks, block_size, total_size):
        if total_size > 0:
            downloaded = blocks * block_size
            pct = min(100.0, (downloaded / total_size) * 100.0)
            print(f"\r    Progress: {pct:.1f}% ({downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB)", end="", flush=True)

    urllib.request.urlretrieve(DOWNLOAD_URL, str(CLOUDFLARED_BIN), reporthook=progress)
    print("\n[✓] cloudflared downloaded successfully.")
    return CLOUDFLARED_BIN


def start_tunnel(port: int = 8000) -> None:
    bin_path = ensure_cloudflared()
    print(f"[*] Launching Cloudflare Tunnel for http://127.0.0.1:{port}...")

    cmd = [str(bin_path), "tunnel", "--url", f"http://127.0.0.1:{port}"]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    url_found = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    try:
        assert process.stdout is not None
        for line in iter(process.stdout.readline, ""):
            print(line, end="")
            if not url_found:
                match = url_pattern.search(line)
                if match:
                    url_found = match.group(0)
                    print("\n" + "=" * 70)
                    print("🚀 CLOUDFLARE PUBLIC TUNNEL IS LIVE!")
                    print(f"🌍 Public Global HTTPS URL: {url_found}")
                    print(f"🔒 Admin Panel: {url_found}/admin")
                    print(f"📱 Anyone worldwide can access your site right now!")
                    print("=" * 70 + "\n")
    except KeyboardInterrupt:
        print("\n[*] Stopping Cloudflare tunnel...")
        process.terminate()
        process.wait()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    start_tunnel(port)
