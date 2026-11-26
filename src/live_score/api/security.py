"""Security and high-concurrency rate limiting middlewares.

Protects against:
- High-concurrency polling exhaustion (10k users) via Sliding-Window Rate Limiting.
- Brute force admin credential guessing via IP Lockout Jail.
- Memory exhaustion and DoS via Request Body Size Guard.
- Clickjacking and MIME confusion via Standard Security Headers.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


def get_client_ip(request: Request) -> str:
    """Extracts client IP, respecting Cloudflare CF-Connecting-IP, True-Client-IP, and X-Forwarded-For."""
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip and cf_ip.strip():
        return cf_ip.strip()

    true_ip = request.headers.get("true-client-ip")
    if true_ip and true_ip.strip():
        return true_ip.strip()

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First IP in the list is the client IP
        ip = forwarded.split(",")[0].strip()
        if ip:
            return ip

    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window rate limiter and brute-force jail."""

    def __init__(
        self,
        window_seconds: int = 60,
        jail_seconds: int = 900,
        max_auth_failures: int = 5,
        auth_failure_window: int = 900,
    ) -> None:
        self.window_seconds = window_seconds
        self.jail_seconds = jail_seconds
        self.max_auth_failures = max_auth_failures
        self.auth_failure_window = auth_failure_window

        self._lock = threading.RLock()
        self._windows: dict[str, list[float]] = {}
        self._auth_failures: dict[str, list[float]] = {}
        self._jailed: dict[str, float] = {}

    def check_rate_limit(
        self,
        ip: str,
        category: str,
        max_requests: int,
    ) -> tuple[bool, int, int]:
        """Checks if a request is allowed. Returns (allowed, remaining, retry_after)."""
        now = time.monotonic()
        key = f"{ip}:{category}"

        with self._lock:
            history = self._windows.get(key, [])
            cutoff = now - self.window_seconds
            # Prune old timestamps
            history = [ts for ts in history if ts > cutoff]

            if len(history) >= max_requests:
                oldest = history[0]
                retry_after = max(1, int(oldest + self.window_seconds - now))
                self._windows[key] = history
                return False, 0, retry_after

            history.append(now)
            self._windows[key] = history
            remaining = max(0, max_requests - len(history))
            return True, remaining, 0

    def record_admin_auth_failure(self, ip: str) -> None:
        """Records a failed admin token attempt and locks out the IP if limit is reached."""
        now = time.monotonic()
        with self._lock:
            failures = self._auth_failures.get(ip, [])
            cutoff = now - self.auth_failure_window
            failures = [ts for ts in failures if ts > cutoff]
            failures.append(now)
            self._auth_failures[ip] = failures

            if len(failures) >= self.max_auth_failures:
                self._jailed[ip] = now + self.jail_seconds

    def is_jailed(self, ip: str) -> bool:
        jailed, _ = self.check_jail(ip)
        return jailed

    def check_jail(self, ip: str) -> tuple[bool, int]:
        """Returns (is_jailed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            jail_until = self._jailed.get(ip)
            if not jail_until:
                return False, 0
            if jail_until <= now:
                del self._jailed[ip]
                return False, 0
            return True, max(1, int(jail_until - now))

    def reset(self) -> None:
        with self._lock:
            self._windows.clear()
            self._auth_failures.clear()
            self._jailed.clear()


# Global limiter instance
global_rate_limiter = SlidingWindowRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforces tiered rate limits and jail lockouts."""

    def __init__(
        self,
        app,
        limiter: Optional[SlidingWindowRateLimiter] = None,
        public_limit: int = 120,
        analytics_limit: int = 30,
        admin_limit: int = 30,
    ) -> None:
        super().__init__(app)
        self.limiter = limiter or global_rate_limiter
        self.public_limit = public_limit
        self.analytics_limit = analytics_limit
        self.admin_limit = admin_limit

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Never rate-limit CORS preflight OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path

        # Exclude static documentation or root health checks
        if not path.startswith("/api/"):
            return await call_next(request)

        ip = get_client_ip(request)

        # 1. Check IP Jail
        is_jailed, retry_after = self.limiter.check_jail(ip)
        if is_jailed:
            headers = {"Retry-After": str(retry_after)}
            origin = request.headers.get("origin")
            if origin:
                headers["Access-Control-Allow-Origin"] = origin
                headers["Access-Control-Allow-Credentials"] = "true"
            return JSONResponse(
                status_code=429,
                content={"detail": "IP locked out due to multiple failed authentication attempts."},
                headers=headers,
            )

        # 2. Determine Category and Threshold
        is_loopback = ip in {"127.0.0.1", "::1", "localhost"}
        if path.startswith("/api/v1/analytics/track"):
            category = "analytics"
            limit = 500 if is_loopback and self.analytics_limit == 30 else self.analytics_limit
        elif path.startswith("/api/v1/admin"):
            category = "admin"
            limit = 200 if is_loopback and self.admin_limit == 30 else self.admin_limit
        else:
            category = "public"
            limit = 2000 if is_loopback and self.public_limit == 120 else self.public_limit

        allowed, remaining, retry_after = self.limiter.check_rate_limit(ip, category, limit)
        if not allowed:
            headers = {
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            }
            origin = request.headers.get("origin")
            if origin:
                headers["Access-Control-Allow-Origin"] = origin
                headers["Access-Control-Allow-Credentials"] = "true"
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded for {category} endpoints. Please wait."},
                headers=headers,
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard OWASP recommended security headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        headers = response.headers
        headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith("/api/v1/stream/player"):
            # Player proxy endpoint must be embeddable in iframes (SPA & Blogger)
            if "x-frame-options" in headers:
                del headers["x-frame-options"]
            if "X-Frame-Options" in headers:
                del headers["X-Frame-Options"]
            headers["Content-Security-Policy"] = "frame-ancestors *;"
            headers["Access-Control-Allow-Origin"] = "*"
        else:
            headers["X-Frame-Options"] = "SAMEORIGIN"
            if "Content-Security-Policy" not in headers:
                headers["Content-Security-Policy"] = (
                    "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: http: data: blob:; "
                    "frame-src *; img-src * data: blob:; media-src * data: blob:;"
                )
        headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        headers["X-XSS-Protection"] = "1; mode=block"
        return response


class RequestSizeLimiterMiddleware(BaseHTTPMiddleware):
    """Rejects request bodies exceeding maximum payload sizes to prevent memory exhaustion."""

    def __init__(
        self,
        app,
        max_public_bytes: int = 65_536,  # 64 KB
        max_admin_bytes: int = 524_288,   # 512 KB
    ) -> None:
        super().__init__(app)
        self.max_public_bytes = max_public_bytes
        self.max_admin_bytes = max_admin_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length_header = request.headers.get("content-length")
        if content_length_header:
            try:
                content_length = int(content_length_header)
                path = request.url.path
                max_allowed = (
                    self.max_admin_bytes if path.startswith("/api/v1/admin") else self.max_public_bytes
                )
                if content_length > max_allowed:
                    headers = {}
                    origin = request.headers.get("origin")
                    if origin:
                        headers["Access-Control-Allow-Origin"] = origin
                        headers["Access-Control-Allow-Credentials"] = "true"
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Payload Too Large. Maximum allowed size is {max_allowed} bytes."
                        },
                        headers=headers,
                    )
            except ValueError:
                pass

        return await call_next(request)
