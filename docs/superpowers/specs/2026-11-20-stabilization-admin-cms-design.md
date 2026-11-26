# Design Document: Platform Stabilization, Lazy Scraper Hook & Admin CMS

**Date:** 2026-11-20  
**Status:** Proposed for Approval  
**Project:** `C:\Users\Mohany\Desktop\football-live-score-platform`  
**Baseline Spec:** `docs/superpowers/specs/2026-11-18-football-live-score-platform-design.md`, `docs/superpowers/specs/PRD.md`

---

## 1. Intent & Why

Audit and stabilize every function in the Arabic Football Live Score & Streaming Platform so that both automated test suites and live end-to-end runtime behavior work reliably, and complete the two missing product surfaces from the PRD:
1. An in-app **Admin CMS UI** (`لوحة التحكم`) so editors can manage stream servers and emergency match overrides directly in the browser.
2. A **configurable lazy stream scraper hook** (`LIVE_SCORE_SCRAPER_URL`) wired into the live read path via `PriorityResolver` (`Admin > API > Scraper`).

---

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- **Zero failing tests & full regression coverage:** Fix the failing snapshot test and lock down every discovered runtime bug with a failing-first regression test (per `/diagnosing-bugs`).
- **Working live Admin API + CMS UI:** Admin overrides and stream mutations work identically on live catalog fixtures and demo fixtures, with a fast RTL Admin panel in the frontend.
- **Uninterrupted, cross-browser stream playback:** Stop the 30s poll from resetting/remounting the active stream player, and add `hls.js` so `.m3u8` streams play in Chrome, Edge, and Firefox (native `<video>` fallback on Safari).
- **Resilient, fast live data ingestion:** Avoid 18-league timeout stalls on the currently down `worldcup26.ir` wrapper by making ESPN primary by default while preserving `worldcup26.ir` as fallback/override.
- **Accurate match metadata & UX:** Preserve `stadium`/`referee` on cached detail reads, eliminate stale poll race conditions, pass `tz` explicitly (with a header timezone selector), and tick upcoming countdowns every second.
- **Complete 3-tier priority wiring:** Lazily scrape streams per opened match when `LIVE_SCORE_SCRAPER_URL` is configured, merging `Admin > API > Scraper` without slowing down schedule loads.

### Non-Goals
- Hardcoding any specific third-party streaming portal URL or adding proxy/CF-bypass infrastructure.
- Introducing client-side URL routing (`react-router-dom`) or backend user-account/JWT auth systems (existing `X-Admin-Token` header contract stays authoritative).
- Hosting or proxying video streams.

### Anti-Goals
- **Breaking existing public/admin API contracts:** All existing `/api/v1/matches/*` and `/api/v1/admin/*` schemas and status codes remain backward-compatible.
- **Interrupting active playback during live score refreshes:** Score/event/stat updates must never reload the active iframe or HLS player unless the active server's URL actually changed or was removed.
- **Data loss on SQLite schema upgrade:** Migrating `admin_streams` to a composite primary key must preserve any existing rows in `data/live_score.db`.

---

## 3. Constraints

- **RTL-first Arabic UI, Latin tactical names:** All new UI (Admin CMS, timezone picker) follows `dir="rtl"`, dark/light mode tokens, and `Cairo`/`Inter` typography.
- **Zero secrets in client bundles:** `X-Admin-Token` is entered by the editor in the Admin UI and stored only in `sessionStorage` (cleared on logout).
- **Windows standalone environment:** Python runs from `.venv\Scripts\python.exe`; Node/npm runs from `.tools\node-v22.14.0-win-x64`.
- **Minimal new dependencies:** Add only `hls.js` on the frontend; zero new Python packages.

---

## 4. Approaches Considered & Selected

### Approach 1: In-place modular upgrade with lazy scraper hydration (Selected)
- Share fixture lookup between public and admin routes via `catalog` + fallback map.
- Keep `LiveFixturesCatalog` lazy: scrape streams per match inside `get_detail()` behind an optional `LIVE_SCORE_SCRAPER_URL` env var with TTL caching.
- Keep the frontend lightweight: toggle `AdminPanel.jsx` from a header button (`لوحة التحكم`), add `hls.js` to `StreamPlayerContainer.jsx`, and fix polling/countdowns in place.
- **Trade-offs:** No bookmarkable `/admin` URL, but zero router bloat, zero unnecessary scraping of unopened matches, and clean minimal diff.
- **Why selected:** Matches the existing lazy-hydration architecture and lets us fix and verify every function rapidly with high test coverage.

### Approach 2: React Router (`/admin`) + background scraper daemon (Not selected)
- Separate routes via `react-router-dom` plus a background thread continuously scraping streams for all 5-day fixtures.
- **Trade-offs:** Adds router dependency and hammers target stream portals for dozens of matches users never open.

---

## 5. Detailed Design (Bug Fixes & New Capabilities)

### 5.1 Backend Fixes

1. **Injectable clock in `LiveFixturesCatalog` (`src/live_score/api/catalog.py`)**
   - Accept optional `clock: Callable[[], datetime] = None` (default `lambda: datetime.now(timezone.utc)`).
   - Use `self._clock()` in `_load_snapshot()` when evaluating `age > self._snapshot_max_age` (and as default in `refresh()`, `fixtures()`, `seed_demo()`, `fixture_map()`, `get_detail()`).
   - Fixes `test_catalog_persists_and_reloads_the_last_live_snapshot` deterministically regardless of wall-clock date.

2. **Preserve summary metadata in `_overlay_match` (`src/live_score/api/catalog.py`)**
   - When overlaying `base.match` onto a cached `MatchDetail`, preserve summary-hydrated `stadium` and `referee` if `base.match` has `None` for those fields.

3. **Shared live fixture lookup for Admin routes (`src/live_score/api/admin_routes.py`, `src/live_score/api/public_routes.py`)**
   - Add a helper `_resolve_fixture(request, match_id)` that queries `catalog.get_detail(match_id, now)` (or `catalog.fixture_map(now).get(match_id)` to avoid unnecessary summary HTTP calls on writes) when `app.state.catalog` is active, falling back to `app.state.fixtures.get(match_id)`.
   - Admin endpoints (`POST/DELETE /streams`, `POST/DELETE /override`) immediately work for all refreshed live matches as well as demo matches.
   - Add optional `?tz=` query parameter to `GET /api/v1/matches/{match_id}` (defaulting to `app.state.timezone_name`, returning `400` on invalid timezone just like `/matches/today`).

4. **Admin match listing endpoint (`src/live_score/api/admin_routes.py`, `src/live_score/api/schemas.py`)**
   - Add `GET /api/v1/admin/matches?date=YYYY-MM-DD&tz=...&q=...` (protected by `require_admin`).
   - Returns list of resolved `AdminMatchOut` items (match card + resolved `servers` + `admin_server_ids` + raw `override` dict if active) so the Admin CMS can inspect, edit, toggle, and delete admin servers and overrides cleanly.
   - When `date` is omitted, returns all matches in the current window sorted by kickoff time; when `date` is provided, filters by local date in `tz`.

5. **Composite primary key for `admin_streams` (`src/live_score/api/store.py`)**
   - Change schema to `PRIMARY KEY (match_id, server_id)`.
   - On startup, inspect `PRAGMA table_info(admin_streams)`; if the existing table uses single-column PK (`server_id` only), safely migrate rows into the new composite-PK table inside a transaction.
   - Share `_normalized_url` normalization between `store.py` and `presenters.py` (`_merge_streams`) so deduplication is identical across writes and reads.

6. **Upstream provider order (`src/live_score/api/fixtures.py`)**
   - When `LIVE_SCORE_API_URL` is unset (default): use `EspnSoccerClient()` as primary and `LiveScoreV2Client(DEFAULT_BASE_URL)` as secondary in `FallbackSoccerClient` (unless `LIVE_SCORE_ESPN_FALLBACK=off`, in which case use `LiveScoreV2Client` directly).
   - When `LIVE_SCORE_API_URL` is explicitly set to a URL (not `"demo"`): honor it as primary with `EspnSoccerClient()` as secondary (unless `LIVE_SCORE_ESPN_FALLBACK=off`).
   - When `LIVE_SCORE_API_URL=demo`: keep deterministic demo mode.
   - Update `.env.example` and `README.md` to document `LIVE_SCORE_SCRAPER_URL` and the ESPN-first default.

7. **Adapter bug fixes & lazy scraper wiring**
   - `src/live_score/adapters/livescore_client.py`: replace `item.get("elapsed") or item.get("elapsed_time")` with an explicit `is not None` check so minute `0` is preserved.
   - `src/live_score/adapters/scraper_adapter.py`: restrict `<a href="...">` matching in `tab_pattern` so plain navigation links aren't misclassified as stream embeds—require either a `data-*` stream attribute, or an `href` pointing to a stream/embed/player/video/m3u8/youtube URL or inside an element with stream/server/player hints (`class`/`id`/Arabic server keywords like `سيرفر`/`بث`/`جودة`/`مشاهدة`). Preserve all existing unit-test behaviors.
   - `src/live_score/api/catalog.py` & `src/live_score/api/fixtures.py`: accept optional `scraper` (`PortalScraperAdapter`) and `scraper_ttl_seconds` (default `120.0`). When `LIVE_SCORE_SCRAPER_URL` is set, `create_catalog()` passes `PortalScraperAdapter(base_url=...)`. On `get_detail()`, lazily call `scraper.fetch_stream_servers(match.home_team.name_ar or match.home_team.name_en, match.away_team.name_ar or match.away_team.name_en)` *(builder call: matches Arabic portal convention in `test_adapters.py` without doubling HTTP requests)*, cached per `match_id` for `scraper_ttl_seconds` and swallowing errors so scraping never breaks match detail, then merge via `PriorityResolver.resolve(api_match=detail.match, scraped_match=...)` before returning to `presenters.py` (which applies `Admin` on top).

### 5.2 Frontend Fixes & Admin CMS UI

1. **Stable stream player + `hls.js` (`frontend/src/components/StreamPlayerContainer.jsx`)**
   - Install `hls.js` in `frontend/package.json`.
   - Compute a stable signature string of active servers (`id|url|type|sandbox` joined) and only reset `activeIndex` / `attempted` / `failedAll` / `retryKey` when the currently selected server disappears or changes URL—never on identical 30s poll payloads.
   - For `type === "m3u8"`:
     - If `Hls.isSupported()`, instantiate `Hls`, attach to `<video>`, load `current.url`, trigger `failCurrent()` on fatal `Hls.Events.ERROR`, and call `hls.destroy()` on unmount/switch.
     - Otherwise, render `<video src={current.url} onError={failCurrent} />` so Safari plays HLS natively and unsupported browsers (plus jsdom tests) fire `onError` → `failCurrent()` cleanly *(builder call: preserves existing Vitest HLS failover tests without breaking Safari or non-MSE fallbacks)*.

2. **Poll safety, timezone selector & live countdown (`frontend/src/App.jsx`, `frontend/src/lib/api.js`, `frontend/src/components/MatchCard.jsx`, `frontend/src/components/MatchDetailHybrid.jsx`)**
   - Add `cancelled` / `AbortController` guards to both 30s polling effects in `App.jsx` so switching tabs or closing match detail can never be overwritten by an in-flight poll.
   - Always pass `tz` to `fetchTodayMatches` and `fetchMatchDetail`, backed by a compact timezone selector in the header (defaults to `Asia/Riyadh`, persisted in `localStorage`, supporting `Asia/Riyadh`, `Africa/Cairo`, `Africa/Casablanca`, `Asia/Dubai`, `Europe/London`, `UTC`).
   - Add a shared `useCountdown(initialSeconds)` hook (or 1s tick effect synced to prop updates) so `SCHEDULED` countdown badges on both `MatchCard` and `MatchDetailHybrid` tick down every second live.
   - Show distinct Arabic badge for `HALFTIME` (`استراحة`) rather than `مباشر الآن (استراحة)`.

3. **Admin CMS UI (`frontend/src/components/AdminPanel.jsx`, `frontend/src/lib/api.js`)**
   - Header toggle button `لوحة التحكم` switches between public view and `AdminPanel`.
   - Token bar at top: editor enters `X-Admin-Token` (stored in `sessionStorage` under `kora-admin-token`), verified against `GET /api/v1/admin/matches`. Invalid token displays a clear Arabic error; logout clears `sessionStorage`.
   - Match list panel: filter by date (`الأمس`, `اليوم`, `الغد`, `الكل`) and live search input (Arabic/English team or league name); highlights overridden matches with an orange badge (`تعديل إداري`).
   - Match editor panel:
     - **Manual Override form:** `home_score`, `away_score`, `status` select (`SCHEDULED`, `IN_PLAY`, `HALFTIME`, `EXTRA_TIME`, `PENALTIES`, `FINISHED`, `POSTPONED`), `elapsed_time`, `channel`, `commentator`, `stadium`, `referee`, with **حفظ التعديل** (`POST /override`) and **إلغاء التعديل** (`DELETE /override`).
     - **Stream Servers manager:** lists current servers (marking admin vs. base/scraped), quick active toggle (`is_active`), edit button (populates form), delete button (`DELETE /streams/{id}` for admin streams), and add/update form (`server_name`, `url`, `type`, `quality`, `is_active` → `POST /streams`).
     - Immediate feedback banners (Arabic success/error messages) and automatic refresh of the match list + public schedule on return.

---

## 6. Verification Plan (Per `/diagnosing-bugs` & `/verification-before-completion`)

1. **Red-green regression tests for every bug:**
   - Backend (`pytest`): snapshot clock test, live catalog admin override/stream test (no 404), composite PK multi-match `server_id` test, `_overlay_match` preserving stadium/referee test, ESPN-first client order test, `elapsed == 0` test, scraper nav-link filtering + lazy catalog scraper integration test, `GET /api/v1/admin/matches` auth & filter test, `GET /api/v1/matches/{id}?tz=` test.
   - Frontend (`vitest`): `StreamPlayerContainer` does not reset/remount on identical server list refresh, `hls.js` lifecycle test, live countdown tick test, `AdminPanel` auth + stream CRUD + override save/clear tests.
2. **Production build:** `npm run build` passes cleanly.
3. **End-to-end live verification:** Start the FastAPI backend + Vite frontend, verify live ESPN fixtures load, open a match center, verify Admin CMS login + stream add + manual score override + public reflection + cleanup in a real browser / HTTP check.
4. **Cleanup:** Remove any temporary test overrides/DB rows from `data/live_score.db` if touched, ensure zero debug tags remain, and confirm full `pytest` + `vitest` + `vite build` pass.

---

## 7. What Is Left to the Builder

- Exact component styling details inside `AdminPanel.jsx` (reusing existing `glass-card`, `brand`, dark/light Tailwind classes).
- Helper decomposition inside `catalog.py` and `admin_routes.py` to keep files clean and readable.
