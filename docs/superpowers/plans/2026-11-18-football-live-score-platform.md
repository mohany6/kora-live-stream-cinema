# Arabic Football Live Score & Streaming Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status (2026-11-18):** All tasks implemented and verified. No git repository was available in this environment, so the commit steps were not executed.

**Goal:** Build a complete Arabic RTL football live score and match streaming portal featuring KoraCity-style match cards, a hybrid match center with multi-server video player, a 3-tier data engine (rezarahiminia/livescoreFootball + scraper daemon + admin CMS), and Figma design token integration.

**Architecture:** A FastAPI/Python backend coordinating a Priority Ingestion Resolver (Admin Override > Open-Source API > Scraper Daemon) with a local SQLite/PostgreSQL store, paired with a responsive React + Tailwind CSS RTL frontend with direct client-side stream embedding and live match center.

**Tech Stack:** Python 3.12 (FastAPI, Uvicorn, Pydantic, PyTest), React + Tailwind CSS (RTL support, Video/HLS embeds), SQLite/PostgreSQL.

**Spec:** `docs/superpowers/specs/2026-11-18-football-live-score-platform-design.md`

---

## Global Constraints
- Language & Direction: Right-to-Left (RTL) Arabic interface across all screens and components.
- Tactical Lineups: Player names on pitch in Latin/English characters (Option B), team names, events, and UI in Arabic.
- Zero Video Proxying: All video streams embedded client-side directly via sandboxed iframes or HLS players.
- Stream Priority: `Admin Override` > `Sports API / Open Backend` > `Scraper Ingestion`.
- Scraper Lifecycle: Activates 30 minutes before kickoff and refreshes dynamically during live matches.

---

## Review Focus
1. **Unmatched Arabic team names:** Scraped match names like `ليفربول` must map to `Liverpool FC` via alias dictionary or land safely in the Admin Unassigned Tray without breaking ingestion.
2. **Broken stream server failover:** When an external stream fails to load, client player must auto-switch to the next active server pill or display a fallback prompt without crashing.
3. **Timezone consistency:** Kickoff timestamps stored in UTC must format accurately to user local time (e.g. `14:00 بتوقيت مكة`).
4. **State transitions:** A match moving from Upcoming to Live must swap the green countdown badge for the pulsing red `مباشر الآن` badge instantly.
5. **Admin emergency override persistence:** An admin manually setting a score or swapping a stream URL must not be overwritten by subsequent automated API or scraper sync cycles.

---

## Task Structure

### Task 1: Core Domain Models & Priority Data Resolver

**Files:**
- Create: `src/live_score/domain/models.py`
- Create: `src/live_score/domain/resolver.py`
- Test: `tests/live_score/test_resolver.py`

**Interfaces:**
- Produces: `Match`, `Team`, `League`, `StreamServer`, `MatchEvent`, `LineupPlayer`, `MatchDetail`
- Produces: `PriorityResolver.resolve(api_match: Optional[Match], scraped_match: Optional[Match], admin_override: Optional[Match]) -> Match`
- Produces: `TeamAliasMatcher.match_team(arabic_name: str) -> Optional[str]`

- [x] **Step 1: Write the failing test for PriorityResolver and TeamAliasMatcher**

```python
def test_priority_resolver_admin_overrides_api_and_scraper():
    # Admin override must take precedence over both API and scraper
    ...
```

- [x] **Step 2: Run test to verify it fails**

Run: `.\venv\Scripts\pytest.exe tests/live_score/test_resolver.py -v`  
Expected: FAIL with module import / definition error.

- [x] **Step 3: Implement domain models and resolver logic**

Implement `models.py` with Pydantic v2 schemas and `resolver.py` enforcing the 3-tier hierarchy (`Admin Override` > `API Data` > `Scraped Data`) and Arabic alias lookup.

- [x] **Step 4: Run test to verify it passes**

Run: `.\venv\Scripts\pytest.exe tests/live_score/test_resolver.py -v`  
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add src/live_score/domain/ tests/live_score/
git commit -m "feat(live_score): domain models and priority ingestion resolver"
```

---

### Task 2: Upstream Ingestion Adapters (livescoreFootball client & Scraper stub)

**Files:**
- Create: `src/live_score/adapters/livescore_client.py`
- Create: `src/live_score/adapters/scraper_adapter.py`
- Test: `tests/live_score/test_adapters.py`

**Interfaces:**
- Consumes: `src/live_score/domain/models.py`
- Produces: `LiveScoreFootballClient.fetch_today_matches() -> list[Match]`
- Produces: `PortalScraperAdapter.fetch_stream_servers(match_query: str) -> list[StreamServer]`

- [x] **Step 1: Write failing adapter tests with mock JSON payloads**

```python
def test_livescore_client_normalizes_fixtures():
    client = LiveScoreFootballClient(base_url="http://mock-api")
    ...
```

- [x] **Step 2: Run test to verify it fails**

Run: `.\venv\Scripts\pytest.exe tests/live_score/test_adapters.py -v`  
Expected: FAIL with class missing.

- [x] **Step 3: Implement `LiveScoreFootballClient` and `PortalScraperAdapter`**

Implement mapping from `rezarahiminia/livescoreFootball` schema to internal `Match` models, plus stream server parser.

- [x] **Step 4: Run test to verify it passes**

Run: `.\venv\Scripts\pytest.exe tests/live_score/test_adapters.py -v`  
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add src/live_score/adapters/ tests/live_score/
git commit -m "feat(live_score): livescoreFootball client and stream scraper adapter"
```

---

### Task 3: Admin CMS & Match Stream Override API

**Files:**
- Create: `src/live_score/api/admin_routes.py`
- Create: `src/live_score/api/public_routes.py`
- Create: `src/live_score/api/app.py`
- Test: `tests/live_score/test_api.py`

**Interfaces:**
- Consumes: `src/live_score/domain/resolver.py`
- Produces: `GET /api/v1/matches/today` (Returns daily schedule with Option A format)
- Produces: `GET /api/v1/matches/{id}` (Returns hybrid match detail: stream servers, lineup, events)
- Produces: `POST /api/v1/admin/matches/{id}/streams` (Adds/edits stream server URLs)
- Produces: `POST /api/v1/admin/matches/{id}/override` (Sets emergency manual score/status)

- [x] **Step 1: Write failing tests for public and admin API endpoints**

```python
def test_admin_stream_override_endpoint():
    ...
```

- [x] **Step 2: Run test to verify it fails**

Run: `.\venv\Scripts\pytest.exe tests/live_score/test_api.py -v`  
Expected: FAIL.

- [x] **Step 3: Implement FastAPI routes in `admin_routes.py` and `public_routes.py`**

Build lightweight REST endpoints with in-memory / SQLite backing store supporting instant stream and score overrides.

- [x] **Step 4: Run test to verify it passes**

Run: `.\venv\Scripts\pytest.exe tests/live_score/test_api.py -v`  
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add src/live_score/api/ tests/live_score/
git commit -m "feat(live_score): admin and public match REST APIs"
```

---

### Task 4: PRD Specification Document & Figma Design System Tokens

**Files:**
- Create: `docs/superpowers/specs/PRD.md`
- Create: `design/tokens.json`
- Test: `tests/live_score/test_tokens.py`

**Interfaces:**
- Produces: Complete Product Requirements Document (`PRD.md`) with state schemas, failover logic, and database ERD.
- Produces: `tokens.json` with RTL spacing scales, `live-red` (#dc2626), `countdown-green` (#16a34a), `pitch-green` (#15803d), and dark mode neutral tokens ready for Figma MCP sync.

- [x] **Step 1: Write failing test verifying token schema and required color/spacing variables**

- [x] **Step 2: Run test to verify it fails**

Run: `.\venv\Scripts\pytest.exe tests/live_score/test_tokens.py -v`  
Expected: FAIL with file not found.

- [x] **Step 3: Author `PRD.md` and generate `design/tokens.json`**

Write the complete PRD covering all data contracts and state machines, and export standardized design tokens.

- [x] **Step 4: Run test to verify it passes**

Run: `.\venv\Scripts\pytest.exe tests/live_score/test_tokens.py -v`  
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add docs/superpowers/specs/PRD.md design/ tokens.json tests/live_score/
git commit -m "docs(prd): complete PRD specification and Figma design tokens"
```

---

### Task 5: Frontend Match Card & Home Schedule Component (Option A - RTL)

**Files:**
- Create: `frontend/src/components/MatchCard.jsx`
- Create: `frontend/src/components/ScheduleFilterTabs.jsx`
- Test: `frontend/src/components/__tests__/MatchCard.test.jsx`

**Interfaces:**
- Consumes: `GET /api/v1/matches/today`
- Produces: `<MatchCard match={match} onSelect={handleSelect} />`
- Produces: `<ScheduleFilterTabs activeTab={tab} onTabChange={setTab} />`

- [x] **Step 1: Write test checking RTL structure, home team on right, away on left, and live badge**

- [x] **Step 2: Implement `MatchCard.jsx` and `ScheduleFilterTabs.jsx`**

Adhere strictly to Option A layout: standalone card container, prominent team crests, centered live pulsing indicator or countdown timer badge, competition subtitle.

- [x] **Step 3: Verify component renders correctly across states (Live, Upcoming, Finished)**

- [x] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): Option A match card and schedule filter tabs"
```

---

### Task 6: Hybrid Match Detail Screen (Stream Player + Tactical Center)

**Files:**
- Create: `frontend/src/components/StreamPlayerContainer.jsx`
- Create: `frontend/src/components/TacticalPitchView.jsx`
- Create: `frontend/src/components/MatchDetailHybrid.jsx`
- Test: `frontend/src/components/__tests__/MatchDetailHybrid.test.jsx`

**Interfaces:**
- Consumes: `<StreamPlayerContainer servers={match.servers} />`
- Consumes: `<TacticalPitchView homeLineup={match.homeLineup} awayLineup={match.awayLineup} />`
- Produces: Fully assembled Hybrid Match Detail page with stream selector pills and tabbed stats.

- [x] **Step 1: Write test for server switching and client-side error fallback**

- [x] **Step 2: Implement `StreamPlayerContainer` with quality pills and sandboxed iframe/HLS player**

- [x] **Step 3: Implement `TacticalPitchView` with visual pitch graphic and English player names (Option B)**

- [x] **Step 4: Implement tabs for Timeline (`الملخص`), Lineup (`التشكيلة`), Stats (`الإحصائيات`), and Table (`الترتيب`)**

- [x] **Step 5: Verify seamless integration and commit**

```bash
git add frontend/
git commit -m "feat(frontend): hybrid match detail screen with stream player and tactical pitch"
```
