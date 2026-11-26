# Design Doc: Kooralive Triad Integration (3-Day Switcher + Multi-Quality Clappr Player + Compact Cards)

**Date:** 2026-11-24  
**Author:** Antigravity Team  
**Status:** Approved & Ready for Planning  
**Target Workspaces:** `football-live-score-platform` & `blogger_theme`

---

## 1. Intent & Context

Following a technical inspection and reverse-engineering of `https://kooralive.la/`, three high-impact features were identified that drive kooralive's high traffic, high session duration, and resilient monetization:
1. **3-Day Navigation Bar (Yesterday, Today, Tomorrow):** Allowing users to instantly review yesterday's results, today's live action, and tomorrow's schedule without reloading the page.
2. **Multi-Bitrate Stream Engine (Clappr + Level Selector):** Seamless manual quality switching (1080p, 720p, 480p, 360p, Auto) for `.m3u8` HLS streams with rapid buffer recovery.
3. **Compact High-Density Match Cards (`AY_Match` style):** A sleek, high-density listing mode with integrated native ads placed directly behind each match card for maximum CTR.

The user explicitly requested implementing **all three features** ("create the 3").

---

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- **G1 (3-Day Switcher in Blogger):** Add interactive `[مباريات الأمس | مباريات اليوم | مباريات الغد]` tabs in the Blogger theme and HTML preview. Toggling days dynamically updates both the match rail and the top Hero showcase with the top match for that day (showing "انتهت" for yesterday, live countdown for today, and upcoming time for tomorrow).
- **G2 (Clappr Multi-Quality Player in Platform):** Upgrade `StreamPlayerContainer.jsx` in the React frontend to integrate Clappr Player with the `LevelSelector` plugin for `.m3u8` streams, offering explicit quality selection (1080p, 720p, 480p, 360p, Auto) alongside the existing iframe fallback.
- **G3 (Compact Match Card Mode):** Implement the `AY_Match` compact design in `blogger_theme` with dedicated sponsor/ad units positioned behind each card, and add a clean compact list view toggle in the React app without spamming ads.
- **G4 (Zero-Regressions):** Maintain 100% pass rates across existing Pytest (133 tests) and Vitest (43 tests) suites.

### Non-Goals
- Hosting raw video streams on the root domain (preserving 3-tier DMCA immunity).
- Adding intrusive malware/scam ads (sticking to clean Adsterra/Monetag banner and Direct Link placements).

### Anti-Goals
- Forcing page reloads when toggling between Yesterday/Today/Tomorrow.
- Breaking responsive mobile layouts.

---

## 3. Builder Check Clarifications & Architectural Decisions

Following the Builder Review check, the following architectural choices were settled:

1. **Data Lifecycle for Blogger 3-Day Switcher:**
   - **Decision:** Hybrid approach. Verified multi-day match datasets for Yesterday, Today, and Tomorrow are compiled directly into the theme by `scripts/build_modern_blogger_theme.py`. At runtime, client-side JS handles instant tab switching with zero network lag, and optionally connects to the live API when available.
2. **Hero Showcase Behavior on Day Switching:**
   - **Decision:** Dynamic Hero. When the user switches to Yesterday, the Hero card displays yesterday's #1 match with final scores (`FINISHED`). When switching to Tomorrow, it displays tomorrow's #1 upcoming fixture (`SCHEDULED`). Switching back to Today restores the live ticking countdown.
3. **Scope of Compact Mode in React App:**
   - **Decision:** In the Blogger theme, the compact card includes the under-card affiliate button (`"سيرفر بديل ⇦"`). In the React platform, the compact mode is implemented as a clean view density toggle (`[عادي | مدمج]`) without injecting ad banners under every single row, maintaining a premium SaaS feel.
4. **React 3-Day Switcher Status:**
   - **Decision:** The React app already has a working `ScheduleFilterTabs` component connected to `/api/v1/matches`. We will align its visual styling to match the new Cyber-Stadium pill aesthetic.

---

## 4. Architectural & Component Details

### 4.1. Feature 1: 3-Day Switcher (Blogger Theme & Preview)
In `blogger_theme/theme_preview.html` and `blogger_theme/kora_pro_blogger_theme.xml`:
- Navigation pill bar:
  ```html
  <div class="day-tabs-nav">
    <button class="day-tab" id="dayTab_yesterday" onclick="switchDayTab('yesterday')">مباريات الأمس</button>
    <button class="day-tab active" id="dayTab_today" onclick="switchDayTab('today')">مباريات اليوم</button>
    <button class="day-tab" id="dayTab_tomorrow" onclick="switchDayTab('tomorrow')">مباريات الغد</button>
  </div>
  ```
- Match datasets:
  - **Yesterday (`yesterday`):**
    - برينتفورد 4 - 0 إيفرتون (انتهت)
    - ليفانتي 1 - 1 إلتشي (انتهت)
    - مونزا 3 - 0 فيورنتينا (انتهت)
    - باشاك شهير 4 - 2 تشوروم (انتهت)
  - **Today (`today`):**
    - أرسنال vs بوروسيا دورتموند (23:00 مكة)
    - مانشستر سيتي vs نابولي (23:00 مكة)
    - ريال مدريد vs PSV أيندهوفن (23:00 مكة)
    - غلطة سراي vs أستون فيلا (20:45 مكة)
  - **Tomorrow (`tomorrow`):**
    - كلوب بروج vs ليفربول (23:00 مكة)
    - إنتر ميلان vs شتوتغارت (23:00 مكة)
    - بايرن ميونخ vs ليل (23:00 مكة)
    - باريس سان جيرمان vs روما (23:00 مكة)

### 4.2. Feature 2: Clappr Multi-Quality Player Engine (Frontend Platform)
In `frontend/src/components/StreamPlayerContainer.jsx`:
- For HLS streams (`server.type === "m3u8"` or `server.type === "clappr"`):
  - Support loading Clappr with `LevelSelectorPlugin` dynamically from CDN (`cdn.jsdelivr.net/npm/@clappr/player@latest` and `cdn.jsdelivr.net/npm/clappr-level-selector-plugin@latest`).
  - Provide resolution picker UI (1080p, 720p, 480p, 360p, تلقائي).
  - Robust fallback to existing native `Hls.js` video player if Clappr CDN is unavailable or disabled.
  - Keep full compatibility with iframe embed servers.

### 4.3. Feature 3: Compact Match Card Mode (`AY_Match` Style)
In `blogger_theme`:
- Add a view mode toggle: `[عرض مدمج | عرض مفصل]`.
- Compact layout specification:
  - Height: ~68px per match item.
  - Grid: Team 1 (Logo + Name) | Center Score / Time Pill | Team 2 (Logo + Name).
  - Bottom strip: Channel & Stadium on right, "سيرفر بديل ⇦" button on left.
  - Responsive down to 320px mobile screens.

---

## 5. Verification & Testing Plan

1. **Blogger Theme & Preview:**
   - Execute `scripts/build_modern_blogger_theme.py`.
   - Validate XML schema with `xml.etree.ElementTree.parse()`.
   - Verify day switching (Yesterday, Today, Tomorrow) and compact view toggle in `theme_preview.html`.
2. **Frontend Test Suite:**
   - Run `npm test` across all 8 Vitest suites.
   - Add/update tests in `StreamPlayerContainer.test.jsx` for quality level switching.
3. **Backend Test Suite:**
   - Run `pytest -q` to confirm all 133 backend endpoints remain green.
