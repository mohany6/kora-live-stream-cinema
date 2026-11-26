# Task 2 Brief: Static Matches JSON Stream Exporter

**Working Directory:** `C:\Users\Mohany\Desktop\football-live-score-platform`
**Python Venv:** `C:\Users\Mohany\Desktop\football-live-score-platform\.venv\Scripts\python.exe`

## Goal
Create `scripts/export_static_streams.py` and unit tests in `tests/test_static_stream_exporter.py` that dump today's verified matches and multi-server streaming URLs to `frontend/public/data/matches.json` (and `data/matches.json`), so Cloudflare Pages can serve live streaming matches as static JSON without requiring a live FastAPI server.

## Files to Create
- `scripts/export_static_streams.py`
- `tests/test_static_stream_exporter.py`

## Detailed Requirements
1. **`scripts/export_static_streams.py`**:
   - `export_static_matches_json(target_path: Path | None = None, now: datetime | None = None) -> int`:
     - Reads today's fixtures using `create_catalog(now).fixture_map(now)`.
     - Serializes each match into the exact schema expected by `frontend/src/App.jsx`:
       - `id`, `status` (IN_PLAY, SCHEDULED, FINISHED), `status_label_ar`, `elapsed_time`, `live_minute_label`, `kickoff_time_local`, `kickoff_date_local`, `countdown_seconds`, `competition_subtitle`, `channel`, `commentator`, `stadium`, `referee`, `has_stream` (bool).
       - `home_team`: `{"name_ar": ..., "name_en": ..., "logo_url": ...}`
       - `away_team`: `{"name_ar": ..., "name_en": ..., "logo_url": ...}`
       - `league`: `{"name_ar": ..., "name_en": ..., "round": ...}`
       - `servers`: list of server objects `[{"id": "...", "server_name": "سيرفر 1 (HD)", "url": "...", "type": "iframe"|"m3u8", "is_active": True}]`
       - Detail metadata: `home_lineup`, `away_lineup`, `home_formation`, `away_formation`, `events`, `stats`, `standings`.
     - Writes to `frontend/public/data/matches.json` (defaults to `frontend/public/data/matches.json`, and if target_path is specified, writes there).
     - Returns the total count of matches exported.
   - CLI execution (`if __name__ == "__main__":`): outputs count and saved path.
2. **`tests/test_static_stream_exporter.py`**:
   - Tests `export_static_matches_json` with mocked catalog data.
   - Verifies JSON structure contains `matches` list, `updated_at`, `count`, and valid match fields.
   - Run tests: `.\.venv\Scripts\python.exe -m pytest tests/test_static_stream_exporter.py` (Must PASS).
   - Run full suite: `.\.venv\Scripts\python.exe -m pytest` (Must PASS).
