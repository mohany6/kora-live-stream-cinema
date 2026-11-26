# Design Document: Modern Cockpit Admin Panel & Dynamic Ads Engine

- **Date:** 2026-11-21
- **Status:** Proposed
- **Authors:** Senior Design Engineer / Antigravity Agent
- **Target App:** `football-live-score-platform`

---

## 1. Executive Summary & Goals

The user requested upgrading the existing live score admin panel to be **powerful and modern** (Cockpit / Command Center UX) and introducing a **Dynamic Ads Engine** that gives the administrator total control over advertising across the platform:
1. **Full Ad Lifecycle**: Add, update, delete, reorder, preview, and toggle active/paused state on any ad in real time.
2. **Placement & Device Targeting**: Assign ads to strategic placements (`header_top`, `in_feed`, `player_top`, `player_bottom`, `sticky_bottom`) with device filters (`all`, `desktop`, `mobile`).
3. **Format Flexibility**: Support both **Image Banners** (custom graphic + target hyperlink) and **Custom HTML/Scripts** (Google AdSense, programmatic tags).
4. **Cockpit Admin Experience**: A high-density, multi-tabbed administration dashboard (aligned with `bexa` and `frontend-design` guidelines) featuring platform statistics, instant status badges, stream link presets, and zero-emoji UI.

---

## 2. Architecture & Data Model

### 2.1 SQLite Schema (`ads` table)
Integrated into `src/live_score/api/store.py` with automatic table creation and migrations:

```sql
CREATE TABLE IF NOT EXISTS ads (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    position TEXT NOT NULL,         -- 'header_top' | 'in_feed' | 'player_top' | 'player_bottom' | 'sticky_bottom'
    ad_type TEXT NOT NULL,          -- 'image_banner' | 'custom_html'
    image_url TEXT,
    link_url TEXT,
    html_code TEXT,
    target_device TEXT DEFAULT 'all', -- 'all' | 'desktop' | 'mobile'
    is_active INTEGER DEFAULT 1,    -- 1 = enabled, 0 = paused
    priority INTEGER DEFAULT 0,     -- higher integer appears first
    created_at TEXT NOT NULL,       -- ISO UTC
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ads_position_active ON ads(position, is_active, priority DESC);
```

### 2.2 Domain & Pydantic Schemas (`src/live_score/api/schemas.py`)
- `AdIn`: Creation schema with URL/HTML validators and position checks.
- `AdUpdateIn`: Partial update schema.
- `AdOut`: Output model with formatting and validation.
- `AdsListOut`: Envelope model for listings.

### 2.3 API Endpoints
- **Public**:
  - `GET /api/v1/ads?position={pos}&device={dev}`: Returns active, prioritized ads for public display with caching.
- **Admin** (protected by `X-Admin-Token`):
  - `GET /api/v1/admin/ads`: Returns all ads with status and metadata.
  - `POST /api/v1/admin/ads`: Creates a new ad.
  - `PUT /api/v1/admin/ads/{id}`: Updates an existing ad.
  - `DELETE /api/v1/admin/ads/{id}`: Deletes an ad.
  - `PATCH /api/v1/admin/ads/{id}/toggle`: Toggles `is_active` instantly.

---

## 3. Frontend Component & UX Architecture

### 3.1 `<AdSlot position="..." />` Component
- Position-aware rendering component loaded on demand.
- Supports both **Image Banners** with sponsor labels and **Custom HTML/AdSense** scripts with sandboxed execution.
- Respects device targeting (`hidden md:block` for desktop only, `md:hidden` for mobile only).
- Includes an optional dismiss (`×`) for `sticky_bottom` sticky drawer banner.
- Zero layout thrashing: if no active ad exists for a slot, renders nothing without residual borders or spacing.

### 3.2 Prime Ad Placements
1. `header_top`: Directly below the main top navigation bar (responsive billboard / leaderboard).
2. `in_feed`: Interspersed between league groups in the match list.
3. `player_top`: Above the video player inside match center.
4. `player_bottom`: Directly underneath the streaming server pills and channel metadata.
5. `sticky_bottom`: Fixed floating bottom bar for high-conversion sponsorship banners.

### 3.3 Overhauled Modern `AdminPanel.jsx` (Cockpit Layout)
- **Top Bar**:
  - Quick metric widgets:
    - ⚽ **مباريات اليوم** (Active Match Count)
    - 🟢 **تغطية البث** (Stream Coverage %)
    - 📢 **الإعلانات النشطة** (Active Ads Count)
  - Tab Switcher:
    - **المباريات والبث المباشر** (Matches & Live Stream Hub)
    - **إدارة الإعلانات والشاشات** (Ads CMS Engine)
    - **حالة المنصة** (System & Cache Overview)
- **Tab 1 — Matches & Stream Hub**:
  - Retains and improves existing match search, live status indicators, stream presets, and manual score overrides.
- **Tab 2 — Ads CMS Engine**:
  - Quick Filter Pills: `الكل`, `أعلى الصفحة`, `بين المباريات`, `أعلى المشغل`, `أسفل المشغل`, `شريط سفلي`.
  - Action: `+ إضافة إعلان جديد`.
  - Ad Cards Grid: Shows preview thumbnail, position badge, device badge, instant toggle switch (`مفعل` / `معطل`), edit, and delete buttons.
  - Modal Drawer: Rich form with position visual selector, type switcher (Image vs HTML), and live preview box.

---

## 4. Verification & Testing Strategy
- **Backend (Pytest)**:
  - Unit tests for `AdminStore` ads CRUD and SQL index integrity.
  - Integration tests for `/api/v1/ads` and `/api/v1/admin/ads/*` endpoints with authentication and validation checks.
- **Frontend (Vitest)**:
  - Unit test for `<AdSlot />` with image banners and empty states.
  - Unit test for `AdminPanel` ads tab switching and form submission.
- **End-to-End Live Check**:
  - Create ad via Admin CMS -> verify presence in public API -> verify rendered HTML on `localhost:5173`.
