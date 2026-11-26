import time
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from live_score.api.security import SlidingWindowRateLimiter, RateLimitMiddleware


def test_sliding_window_rate_limiter_allows_and_blocks():
    limiter = SlidingWindowRateLimiter(window_seconds=60)
    ip = "192.168.1.100"

    # Allow up to limit
    for _ in range(5):
        allowed, remaining, retry_after = limiter.check_rate_limit(ip, category="test", max_requests=5)
        assert allowed is True

    # 6th request is blocked
    allowed, remaining, retry_after = limiter.check_rate_limit(ip, category="test", max_requests=5)
    assert allowed is False
    assert remaining == 0
    assert retry_after > 0


def test_admin_auth_failure_jail():
    limiter = SlidingWindowRateLimiter()
    ip = "10.0.0.5"

    assert limiter.is_jailed(ip) is False

    # 4 failures: not yet jailed
    for _ in range(4):
        limiter.record_admin_auth_failure(ip)
        assert limiter.is_jailed(ip) is False

    # 5th failure: jailed!
    limiter.record_admin_auth_failure(ip)
    assert limiter.is_jailed(ip) is True
    jailed, retry_after = limiter.check_jail(ip)
    assert jailed is True
    assert retry_after > 0


def test_rate_limit_middleware_integration():
    app = FastAPI()
    limiter = SlidingWindowRateLimiter(window_seconds=60)
    app.add_middleware(RateLimitMiddleware, limiter=limiter, public_limit=3, admin_limit=2)

    @app.get("/api/v1/matches/today")
    def public_route():
        return {"ok": True}

    client = TestClient(app)

    # 3 allowed requests
    for i in range(3):
        res = client.get("/api/v1/matches/today")
        assert res.status_code == 200
        assert "X-RateLimit-Limit" in res.headers
        assert "X-RateLimit-Remaining" in res.headers

    # 4th request gets 429 Too Many Requests
    blocked = client.get("/api/v1/matches/today")
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    assert "detail" in blocked.json()


def test_cloudflare_ip_resolution_and_isolation():
    app = FastAPI()
    limiter = SlidingWindowRateLimiter(window_seconds=60)
    app.add_middleware(RateLimitMiddleware, limiter=limiter, public_limit=2)

    @app.get("/api/v1/ping")
    def ping():
        return {"ping": "pong"}

    client = TestClient(app)

    # User 1 through Cloudflare Edge (CF-Connecting-IP: 203.0.113.195)
    cf_headers_user1 = {"CF-Connecting-IP": "203.0.113.195"}
    assert client.get("/api/v1/ping", headers=cf_headers_user1).status_code == 200
    assert client.get("/api/v1/ping", headers=cf_headers_user1).status_code == 200
    # User 1 hits rate limit
    assert client.get("/api/v1/ping", headers=cf_headers_user1).status_code == 429

    # User 2 through Cloudflare Edge (CF-Connecting-IP: 198.51.100.42) is NOT blocked
    cf_headers_user2 = {"CF-Connecting-IP": "198.51.100.42"}
    assert client.get("/api/v1/ping", headers=cf_headers_user2).status_code == 200
