# Design Document: Blogger-Centric Live Hub, High-Yield Adsterra Monetization, Anti-Takedown Architecture & Homepage Content Upgrades

- **Date:** 2026-11-25
- **Status:** Approved / Enhanced with Homepage SEO & Monetization Architecture
- **Target Repository:** `C:\Users\Mohany\Desktop\football-live-score-platform`
- **Adsterra Approved Domain:** `kora-live-to.blogspot.com` (Account ID: `6226474`)
- **Backend / Sub-Engine:** Local FastAPI service on port 8000 via Cloudflare Tunnel (`trycloudflare.com`)

---

## 1. Intent & The Why

The platform currently suffers from an acute monetization leak, severe operational fragility, and thin homepage content:
1. **The $0.02 Revenue Trap**: The publisher account in Adsterra earned only $0.02 across 86 impressions because the highest-yielding format (**Popunder**, accounting for 80%+ of sports streaming ad revenue) was completely omitted from the theme code. Furthermore, visitors clicking on matches were redirected off-site to transient `*.trycloudflare.com` URLs where Adsterra is unapproved, causing 100% loss of streaming viewability time and ad impressions.
2. **Thin Homepage & High Bounce Rate**: The homepage currently only displays a plain list of match cards without status filtering, league carousels, expandable match intel, or semantic SEO editorial text. Search crawlers view it as low-text thin content, while users bounce after 10 seconds without interacting.
3. **Ephemeral Link Rot**: Cloudflare Quick Tunnels generate a new random subdomain upon each restart, immediately turning all links, fetch calls, and published articles on Blogger into dead HTTP 530/404 pages.
4. **Severe Deletion Risk**: Direct embedding of pirated video streams in static Blogger posts inevitably triggers automated DMCA takedown notices via Lumen Database, leading to Google terminating the Blogspot subdomain.
5. **Backend Defects**: Core logic bugs in `resolver.py` (80% of Arabic clubs fail to match), `store.py` (duplicate `close()` dropping analytics), and `public_routes.py` (stripping videojs player initialization) impair stability.

This project redesigns the architecture to establish **Blogger as the primary, safe, content-rich, and fully monetized hub**, upgrades the homepage for maximum organic traffic and dwell time, fixes all backend and scraper bugs, protects the blog from Google deletion, and automates synchronization between the transient tunnel and Blogger.

---

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- **Homepage SEO & Dwell-Time Overhaul**:
  - Live Status Filter Pills: `[الكل (All)]`, `[🔴 جارية الآن (Live)]`, `[⏳ القادمة (Scheduled)]`, `[🏁 المنتهية (Finished)]`.
  - Major League Filter Carousel: Instant filtering for UEFA Champions League, Premier League, LaLiga, Saudi Pro League, Serie A, etc.
  - In-Card Expandable Details: Dropdown for stadium, referee, channel, commentator, and dual action buttons.
  - Semantic SEO Keyword Block & FAQ Schema: Rich, topical 400-word sports editorial with FAQPage JSON-LD to win Google Rich SERP snippets.
  - Community Sticky Badges: Telegram channel link, "Add to Bookmarks (Ctrl+D)", and Goal Alert prompt to drive direct returning traffic.
- **Maximize Adsterra Revenue (10x–30x Boost)**: Integrate all 6 approved Adsterra units:
  - Official Popunder with 20-minute user session frequency capping.
  - SocialBar notification widget.
  - Responsive Top Billboard (`728x90` desktop / `320x50` mobile) with fixed CSS containers (0 CLS).
  - Dual `160x600` Desktop Skyscraper banners on wide screens (`>= 1320px`).
  - Native Banner inserted strategically after match #3 in the schedule and directly below the video player.
  - Smartlinks (BudgetEzy & AsiaFilm rotated 50/50) attached to "VIP Server 2" buttons and intent-triggered click handlers.
- **Blogger Anti-Takedown Immunity**: Ensure Blogger hosts 100% clean, legal content (ESPN-backed schedules, lineups, live scores, statistics, and editorial previews). Stream player embeds are hydrated dynamically client-side or served via a decoupled redirector with `noindex`, preventing automated DMCA strikes against Blogger.
- **Self-Healing Tunnel & Permanent Links**: Replace hardcoded tunnel URLs with the Blogger Same-Origin Feed Bridge pattern so that restarting Cloudflare Tunnel never breaks published posts or navigation.
- **Backend Bug Remediation**:
  - Invert `_CANONICAL_ARABIC` in `resolver.py` so all 350+ European and Arab clubs resolve bidirectionally without false negatives.
  - Fix `store.py` duplicate `close()` method.
  - Fix `public_routes.py` player proxy so VideoJS is not stripped.
  - Fix `auto_blogger_publisher.py` trend scoring for halftime/extra time and timezone DST calculations.
- **Hands-Free Automation**: Fully automated fixture ingestion, stream scraping, daily trending article generation and publishing via Mail-to-Blogger, and daily JSON/XML blog backup.

### Non-Goals
- Migrating away from Blogger to WordPress or paid hosting.
- Hosting raw `.ts` or `.m3u8` video segments on local storage (streams remain proxied/embedded from upstream open web providers).
- Buying paid domains or custom SSL certificates at this stage (all components utilize existing Blogger + free Cloudflare Tunnel).

### Anti-Goals
- **No Invisible Clickbait / Click Hijacking**: Do not overlay invisible clickable divs across the whole screen; this causes immediate Adsterra account termination for click fraud.
- **No Trapping Redirect Loops**: Never disable browser back navigation or trigger popunders on every click, which triggers Google Chrome "Deceptive Site Ahead" blacklisting.

---

## 3. Homepage Content & SEO Architecture Upgrade

To transform the homepage into a high-converting, high-ranking destination that captures top Google rankings and maximizes dwell time, the following components are integrated directly into `blogger_theme/kora_pro_blogger_theme.xml` and `scripts/build_modern_blogger_theme.py`:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TOP NAVIGATION & COMMUNITY BAR                  │
│  [⚽ كورة لايف]       [⭐ أضف للمفضلة]    [📱 تيليجرام البث]   [☀️ نهاري] │
├────────────────────────────────────────────────────────────────────────┤
│             SPONSOR BILLBOARD (Responsive 728x90 / 320x50)             │
├────────────────────────────────────────────────────────────────────────┤
│ 3-DAY SWITCHER: [مباريات الأمس] | [★ مباريات اليوم ★] | [مباريات الغد]   │
│ LIVE STATUS FILTER: [الكل] [🔴 مباشر الآن] [⏳ القادمة] [🏁 المنتهية]   │
│ LEAGUE PILLS: [دوري أبطال أوروبا] [الدوري الإنجليزي] [الدوري الإسباني]... │
├────────────────────────────────────────────────────────────────────────┤
│                       MATCH CARDS FEED (Grouped)                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Match 1: ريال مدريد vs بايرن ميونخ (Live Minute / Score)         │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Match 2: ليفربول vs مانشستر سيتي (Live Minute / Score)           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Match 3: برشلونة vs أتلتيكو مدريد (Live Minute / Score)          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  >>> IN-FEED ADSTERRA NATIVE BANNER (High Visibility & CTR) <<<        │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Match 4 ...                                                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────────────────┤
│              SEMANTIC SEO CONTENT HUB (Authority Text)                 │
│  • H2: تغطية شاملة لجدول مباريات اليوم والقنوات الناقلة                │
│  • 350-word editorial targeting core ranking keywords                  │
│  • FAQ Accordion with Schema.org FAQPage JSON-LD for Google Rich SERP │
├────────────────────────────────────────────────────────────────────────┤
│ STICKY BOTTOM AD BAR (Adsterra VIP Smartlink with Dismiss Button)      │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Live Status Quick-Filters & League Navigation
- **Status Filter Chips**:
  - `data-filter="all"`: Shows all fixtures for the selected day.
  - `data-filter="live"`: Isolates matches where `status == "IN_PLAY"` or status text contains "مباشر" / "شوط". Displays a glowing red beacon `🔴 مباشر الآن`.
  - `data-filter="scheduled"`: Isolates upcoming matches where `status == "SCHEDULED"`.
  - `data-filter="finished"`: Isolates ended matches with final scores.
- **League Filter Carousel**: Horizontal swipeable pills on mobile and sticky bar on desktop filtering matches by `data-league` attribute without reloading the page.

### 3.2 In-Card Interactive Intel & Action Drawer
- Each match card contains an expandable quick-drawer:
  - Kickoff times in KSA, Cairo, and UTC.
  - Channel name with logo icon, official commentator, and stadium.
  - Direct Action Triggers:
    - `[⚡ مشاهدة البث الحي]` -> Opens the in-page Lightbox/Modal Player.
    - `[🚀 سيرفر 2 VIP فائق السرعة]` -> Triggers rotated Smartlink in background tab and switches stream to Server 2.

### 3.3 Semantic SEO Text & Google Rich Snippets (FAQPage Schema)
- At the bottom of the homepage (below the fixtures container), a dedicated, beautifully formatted SEO block is included:
  - **H2:** `كورة لايف - جدول مباريات اليوم وبث مباشر لأهم البطولات العالمية`
  - **Contextual Editorial Copy:** Incorporates targeted head-terms naturally: *مباريات اليوم بث مباشر، يلا شوت، كورة لايف، جدول مباريات اليوم، دوري أبطال أوروبا، الدوري الإنجليزي، الدوري الإسباني، دوري روشن السعودي*.
  - **Interactive FAQ Accordion:**
    1. *س: كيف يمكنني متابعة نتائج ومباريات اليوم مباشرة بدون تقطيع؟*
    2. *س: ما هي أهم البطولات والدوريات التي يغطيها موقع كورة لايف؟*
    3. *س: هل تتوفر تغطية حية للتشكيلات والقنوات الناقلة والمعلقين؟*
    4. *س: هل يعمل الموقع بسلاسة على الهواتف الذكية والأجهزة اللوحية؟*
  - **Schema.org JSON-LD**: Embedded `FAQPage` and `SportsEvent` structured data, allowing Google to display expandable rich FAQ questions and match cards directly in search results.

---

## 4. Builder Check Rulings & Settled Decisions

During the architectural builder review, 5 critical planning questions were evaluated and settled as follows:

### Ruling 1: Dynamic Cloudflare Tunnel Discovery (Blogger Same-Origin Feed Bridge)
- **Decision**: Avoid fragile third-party registries (GitHub tokens, KV databases). Instead, leverage Blogger's native same-origin JSON feed:
  1. When `auto_blogger_publisher.py` publishes today's trending post via Mail-to-Blogger, it automatically embeds a clean metadata marker: `<div id="kora-stream-bridge" data-tunnel="https://*.trycloudflare.com" style="display:none"></div>`.
  2. Client-side JavaScript in the Blogger theme queries its own feed: `fetch('/feeds/posts/default?alt=json&max-results=1')`.
  3. The script extracts the active tunnel URL and stores it in `localStorage.setItem('kora_active_tunnel', url)`.
  4. First-time visitors and recurring users alike receive the active URL automatically within 200ms without CORS issues, tokens, or external dependencies.

### Ruling 2: In-Theme Video Player & Post Integration (No Manual Page Creation)
- **Decision**: Eliminate the requirement for manual page creation in Blogger. The player is built directly into the **Blogger Theme XML**:
  1. **In-Post Articles**: When a user views any match article (`b:if cond='data:view.isPost'`), the theme dynamically renders the stream player container (`.kora-stream-player-box`) with server tabs directly above the article analysis.
  2. **Homepage Match Cards**: Clicking a match card opens the embedded **Lightbox/Modal Player** with live stream tabs directly on the homepage, while providing a link to read the full analytical post.
  3. **Zero Manual Setup**: Updating the theme XML once empowers all existing and future posts with live streaming capabilities automatically.

### Ruling 3: Popunder Script Orchestration & 20-Minute Persistent Cap
- **Decision**: The Popunder script tag (`https://capitalhospitals.org/1/9d3379bfa7b20556e0328830cd7e5e7f`) is injected dynamically into `<head>` upon the first user interaction (click/touch), gated by `localStorage.getItem('kora_pop_ts')`:
  - If `kora_pop_ts` is absent or older than 20 minutes (1,200,000 ms), the script is injected synchronously on the click event.
  - `kora_pop_ts` is immediately refreshed in `localStorage` to the current timestamp.
  - This guarantees that popunders never fire repeatedly across multiple tabs or page refreshes, fully satisfying Google Safe Browsing standards while delivering 100% of legitimate Adsterra revenue.

### Ruling 4: Smartlink VIP Server 2 Interaction Flow
- **Decision**: When the user clicks "سيرفر 2 - فائق السرعة (VIP)":
  1. The Smartlink offer (BudgetEzy / AsiaFilm rotated 50/50) opens in a **new background tab** (`window.open(smartlink, '_blank')`).
  2. The embedded player in the current window **simultaneously switches to stream server 2** (`/api/v1/stream/player/{slug}?serv=1`).
  3. The user gets uninterrupted match streaming on Blogger, while the publisher earns a high-converting Smartlink click.

### Ruling 5: Automated Backup Architecture (`scripts/backup_blogger_content.py`)
- **Decision**: Implement a two-tier zero-credential backup:
  1. **Cloud Feed Scraper**: Queries `https://kora-live-to.blogspot.com/feeds/posts/default?alt=json&max-results=500` and dumps all published articles, titles, timestamps, and comments into `data/backups/blogger_posts_YYYY-MM-DD.json`.
  2. **Local Theme & Article Archive**: Archives the current `kora_pro_blogger_theme.xml` and HTML templates in `data/backups/`.
  3. Requires no Google account passwords or 2FA, and runs completely unattended via Windows Task Scheduler or batch launcher.

---

## 5. Detailed Component Design & Specifications

### 5.1 Adsterra Monetization Engine Architecture

All 6 Adsterra ad codes provided by the user are integrated systematically:

1. **Popunder (High-Yield Core)**:
   - Code: `<script data-cfasync="false" src="https://capitalhospitals.org/1/9d3379bfa7b20556e0328830cd7e5e7f"></script>`
   - Orchestration: Gated by 20-minute `localStorage` timestamp on interaction.
2. **SocialBar Widget**:
   - Code: `<script data-cfasync="false" src="https://czernik.org/14/4d85a8908516d9c268b82f4a5df10c8a"></script>`
   - Placement: In `<head>`, loaded once globally with `data-cfasync="false"`.
3. **Responsive Header Billboard**:
   - Desktop (`>= 768px`): `728x90` key `6703ea03ffb309455182c593d4e6ea81` via `czernik.org/22/`
   - Mobile (`< 768px`): `320x50` key `1cdf29d3af257663a92ffa6b5207a68a` via `czernik.org/22/`
   - CSS Container: Fixed `min-height: 90px` (desktop) and `min-height: 50px` (mobile) with `@media` separation.
4. **Desktop Skyscraper Gutters (160x600)**:
   - Code: Key `bee904d3f2a415fcd8e41f64598a9680` via `czernik.org/22/`
   - Placement: Fixed floating sidebars on desktop viewports (`>= 1320px` width) outside the 1100px main content wrapper. Provides continuous viewability during the match.
5. **Native Banner (`container-f1180bd1a9f13152d2247022e3f6f1b0`)**:
   - Code: `czernik.org/21/f1180bd1a9f13152d2247022e3f6f1b0`
   - Primary Position: In-feed after match card #3 in the homepage schedule.
   - Secondary Position: Directly beneath the match details/player in post articles.
6. **Smartlink Rotation (VIP Stream Switchers)**:
   - Links: BudgetEzy (`https://budgetezy.org/4/ae626546295ba9dbdec2ea24a521084c`) and AsiaFilm (`https://asiafilm.org/4/67d5c06c56eb1c96b2ff42f4dc88412e`).
   - Trigger: Bound to "سيرفر 2 - فائق السرعة (VIP)" and sticky bottom bar CTA. Rotated 50/50 randomly to prevent offer fatigue.

---

### 5.2 Anti-Takedown & Google Deletion Protection (The Decoupled Shield)

1. **Static HTML Cleanliness**: Articles created by `article_generator.py` contain NO direct video embeds or pirated URLs in their raw source. They feature match metadata, Schema.org SportsEvent JSON-LD, tactical lineups, and an interactive trigger button.
2. **DMCA Safe Harbor Notice**: Permanent legal notice embedded in the footer:
   > "موقع كورة لايف بوابة إخبارية رياضية للنتائج الحية. الموقع لا يخزن ولا يبث أي مواد فيديو على خوادمه الخاصة. جميع المواد معروضة من أطراف ثالثة ومصادر عامة على شبكة الإنترنت المفتوحة وفقاً لـ 17 U.S.C. § 512."
3. **NoIndex Shield on Player Endpoints**: Dedicated player routes specify `<meta name="robots" content="noindex, nofollow"/>`.

---

### 5.3 Backend & Domain Logic Repairs

1. **Bidirectional Team Alias Resolution (`resolver.py`)**:
   - In `_get_normalized_base()`, iterate over `_CANONICAL_ARABIC.items()` and invert each entry (`norm(ar) -> en`) into `base`.
   - In `get_arabic_name()`, add a fallback lookup in `_BASE_ALIASES` so clubs like Sabah FK, Viking FK, and Slavia Prague map to their proper Arabic names.
2. **Store Connection & Flusher Fix (`store.py`)**:
   - Remove redundant `close(self)` at line 779. Ensure `_stop_flusher.set()` is executed, visit queue is flushed, and the lock is properly released on app shutdown.
3. **VideoJS Player Initialization Fix (`public_routes.py`)**:
   - In `stream_player_proxy`, refine the regex removing IMA ads so that `const player = videojs(...)` remains intact, preventing black screen player failures.
4. **Timezone & Trend Calculation (`auto_blogger_publisher.py` & `article_generator.py`)**:
   - Replace hardcoded `+ timedelta(hours=2)` with `zoneinfo.ZoneInfo("Africa/Cairo")` to maintain accuracy during Egyptian Daylight Saving Time.
   - Update match trend scoring: award +200 points for `HALFTIME`, `EXTRA_TIME`, and `PENALTIES`.

---

## 6. Verification & Testing Strategy (Test-Driven Development)

1. **Unit Tests (Backend)**:
   - `tests/live_score/test_resolver_bidirectional.py`: Verify that `TeamAliasMatcher.match_team('غلطة سراي')` returns `'Galatasaray'`, `'ريال بيتيس'` returns `'Real Betis'`, and `'Sabah FK'` returns Arabic.
   - `tests/live_score/test_store_flusher.py`: Verify that calling `store.close()` flushes pending visits and sets `_stop_flusher` without raising `sqlite3.ProgrammingError`.
   - `tests/live_score/test_player_proxy.py`: Verify that `stream_player_proxy` preserves VideoJS initialization while stripping popunder scripts.
2. **Integration Tests (Blogger Theme & Ads)**:
   - `tests/test_blogger_theme_ads.py`: Verify generated XML contains Popunder, SocialBar, 728x90, 320x50, 160x600, Native Banner, Smartlinks, Status Filters, and FAQ Schema.
   - Validate that no hardcoded ephemeral `trycloudflare.com` domain is baked into the theme XML without fallback.
3. **Full Test Suite Run**: Ensure all 141+ tests pass with zero regressions.

---

## 7. Implementation Rollout Plan

- **Task 1: Backend Domain & Resolver Repairs**: Invert canonical aliases and fix bidirectional team name matching in `resolver.py`.
- **Task 2: API & Storage Defect Fixes**: Fix `store.py` duplicate `close()`, refine `public_routes.py` player proxy, and update Cairo timezone handling.
- **Task 3: Blogger Theme Redesign with Full Adsterra Units & Homepage Upgrades**: Implement Popunder (with 20m persistent cap), 160x600 skyscrapers, Native Banner in-feed, live status filter chips, league carousel, and FAQ SEO section in `build_modern_blogger_theme.py`.
- **Task 4: Dynamic Tunnel Discovery & Post-Player Integration**: Add Same-Origin Feed Bridge in theme JS and update article generator to inject player containers and metadata.
- **Task 5: Automated Backup & Publishing Enhancements**: Write `scripts/backup_blogger_content.py` and update `scripts/auto_blogger_publisher.py`.
- **Task 6: Verification & End-to-End Test Execution**.
