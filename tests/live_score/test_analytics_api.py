"""Tests for analytics endpoints: POST /api/v1/analytics/track and GET /api/v1/admin/analytics/stats."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from live_score.api.app import create_app

FIXED_NOW = datetime(2026, 11, 18, 16, 0, tzinfo=timezone.utc)
ADMIN_TOKEN = "test-admin-token"
ADMIN_HEADERS = {"X-Admin-Token": ADMIN_TOKEN}


@pytest.fixture
def client(tmp_path):
    app = create_app(
        fixtures=[],
        db_path=str(tmp_path / "analytics_test.db"),
        admin_token=ADMIN_TOKEN,
        clock=lambda: FIXED_NOW,
    )
    with TestClient(app) as tc:
        yield tc


def test_public_track_visit(client):
    res = client.post(
        "/api/v1/analytics/track",
        json={
            "visitor_id": "test-visitor-1",
            "path": "/matches/today",
            "device": "mobile",
            "referrer": "https://google.com",
        },
    )
    assert res.status_code == 200
    assert res.json()["recorded"] is True


def test_admin_analytics_stats_requires_auth(client):
    assert client.get("/api/v1/admin/analytics/stats").status_code == 401


def test_admin_analytics_stats_periods(client):
    # Track some visits
    client.post(
        "/api/v1/analytics/track",
        json={"visitor_id": "v1", "path": "/", "device": "desktop"},
    )
    client.post(
        "/api/v1/analytics/track",
        json={"visitor_id": "v2", "path": "/matches/1", "device": "mobile"},
    )

    # 1. Week stats
    res_week = client.get("/api/v1/admin/analytics/stats?period=week", headers=ADMIN_HEADERS)
    assert res_week.status_code == 200
    data_week = res_week.json()
    assert data_week["period"] == "week"
    assert "summary" in data_week
    assert data_week["summary"]["total_visits"] >= 2
    assert len(data_week["chart_data"]) == 7
    assert "device_stats" in data_week
    assert "top_pages" in data_week

    # 2. Day stats
    res_day = client.get("/api/v1/admin/analytics/stats?period=day", headers=ADMIN_HEADERS)
    assert res_day.status_code == 200
    assert len(res_day.json()["chart_data"]) == 24

    # 3. Month stats
    res_month = client.get("/api/v1/admin/analytics/stats?period=month", headers=ADMIN_HEADERS)
    assert res_month.status_code == 200
    assert len(res_month.json()["chart_data"]) == 30

    # 4. Year stats
    res_year = client.get("/api/v1/admin/analytics/stats?period=year", headers=ADMIN_HEADERS)
    assert res_year.status_code == 200
    assert len(res_year.json()["chart_data"]) == 12
