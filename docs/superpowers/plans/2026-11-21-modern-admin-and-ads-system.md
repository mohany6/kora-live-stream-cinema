# Modern Admin Cockpit & Dynamic Ads Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overhaul the admin panel into a high-density, modern SaaS Cockpit and build an end-to-end dynamic advertising engine supporting full CRUD, device targeting, and 5 prime responsive placements across the platform.

**Architecture:** Extend SQLite `AdminStore` with an indexed `ads` table and CRUD operations; introduce typed Pydantic models for ad validation; expose public and authenticated admin REST endpoints; create a lightweight, zero-layout-shift `<AdSlot />` frontend component supporting image banners and custom AdSense scripts; and completely redesign `AdminPanel.jsx` into a 3-tab modern Cockpit dashboard with live metric counters and zero-emoji UI.

**Tech Stack:** Python 3.12, FastAPI, SQLite, Pydantic v2, React 18, Tailwind CSS, Vitest, Pytest.

**Spec:** `docs/superpowers/specs/2026-11-21-modern-admin-and-ads-system-design.md`

## Global Constraints
- RTL-first Arabic typography and layout across all administrative and public views.
- Strict token authentication (`X-Admin-Token`) on all ad mutations and private listings.
- Zero layout thrashing: `<AdSlot />` must render nothing (`null`) when no active ad is assigned to a position.
- Safe sandboxed rendering of custom HTML/AdSense scripts.
- Zero emojis in code and production UI (use clean SVG/Lucide primitives as per `bexa`).
- All existing tests (94 pytest + 33 vitest) must continue passing with 100% success.

## Review Focus
1. SQL injection or malformed HTML in ad creation -> Validate URLs and sanitize/sandbox script inputs.
2. Stale or inactive ads showing to visitors -> Strict SQL filter on `is_active = 1` and cached public query invalidation.
3. Rapid toggling of ad status -> Atomic SQLite updates via `PATCH /ads/{id}/toggle`.
4. Mobile layout distortion from wide banners -> Responsive constraints (`max-w-full`, `overflow-hidden`, device breakpoints).
5. Tab switching state loss in Admin Panel -> Persistent or decoupled state between Matches Hub and Ads CMS.

---

### Task 1: SQLite Ads Storage Engine & Unit Tests

**Files:**
- Modify: `src/live_score/api/store.py`
- Create: `tests/live_score/test_store_ads.py`

- [ ] **Step 1: Write the failing unit tests for Ads Store**
  Create `tests/live_score/test_store_ads.py` testing:
  - Table creation on initialization.
  - `upsert_ad`, `get_ad`, `list_ads` (with position, is_active, and device filters).
  - `delete_ad` removing row cleanly.
  - `toggle_ad_active` flipping 1 to 0 and 0 to 1.
  - Priority ordering (higher priority returned first).

- [ ] **Step 2: Run test to confirm it fails**
  Run: `.\.venv\Scripts\python.exe -m pytest tests/live_score/test_store_ads.py`
  Confirm `AttributeError` or missing methods.

- [ ] **Step 3: Implement Ads SQLite schema and CRUD methods in `AdminStore`**
  In `src/live_score/api/store.py`:
  - Add `CREATE TABLE IF NOT EXISTS ads (...)` and index in `_init_db()`.
  - Add `upsert_ad(self, ad_dict: dict[str, Any]) -> dict[str, Any]`.
  - Add `get_ad(self, ad_id: str) -> Optional[dict[str, Any]]`.
  - Add `list_ads(self, position: Optional[str] = None, active_only: bool = False, device: Optional[str] = None) -> list[dict[str, Any]]`.
  - Add `delete_ad(self, ad_id: str) -> bool`.
  - Add `toggle_ad_active(self, ad_id: str) -> Optional[bool]`.

- [ ] **Step 4: Run test to confirm it passes**
  Run: `.\.venv\Scripts\python.exe -m pytest tests/live_score/test_store_ads.py`

---

### Task 2: Pydantic Schemas & Public Ads Route

**Files:**
- Modify: `src/live_score/api/schemas.py`
- Modify: `src/live_score/api/public_routes.py`
- Create: `tests/live_score/test_public_ads.py`

- [ ] **Step 1: Write the failing tests for Public Ads API**
  Create `tests/live_score/test_public_ads.py` testing:
  - `GET /api/v1/ads` returns active ads.
  - `GET /api/v1/ads?position=header_top` filters by placement.
  - Inactive ads are excluded from public output.

- [ ] **Step 2: Run test to confirm failure**
  Run: `.\.venv\Scripts\python.exe -m pytest tests/live_score/test_public_ads.py`

- [ ] **Step 3: Add Pydantic ad models and public route**
  In `src/live_score/api/schemas.py`:
  - Define `AdIn`, `AdUpdateIn`, `AdOut`, `AdsListOut`.
  In `src/live_score/api/public_routes.py`:
  - Add `GET /ads` route querying `store.list_ads(active_only=True)`.

- [ ] **Step 4: Run test to confirm it passes**
  Run: `.\.venv\Scripts\python.exe -m pytest tests/live_score/test_public_ads.py`

---

### Task 3: Admin CMS Ads Endpoints with Authentication

**Files:**
- Modify: `src/live_score/api/admin_routes.py`
- Create: `tests/live_score/test_admin_ads.py`

- [ ] **Step 1: Write failing tests for Admin Ads endpoints**
  Create `tests/live_score/test_admin_ads.py` testing:
  - Unauthenticated requests return 401.
  - `GET /api/v1/admin/ads` returns all ads including inactive.
  - `POST /api/v1/admin/ads` creates ad and returns 201.
  - `PUT /api/v1/admin/ads/{id}` updates fields.
  - `PATCH /api/v1/admin/ads/{id}/toggle` toggles active state.
  - `DELETE /api/v1/admin/ads/{id}` deletes ad.

- [ ] **Step 2: Run test to confirm failure**
  Run: `.\.venv\Scripts\python.exe -m pytest tests/live_score/test_admin_ads.py`

- [ ] **Step 3: Implement Admin Ads routes in `admin_routes.py`**
  Add endpoints with `require_admin` dependency and error handling.

- [ ] **Step 4: Run tests to confirm all backend tests pass**
  Run: `.\.venv\Scripts\python.exe -m pytest`

---

### Task 4: Frontend `<AdSlot />` Component & Integration

**Files:**
- Create: `frontend/src/components/AdSlot.jsx`
- Create: `frontend/src/components/__tests__/AdSlot.test.jsx`
- Modify: `frontend/src/lib/api.js`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/MatchDetailHybrid.jsx`

- [ ] **Step 1: Write frontend tests for `<AdSlot />`**
  Create `frontend/src/components/__tests__/AdSlot.test.jsx`:
  - Renders image banner with sponsor label and link.
  - Renders custom HTML snippet.
  - Renders null when no ad matches the position.
  - Handles dismissal on `sticky_bottom`.

- [ ] **Step 2: Run test to confirm failure**
  Run: `npm test -- --run AdSlot`

- [ ] **Step 3: Implement `<AdSlot />` and API client functions**
  In `frontend/src/lib/api.js`:
  - Add ad API methods (`fetchActiveAds`, `fetchAdminAds`, `createAdminAd`, `updateAdminAd`, `deleteAdminAd`, `toggleAdminAd`).
  In `frontend/src/components/AdSlot.jsx`:
  - Implement position-aware ad component with image banner and safe HTML rendering.
  In `frontend/src/App.jsx`:
  - Mount `<AdSlot position="header_top" />` below header.
  - Mount `<AdSlot position="in_feed" />` between leagues.
  - Mount `<AdSlot position="sticky_bottom" />` at viewport bottom.
  In `frontend/src/components/MatchDetailHybrid.jsx`:
  - Mount `<AdSlot position="player_top" />` above player.
  - Mount `<AdSlot position="player_bottom" />` below stream tabs.

- [ ] **Step 4: Run test to confirm AdSlot tests pass**
  Run: `npm test -- --run AdSlot`

---

### Task 5: Overhaul `AdminPanel.jsx` into Modern Cockpit Dashboard

**Files:**
- Modify: `frontend/src/components/AdminPanel.jsx`
- Modify: `frontend/src/components/__tests__/AdminPanel.test.jsx`

- [ ] **Step 1: Write tests for Admin Cockpit tabs**
  Update `frontend/src/components/__tests__/AdminPanel.test.jsx`:
  - Test switching between "المباريات والبث" and "إدارة الإعلانات".
  - Test ad creation modal trigger and active toggle.

- [ ] **Step 2: Implement Modern Cockpit layout in `AdminPanel.jsx`**
  - Top metric widgets (مباريات اليوم، تغطية البث %، إعلانات نشطة).
  - 3-tab navigation bar (المباريات والبث المباشر، نظام الإعلانات، نظرة عامة).
  - Tab 1: Enhanced Match & Live Stream Hub (status badges, quick stream presets, overrides).
  - Tab 2: Full Ads CMS (Grid of ad cards, visual position filters, creation/edit drawer, toggle switches, live preview, delete confirmation).
  - Tab 3: System & Cache status.
  - Zero emojis in UI / code (clean SVG icons).

- [ ] **Step 3: Run Vitest suite**
  Run: `npm test -- --run`

---

### Task 6: Full System Build, E2E Verification & Initial Ads Seeding

**Files:**
- Modify: `scripts/full_live_test.py`
- Rebuild: `frontend/dist`

- [ ] **Step 1: Add ad integration checks to `scripts/full_live_test.py`**
  Add live tests for creating an ad, toggling it, verifying public visibility on `/api/v1/ads`, and deleting it.

- [ ] **Step 2: Seed sample placeholder ads**
  Insert clean default ads in `header_top` and `player_bottom` for demo readiness.

- [ ] **Step 3: Rebuild frontend bundle**
  Run: `npm run build`

- [ ] **Step 4: Run complete Pytest, Vitest, and live E2E test suites**
  Verify 100% pass across all tests and live server on port 8000.
