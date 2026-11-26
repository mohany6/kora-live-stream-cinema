import tempfile
from pathlib import Path
from live_score.api.store import AdminStore

def test_store_close_stops_flusher():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        store = AdminStore(db_path)
        store.record_visit("visitor1", "/test", "desktop", "")
        store.close()
        assert store._stop_flusher.is_set()
        assert not store._flusher_thread.is_alive()
