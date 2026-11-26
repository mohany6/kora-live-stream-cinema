import time
from live_score.api.store import AdminStore


def test_sqlite_pragmas_and_batch_telemetry():
    store = AdminStore(":memory:")
    
    # 1. Verify WAL or in-memory pragmas and busy_timeout
    busy_timeout = store._conn.execute("PRAGMA busy_timeout").fetchone()[0]
    assert busy_timeout >= 5000

    # 2. Record multiple visits in rapid succession
    for i in range(50):
        store.record_visit(
            visitor_id=f"v_{i}",
            path="/matches/today",
            device="mobile" if i % 2 == 0 else "desktop",
            referrer="https://google.com",
        )

    # 3. Flushes correctly and records in site_visits table
    store.flush_visits()
    
    summary = store.get_analytics_summary()
    assert summary["today_visits"] == 50
    assert summary["today_uniques"] == 50


def test_auto_batch_flush_on_threshold():
    store = AdminStore(":memory:")
    # Batch threshold is 100 items
    for i in range(105):
        store.record_visit(
            visitor_id=f"v_{i}",
            path="/",
            device="desktop",
        )
    
    # Since 105 >= 100, the first 100 should have flushed automatically
    row = store._conn.execute("SELECT COUNT(*) FROM site_visits").fetchone()
    assert row[0] >= 100
    
    # Clean flush the rest
    store.flush_visits()
    row = store._conn.execute("SELECT COUNT(*) FROM site_visits").fetchone()
    assert row[0] == 105
