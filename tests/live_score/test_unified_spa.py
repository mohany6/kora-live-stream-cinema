from pathlib import Path
from fastapi.testclient import TestClient
from live_score.api.app import create_app


def test_unified_spa_serves_html_and_preserves_api():
    app = create_app()
    client = TestClient(app)

    # 1. API endpoint returns JSON and is NOT overridden by SPA
    api_res = client.get("/api/v1/matches/today")
    assert api_res.status_code == 200
    assert api_res.headers["content-type"].startswith("application/json")
    assert "matches" in api_res.json()

    # 2. Root / returns HTML from frontend/dist
    dist_index = Path("frontend/dist/index.html")
    if dist_index.exists():
        root_res = client.get("/")
        assert root_res.status_code == 200
        assert "text/html" in root_res.headers["content-type"]
        assert "كورة لايف" in root_res.text

        # 3. Client SPA route /admin returns index.html as well
        admin_res = client.get("/admin")
        assert admin_res.status_code == 200
        assert "text/html" in admin_res.headers["content-type"]
        assert "كورة لايف" in admin_res.text
