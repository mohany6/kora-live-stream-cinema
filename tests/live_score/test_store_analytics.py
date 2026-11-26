"""Tests for AdminStore site analytics and visitor tracking."""

from datetime import datetime, timezone, timedelta
import pytest
from live_score.api.store import AdminStore


@pytest.fixture
def store():
    s = AdminStore(":memory:")
    yield s
    s.close()


def test_site_visits_table_created(store):
    row = store._conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='site_visits'"
    ).fetchone()
    assert row is not None
    assert row["name"] == "site_visits"


def test_record_visit_and_summary(store):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Record some visits
    store.record_visit(visitor_id="v1", path="/", device="desktop")
    store.record_visit(visitor_id="v1", path="/matches/today", device="desktop") # same visitor
    store.record_visit(visitor_id="v2", path="/matches/today", device="mobile")

    summary = store.get_analytics_summary()
    assert summary["today_visits"] == 3
    assert summary["today_uniques"] == 2
    assert summary["total_visits"] == 3
    assert summary["total_uniques"] == 2


def test_analytics_by_period_day_week_month_year(store):
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    last_week_str = (now - timedelta(days=5)).strftime("%Y-%m-%d")

    # Insert visits with specific dates
    with store._conn:
        store._conn.execute(
            """
            INSERT INTO site_visits (timestamp, date, hour, visitor_id, path, device, referrer)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (now.isoformat(), today_str, now.hour, "u_today", "/", "mobile", "google"),
        )
        store._conn.execute(
            """
            INSERT INTO site_visits (timestamp, date, hour, visitor_id, path, device, referrer)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ((now - timedelta(days=1)).isoformat(), yesterday_str, 14, "u_yest", "/matches/1", "desktop", "direct"),
        )
        store._conn.execute(
            """
            INSERT INTO site_visits (timestamp, date, hour, visitor_id, path, device, referrer)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ((now - timedelta(days=5)).isoformat(), last_week_str, 18, "u_week", "/matches/today", "mobile", "twitter"),
        )

    # 1. Day breakdown (hours 0-23)
    day_data = store.get_analytics_timeseries(period="day")
    assert len(day_data) == 24
    assert any(item["visits"] > 0 for item in day_data)

    # 2. Week breakdown (7 days)
    week_data = store.get_analytics_timeseries(period="week")
    assert len(week_data) == 7
    total_week_visits = sum(item["visits"] for item in week_data)
    assert total_week_visits >= 3

    # 3. Month breakdown (30 days)
    month_data = store.get_analytics_timeseries(period="month")
    assert len(month_data) == 30

    # 4. Year breakdown (12 months)
    year_data = store.get_analytics_timeseries(period="year")
    assert len(year_data) == 12


def test_device_breakdown_and_top_pages(store):
    store.record_visit(visitor_id="v1", path="/matches/today", device="mobile")
    store.record_visit(visitor_id="v2", path="/matches/today", device="mobile")
    store.record_visit(visitor_id="v3", path="/", device="desktop")

    devices = store.get_device_breakdown(period="week")
    assert devices.get("mobile", 0) == 2
    assert devices.get("desktop", 0) == 1

    top_pages = store.get_top_pages(period="week", limit=5)
    assert len(top_pages) >= 1
    assert top_pages[0]["path"] == "/matches/today"
    assert top_pages[0]["visits"] == 2
