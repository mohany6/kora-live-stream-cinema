# Task 3 Brief: Refactor React Frontend to Pure Stream Cinema SPA

**Working Directory:** `C:\Users\Mohany\Desktop\football-live-score-platform\frontend`
**Node Path:** `C:\Users\Mohany\Desktop\football-live-score-platform\.tools\node-v22.14.0-win-x64\node.exe`
**NPM:** Add `C:\Users\Mohany\Desktop\football-live-score-platform\.tools\node-v22.14.0-win-x64;` to `PATH`.

## Goal
Transform the React SPA on Cloudflare Pages into a high-performance, distraction-free "Match Stream Cinema" that loads match and stream data directly from static `/data/matches.json` (no live FastAPI server needed), removes obsolete admin panels, and provides persistent loop-back links to the Blogger main hub.

## Files to Modify/Create
- `frontend/src/lib/api.js`
- `frontend/src/App.jsx`
- `frontend/src/components/StreamPlayerContainer.jsx`
- `frontend/src/components/MatchDetailHybrid.jsx`
- `frontend/src/AppStreamCinema.test.jsx`

## Detailed Requirements
1. **`frontend/src/lib/api.js`**:
   - Update `fetchTodayMatches({ date, tz, signal })`:
     - Fetch `/data/matches.json` statically.
     - Fallback to `/api/v1/matches/today` if `/data/matches.json` is unavailable or returns 404.
   - Update `fetchMatchDetail(matchId, { tz, signal })`:
     - First attempt to load `/data/matches.json` and find match by `match.id == matchId`.
     - If the match in `matches.json` contains `servers`, construct detail payload directly from it:
       `{ match: m, servers: m.servers || [], home_lineup: m.home_lineup || [], away_lineup: m.away_lineup || [], home_formation: m.home_formation || "—", away_formation: m.away_formation || "—", events: m.events || [], stats: m.stats || [], standings: m.standings || [] }`
     - Fallback to `/api/v1/match/{matchId}` if not found in static JSON.
2. **`frontend/src/App.jsx`**:
   - Remove `AdminPanel` import, state (`showAdmin`), and the `لوحة التحكم` toggle button.
   - Keep status filter chips (الكل, مباشر الآن, لم تبدأ, انتهت).
   - Ensure the Header has the glowing Blogger Hub button: `🌐 الموقع الرئيسي (بلوجر) ↗` linking to `https://kora-live-to.blogspot.com`.
   - Ensure the Footer has the prominent Blogger Hub link.
3. **`frontend/src/components/StreamPlayerContainer.jsx` & `MatchDetailHybrid.jsx`**:
   - Ensure the VIP 4K Server button (`⚡ سيرفر VIP (4K بدون تقطيع)`) is present in the server switcher list with `data-testid="server-vip-link"` linking to `https://budgetezy.org/4/ae626546295ba9dbdec2ea24a521084c`.
   - Ensure `MatchDetailHybrid` has the back button and toolbar link to `https://kora-live-to.blogspot.com`.
4. **`frontend/src/AppStreamCinema.test.jsx`**:
   - Write unit tests verifying:
     - Matches load cleanly from `/data/matches.json`.
     - `admin-panel-toggle` is NOT rendered.
     - `blogger-hub-link` is present and targets `https://kora-live-to.blogspot.com`.
     - `server-vip-link` is present and targets `https://budgetezy.org/4/ae626546295ba9dbdec2ea24a521084c`.
5. **Verification**:
   - Run Vitest: `npm run test` (Must PASS 100%).
   - Run Vite Build: `npm run build` (Must PASS with clean `frontend/dist`).
