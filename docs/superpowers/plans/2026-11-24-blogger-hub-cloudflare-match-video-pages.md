# Blogger Schedule Hub & Cloudflare Dedicated Match Video Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the Blogger site (`kora-live-to.blogspot.com`) into the exact cyber-dark match schedule hub from the React screenshot, and configure the Cloudflare tunnel platform (`*.trycloudflare.com`) as a dedicated video player destination where every match has its own direct `/match/{id}` URL with full intel, multi-server streaming, and ad monetization across all pages.

**Architecture:** 
1. **Frontend Routing (`frontend/src/App.jsx`):** Parse `/match/{id}` directly from `window.location.pathname` on mount and `popstate`, rendering `MatchDetailHybrid` in full focus with multi-server HLS streaming, tactical pitch, comparative stats, and ad containers.
2. **Video Player Monetization & Navigation (`MatchDetailHybrid.jsx`):** Add sticky bottom ad banner, server-switch ad triggers, and a dual return button (back to schedule or back to Blogger).
3. **Blogger Theme Generator (`scripts/build_modern_blogger_theme.py`):** Replicate the platform screenshot in Blogger XML (sponsor banner, timezone picker, yesterday/today/tomorrow tabs, league headers, match cards with countdowns) linking directly to `{platform_url}/match/{id}`.

**Tech Stack:** React 18, Vite, Tailwind CSS, FastAPI, Python 3.12, Blogger XML / Blogger v3 Widget syntax, Clappr / HLS.js.

**Spec:** `C:\Users\Mohany\Desktop\football-live-score-platform\docs\superpowers\specs\2026-11-24-blogger-hub-cloudflare-match-video-pages-design.md`

## Global Constraints
- Zero dollar budget ($0): No paid external services, hosting, or APIs.
- Non-admin Windows execution.
- Maintain RTL Arabic typography (`Cairo`, `Chakra Petch`).
- Preserve 3-tier DMCA shield: Zero direct stream iframes on Blogger root domain.
- All pages on both Blogger and Cloudflare must support ad monetization placements (header, player bottom, sticky bottom, in-feed).
- Existing test suites must remain 100% green (137 Pytest, 45+ Vitest).

## Review Focus
1. Direct navigation or browser refresh on `/match/401915378` must load the video player page without 404 error.
2. Clicking "العودة إلى جدول المباريات" on Cloudflare must navigate back to `/` and update the browser URL without full-page reload, or link to Blogger if referrer indicates.
3. Offline / tunnel restart fallback on Blogger: When `fetch` fails, match cards must gracefully display baked static data or `localStorage` cache instead of blanking out.
4. Sticky bottom ads on both platforms must have working dismiss buttons that do not re-open during the same session.
5. All match card links generated in Blogger must point to valid `/match/{id}` URLs on the active Cloudflare tunnel domain.

---

### Task 1: React Path-Based Routing for Match Video Player (`/match/:id`)

**Files:**
- Modify: `frontend/src/App.jsx:45-120`
- Modify: `frontend/src/App.jsx:340-420`
- Test: `frontend/src/MatchRouting.test.jsx`

**Interfaces:**
- Consumes: `window.location.pathname`, `fetchMatchDetail(matchId, { tz })`
- Produces: `getMatchIdFromPath()`, path-aware `selectedId` state, and history synchronization via `pushState`

- [ ] **Step 1: Write the failing test for path parsing and match loading**

Create `frontend/src/MatchRouting.test.jsx`:
```javascript
import { describe, expect, it, vi } from "vitest";
import { getMatchIdFromPath } from "./App";

describe("getMatchIdFromPath", () => {
  it("extracts match ID from standard /match/123 path", () => {
    expect(getMatchIdFromPath("/match/401915378")).toBe("401915378");
  });

  it("extracts match ID with trailing slash", () => {
    expect(getMatchIdFromPath("/match/barca-vs-sabah/")).toBe("barca-vs-sabah");
  });

  it("returns null for root or unrelated paths", () => {
    expect(getMatchIdFromPath("/")).toBeNull();
    expect(getMatchIdFromPath("/admin")).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test frontend/src/MatchRouting.test.jsx`  
Expected: FAIL with `getMatchIdFromPath is not exported from ./App`.

- [ ] **Step 3: Implement `getMatchIdFromPath` and location listeners in `frontend/src/App.jsx`**

1. Export `getMatchIdFromPath(pathname = typeof window !== "undefined" ? window.location.pathname : "")`:
   ```javascript
   export function getMatchIdFromPath(pathname = typeof window !== "undefined" ? window.location.pathname : "") {
     if (!pathname) return null;
     const match = pathname.match(/^\/match\/([a-zA-Z0-9_-]+)/);
     return match ? match[1] : null;
   }
   ```
2. In `App()`, initialize `selectedId` with:
   ```javascript
   const [selectedId, setSelectedId] = useState(() => getMatchIdFromPath());
   ```
3. In `handleLocationChange()` inside `useEffect`, add:
   ```javascript
   const matchId = getMatchIdFromPath(p);
   if (matchId) {
     setSelectedId(matchId);
     setShowAdmin(false);
   } else if (p === "/" && !isAdmin) {
     setSelectedId(null);
     setDetail(null);
   }
   ```
4. When selecting a match card (`handleSelectMatch`), push state:
   ```javascript
   if (typeof window !== "undefined" && window.history?.pushState) {
     window.history.pushState(null, "", `/match/${match.id}`);
   }
   setSelectedId(match.id);
   ```
5. In `closeDetail()`, update history to `/`:
   ```javascript
   if (typeof window !== "undefined" && window.history?.pushState && window.location.pathname.startsWith("/match/")) {
     window.history.pushState(null, "", "/");
   }
   setSelectedId(null);
   setDetail(null);
   setDetailError(null);
   ```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test frontend/src/MatchRouting.test.jsx`  
Expected: PASS (all 3 tests pass).

- [ ] **Step 5: Run full frontend test suite**

Run: `npm --prefix frontend test`  
Expected: All tests pass.

---

### Task 2: Video Player Page Monetization & Enhanced Match Intel Navigation

**Files:**
- Modify: `frontend/src/components/MatchDetailHybrid.jsx:270-320`
- Test: `frontend/src/components/MatchDetailHybrid.test.jsx`

**Interfaces:**
- Consumes: `<AdSlot position="sticky_bottom" />`, `StreamPlayerContainer`, `onBack`
- Produces: Sticky bottom ad slot in match detail, dual "العودة" navigation link (Blogger or local).

- [ ] **Step 1: Write the failing test for sticky bottom ad in MatchDetailHybrid**

Update `frontend/src/components/MatchDetailHybrid.test.jsx`:
```javascript
it("renders sticky bottom ad slot within match detail", () => {
  render(<MatchDetailHybrid detail={mockDetail} onBack={() => {}} />);
  expect(screen.getByTestId("ad-slot-sticky_bottom")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test frontend/src/components/MatchDetailHybrid.test.jsx`  
Expected: FAIL (`Unable to find element with data-testid="ad-slot-sticky_bottom"`).

- [ ] **Step 3: Update `MatchDetailHybrid.jsx` with sticky bottom ad and Blogger return button**

1. In `MatchDetailHybrid.jsx`:
   Add `<AdSlot position="sticky_bottom" />` at the bottom of the container.
2. In the back button area in `MatchDetailHybrid.jsx`:
   Add a direct Blogger link pill if referrer or default is set:
   ```jsx
   <div className="flex items-center gap-2">
     <button
       type="button"
       onClick={onBack}
       className="flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-white transition hover:bg-white/20"
     >
       ← العودة إلى جدول المباريات
     </button>
     <a
       href="https://kora-live-to.blogspot.com"
       target="_blank"
       rel="noopener noreferrer"
       className="hidden sm:inline-flex items-center gap-1 text-[11px] font-bold text-slate-400 hover:text-emerald-400 transition"
     >
       مدونة كورة لايف ↗
     </a>
   </div>
   ```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test frontend/src/components/MatchDetailHybrid.test.jsx`  
Expected: PASS.

- [ ] **Step 5: Rebuild frontend production assets**

Run: `npm --prefix frontend run build`  
Expected: `vite build` completes with 0 errors, output in `frontend/dist/`.

---

### Task 3: Modern Cyber-Dark Blogger Theme Overhaul

**Files:**
- Modify: `scripts/build_modern_blogger_theme.py`
- Test: `scripts/test_blogger_theme_xml.py` (or pytest check)

**Interfaces:**
- Consumes: `data/tunnel_url.txt`, `src/live_score/domain/models.py`, `src/live_score/infra/store.py`
- Produces: `blogger_theme/theme_preview.html`, `blogger_theme/kora_pro_blogger_theme.xml`

- [ ] **Step 1: Write test verifying theme compilation and match link structure**

Create `tests/test_blogger_theme_build.py`:
```python
import xml.etree.ElementTree as ET
from pathlib import Path
from scripts.build_modern_blogger_theme import generate_theme_preview, generate_blogger_xml, get_platform_url

def test_blogger_theme_valid_xml():
    xml_path = generate_blogger_xml()
    assert xml_path.exists()
    tree = ET.parse(xml_path)
    root = tree.getroot()
    assert "html" in root.tag.lower()

def test_blogger_match_links_use_path_route():
    xml_path = generate_blogger_xml()
    content = xml_path.read_text(encoding="utf-8")
    platform_url = get_platform_url()
    assert f"{platform_url}/match/" in content or "/match/" in content
    assert "ad-slot-header" in content or "Official Sponsor" in content
    assert "ad-slot-sticky" in content or "sticky-banner" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\pytest.exe tests/test_blogger_theme_build.py -v`  
Expected: FAIL (links currently point to `/` or `#match-` instead of `/match/{id}`).

- [ ] **Step 3: Update `scripts/build_modern_blogger_theme.py`**

1. Replicate the React screenshot layout:
   - Header with cyber badge "كورة لايف - نتائج مباشرة • بث متعدد السيرفرات • تحليل تكتيكي" + timezone select.
   - Sponsor Billboard Banner with "إعلان" badge (`Kora Live - Official Sponsor Banner`).
   - 3-day switcher tabs (`مباريات الأمس` | `مباريات اليوم` | `مباريات الغد`) with count pill.
   - League headers: `دوري أبطال أوروبا`, etc.
   - Match cards matching screenshot:
     - Right: Home team logo & name
     - Center: Local time (`20:45`), countdown (`تبدأ بعد: 19:26:45`), channel (`beIN SPORTS 1 HD`), note (`سيتم تحديث روابط البث قبل انطلاق المباراة`).
     - Left: Away team logo & name
     - Action button & card link: `href="{platform_url}/match/{match.id}"` target `_blank`.
2. Add 3 ad slot containers:
   - Top Leaderboard (728x90)
   - Mid-feed ad slot between league groups (300x250)
   - Sticky bottom floating ad banner with dismiss button.
3. Update conditional rendering:
   - `<b:if cond='data:view.isHomepage'>`: Render full schedule hub.
   - `<b:if cond='data:view.isPost'>`: Render post content with top CTA button.
4. Client-side JS fetches `{platform_url}/api/matches/today?tz={tz}` with fallback to baked cards and `localStorage`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\pytest.exe tests/test_blogger_theme_build.py -v`  
Expected: PASS.

---

### Task 4: Automated Theme Application and End-to-End Verification

**Files:**
- Modify: `apply_blogger_theme.bat`
- Verify: Live Cloudflare tunnel endpoint and Blogger theme copy

- [ ] **Step 1: Run theme generator and copy to clipboard**

Run: `.\.venv\Scripts\python.exe scripts/build_modern_blogger_theme.py`  
Expected: Successfully generates `theme_preview.html` and `kora_pro_blogger_theme.xml`.

- [ ] **Step 2: Run all backend tests (Pytest)**

Run: `.\.venv\Scripts\pytest.exe -v`  
Expected: All 137+ tests pass.

- [ ] **Step 3: Run all frontend tests (Vitest)**

Run: `npm --prefix frontend test`  
Expected: All 45+ tests pass.

- [ ] **Step 4: Verify live `/match/{id}` route via curl/requests**

Run: `.\.venv\Scripts\python.exe -c "import urllib.request; res = urllib.request.urlopen('http://127.0.0.1:8000/match/401915378'); print(res.status)"`  
Expected: 200 OK.

- [ ] **Step 5: Run `apply_blogger_theme.bat` to copy theme to clipboard**

Run: `.\apply_blogger_theme.bat`  
Expected: Copies XML to Windows clipboard and opens Blogger Theme Edit page in browser.
