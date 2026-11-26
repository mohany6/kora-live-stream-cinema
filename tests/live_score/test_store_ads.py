"""Tests for AdminStore ads table and CRUD operations."""

import pytest
from live_score.api.store import AdminStore


@pytest.fixture
def store():
    s = AdminStore(":memory:")
    yield s
    s.close()


def test_ads_table_created(store):
    # Verify table exists in SQLite
    row = store._conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ads'"
    ).fetchone()
    assert row is not None
    assert row["name"] == "ads"


def test_upsert_and_get_ad(store):
    payload = {
        "title": "Header Banner 1",
        "position": "header_top",
        "ad_type": "image_banner",
        "image_url": "https://example.com/banner.png",
        "link_url": "https://example.com",
        "target_device": "all",
        "is_active": True,
        "priority": 10,
    }
    created = store.upsert_ad(payload)
    assert created["id"] is not None
    assert created["title"] == "Header Banner 1"
    assert created["is_active"] is True
    assert created["priority"] == 10
    assert "created_at" in created
    assert "updated_at" in created

    fetched = store.get_ad(created["id"])
    assert fetched is not None
    assert fetched["id"] == created["id"]
    assert fetched["title"] == "Header Banner 1"
    assert fetched["position"] == "header_top"
    assert fetched["image_url"] == "https://example.com/banner.png"
    assert fetched["is_active"] is True


def test_upsert_update_existing_ad(store):
    created = store.upsert_ad({
        "title": "Initial",
        "position": "player_bottom",
        "ad_type": "custom_html",
        "html_code": "<div>Ad</div>",
        "is_active": True,
        "priority": 5,
    })
    ad_id = created["id"]

    updated = store.upsert_ad({
        "id": ad_id,
        "title": "Updated Title",
        "position": "player_bottom",
        "ad_type": "custom_html",
        "html_code": "<div>Updated Ad</div>",
        "is_active": False,
        "priority": 20,
    })
    assert updated["id"] == ad_id
    assert updated["title"] == "Updated Title"
    assert updated["is_active"] is False
    assert updated["priority"] == 20

    fetched = store.get_ad(ad_id)
    assert fetched["title"] == "Updated Title"
    assert fetched["is_active"] is False
    assert fetched["priority"] == 20


def test_list_ads_filtering(store):
    store.upsert_ad({
        "id": "ad-1",
        "title": "Header Active All",
        "position": "header_top",
        "ad_type": "image_banner",
        "target_device": "all",
        "is_active": True,
        "priority": 1,
    })
    store.upsert_ad({
        "id": "ad-2",
        "title": "Header Inactive All",
        "position": "header_top",
        "ad_type": "image_banner",
        "target_device": "all",
        "is_active": False,
        "priority": 10,
    })
    store.upsert_ad({
        "id": "ad-3",
        "title": "Header Active Mobile",
        "position": "header_top",
        "ad_type": "image_banner",
        "target_device": "mobile",
        "is_active": True,
        "priority": 5,
    })
    store.upsert_ad({
        "id": "ad-4",
        "title": "Player Bottom Active Desktop",
        "position": "player_bottom",
        "ad_type": "image_banner",
        "target_device": "desktop",
        "is_active": True,
        "priority": 100,
    })

    # All ads
    all_ads = store.list_ads()
    assert len(all_ads) == 4
    # Ordered by priority DESC
    assert [a["id"] for a in all_ads] == ["ad-4", "ad-2", "ad-3", "ad-1"]

    # Active only
    active_ads = store.list_ads(active_only=True)
    assert len(active_ads) == 3
    assert "ad-2" not in [a["id"] for a in active_ads]

    # Position filter
    header_ads = store.list_ads(position="header_top")
    assert len(header_ads) == 3
    assert all(a["position"] == "header_top" for a in header_ads)

    # Active + Position
    active_header = store.list_ads(position="header_top", active_only=True)
    assert len(active_header) == 2
    assert [a["id"] for a in active_header] == ["ad-3", "ad-1"]

    # Device targeting: mobile should get target_device in ('all', 'mobile')
    mobile_active = store.list_ads(position="header_top", active_only=True, device="mobile")
    assert len(mobile_active) == 2
    assert {a["id"] for a in mobile_active} == {"ad-1", "ad-3"}

    # Device targeting: desktop should get target_device in ('all', 'desktop')
    desktop_active = store.list_ads(position="header_top", active_only=True, device="desktop")
    assert len(desktop_active) == 1
    assert desktop_active[0]["id"] == "ad-1"


def test_toggle_ad_active(store):
    ad = store.upsert_ad({
        "title": "Toggle test",
        "position": "in_feed",
        "ad_type": "image_banner",
        "is_active": True,
    })
    ad_id = ad["id"]
    assert store.get_ad(ad_id)["is_active"] is True

    new_state = store.toggle_ad_active(ad_id)
    assert new_state is False
    assert store.get_ad(ad_id)["is_active"] is False

    new_state = store.toggle_ad_active(ad_id)
    assert new_state is True
    assert store.get_ad(ad_id)["is_active"] is True

    # Non-existent ad
    assert store.toggle_ad_active("non-existent-id") is None


def test_delete_ad(store):
    ad = store.upsert_ad({
        "title": "To delete",
        "position": "sticky_bottom",
        "ad_type": "image_banner",
    })
    ad_id = ad["id"]
    assert store.get_ad(ad_id) is not None

    deleted = store.delete_ad(ad_id)
    assert deleted is True
    assert store.get_ad(ad_id) is None

    # Deleting again returns False
    assert store.delete_ad(ad_id) is False
