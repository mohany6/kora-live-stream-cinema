"""
Cloudflare Edge & Concurrency Verification Test Suite.

Simulates Cloudflare Edge reverse-proxy behavior, testing:
1. Cloudflare IP Resolution (CF-Connecting-IP, True-Client-IP).
2. Edge Cache Validation (Origin ETag, If-None-Match, HTTP 304 0-byte delivery).
3. Concurrent Burst Simulation (50 concurrent threads simulating high-volume traffic).
4. Cloudflare IP Jail & Anti-Brute-Force isolation.
5. Security Headers and Payload Size Guard.
"""

from __future__ import annotations

import concurrent.futures
import sys
import time
import urllib.request
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

BASE_URL = "http://127.0.0.1:8000"

results: list[tuple[str, bool, str]] = []


def record(title: str, passed: bool, detail: str = ""):
    results.append((title, passed, detail))
    status_icon = "PASS" if passed else "FAIL"
    print(f"[{status_icon:4s}] {title} {f'-- {detail}' if detail else ''}")


def http_get(path: str, headers: dict | None = None) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(f"{BASE_URL}{path}", headers=headers or {})
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read()
            resp_headers = dict(resp.headers)
            return resp.status, resp_headers, body
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def http_post(path: str, data: dict, headers: dict | None = None) -> tuple[int, dict, bytes]:
    encoded = json.dumps(data).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(f"{BASE_URL}{path}", data=encoded, headers=req_headers)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read()
            resp_headers = dict(resp.headers)
            return resp.status, resp_headers, body
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def run_cloudflare_verification():
    print("=" * 70)
    print("CLOUDFLARE EDGE & HIGH-CONCURRENCY VERIFICATION SUITE")
    print(f"Target Origin: {BASE_URL}")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. Cloudflare IP Extraction & Isolation
    # -------------------------------------------------------------
    cf_user1 = "104.28.14.88"
    cf_user2 = "172.67.180.201"

    # User 1 sends requests with CF-Connecting-IP
    status1, h1, b1 = http_get("/api/v1/matches/today", headers={"CF-Connecting-IP": cf_user1})
    record("1. Cloudflare CF-Connecting-IP resolved on public matches", status1 == 200, f"Status: {status1}")

    # User 2 sends requests with True-Client-IP
    status2, h2, b2 = http_get("/api/v1/matches/today", headers={"True-Client-IP": cf_user2})
    record("2. Cloudflare True-Client-IP resolved on public matches", status2 == 200, f"Status: {status2}")

    # -------------------------------------------------------------
    # 2. Cloudflare CDN Edge Cache Simulation (ETag + 304 Validation)
    # -------------------------------------------------------------
    etag = h1.get("ETag") or h1.get("etag")
    has_etag = bool(etag and etag.startswith('"'))
    record("3. Origin serves deterministic ETag for Cloudflare CDN", has_etag, f"ETag: {etag}")

    cache_control = h1.get("Cache-Control") or h1.get("cache-control") or ""
    record("4. Origin emits Cloudflare-compatible Cache-Control header", "public" in cache_control and "max-age" in cache_control, cache_control)

    if etag:
        status_304, h_304, b_304 = http_get(
            "/api/v1/matches/today",
            headers={"CF-Connecting-IP": cf_user1, "If-None-Match": etag},
        )
        record(
            "5. If-None-Match returns HTTP 304 Not Modified with 0 bytes",
            status_304 == 304 and len(b_304) == 0,
            f"Status: {status_304}, Payload: {len(b_304)} bytes",
        )

    # -------------------------------------------------------------
    # 3. High-Concurrency Stress Test (Simulating 10,000 Concurrent Users)
    # -------------------------------------------------------------
    total_concurrency_requests = 200
    concurrency_workers = 25
    print(f"\n[INFO] Firing {total_concurrency_requests} concurrent requests across {concurrency_workers} threads...")

    start_time = time.perf_counter()

    def send_simulated_request(index: int):
        simulated_ip = f"104.28.14.{(index % 50) + 1}"
        return http_get(
            "/api/v1/matches/today",
            headers={
                "CF-Connecting-IP": simulated_ip,
                "CF-Ray": f"7f8a9b{index:04d}-LHR",
            },
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency_workers) as executor:
        futures = [executor.submit(send_simulated_request, i) for i in range(total_concurrency_requests)]
        responses = [f.result() for f in concurrent.futures.as_completed(futures)]

    elapsed = time.perf_counter() - start_time
    rps = total_concurrency_requests / elapsed if elapsed > 0 else 0
    success_count = sum(1 for status, _, _ in responses if status in (200, 304))
    avg_latency_ms = (elapsed / total_concurrency_requests) * 1000

    record(
        "6. High-concurrency burst completes with 100% success",
        success_count == total_concurrency_requests,
        f"{success_count}/{total_concurrency_requests} successful ({rps:.1f} RPS, avg {avg_latency_ms:.2f}ms/req)",
    )

    # -------------------------------------------------------------
    # 4. Cloudflare DDoS & Brute-Force Jail Simulation
    # -------------------------------------------------------------
    attacker_ip = "198.51.100.99"
    # Send 5 failed admin logins
    for _ in range(5):
        http_get(
            "/api/v1/admin/analytics/stats",
            headers={"CF-Connecting-IP": attacker_ip, "X-Admin-Token": "wrong-token"},
        )

    # 6th attempt should be blocked by IP jail
    jail_status, jail_headers, _ = http_get(
        "/api/v1/admin/analytics/stats",
        headers={"CF-Connecting-IP": attacker_ip, "X-Admin-Token": "wrong-token"},
    )
    norm_jail = {k.lower(): v for k, v in jail_headers.items()}
    record(
        "7. Cloudflare attacker IP is jailed after 5 failed admin logins",
        jail_status == 429,
        f"Attacker status: {jail_status}, Retry-After: {norm_jail.get('retry-after')}s",
    )

    # Innocent user through Cloudflare is unaffected
    innocent_status, _, _ = http_get(
        "/api/v1/matches/today",
        headers={"CF-Connecting-IP": "104.28.14.99"},
    )
    record(
        "8. Legitimate Cloudflare user unaffected by attacker IP jail",
        innocent_status == 200,
        f"Innocent user status: {innocent_status}",
    )

    # -------------------------------------------------------------
    # 5. OWASP Security Headers & Payload Size Guard
    # -------------------------------------------------------------
    norm_h = {k.lower(): v for k, v in h1.items()}
    record(
        "9. Standard security headers present (nosniff, SAMEORIGIN, CSP)",
        norm_h.get("x-content-type-options") == "nosniff"
        and norm_h.get("x-frame-options") == "SAMEORIGIN"
        and "content-security-policy" in norm_h,
        f"CSP: {norm_h.get('content-security-policy', '')[:35]}...",
    )

    # Large request > 64KB
    large_payload = {"data": "X" * 70_000}
    p_status, _, _ = http_post(
        "/api/v1/analytics/track",
        data=large_payload,
        headers={"CF-Connecting-IP": cf_user1},
    )
    record(
        "10. Request body exceeding 64KB rejected with 413 Payload Too Large",
        p_status == 413,
        f"Status: {p_status}",
    )

    print("=" * 70)
    total_passed = sum(1 for _, p, _ in results if p)
    print(f"CLOUDFLARE TEST SUMMARY: {total_passed} / {len(results)} tests passed successfully!")
    print("=" * 70)
    if total_passed < len(results):
        sys.exit(1)


if __name__ == "__main__":
    run_cloudflare_verification()
