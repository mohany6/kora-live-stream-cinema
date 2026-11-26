# Kooralive Triad Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the 3 core features from kooralive.la: a 3-Day Navigation Switcher (Yesterday/Today/Tomorrow) in the Blogger theme, a Multi-Quality Clappr Player with Level Selector in the live platform, and a Compact Match Card view (`AY_Match` style) with under-card ads.

**Architecture:** 
1. Build-time generator updates compile verified multi-day fixture datasets (Yesterday with finished scores, Today with live countdowns, Tomorrow with scheduled times) into the Blogger theme with vanilla JS instant switching.
2. The React streaming container is enhanced to support Clappr HLS Player with `LevelSelectorPlugin` for manual resolution switching (1080p, 720p, 480p, 360p, Auto) with graceful fallback to `Hls.js`.
3. A view density toggle is integrated into the Blogger theme and preview to toggle between standard cards and compact 68px row cards with dedicated under-card affiliate buttons.

**Tech Stack:** Python 3.12/3.15, React 19, Tailwind CSS, Vite, Vitest, Vanilla JS, Clappr 0.4+, Blogger XML (XHTML).

**Spec:** `docs/superpowers/specs/2026-11-24-kooralive-features-design.md`

## Global Constraints
- Must remain $0 zero-cost without requiring Windows Administrator privileges.
- Must preserve 100% test passing rates across all Pytest (133 tests) and Vitest (43 tests).
- Blogger XML must strictly validate as well-formed XHTML via `xml.etree.ElementTree.parse()`.
- Video streams must never be hosted on the Blogger root domain (preserving 3-tier DMCA shield).

## Review Focus
- **Empty or missing server URL in Clappr:** When a server with `type: "clappr"` or `type: "m3u8"` has an empty or invalid URL, fallback to the next active server or empty state without crashing.
- **Day switching while countdown is ticking:** When the user switches from Today to Yesterday or Tomorrow, the interval timer must pause or recalibrate to avoid displaying negative or invalid time differences.
- **Zero-match bucket handling:** If yesterday or tomorrow has no fixtures in a custom filter, render a clean empty message instead of broken HTML.
- **Mobile responsiveness in Compact View:** Ensure team names, logos, score badges, and ad buttons do not overflow horizontally on 320px screens.
- **Blogger tag escaping in XML:** Ensure `&`, `<`, and `>` inside scripts in Blogger XML are wrapped in `<![CDATA[ ... ]]>` or XML-escaped to avoid XML parse failures.

---

### Task 1: Multi-Day Datasets & Generator Logic in `build_modern_blogger_theme.py`

**Files:**
- Modify: `scripts/build_modern_blogger_theme.py`
- Test: `tests/test_blogger_theme_generator.py`

**Interfaces:**
- Consumes: Verified match records from ESPN API feed.
- Produces: `MULTI_DAY_DATA` dictionary with keys `'yesterday'`, `'today'`, `'tomorrow'`.

- [ ] **Step 1: Write unit test in `tests/test_blogger_theme_generator.py`**
```python
import xml.etree.ElementTree as ET
from pathlib import Path
from scripts.build_modern_blogger_theme import build_preview_html, build_blogger_xml, MULTI_DAY_DATA

def test_multi_day_datasets_present():
    assert "yesterday" in MULTI_DAY_DATA
    assert "today" in MULTI_DAY_DATA
    assert "tomorrow" in MULTI_DAY_DATA
    assert len(MULTI_DAY_DATA["yesterday"]) >= 2
    assert len(MULTI_DAY_DATA["today"]) >= 2
    assert len(MULTI_DAY_DATA["tomorrow"]) >= 2

def test_xml_is_valid_and_contains_day_switcher():
    xml = build_blogger_xml()
    tree = ET.fromstring(xml)
    assert tree.tag == "{http://www.w3.org/1999/xhtml}html"
    assert "dayTab_yesterday" in xml
    assert "dayTab_today" in xml
    assert "dayTab_tomorrow" in xml
```

- [ ] **Step 2: Run test to verify it fails**
Run: `.\.venv\Scripts\python.exe -m pytest tests/test_blogger_theme_generator.py -v`
Expected: FAIL (cannot import `MULTI_DAY_DATA` or missing day switcher)

- [ ] **Step 3: Implement `MULTI_DAY_DATA` and generator logic in `scripts/build_modern_blogger_theme.py`**
Define real match collections:
- `yesterday`: Brentford 4-0 Everton, Levante 1-1 Elche, Monza 3-0 Fiorentina, Basaksehir 4-2 Corum FK (all `status: "FINISHED"`).
- `today`: Arsenal vs Dortmund, Man City vs Napoli, Real Madrid vs PSV, Galatasaray vs Aston Villa.
- `tomorrow`: Club Brugge vs Liverpool, Inter vs Stuttgart, Bayern vs Lille, PSG vs Roma.

- [ ] **Step 4: Run test to verify it passes**
Run: `.\.venv\Scripts\python.exe -m pytest tests/test_blogger_theme_generator.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**
`git add scripts/build_modern_blogger_theme.py tests/test_blogger_theme_generator.py`
`git commit -m "feat(theme): add multi-day fixture datasets to theme generator"`

---

### Task 2: 3-Day Switcher UI & Interactive Tab Switching in Blogger Theme

**Files:**
- Modify: `scripts/build_modern_blogger_theme.py`
- Output: `blogger_theme/theme_preview.html`
- Output: `blogger_theme/kora_pro_blogger_theme.xml`
- Test: `tests/test_blogger_theme_generator.py`

**Interfaces:**
- Consumes: `MULTI_DAY_DATA`
- Produces: JavaScript `switchDayTab(dayKey)` updating `#matchesRailContainer` and `#heroMatchCard`.

- [ ] **Step 1: Write test for day switcher DOM rendering**
```python
def test_day_switcher_script_in_html():
    html = build_preview_html()
    assert "switchDayTab" in html
    assert "activeDayKey" in html
    assert "day-tab active" in html
```

- [ ] **Step 2: Run test to verify failure**
Run: `.\.venv\Scripts\python.exe -m pytest tests/test_blogger_theme_generator.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Day Switcher HTML & JS in `build_modern_blogger_theme.py`**
- Add `.day-tabs-nav` styled with cyber-stadium glassmorphism.
- Implement `switchDayTab(dayKey)` in JS:
  - Toggles active CSS class on the 3 tabs.
  - Updates `#matchesRailContainer` with the corresponding day's match cards.
  - Updates `#heroMatchCard` to showcase that day's #1 match:
    - If `yesterday`: hero score shows final score, status badge shows "انتهت - النتيجة النهائية".
    - If `today`: hero score shows "VS", status badge shows live countdown.
    - If `tomorrow`: hero score shows "VS", status badge shows tomorrow's kickoff time.

- [ ] **Step 4: Recompile and verify test passes**
Run: `.\.venv\Scripts\python.exe scripts/build_modern_blogger_theme.py && .\.venv\Scripts\python.exe -m pytest tests/test_blogger_theme_generator.py -v`
Expected: PASS and valid XML schema.

- [ ] **Step 5: Commit changes**
`git add scripts/build_modern_blogger_theme.py blogger_theme/`
`git commit -m "feat(blogger): implement 3-day switcher with dynamic hero updates"`

---

### Task 3: Compact Match Card Mode (`AY_Match` Style) with Under-Card Ads

**Files:**
- Modify: `scripts/build_modern_blogger_theme.py`
- Output: `blogger_theme/theme_preview.html`
- Output: `blogger_theme/kora_pro_blogger_theme.xml`
- Test: `tests/test_blogger_theme_generator.py`

**Interfaces:**
- Consumes: Match records
- Produces: `renderCompactCard(m, idx)` and view density toggle button.

- [ ] **Step 1: Write test for compact mode elements**
```python
def test_compact_mode_markup_and_style():
    html = build_preview_html()
    assert "ay-match-compact" in html
    assert "toggleViewMode" in html
    assert "ad-card-behind-match" in html
```

- [ ] **Step 2: Run test to verify failure**
Run: `.\.venv\Scripts\python.exe -m pytest tests/test_blogger_theme_generator.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Compact Mode CSS & Toggle Logic**
- CSS for `.ay-match-compact`: ~68px height, 3-column grid (Team 1 | Score/Time Center | Team 2), hover glow.
- Under-card ad bar: `.ad-card-behind-match` with high-contrast `"سيرفر بديل ⇦"` button.
- Toggle button: `[عرض مدمج | عرض مفصل]` in the section title bar.
- JS function `toggleViewMode(mode)` saving preference to `localStorage`.

- [ ] **Step 4: Recompile and run tests**
Run: `.\.venv\Scripts\python.exe scripts/build_modern_blogger_theme.py && .\.venv\Scripts\python.exe -m pytest tests/test_blogger_theme_generator.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**
`git add scripts/build_modern_blogger_theme.py blogger_theme/`
`git commit -m "feat(theme): add compact card mode with under-card ads and view toggle"`

---

### Task 4: Clappr Multi-Quality Stream Player in Live Platform

**Files:**
- Modify: `frontend/src/components/StreamPlayerContainer.jsx`
- Test: `frontend/src/components/__tests__/StreamPlayerContainer.test.jsx`

**Interfaces:**
- Consumes: `servers` array with `type: "m3u8"` or `type: "clappr"`.
- Produces: Resolution level selector UI and player container.

- [ ] **Step 1: Write tests in `StreamPlayerContainer.test.jsx` for quality level handling**
```javascript
it("renders quality selector options when playing an hls stream", () => {
  const servers = [
    { id: "s1", server_name: "سيرفر 1 - متعدد الجودات", url: "https://example.com/live.m3u8", type: "m3u8" }
  ];
  render(<StreamPlayerContainer servers={servers} channel="beIN 1" />);
  expect(screen.getByTestId("quality-selector")).toBeInTheDocument();
  expect(screen.getByText(/تلقائي|Auto/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run vitest to verify test fails**
Run: `cmd /c "set PATH=C:\Users\Mohany\Desktop\football-live-score-platform\.tools\node-v22.14.0-win-x64;%PATH% && cd /d C:\Users\Mohany\Desktop\football-live-score-platform\frontend && npm test -- src/components/__tests__/StreamPlayerContainer.test.jsx"`
Expected: FAIL (missing `quality-selector`)

- [ ] **Step 3: Implement Clappr quality level selector in `StreamPlayerContainer.jsx`**
- Add quality level selector buttons: `['Auto', '1080p', '720p', '480p', '360p']`.
- When `Hls.isSupported()`:
  - Listen for `Hls.Events.MANIFEST_PARSED` and expose quality levels if multi-bitrate manifest.
  - Set `hls.currentLevel` on level click.
- Add `data-testid="quality-selector"` pill bar above/below video player.
- Ensure fallback to iframe servers remains intact.

- [ ] **Step 4: Run vitest to verify test passes**
Run: `cmd /c "set PATH=C:\Users\Mohany\Desktop\football-live-score-platform\.tools\node-v22.14.0-win-x64;%PATH% && cd /d C:\Users\Mohany\Desktop\football-live-score-platform\frontend && npm test"`
Expected: PASS (all 8 test suites pass).

- [ ] **Step 5: Commit changes**
`git add frontend/src/components/StreamPlayerContainer.jsx frontend/src/components/__tests__/StreamPlayerContainer.test.jsx`
`git commit -m "feat(player): add multi-quality level selector for live hls streams"`

---

### Task 5: Full Regression Testing & Theme Rebuild

**Files:**
- Verify: `blogger_theme/theme_preview.html`
- Verify: `blogger_theme/kora_pro_blogger_theme.xml`
- Verify: `frontend/dist/`
- Verify: `publish_today_trend.bat`

- [ ] **Step 1: Run full Python backend tests**
Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: 134+ PASS (all passing).

- [ ] **Step 2: Run full Frontend Vitest suite**
Run: `cmd /c "set PATH=C:\Users\Mohany\Desktop\football-live-score-platform\.tools\node-v22.14.0-win-x64;%PATH% && cd /d C:\Users\Mohany\Desktop\football-live-score-platform\frontend && npm test"`
Expected: 44+ PASS (all 8 suites passing).

- [ ] **Step 3: Rebuild frontend production bundle**
Run: `cmd /c "set PATH=C:\Users\Mohany\Desktop\football-live-score-platform\.tools\node-v22.14.0-win-x64;%PATH% && cd /d C:\Users\Mohany\Desktop\football-live-score-platform\frontend && npm run build"`
Expected: Build successfully created in `frontend/dist/`.

- [ ] **Step 4: Test `publish_today_trend.bat` execution**
Run: `cmd /c "cd /d C:\Users\Mohany\Desktop\football-live-score-platform && publish_today_trend.bat"`
Expected: Clean execution, 0 errors.

- [ ] **Step 5: Commit and wrap up**
`git add -A`
`git commit -m "chore(release): complete kooralive triad integration across platform and theme"`
