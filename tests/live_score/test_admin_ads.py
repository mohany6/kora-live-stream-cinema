"""Tests for Admin Ads CMS endpoints: /api/v1/admin/ads."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from live_score.api.app import create_app

FIXED_NOW = datetime(2026, 11, 18, 16, 0, tzinfo=timezone.utc)
ADMIN_TOKEN = "test-admin-token"
HEADERS = {"X-Admin-Token": ADMIN_TOKEN}


@pytest.fixture
def client(tmp_path):
    app = create_app(
        fixtures=[],
        db_path=str(tmp_path / "admin_ads_test.db"),
        admin_token=ADMIN_TOKEN,
        clock=lambda: FIXED_NOW,
    )
    with TestClient(app) as tc:
        yield tc


def test_admin_ads_requires_auth(client):
    assert client.get("/api/v1/admin/ads").status_code == 401
    assert client.post("/api/v1/admin/ads", json={"title": "Test"}).status_code == 401
    assert client.put("/api/v1/admin/ads/123", json={"title": "Test"}).status_code == 401
    assert client.patch("/api/v1/admin/ads/123/toggle").status_code == 401
    assert client.delete("/api/v1/admin/ads/123").status_code == 401


def test_admin_ads_crud_lifecycle(client):
    # 1. Create ad
    create_payload = {
        "title": "Sponsor Banner",
        "position": "player_bottom",
        "ad_type": "image_banner",
        "image_url": "https://example.com/banner.jpg",
        "link_url": "https://example.com/sponsor",
        "target_device": "all",
        "is_active": True,
        "priority": 10,
    }
    create_res = client.post("/api/v1/admin/ads", json=create_payload, headers=HEADERS)
    assert create_res.status_code == 201
    ad = create_res.json()
    ad_id = ad["id"]
    assert ad["title"] == "Sponsor Banner"
    assert ad["position"] == "player_bottom"
    assert ad["is_active"] is True
    assert ad["priority"] == 10

    # 2. List ads (includes inactive if any)
    list_res = client.get("/api/v1/admin/ads", headers=HEADERS)
    assert list_res.status_code == 200
    ads = list_res.json()["ads"]
    assert len(ads) == 1
    assert ads[0]["id"] == ad_id

    # 3. Update ad
    update_res = client.put(
        f"/api/v1/admin/ads/{ad_id}",
        json={"title": "Updated Sponsor Banner", "priority": 25},
        headers=HEADERS,
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["title"] == "Updated Sponsor Banner"
    assert updated["priority"] == 25
    assert updated["image_url"] == "https://example.com/banner.jpg"

    # 4. Toggle active state
    toggle_res = client.patch(f"/api/v1/admin/ads/{ad_id}/toggle", headers=HEADERS)
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_active"] is False

    # Check that public endpoint no longer shows it
    pub_res = client.get("/api/v1/ads")
    assert len(pub_res.json()["ads"]) == 0

    # Toggle back
    toggle_res2 = client.patch(f"/api/v1/admin/ads/{ad_id}/toggle", headers=HEADERS)
    assert toggle_res2.status_code == 200
    assert toggle_res2.json()["is_active"] is True

    # 5. Delete ad
    del_res = client.delete(f"/api/v1/admin/ads/{ad_id}", headers=HEADERS)
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # 6. Verify empty list
    list_after = client.get("/api/v1/admin/ads", headers=HEADERS)
    assert len(list_after.json()["ads"]) == 0


def test_admin_ads_not_found_handling(client):
    assert client.put("/api/v1/admin/ads/unknown", json={"title": "X"}, headers=HEADERS).status_code == 404
    assert client.patch("/api/v1/admin/ads/unknown/toggle", headers=HEADERS).status_code == 404
    assert client.delete("/api/v1/admin/ads/unknown", headers=HEADERS).status_code == 404
