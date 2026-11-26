# Design: Blogger Schedule Hub & Cloudflare Dedicated Match Video Pages

**Date:** 2026-11-24  
**Status:** Approved for Implementation  
**Author:** Antigravity (Google DeepMind) & User  

---

## 1. Intent & The Why

### Background & Context
The platform consists of:
1. A FastAPI backend + React Vite frontend served via Cloudflare Tunnel (`https://channels-heavy-gently-prevent.trycloudflare.com`).
2. A Blogger site (`https://kora-live-to.blogspot.com`) serving as an SEO-friendly landing hub.

### The Goal
The user desires an architectural separation matching high-traffic sports portals like `kooralive.la`:
- **Blogger Hub (`kora-live-to.blogspot.com`):** Serves as the primary public schedule and fixture hub. It replicates the exact modern cyber-dark design shown in the platform screenshot (sponsor billboard banner, timezone switcher, 3-day tabs, league headers, match cards with countdowns and channel info). Direct embedded stream iframes are excluded from Blogger to protect its domain authority from DMCA issues.
- **Cloudflare Match Video Platform (`*.trycloudflare.com`):** Serves as the dedicated match video player destination with clean, path-based URLs (`/match/{match_id}`).
- **User Journey:**
  1. Visitors arrive at Blogger via Google Search / social media to check today's match schedules.
  2. Clicking any match card on Blogger navigates directly to the dedicated match video page on Cloudflare (`https://channels-heavy-gently-prevent.trycloudflare.com/match/{match_id}`).
  3. On the video page, visitors get multi-server HLS/Clappr streaming (1080p, 720p, 480p, 360p, Auto), live tactical lineups with Latin names, comparative H2H statistics, and timeline events.
  4. Both Blogger and Cloudflare pages feature comprehensive ad monetization containers (top billboard, mid-content/player bottom, sticky bottom floating banner, and alternative server ad triggers).

---

## 2. Goals, Non-Goals & Anti-Goals

### Goals
- **Design Parity on Blogger:** The Blogger theme must mirror the sleek React UI layout:
  - Header with branding, timezone dropdown, and night/day switch.
  - Official Sponsor billboard banner.
  - 3-day switcher tabs (الأمس / اليوم / الغد).
  - Matches grouped by league with team crests, countdowns, channel tags, and direct stream links.
- **Path-Based Video Player Pages (`/match/{match_id}`):**
  - Entering `/match/{id}` loads the React app and automatically focuses `MatchDetailHybrid`.
  - Full-screen match intel, multi-server player with quality selector, lineups, and stats.
  - "العودة لجدول المباريات" button linking back to the Blogger hub.
- **Comprehensive Ad Monetization across All Pages:**
  - Blogger Hub: Top Leaderboard, In-feed banner between leagues, Sticky bottom banner.
  - Cloudflare Video Page: Header banner, Player bottom banner, Sticky bottom banner, and Server switch ad triggers.
- **Maintain Reliability & $0 Cost:** Zero paid subscriptions, full compatibility with Cloudflare tunnel and Blogger free hosting. 100% passing test suites (Pytest + Vitest).

### Non-Goals
- Hosting actual `.ts` or `.m3u8` video segments on the local server (streams are relayed via external HLS/Clappr links).
- Replacing Blogger's hosting infrastructure with custom VPS.

### Anti-Goals
- Never embed direct video stream iframes into Blogger post bodies (would risk Blogger account suspension).
- Never break existing offline or cached fixture display when the backend tunnel is restarting.

---

## 3. Constraints & Technical Decisions (Builder Calls)

1. **Cloudflare Tunnel URL Handling:**
   - `scripts/build_modern_blogger_theme.py` dynamically embeds the active tunnel URL from `data/tunnel_url.txt` into the theme.
   - Client-side JS caches the base URL in `localStorage` with a fallback mechanism, ensuring seamless zero-config updates whenever `apply_blogger_theme.bat` is executed.
2. **Blogger Theme Conditional Layout:**
   - Homepage (`<b:if cond='data:view.isHomepage'>`): Renders the full dynamic cyber-stadium schedule hub with sponsor banners, day tabs, and league match cards.
   - Post Pages (`<b:if cond='data:view.isPost'>`): Renders the SEO article text, structured JSON-LD schema, and a prominent "شاهد البث المباشر الآن 📺" CTA button pointing to `/match/{match_id}`.
3. **Fixture Fallback Strategy:**
   - Double redundancy: Initial match cards for today are statically inlined into the XML at build time by querying SQLite. Client-side JS fetches live updates from `{platform_url}/api/matches/today` and caches the payload in `localStorage`. If the tunnel is temporarily restarting, visitors see the baked/cached fixtures.
4. **Server Ad Trigger:**
   - Implemented as a lightweight, non-intrusive frontend trigger in `StreamPlayerContainer.jsx` / `MatchDetailHybrid.jsx` with a 1-per-session cap (`sessionStorage`), triggering an optional affiliate/sponsor link when switching servers.

---

## 4. Architectural Approaches

### Approach 1: Hash-Based Client Routing (`/#match-{id}`)
- React app listens to URL hash fragments (`window.location.hash`).
- **Trade-off:** Fast to implement, but non-standard URLs (`/#match-123`).

### Approach 2: Path-Based Dedicated Route (`/match/{id}`) — **SELECTED**
- Professional, RESTful URLs: `https://channels-heavy-gently-prevent.trycloudflare.com/match/{id}`.
- FastAPI's SPA fallback catch-all `/{full_path:path}` serves `index.html` for any `/match/{id}` request.
- React `App.jsx` parses `window.location.pathname` on mount and on `popstate`:
  - If matching `/match/([a-zA-Z0-9_-]+)`, extracts `match_id`, immediately sets `selectedId = match_id`, and fetches match details.
  - Replaces or updates browser history via `window.history.pushState(null, "", "/match/" + id)` when clicking matches in the internal view.
  - Provides a clean "العودة إلى جدول المباريات" button leading back to Blogger.

---

## 5. Technical Implementation Details

### 5.1 React Client URL Routing & Navigation (`frontend/src/App.jsx`)
1. **Path Parser:**
   ```javascript
   function getMatchIdFromPath() {
     if (typeof window === "undefined") return null;
     const match = window.location.pathname.match(/^\/match\/([a-zA-Z0-9_-]+)/);
     return match ? match[1] : null;
   }
   ```
2. **Mount & History Listener:**
   - Initialize `selectedId` with `getMatchIdFromPath()`.
   - On `popstate`, re-check path; if navigating back to `/`, close match detail.
3. **Card Selection & Back Button:**
   - Selecting a match updates URL to `/match/{id}` using `pushState`.
   - "العودة إلى جدول المباريات" in `MatchDetailHybrid.jsx`:
     - Checks document referrer or default: links back to `https://kora-live-to.blogspot.com`.

### 5.2 Ad Placements on Cloudflare Match Video Page
- `MatchDetailHybrid.jsx` integrates:
  - `<AdSlot position="player_top" />`
  - `<AdSlot position="player_bottom" />`
  - `<AdSlot position="sticky_bottom" />` at viewport bottom with close button.
  - Server selection tab triggers with session frequency cap.

### 5.3 Blogger Modern Theme Overhaul (`scripts/build_modern_blogger_theme.py`)
Update theme template to replicate the React cyber-dark interface:
1. **Header & Brand Bar:**
   - Logo, Title: "كورة لايف - نتائج مباشرة • بث متعدد السيرفرات • تحليل تكتيكي"
   - Timezone selector dropdown ("مكة المكرمة GMT+3", "القاهرة GMT+2", etc.)
   - Theme toggle button.
2. **Official Sponsor Billboard Banner:**
   - Dedicated high-CTR ad container with "إعلان" badge.
3. **3-Day Switcher Tabs:**
   - Tabs: `مباريات الأمس` | `مباريات اليوم` | `مباريات الغد`
   - Active match counter badge (e.g. `9 مباريات`).
4. **League Headers & Match Cards:**
   - Grouping by competition (e.g. `دوري أبطال أوروبا`, `الدوري الإنجليزي الممتاز`).
   - Card layout identical to screenshot:
     - Right: Home Team (Logo + Name)
     - Center: Local Kickoff Time + Countdown ("تبدأ بعد: hh:mm:ss") + Channel ("beIN SPORTS 1 HD") + Status note.
     - Left: Away Team (Logo + Name)
     - Primary Action: Direct link to `{platform_url}/match/{match.id}`.
5. **Blogger Ad Slots:**
   - `ad-slot-header`: Top leaderboard banner (728x90 / responsive).
   - `ad-slot-infeed`: Mid-content banner between league groups (300x250 / responsive).
   - `ad-slot-sticky`: Bottom floating banner (320x50 / responsive) with dismiss button.
6. **Dynamic Sync Engine:**
   - Client-side script fetches `{platform_url}/api/matches/today?tz={selectedTz}` and dynamically hydrates the match cards.

### 5.4 Backend Verification & Routing (`src/live_score/api/app.py`)
- Verified: `/{full_path:path}` serves `frontend/dist/index.html` for any `/match/{match_id}` request.
- Verified: `/api/match/{match_id}` returns complete match details (scores, commentary, tactical lineups, TV channels).

---

## 6. Verification & Success Criteria
1. **Vitest (Frontend):**
   - Unit tests verifying path parsing `/match/{id}` triggers match detail loading.
   - Test verifying "العودة إلى جدول المباريات" resets path.
2. **Pytest (Backend):**
   - Test verifying `GET /match/{match_id}` returns status 200 and serves HTML.
   - All 137 backend tests remain green.
3. **Blogger XML Compilation:**
   - `scripts/build_modern_blogger_theme.py` builds `kora_pro_blogger_theme.xml` cleanly.
   - `xml.etree.ElementTree.parse()` confirms valid XML syntax.
4. **Live Verification:**
   - Navigating to `https://channels-heavy-gently-prevent.trycloudflare.com/match/401915378` directly opens the video player page with intel and ad containers.
   - Clicking a match card on Blogger links directly to that URL.
