"""
DuckDNS IP Synchronization Client.

Updates DuckDNS dynamically with your current public IP address,
ensuring your free custom subdomain (e.g. yourname.duckdns.org) always points
to this machine.
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.parse
import urllib.request
from typing import Optional


def update_duckdns(domain: str, token: str, ip: Optional[str] = None) -> tuple[bool, str]:
    """Updates DuckDNS record. Returns (success, response_message)."""
    # Clean domain if user passed full URL or *.duckdns.org
    clean_domain = domain.lower().replace(".duckdns.org", "").replace("https://", "").replace("http://", "").strip()
    clean_token = token.strip()

    params = {"domains": clean_domain, "token": clean_token}
    if ip and ip.strip():
        params["ip"] = ip.strip()

    query_str = urllib.parse.urlencode(params)
    url = f"https://www.duckdns.org/update?{query_str}"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DuckDNS-Kora-Sync/1.0"},
    )

    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            body = resp.read().decode("utf-8", "ignore").strip()
            if body == "OK":
                return True, "OK"
            return False, body
    except Exception as exc:
        return False, str(exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="DuckDNS Dynamic IP Synchronization")
    parser.add_argument("--domain", required=True, help="DuckDNS subdomain (e.g. kora-live)")
    parser.add_argument("--token", required=True, help="DuckDNS Account Token")
    parser.add_argument("--ip", default=None, help="Explicit IP override (optional)")
    parser.add_argument("--interval", type=int, default=0, help="Sync interval in seconds (0 for one-off run)")
    args = parser.parse_args()

    print(f"[*] Starting DuckDNS sync for domain: {args.domain}.duckdns.org")
    while True:
        success, msg = update_duckdns(args.domain, args.token, args.ip)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        if success:
            print(f"[{timestamp}] [SUCCESS] DuckDNS updated successfully (OK)")
        else:
            print(f"[{timestamp}] [ERROR] DuckDNS update failed: {msg}")

        if args.interval <= 0:
            sys.exit(0 if success else 1)

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
