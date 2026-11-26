# Design Doc: AlbaPlayer Live Stream Integration via Dynamic Channel Mapping

**Date:** 2026-11-25  
**Author:** Antigravity Team  
**Status:** Pending Approval  
**Target Workspaces:** `football-live-score-platform` (`src/live_score`, `frontend`)

---

## 1. Intent & Context

The platform has a high-conversion Blogger schedule hub (`kora-live-to.blogspot.com`) and an interactive React Match Center (`/match/{id}`).
Following our technical reconnaissance of `https://kooralive.la/`, we analyzed how modern sports streaming portals deliver multi-server live broadcasts without manual stream URL entry for every match:
- Streaming hubs do not bind streams directly to individual match IDs; instead, they route video feeds by **Channel Slugs** (e.g. `bein-sports-hd-1`, `bein-sports-xtra-1`) embedded via the **AlbaPlayer** engine (`https://24.shootinggames1.com/albaplayer/{slug}/?serv={n}`).
- The user explicitly requested:
  1. Linking matches to AlbaPlayer streams.
  2. Directing visitors from match cards on Blogger and the platform into the **interactive Match Center** (`/match/{id}`) where they watch the live broadcast inside `StreamPlayerContainer.jsx` alongside the tactical pitch view, live statistics, lineups, and match timeline.
  3. Restricting stream activation strictly to **30 minutes prior to kickoff until match completion**, preventing premature broadcasts on future fixtures.

---

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- **G1 (Channel-to-AlbaPlayer Mapper):** Implement a robust `ChannelStreamMapper` in `src/live_score/domain/resolver.py` that maps official Arabic and English TV channel names to verified AlbaPlayer channel slugs (`bein-sports-hd-1` .. `bein-sports-hd-9`, `bein-sports-xtra-1` .. `bein-sports-xtra-2`) and generates multi-server embed URLs (`serv=0`, `serv=1`).
- **G2 (Lifecycle-Gated Stream Hydration):** Integrate `ChannelStreamMapper` into `PriorityResolver.resolve()` such that AlbaPlayer streams are hydrated on-the-fly **only** when a match has a valid mapped channel AND is either currently live (`is_live`) or within 30 minutes of kickoff (`now >= kickoff_time - timedelta(minutes=30)` and not `FINISHED`).
- **G3 (Admin Override Preservation):** Retain strict priority rules where Admin overrides always take 100% precedence over automated AlbaPlayer streams at any time.
- **G4 (Player Iframe Compatibility):** Ensure `StreamPlayerContainer.jsx` in the React frontend safely renders AlbaPlayer iframes with `referrerPolicy="no-referrer"` and `sandbox="allow-forms allow-same-origin allow-scripts"` to prevent upstream CDN referer blocking.
- **G5 (Comprehensive Testing):** Maintain 100% pass rate on all Pytest (139/139) and Vitest (50/50) suites, adding dedicated unit tests for channel resolution, timing gates, and embed generation.

### Non-Goals
- Hosting raw `.ts` or `.m3u8` video chunks directly on our Cloudflare tunnel / origin server (retaining 3-tier DMCA immunity).
- Mutating stored disk snapshots (`snapshot.json`) with third-party player URLs.
- Bypassing the Match Center or sending visitors directly to external spam domains.

### Anti-Goals
- Displaying active live stream player for matches scheduled days in advance.
- Hardcoding static match IDs to streams in source code.
- Breaking existing direct HLS `.m3u8` streams or Clappr player support.

---

## 3. Approaches Considered & Trade-offs

1. **Approach 1: Dynamic Channel-to-AlbaPlayer Resolver in Backend (Selected & Approved)**
   - *Description:* Backend inspects the match's channel property (e.g. `beIN SPORTS 1 HD`), normalizes the alias, and generates multi-server `StreamServer` objects on-the-fly during resolution.
   - *Trade-offs:* Automatic, zero manual intervention, fully testable with Python unit tests, respects Admin overrides and lifecycle gates.
2. **Approach 2: Client-Side Fallback Mapper in React Frontend**
   - *Description:* `StreamPlayerContainer.jsx` generates AlbaPlayer iframes on-the-fly when `servers` array is empty.
   - *Trade-offs:* Leaks domain logic into UI layer, makes API responses inconsistent with UI state, harder to test centrally.
3. **Approach 3: Real-Time Web Scraper Ingestion**
   - *Description:* Continuously scrape external schedule portals to discover live player links.
   - *Trade-offs:* Fragile, introduces network latency and potential downtime if third-party HTML structures shift.

---

## 4. Architectural & Component Details

### 4.1. Channel Slug Mapping Dictionary (`ChannelStreamMapper`)
Located in `src/live_score/domain/resolver.py`:
Standardizes channel variations against verified upstream slugs:
- **beIN SPORTS HD 1–9 (Verified live HTTP 200 schema):**
  - `beIN SPORTS 1 HD`, `beIN Sports 1`, `بي ان سبورت 1`, `بي ان 1` -> `bein-sports-hd-1`
  - `beIN SPORTS 2 HD` .. `beIN SPORTS 9 HD` -> `bein-sports-hd-2` .. `bein-sports-hd-9`
- **beIN SPORTS XTRA:**
  - `beIN SPORTS XTRA 1`, `beIN Xtra 1`, `اكسترا 1` -> `bein-sports-xtra-1`
  - `beIN SPORTS XTRA 2`, `beIN Xtra 2`, `اكسترا 2` -> `bein-sports-xtra-2`
- **beIN SPORTS English & News:**
  - `beIN SPORTS English 1` -> `bein-sports-english-1`
  - `beIN SPORTS News`, `الإخبارية` -> `bein-sports-news`
- **Fallback for Unverified Channels (SSC, Alkass, AD Sports):**
  - If a channel has no verified active AlbaPlayer slug, return an empty list (`[]`). This preserves the clean, helpful fallback message in the UI ("لا توجد سيرفرات متاحة حالياً - سيتم تحديث روابط البث قبل انطلاق المباراة") rather than rendering an HTTP 404 iframe.

### 4.2. Embed URL & Server Generation
For any resolved slug `{slug}`, two fallback servers are constructed:
```python
StreamServer(
    id=f"alba_{slug}_0",
    server_name="سيرفر 1 - AlbaPlayer (أساسي)",
    url=f"https://24.shootinggames1.com/albaplayer/{slug}/?serv=0",
    type="iframe",
    is_active=True,
    quality="multi",
    sandbox="allow-forms allow-same-origin allow-scripts",
)
StreamServer(
    id=f"alba_{slug}_1",
    server_name="سيرفر 2 - AlbaPlayer (احتياطي)",
    url=f"https://24.shootinggames1.com/albaplayer/{slug}/?serv=1",
    type="iframe",
    is_active=True,
    quality="multi",
    sandbox="allow-forms allow-same-origin allow-scripts",
)
```

### 4.3. Lifecycle Timing Gate & Resolver Integration
In `PriorityResolver.resolve`:
```python
def should_hydrate_stream(match: Match, now: Optional[datetime] = None) -> bool:
    if match.status == MatchStatus.FINISHED:
        return False
    if match.is_live:
        return True
    current_time = now or datetime.now(timezone.utc)
    # Active 30 minutes before kickoff
    return current_time >= (match.kickoff_time - timedelta(minutes=30))

# Inside PriorityResolver.resolve():
if not resolved.stream_servers and resolved.channel:
    if should_hydrate_stream(resolved, now=current_time):
        resolved.stream_servers = ChannelStreamMapper.get_servers(resolved.channel)
```
- By keeping hydration strictly inside `PriorityResolver.resolve`, the catalog cache and disk snapshot (`snapshot.json`) remain pure and decoupled from third-party streaming links.

### 4.4. Frontend Security & Sandbox
In `frontend/src/components/StreamPlayerContainer.jsx`:
- Ensure `sandbox` attribute defaults to or respects `current?.sandbox || "allow-forms allow-same-origin allow-scripts allow-presentation"`.
- Ensure `referrerPolicy="no-referrer"` is consistently applied on `<iframe>` to guarantee upstream stream access without CDN origin blocks.

---

## 5. Verification Plan

1. **Python Unit Tests (`pytest`):**
   - Test channel normalization:
     - `beIN SPORTS 1 HD` -> `bein-sports-hd-1`
     - `بي ان سبورت 2` -> `bein-sports-hd-2`
   - Test timing gate:
     - Match at kickoff minus 45 min -> No automated streams (placeholder shown).
     - Match at kickoff minus 25 min -> Streams populated (`alba_bein-sports-hd-1_0`, `alba_bein-sports-hd-1_1`).
     - Match `IN_PLAY` -> Streams populated.
     - Match `FINISHED` -> No automated streams.
   - Test Admin override taking precedence over automated AlbaPlayer streams.
   - Run `pytest tests/live_score/test_resolver.py` -> 100% pass (139/139).
2. **Frontend Vitest Tests (`vitest`):**
   - Test `StreamPlayerContainer.jsx` renders AlbaPlayer iframe with correct `src`, `referrerPolicy="no-referrer"`, and server switcher pills.
   - Run `npm test` / `vitest run` -> 50/50 pass.
3. **End-to-End Live Check:**
   - Verify `/api/v1/matches/{id}` returns populated `stream_servers` when live or within 30 min of kickoff.
   - Verify match detail page in browser loads player iframe correctly.
