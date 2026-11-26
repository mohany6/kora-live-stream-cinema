from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from live_score.api.security import (
    SecurityHeadersMiddleware,
    RequestSizeLimiterMiddleware,
)


def test_security_headers_present():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/ping")
    def ping():
        return {"ping": "pong"}

    client = TestClient(app)
    res = client.get("/ping")

    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert "strict-origin-when-cross-origin" in res.headers.get("Referrer-Policy", "")
    assert "Content-Security-Policy" in res.headers


def test_request_size_limiter_rejects_large_payload():
    app = FastAPI()
    app.add_middleware(RequestSizeLimiterMiddleware, max_public_bytes=1024)

    @app.post("/api/v1/test-upload")
    def upload(payload: dict):
        return {"received": len(payload)}

    client = TestClient(app)

    # 1. Under limit: allowed
    small = client.post("/api/v1/test-upload", json={"msg": "small"})
    assert small.status_code == 200

    # 2. Over limit (e.g. 2KB): rejected with 413
    big = client.post("/api/v1/test-upload", json={"data": "x" * 2000})
    assert big.status_code == 413
    assert "Payload Too Large" in big.json().get("detail", "")
