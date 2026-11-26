import httpx

urls = [
    "http://127.0.0.1:8000/health",
    "http://127.0.0.1:8000/api/v1/matches/today",
    "http://127.0.0.1:8000/api/v1/ads",
    "https://articles-mardi-materials-induced.trycloudflare.com/health",
    "https://articles-mardi-materials-induced.trycloudflare.com/match/401915378",
    "https://kora-live-to.blogspot.com",
    "https://kora-live-to.blogspot.com/2026/11/sabah-fk.html",
]

for url in urls:
    try:
        r = httpx.get(url, timeout=10, follow_redirects=True, verify=False)
        print(f"[✓] {url} -> {r.status_code} ({len(r.text)} bytes)")
    except Exception as e:
        print(f"[-] {url} -> ERROR: {e}")
