"""Tests for the public ads API endpoint: GET /api/v1/ads."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from live_score.api.app import create_app

FIXED_NOW = datetime(2026, 11, 18, 16, 0, tzinfo=timezone.utc)
ADMIN_TOKEN = "test-admin-token"


@pytest.fixture
def client(tmp_path):
    app = create_app(
        fixtures=[],
        db_path=str(tmp_path / "ads_test.db"),
        admin_token=ADMIN_TOKEN,
        clock=lambda: FIXED_NOW,
    )
    store = app.state.store
    # Seed sample ads
    store.upsert_ad({
        "id": "ad-pub-1",
        "title": "Header Leaderboard",
        "position": "header_top",
        "ad_type": "image_banner",
        "image_url": "https://example.com/banner.png",
        "link_url": "https://example.com",
        "target_device": "all",
        "is_active": True,
        "priority": 10,
    })
    store.upsert_ad({
        "id": "ad-pub-2",
        "title": "Inactive Header",
        "position": "header_top",
        "ad_type": "image_banner",
        "image_url": "https://example.com/inactive.png",
        "is_active": False,
        "priority": 50,
    })
    store.upsert_ad({
        "id": "ad-pub-3",
        "title": "Player Bottom Mobile",
        "position": "player_bottom",
        "ad_type": "custom_html",
        "html_code": "<ins class='adsbygoogle'></ins>",
        "target_device": "mobile",
        "is_active": True,
        "priority": 5,
    })
    with TestClient(app) as tc:
        yield tc


def test_get_ads_returns_active_only(client):
    res = client.get("/api/v1/ads")
    assert res.status_code == 200
    data = res.json()
    assert "ads" in data
    ads = data["ads"]
    ids = [a["id"] for a in ads]
    assert "ad-pub-1" in ids
    assert "ad-pub-3" in ids
    assert "ad-pub-2" not in ids  # Inactive must be filtered out


def test_get_ads_filter_by_position(client):
    res = client.get("/api/v1/ads?position=header_top")
    assert res.status_code == 200
    data = res.json()
    ads = data["ads"]
    assert len(ads) == 1
    assert ads[0]["id"] == "ad-pub-1"
    assert ads[0]["position"] == "header_top"


def test_get_ads_filter_by_device(client):
    # Desktop query should not include mobile-only ad
    res_desktop = client.get("/api/v1/ads?device=desktop")
    assert res_desktop.status_code == 200
    desktop_ids = [a["id"] for a in res_desktop.json()["ads"]]
    assert "ad-pub-1" in desktop_ids
    assert "ad-pub-3" not in desktop_ids

    # Mobile query should include both "all" and "mobile"
    res_mobile = client.get("/api/v1/ads?device=mobile")
    assert res_mobile.status_code == 200
    mobile_ids = [a["id"] for a in res_mobile.json()["ads"]]
    assert "ad-pub-1" in mobile_ids
    assert "ad-pub-3" in mobile_ids
