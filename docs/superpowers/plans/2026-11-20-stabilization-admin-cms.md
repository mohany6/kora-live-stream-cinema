# Football Live Score Platform — Stabilization, Lazy Scraper & Admin CMS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all failing tests and confirmed runtime bugs across the backend and RTL React frontend, wire an optional lazy stream scraper into the 3-tier priority catalog, and ship an RTL Admin CMS UI (`لوحة التحكم`).

**Architecture:** Keep the existing FastAPI + SQLite backend and zero-router Vite React frontend. Unify fixture lookup through `LiveFixturesCatalog` for both public and admin routes, lazily merge scraped streams on detail hydration (`Admin > API > Scraper`), default live data to ESPN primary with `worldcup26.ir` secondary, integrate `hls.js` into `StreamPlayerContainer`, and add `AdminPanel.jsx` toggled from the header.

**Tech Stack:** Python 3.12 (`.venv\Scripts\python.exe`), FastAPI, Pydantic v2, SQLite3, pytest; Node 22 (`.tools\node-v22.14.0-win-x64`), React 18, Tailwind CSS, Vite 6, Vitest, `hls.js`.

**Spec:** [2026-11-20-stabilization-admin-cms-design.md](file:///C:/Users/Mohany/Desktop/football-live-score-platform/docs/superpowers/specs/2026-11-20-stabilization-admin-cms-design.md)

## Global Constraints

- RTL-first Arabic UI (`dir="rtl"`, `lang="ar"`) with Latin/English player names on the tactical pitch; dark and light modes supported via existing Tailwind tokens.
- Zero video proxying; all stream URLs must be absolute `http(s)`, iframe embeds sandboxed with `allow-scripts allow-same-origin allow-presentation`.
- Zero secrets in frontend bundles; `X-Admin-Token` is entered by the editor and stored only in `sessionStorage` (`kora-admin-token`).
- Backward compatibility for all existing `/api/v1/matches/*` and `/api/v1/admin/*` endpoints and schemas.
- Non-destructive SQLite migration for existing rows in `data/live_score.db`.
- Minimal dependencies: add only `hls.js` on the frontend; zero new Python packages.
- All commands execute inside `C:\Users\Mohany\Desktop\football-live-score-platform` using `.venv\Scripts\python.exe` for Python and `.tools\node-v22.14.0-win-x64` prepended to `PATH` for Node/npm.

## Review Focus

1. **Legacy SQLite database upgrade with existing `admin_streams` rows:** Opening an already-populated `data/live_score.db` with the old single-column `server_id PRIMARY KEY` must migrate seamlessly to `PRIMARY KEY (match_id, server_id)` without dropping rows or crashing. (Pinned in Task 3.)
2. **Admin write while live catalog refreshes from demo to real fixtures:** Posting an override or stream immediately after catalog refreshes past startup must succeed (`200`/`201`), never `404`. (Pinned in Task 4.)
3. **Scraper failure or timeout on opened match detail:** When `LIVE_SCORE_SCRAPER_URL` is configured but the portal returns HTTP 500 or times out, `GET /api/v1/matches/{id}` must still return `200` with API/admin data intact. (Pinned in Task 2.)
4. **Active stream playback during 30s poll when server list is unchanged vs. changed:** Identical refreshed server lists must NOT reset `activeIndex` or remount the iframe/video, while removing the currently playing server must advance cleanly to an existing active server. (Pinned in Task 5.)
5. **Admin CMS rejected token (`401`) and partial override form submission:** Entering a bad admin token must show an Arabic error without crashing, and submitting only changed fields (e.g., `home_score` alone without empty strings) must send a valid `AdminOverrideIn` payload without triggering `422`. (Pinned in Task 7.)

---

## File Map

| File | Responsibility |
|---|---|
| `src/live_score/adapters/livescore_client.py` | Fix `elapsed == 0` falsy bug |
| `src/live_score/adapters/scraper_adapter.py` | Filter non-stream `<a href>` navigation links |
| `src/live_score/api/catalog.py` | Injectable `clock`, preserve `stadium`/`referee` in `_overlay_match`, lazy `scraper` hydration + TTL cache |
| `src/live_score/api/fixtures.py` | ESPN-first default provider order + optional `LIVE_SCORE_SCRAPER_URL` wiring |
| `src/live_score/api/store.py` | Composite `(match_id, server_id)` PK + migration + exported `normalize_stream_url` |
| `src/live_score/api/presenters.py` | Reuse `normalize_stream_url` in `_merge_streams` |
| `src/live_score/api/schemas.py` | Add `AdminMatchOut` and `AdminMatchesOut` response schemas |
| `src/live_score/api/public_routes.py` | Shared fixture resolver + optional `?tz=` on `GET /api/v1/matches/{match_id}` |
| `src/live_score/api/admin_routes.py` | Live catalog lookup + `GET /api/v1/admin/matches` |
| `.env.example`, `README.md` | Document ESPN-first default and `LIVE_SCORE_SCRAPER_URL` |
| `frontend/package.json` | Add `hls.js` dependency |
| `frontend/src/components/StreamPlayerContainer.jsx` | Stable server signature reset + `hls.js` lifecycle + fallback |
| `frontend/src/lib/useCountdown.js` | New 1s client-side countdown hook |
| `frontend/src/lib/api.js` | Pass `tz` on public calls + admin API client helpers |
| `frontend/src/components/MatchCard.jsx` | Live countdown tick + `HALFTIME` `استراحة` badge |
| `frontend/src/components/MatchDetailHybrid.jsx` | Live countdown tick + `HALFTIME` `استراحة` badge |
| `frontend/src/components/AdminPanel.jsx` | New RTL Admin CMS panel (auth, filters, override editor, stream CRUD) |
| `frontend/src/App.jsx` | Poll cancellation guards, timezone picker, `لوحة التحكم` AdminPanel toggle |

---

### Task 1: Backend Adapters — Fix `elapsed == 0` and Strict Scraper Embed Filtering

**Files:**
- Modify: `src/live_score/adapters/livescore_client.py:240-245`
- Modify: `src/live_score/adapters/scraper_adapter.py:94-136`
- Test: `tests/live_score/test_adapters.py`

**Interfaces:**
- Produces: `LiveScoreFootballClient._map_match_dict(item: dict) -> Optional[Match]` preserving `elapsed == 0`; `PortalScraperAdapter.parse_stream_embeds(html_content: Optional[str]) -> list[StreamServer]` ignoring generic navigation `<a href>` links while matching `data-*` stream attributes and stream-hinted `<a href>` links.

- [ ] **Step 1: Write failing tests in `tests/live_score/test_adapters.py`**

Add two tests:
1. `test_livescore_client_preserves_zero_elapsed_time`: payload with `"elapsed": 0` maps to `match.elapsed_time == 0` (not `None`).
2. `test_portal_scraper_ignores_plain_navigation_links`: HTML containing `<a href="https://portal.example/about">عن الموقع</a>`, `<a href="https://portal.example/news">أخبار</a>`, plus `<a href="https://stream.example/embed/ch1" class="server-btn">سيرفر 1</a>` and `<button data-url="https://player.example/2">سيرفر 2</button>` returns only the 2 stream servers (not `/about` or `/news`).

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/live_score/test_adapters.py -k "zero_elapsed or ignores_plain_navigation" -v`
Expected: FAIL (`None == 0` and `4 == 2`).

- [ ] **Step 3: Fix `livescore_client.py` and `scraper_adapter.py`**

- In `src/live_score/adapters/livescore_client.py:242`, check `item.get("elapsed")` with `is not None` before falling back to `item.get("elapsed_time")`.
- In `src/live_score/adapters/scraper_adapter.py`, add helper `_is_stream_href(tag_html: str, text: str, url: str) -> bool` used only when the match came from `href` (not `data-url`/`data-src`/`data-embed`/`data-stream`): return `True` if URL contains any of `("embed", "player", "stream", "live", "watch", "channel", ".m3u8", "youtube.com", "youtu.be", "video")` OR tag/text contains any stream hint (`"server"`, `"stream"`, `"player"`, `"quality"`, `"embed"`, `"سيرفر"`, `"بث"`, `"مشاهدة"`, `"جودة"`, `"يوتيوب"`, `"hd"`, `"sd"`).

- [ ] **Step 4: Run adapter test suite**

Run: `.\.venv\Scripts\python.exe -m pytest tests/live_score/test_adapters.py -v`
Expected: All tests in `test_adapters.py` PASS.

---

### Task 2: Live Catalog & Provider Priority — Injectable Clock, Metadata Preservation, Lazy Scraper & ESPN-First

**Files:**
- Modify: `src/live_score/api/catalog.py`
- Modify: `src/live_score/api/fixtures.py`
- Modify: `.env.example`, `README.md`
- Test: `tests/live_score/test_livescore_v2.py`

**Interfaces:**
- Consumes: `PortalScraperAdapter.fetch_stream_servers(home_team: str, away_team: str) -> list[StreamServer]`, `PriorityResolver.resolve(...)`
- Produces:
  - `LiveFixturesCatalog(..., clock: Optional[Callable[[], datetime]] = None, scraper: Optional[Any] = None, scraper_ttl_seconds: float = 120.0)`
  - `LiveFixturesCatalog.get_detail(match_id: str, now: Optional[datetime] = None) -> Optional[MatchDetail]` (preserves summary `stadium`/`referee` across cached reads and merges lazy scraped streams via `PriorityResolver`)
  - `_build_live_client(configured_url: str)` (ESPN primary when `configured_url` is empty; custom URL primary when explicitly configured)

- [ ] **Step 1: Verify existing failing snapshot test and add failing regression tests in `tests/live_score/test_livescore_v2.py`**

Add tests:
1. Update `test_catalog_persists_and_reloads_the_last_live_snapshot` to pass `clock=lambda: NOW + timedelta(seconds=30)` on `restored` (and add `test_catalog_uses_injected_clock_for_snapshot_expiry` proving old snapshots expire relative to `clock`, not wall clock).
2. `test_catalog_overlay_preserves_summary_stadium_and_referee`: first `get_detail` hydrates `stadium="Etihad Stadium"` and `referee="Michael Oliver"`; second `get_detail` within `detail_ttl` (where `base.match` has `stadium=None, referee=None`) still returns both `stadium` and `referee` while keeping updated scores.
3. `test_catalog_lazily_merges_scraped_streams_and_tolerates_scraper_errors`: configure a fake scraper on `LiveFixturesCatalog`; `fixtures()` makes 0 scraper calls; `get_detail()` calls scraper once with Arabic team names, caches for `scraper_ttl_seconds`, attaches `stream_servers`, and returns normal detail when scraper raises `RuntimeError`.
4. `test_build_live_client_defaults_to_espn_primary_and_honors_explicit_url`: with empty `LIVE_SCORE_API_URL`, `_build_live_client("")` returns `FallbackSoccerClient` with `isinstance(primary, EspnSoccerClient)` and `isinstance(secondary, LiveScoreV2Client)`; with `"https://custom.example/soccer"`, `primary` is `LiveScoreV2Client("https://custom.example/soccer")` and `secondary` is `EspnSoccerClient`.

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/live_score/test_livescore_v2.py -k "persists_and_reloads or injected_clock or overlay_preserves or lazily_merges or defaults_to_espn" -v`
Expected: FAIL on all 5 tests.

- [ ] **Step 3: Implement changes in `catalog.py`, `fixtures.py`, `.env.example`, and `README.md`**

- In `src/live_score/api/catalog.py`:
  - Add `clock`, `scraper`, `scraper_ttl_seconds=120.0` parameters to `LiveFixturesCatalog.__init__` (`self._clock = clock or (lambda: datetime.now(timezone.utc))`).
  - Use `self._clock()` inside `_load_snapshot()` and as the default `now` in public methods.
  - In `_overlay_match(detail, match)`: copy `match`, and if `updated_match.stadium is None` inherit `detail.match.stadium`; if `updated_match.referee is None` inherit `detail.match.referee`; if `not updated_match.stream_servers` inherit `detail.match.stream_servers`.
  - Add `_scraped_streams(match_id: str, match: Match, now: datetime) -> list[StreamServer]` cached per `match_id` in `self._scraped_cache` for `self._scraper_ttl`, calling `self._scraper.fetch_stream_servers(match.home_team.name_ar or match.home_team.name_en or "", match.away_team.name_ar or match.away_team.name_en or "")` inside a `try/except Exception` block. In `get_detail()`, merge scraped streams via `PriorityResolver.resolve(api_match=detail.match, scraped_match=...)` when non-empty.
- In `src/live_score/api/fixtures.py`:
  - Update `_build_live_client(configured_url: str)`:
    - `fallback_enabled = os.getenv("LIVE_SCORE_ESPN_FALLBACK", "on").strip().lower() not in {"off", "0", "false", "no"}`
    - If `configured_url`: `primary = LiveScoreV2Client(base_url=configured_url)`; return `FallbackSoccerClient(primary, EspnSoccerClient())` if `fallback_enabled` else `primary`.
    - Else (default): return `FallbackSoccerClient(EspnSoccerClient(), LiveScoreV2Client(base_url=DEFAULT_BASE_URL))` if `fallback_enabled` else `LiveScoreV2Client(base_url=DEFAULT_BASE_URL)`.
  - In `create_catalog()`: read `LIVE_SCORE_SCRAPER_URL`; if non-empty, instantiate `PortalScraperAdapter(base_url=scraper_url)` and pass to `LiveFixturesCatalog(..., scraper=scraper)`.
- Update `.env.example` and `README.md` to document `LIVE_SCORE_SCRAPER_URL` and ESPN-first default.

- [ ] **Step 4: Run `test_livescore_v2.py`**

Run: `.\.venv\Scripts\python.exe -m pytest tests/live_score/test_livescore_v2.py -v`
Expected: All tests PASS.

---

### Task 3: SQLite Store & Presenters — Composite Primary Key Migration & Unified URL Normalization

**Files:**
- Modify: `src/live_score/api/store.py`
- Modify: `src/live_score/api/presenters.py:72-85`
- Test: `tests/live_score/test_api.py`

**Interfaces:**
- Produces:
  - `normalize_stream_url(url: str) -> str` exported from `live_score.api.store` and imported by `live_score.api.presenters`
  - `AdminStore` with `PRIMARY KEY (match_id, server_id)` and automatic non-destructive migration of legacy single-column PK tables.

- [ ] **Step 1: Write failing tests in `tests/live_score/test_api.py`**

Add tests:
1. `test_admin_store_allows_same_server_id_across_different_matches`: upsert `id="srv_shared"` on `match_a` and `id="srv_shared"` on `match_b`; assert both matches retain their own distinct URLs and neither overwrote the other; deleting `srv_shared` on `match_a` leaves `match_b` intact.
2. `test_admin_store_migrates_legacy_single_pk_schema_preserving_rows`: create a raw SQLite DB with the old `server_id TEXT PRIMARY KEY` schema and 2 existing rows across 2 matches, instantiate `AdminStore(db_path)`, assert both existing rows remain readable AND inserting a duplicate `server_id` for a different `match_id` now succeeds.

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/live_score/test_api.py -k "same_server_id or migrates_legacy" -v`
Expected: FAIL.

- [ ] **Step 3: Implement composite PK + migration in `store.py` and reuse `normalize_stream_url` in `presenters.py`**

- In `src/live_score/api/store.py`:
  - Rename `_normalized_url` to `normalize_stream_url` (keep `_normalized_url = normalize_stream_url` alias if anything imports it).
  - Create `admin_streams` with `PRIMARY KEY (match_id, server_id)`.
  - In `_create_schema()`, check `PRAGMA table_info(admin_streams)`; if the PK columns are only `["server_id"]`, run a safe table rebuild (`admin_streams_new` -> `INSERT INTO ... SELECT ...` -> `DROP TABLE admin_streams` -> `ALTER TABLE admin_streams_new RENAME TO admin_streams` -> recreate index) inside a single transaction.
  - Update `upsert_stream` SQL to `ON CONFLICT(match_id, server_id) DO UPDATE SET ...`.
- In `src/live_score/api/presenters.py`:
  - Use `normalize_stream_url(server.url)` inside `_merge_streams`.

- [ ] **Step 4: Run API tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/live_score/test_api.py -v`
Expected: All tests PASS.

---

### Task 4: Public & Admin API Routes — Live Catalog Admin Lookup, `GET /api/v1/admin/matches`, and `?tz=` on Detail

**Files:**
- Modify: `src/live_score/api/schemas.py`
- Modify: `src/live_score/api/public_routes.py`
- Modify: `src/live_score/api/admin_routes.py`
- Test: `tests/live_score/test_api.py`

**Interfaces:**
- Consumes: `LiveFixturesCatalog.fixtures(now)`, `LiveFixturesCatalog.fixture_map(now)`, `LiveFixturesCatalog.get_detail(match_id, now)`
- Produces:
  - `GET /api/v1/matches/{match_id}?tz=Asia/Riyadh` (optional `tz`, `400` on invalid timezone)
  - `AdminMatchOut` (`match: MatchCardOut`, `servers: list[StreamServerOut]`, `admin_server_ids: list[str]`, `override: Optional[dict[str, Any]]`) and `AdminMatchesOut` (`date: Optional[str]`, `timezone: str`, `timezone_label_ar: str`, `matches: list[AdminMatchOut]`)
  - `GET /api/v1/admin/matches?date=YYYY-MM-DD&tz=...&q=...` (requires `X-Admin-Token`)
  - Working `POST/DELETE /api/v1/admin/matches/{match_id}/streams` and `/override` for matches dynamically refreshed into `app.state.catalog`.

- [ ] **Step 1: Write failing tests in `tests/live_score/test_api.py`**

Add tests:
1. `test_admin_endpoints_work_on_dynamically_refreshed_catalog_matches`: create an app with an initially empty `app.state.fixtures` and a `LiveFixturesCatalog` whose second refresh loads `"live-999"`; assert `POST /api/v1/admin/matches/live-999/override` returns `200`, `POST /api/v1/admin/matches/live-999/streams` returns `201`, and `GET /api/v1/matches/live-999` reflects both.
2. `test_admin_list_matches_requires_auth_and_returns_streams_and_override_state`: assert `401` without token; with token returns `AdminMatchesOut` containing `admin_server_ids` and `override` dict after applying an override + stream, and filters cleanly by `date` and `q` (Arabic or English team/league substring).
3. `test_public_match_detail_respects_tz_query_param_and_rejects_bad_tz`: `GET /api/v1/matches/match_clasico?tz=UTC` formats `kickoff_time_local` in UTC (different from `Asia/Riyadh`), and `?tz=Invalid/Zone` returns `400`.

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/live_score/test_api.py -k "dynamically_refreshed or admin_list_matches or detail_respects_tz" -v`
Expected: FAIL.

- [ ] **Step 3: Implement schemas and route updates**

- In `src/live_score/api/schemas.py`: add `AdminMatchOut` and `AdminMatchesOut`.
- In `src/live_score/api/public_routes.py`: add optional `tz: Optional[str] = Query(default=None)` to `match_detail`, resolving timezone with `400` on `ValueError`.
- In `src/live_score/api/admin_routes.py`:
  - Update `_get_fixture(request, match_id)`: when `getattr(request.app.state, "catalog", None)` is not `None`, look up `catalog.fixture_map(request.app.state.clock()).get(match_id)` first, falling back to `request.app.state.fixtures.get(match_id)`.
  - Add `GET /api/v1/admin/matches` (`dependencies=[Depends(require_admin)]`) supporting optional `date`, `tz`, and `q` (case-insensitive substring match against `home_team.name_ar`, `home_team.name_en`, `away_team.name_ar`, `away_team.name_en`, `league.name_ar`, `league.name_en`), returning `AdminMatchesOut`.

- [ ] **Step 4: Run full backend test suite**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: All backend tests PASS (0 failures).

---

### Task 5: Frontend Stream Player — Prevent 30s Poll Restarts & Add `hls.js` Support

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/components/StreamPlayerContainer.jsx`
- Test: `frontend/src/components/__tests__/StreamPlayerContainer.test.jsx`

**Interfaces:**
- Produces: `StreamPlayerContainer({ servers, channel, commentator })` preserving playback position/active server across referentially-new but identical `servers` props, and using `hls.js` whenever `Hls.isSupported()` is true (with native `<video src onError>` fallback otherwise).

- [ ] **Step 1: Install `hls.js` in `frontend/`**

Run:
```powershell
Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform\frontend"
$env:Path = "$(Resolve-Path ..\.tools\node-v22.14.0-win-x64);$env:Path"
npm install hls.js
```
Expected: `hls.js` added to `frontend/package.json` `dependencies`.

- [ ] **Step 2: Write failing tests in `frontend/src/components/__tests__/StreamPlayerContainer.test.jsx`**

Add tests:
1. `keeps the selected server and does not remount when servers array is refreshed with identical items`: render with 2 servers, click Server 2 (`server-pill-1`), re-render with a cloned `servers` array (new object references, same content); assert `server-pill-1` stays `aria-selected="true"` and the iframe DOM node identity is unchanged (`===`).
2. `uses hls.js when Hls.isSupported returns true and fails over on fatal HLS error`: mock `hls.js` (`isSupported: () => true`, `loadSource`, `attachMedia`, `on`, `destroy`), render an `m3u8` + `iframe` server list, assert `loadSource` and `attachMedia` are called, trigger the registered `Hls.Events.ERROR` callback with `{ fatal: true }`, assert failover to Server 2 iframe and `destroy()` called.

- [ ] **Step 3: Run StreamPlayerContainer tests to verify new tests fail**

Run:
```powershell
Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform\frontend"
$env:Path = "$(Resolve-Path ..\.tools\node-v22.14.0-win-x64);$env:Path"
npx vitest run src/components/__tests__/StreamPlayerContainer.test.jsx
```
Expected: New tests FAIL.

- [ ] **Step 4: Implement stable server tracking and `hls.js` integration in `StreamPlayerContainer.jsx`**

- Track active server by stable key (`currentUrl` / serialized `activeServers` signature) rather than resetting blindly on `[servers]`:
  - When `activeServers` changes, if the previously selected server URL is still present at some index `nextIdx`, update `activeIndex` to `nextIdx` without bumping `retryKey` or resetting `failedAll`; only reset to `0` if the previously selected server was removed.
- Add a `videoRef` and a `useEffect` for `current?.type === "m3u8"` and `!failedAll`:
  - When `Hls.isSupported()` is true, create `new Hls()`, attach to `videoRef.current`, call `loadSource(current.url)`, listen to `Hls.Events.ERROR` calling `failCurrent()` when `data?.fatal`, and call `hls.destroy()` in cleanup.
  - Otherwise keep `src={current.url}` directly on `<video>` with `onError={failCurrent}` (Safari native HLS + clean fallback/test compatibility).

- [ ] **Step 5: Run StreamPlayerContainer tests**

Run:
```powershell
Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform\frontend"
$env:Path = "$(Resolve-Path ..\.tools\node-v22.14.0-win-x64);$env:Path"
npx vitest run src/components/__tests__/StreamPlayerContainer.test.jsx
```
Expected: All tests PASS (including all 5 pre-existing tests).

---

### Task 6: Frontend Schedule, Match Center & Timezone — Poll Guards, Explicit `tz` Picker, Live Countdown & `HALFTIME` Badge

**Files:**
- Create: `frontend/src/lib/useCountdown.js`
- Modify: `frontend/src/lib/api.js`
- Modify: `frontend/src/components/MatchCard.jsx`
- Modify: `frontend/src/components/MatchDetailHybrid.jsx`
- Modify: `frontend/src/App.jsx`
- Test: `frontend/src/lib/__tests__/api.test.js`, `frontend/src/components/__tests__/MatchCard.test.jsx`

**Interfaces:**
- Produces:
  - `SUPPORTED_TIMEZONES` exported from `frontend/src/lib/api.js` (`Asia/Riyadh`, `Africa/Cairo`, `Africa/Casablanca`, `Asia/Dubai`, `Europe/London`, `UTC`)
  - `fetchMatchDetail(matchId, { tz, signal } = {})` and `fetchTodayMatches({ date, tz, signal } = {})`
  - `useCountdown(initialSeconds: number | null) -> number | null` ticking down by 1s every second while `> 0`

- [ ] **Step 1: Write failing tests in `frontend/src/lib/__tests__/api.test.js` and `frontend/src/components/__tests__/MatchCard.test.jsx`**

Add tests:
1. In `api.test.js`: `fetchMatchDetail` appends `?tz=...` when provided, and `fetchTodayMatches` passes `signal` to `fetch`.
2. In `MatchCard.test.jsx`:
   - `ticks upcoming match countdown down every second`: with `vi.useFakeTimers()`, render upcoming match with `countdown_seconds: 10`, advance 3000ms, assert countdown displays `00:00:07`.
   - `renders distinct استراحة badge for HALFTIME matches`: render a match with `status: "HALFTIME"`, assert `live-badge` displays `استراحة` (not `مباشر الآن (استراحة)`).

- [ ] **Step 2: Run targeted Vitest tests to verify they fail**

Run:
```powershell
Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform\frontend"
$env:Path = "$(Resolve-Path ..\.tools\node-v22.14.0-win-x64);$env:Path"
npx vitest run src/lib/__tests__/api.test.js src/components/__tests__/MatchCard.test.jsx
```
Expected: New tests FAIL.

- [ ] **Step 3: Implement `useCountdown.js`, `api.js`, `MatchCard.jsx`, `MatchDetailHybrid.jsx`, and `App.jsx` updates**

- Create `frontend/src/lib/useCountdown.js`: syncs state when `initialSeconds` changes; decrements once per second via `setInterval` while `> 0` and cleans up on unmount.
- Update `frontend/src/lib/api.js`: export `SUPPORTED_TIMEZONES`, accept `{ tz, signal }` in `fetchTodayMatches` and `fetchMatchDetail`.
- Update `MatchCard.jsx` and `MatchDetailHybrid.jsx`: use `useCountdown(match.countdown_seconds)` for scheduled matches, and render `استراحة` directly when `match.status === "HALFTIME"`.
- Update `App.jsx`:
  - Add `timezone` state (persisted to `localStorage` under `kora-tz`, default `DISPLAY_TIMEZONE`) with a compact `<select aria-label="المنطقة الزمنية">` in the header.
  - Pass `{ date: localDateForOffset(offset, { timeZone: timezone }), tz: timezone, signal }` to `fetchTodayMatches` and `{ tz: timezone, signal }` to `fetchMatchDetail`.
  - Add `cancelled` + `AbortController` cleanup to both 30s polling effects so switching tabs, changing timezone, or closing match detail aborts/ignores in-flight poll responses.

- [ ] **Step 4: Run all frontend tests**

Run:
```powershell
Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform\frontend"
$env:Path = "$(Resolve-Path ..\.tools\node-v22.14.0-win-x64);$env:Path"
npm test
```
Expected: All tests PASS.

---

### Task 7: Frontend Admin CMS UI (`لوحة التحكم`) & Full End-to-End Verification

**Files:**
- Modify: `frontend/src/lib/api.js`
- Create: `frontend/src/components/AdminPanel.jsx`
- Modify: `frontend/src/App.jsx`
- Test: `frontend/src/components/__tests__/AdminPanel.test.jsx`

**Interfaces:**
- Consumes: `GET /api/v1/admin/matches`, `POST /api/v1/admin/matches/{id}/streams`, `DELETE /api/v1/admin/matches/{id}/streams/{server_id}`, `POST /api/v1/admin/matches/{id}/override`, `DELETE /api/v1/admin/matches/{id}/override`
- Produces:
  - Admin API client functions in `frontend/src/lib/api.js`: `fetchAdminMatches({ token, date, tz, q })`, `upsertAdminStream({ token, matchId, payload })`, `deleteAdminStream({ token, matchId, serverId })`, `setAdminOverride({ token, matchId, payload })`, `clearAdminOverride({ token, matchId })`
  - `AdminPanel({ timezone, onClose, onDataChanged })` toggled from the header `لوحة التحكم` button in `App.jsx`.

- [ ] **Step 1: Write failing tests in `frontend/src/components/__tests__/AdminPanel.test.jsx`**

Add tests:
1. `prompts for admin token, stores valid token in sessionStorage, and shows error on 401`: submit invalid token → displays Arabic error; submit valid token → loads match list and saves token in `sessionStorage` (`kora-admin-token`).
2. `submits partial manual override without empty fields and clears override`: select a match, enter `home_score = 3` and `status = FINISHED`, click `حفظ التعديل` → verifies `POST /override` body contains only `{ home_score: 3, status: "FINISHED" }` (no empty strings); click `إلغاء التعديل` → calls `DELETE /override`.
3. `adds, toggles active state, and deletes an admin stream server`: fill stream form (`server_name`, `url`, `type`, `quality`) and submit → calls `POST /streams`; click toggle active → calls `POST /streams` with `is_active: false`; click delete on admin stream → calls `DELETE /streams/{id}`.

- [ ] **Step 2: Run AdminPanel tests to verify they fail**

Run:
```powershell
Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform\frontend"
$env:Path = "$(Resolve-Path ..\.tools\node-v22.14.0-win-x64);$env:Path"
npx vitest run src/components/__tests__/AdminPanel.test.jsx
```
Expected: FAIL (`AdminPanel.jsx` does not exist yet).

- [ ] **Step 3: Implement admin API helpers in `api.js`, create `AdminPanel.jsx`, and wire header toggle in `App.jsx`**

- In `frontend/src/lib/api.js`: add `requestJson(path, { method, token, body, signal })` helper and export the 5 admin API functions sending `X-Admin-Token`.
- Create `frontend/src/components/AdminPanel.jsx`:
  - Reads initial token from `sessionStorage.getItem("kora-admin-token")` (never hardcoded).
  - Auth header bar with token input, `دخول` / `تسجيل الخروج` buttons.
  - Date filter (`الأمس`, `اليوم`, `الغد`, `الكل`), live search input, refresh button, and RTL split layout: match list on inline-start, editor on inline-end.
  - Manual Override form: parses numeric fields cleanly, omits blank fields when posting so partial updates pass Pydantic validation, shows `تعديل إداري` indicator and `إلغاء التعديل` button.
  - Stream Servers manager: lists servers with admin badge, active/inactive toggle button, edit button, delete button (for `admin_server_ids`), and add/update form (`server_name`, `url`, `type`, `quality`, `is_active`).
  - Calls `onDataChanged?.()` after successful mutations so public schedule reloads immediately when returning.
- In `frontend/src/App.jsx`: add `adminOpen` state + header button `لوحة التحكم` that toggles `AdminPanel` cleanly (and refreshes the schedule when closing after changes).

- [ ] **Step 4: Run full test suites and production build**

Run:
```powershell
# Backend
Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform"
.\.venv\Scripts\python.exe -m pytest -v

# Frontend tests + build
Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform\frontend"
$env:Path = "$(Resolve-Path ..\.tools\node-v22.14.0-win-x64);$env:Path"
npm test
npm run build
```
Expected: 100% of backend pytest tests PASS, 100% of frontend vitest tests PASS, `vite build` succeeds with 0 errors.

- [ ] **Step 5: End-to-end live verification & cleanup**

- Start backend (`python run.py` or `uvicorn`) and Vite dev server (`npm run dev`), verify:
  - `GET /health` reports `status: "ok"` and live fixtures loaded via ESPN without `worldcup26.ir` stall.
  - `GET /api/v1/matches/today` and `GET /api/v1/matches/{id}` return live matches and match center details.
  - Admin CMS UI in browser (or full API round-trip): authenticate with `X-Admin-Token`, add a stream + manual override on a live match, verify reflection on the public match card & match center, then delete the test stream & clear the test override so `data/live_score.db` stays clean.
  - Stop temporary dev servers before finishing.
