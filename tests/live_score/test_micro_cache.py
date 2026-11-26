import time
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from live_score.api.cache import MicroCache, micro_cache_response


def test_micro_cache_get_set_ttl():
    cache = MicroCache(default_ttl=1.0)
    cache.set("key1", {"score": "1-0"}, tag="matches")
    
    cached = cache.get("key1")
    assert cached is not None
    assert cached["data"] == {"score": "1-0"}
    assert "etag" in cached

    # Wait for expiration
    time.sleep(1.1)
    assert cache.get("key1") is None


def test_micro_cache_tag_invalidation():
    cache = MicroCache(default_ttl=60.0)
    cache.set("match_1", {"id": 1}, tag="matches")
    cache.set("match_2", {"id": 2}, tag="matches")
    cache.set("ad_1", {"id": 10}, tag="ads")

    assert cache.get("match_1") is not None
    assert cache.get("ad_1") is not None

    cache.invalidate_tag("matches")
    assert cache.get("match_1") is None
    assert cache.get("match_2") is None
    assert cache.get("ad_1") is not None


def test_micro_cache_etag_304_middleware():
    app = FastAPI()
    cache = MicroCache(default_ttl=10.0)

    call_count = {"count": 0}

    @app.get("/api/test-cache")
    async def get_test(request: Request, response: Response):
        cached = cache.get("test_key")
        if cached:
            etag = cached["etag"]
            if request.headers.get("if-none-match") == etag:
                return Response(status_code=304, headers={"ETag": etag})
            response.headers["ETag"] = etag
            return cached["data"]

        call_count["count"] += 1
        data = {"hello": "world", "calls": call_count["count"]}
        etag = cache.set("test_key", data, tag="test")
        response.headers["ETag"] = etag
        return data

    client = TestClient(app)

    # First call: cache miss, status 200, returns ETag
    r1 = client.get("/api/test-cache")
    assert r1.status_code == 200
    assert r1.json()["calls"] == 1
    etag = r1.headers.get("etag")
    assert etag is not None

    # Second call without If-None-Match: cache hit (calls stays 1), status 200
    r2 = client.get("/api/test-cache")
    assert r2.status_code == 200
    assert r2.json()["calls"] == 1
    assert r2.headers.get("etag") == etag

    # Third call with If-None-Match: returns 304 Not Modified with empty body
    r3 = client.get("/api/test-cache", headers={"If-None-Match": etag})
    assert r3.status_code == 304
    assert len(r3.content) == 0
