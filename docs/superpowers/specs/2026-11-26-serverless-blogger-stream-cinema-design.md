# Architecture Design: Serverless Blogger Hub & Stream Cinema

**Date:** 2026-11-26  
**Status:** APPROVED FOR IMPLEMENTATION  
**Target Repositories:** `football-live-score-platform`  
**Domains:**  
- **Main Monetization Hub:** Blogger (`kora-live-to.blogspot.com`) — Adsterra Approved (ID: `6226474`)  
- **Streaming Theater Sub-Site:** Cloudflare Pages (Free, 100% Serverless React SPA)  

---

## 1. Intent & The Why

### Why We Are Doing This
1. **Dwell Time & Monetization on Blogger:**  
   Adsterra publisher account (`6226474`) is approved exclusively on `kora-live-to.blogspot.com`. Adsterra ad formats (Popunders with 20-min cap, SocialBar, Skyscrapers, Native Banners) yield peak RPM/CPM when users spend **extended dwell time (3 to 6+ minutes)** on the page. By introducing automated football news, in-depth match summaries, and video goal highlights directly on Blogger, users stay significantly longer engaged with high-value content.
2. **Pure Match Stream Cinema on Cloudflare Pages:**  
   Users clicking through to watch live broadcasts demand a zero-distraction, lightning-fast streaming player. The non-Blogger site is stripped of heavy blog articles and dedicated strictly to **Live Match Streaming** with multi-server switching (Server 1, Server 2, VIP 4K Smartlink), live minute indicators, and tactical pitch views.
3. **100% Free, Zero-Maintenance Serverless Cloud Infrastructure:**  
   Local batch scripts, manual PC execution, and temporary tunnels (`trycloudflare.com`) are replaced by an automated **GitHub Actions** cron workflow running 24/7 on a **Public GitHub Repository** (benefiting from unlimited free GitHub Actions minutes). The streaming frontend is deployed permanently to **Cloudflare Pages** (unlimited free bandwidth, zero sleep, instant edge delivery).

---

## 2. Confirmed Project Decisions

1. **Blogger Publishing Scope:**  
   Automated publishing is focused strictly on the **Top 3 to 5 High-Traffic Matches per day** (Champions League, Premier League derbies, El Clásico, Saudi Pro League, Al Ahly / Zamalek). This prevents triggering Blogger's ~50 posts/day anti-spam flags while driving maximum traffic and high dwell time.
2. **Post Lifecycle (Two-Stage Evolution):**
   - **Stage 1 (Pre-Match):** Match preview with confirmed lineups, referee, stadium, channel, Arabic commentator, countdown, and prominent `▶ الانتقال إلى سيرفر البث المباشر (HD)` CTA button.
   - **Stage 2 (Post-Match):** Updated with video highlights/goals embed (YouTube/Dailymotion/Twitter open embeds), full goal timeline, tactical statistics, and final score summary.
3. **Cloudflare Pages Stream Delivery:**  
   Stream player utilizes direct responsive embeds with `referrerPolicy="no-referrer"`, HLS (`.m3u8`) direct playback, and the high-converting **VIP 4K Server button (Adsterra Smartlink)** routing to `https://budgetezy.org/4/ae626546295ba9dbdec2ea24a521084c`.
4. **Real-time Live Scores (Hybrid Polling):**  
   While stream links are fetched from static `matches.json`, client-side polling queries public live score endpoints every 30 seconds so live scores and match minutes are never stale.
5. **Clean Separation of Concerns:**  
   - Remove obsolete `/admin` and `/api/v1/ads` from the Cloudflare Pages SPA.  
   - Floating header and bottom bridge button: `🌐 عودة إلى كورة لايف (الأخبار وملخصات الأهداف)` to loop all traffic back to Blogger.

---

## 3. Approaches Considered & Trade-offs

| Approach | Description | Pros | Cons / Trade-offs | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Approach 1 (Selected): Cloudflare Pages + GitHub Actions Cron** | React SPA on Cloudflare Pages reading static `matches.json`. GitHub Actions runs every 20 min to scrape, commit data, and publish to Blogger API. | 100% free forever; 0 server sleep; unlimited bandwidth on Pages; automated 24/7; unlimited CI minutes on Public repo. | Stream URLs scraped periodically rather than sub-second websockets. | **SELECTED (User Choice)** |
| **Approach 2: Cloudflare Workers + Supabase DB** | SPA on Pages, API on Workers, database on Supabase free tier. | Real-time dynamic updates via database triggers. | Free tier limits (Supabase pauses after inactivity, Worker request caps); high complexity. | Discarded |
| **Approach 3: Render Free Container + Vercel SPA** | FastAPI hosted on Render free tier, frontend on Vercel. | Full dynamic Python backend running continuously. | Render free instances sleep after 15 minutes of inactivity; 50-second cold starts. | Discarded |

---

## 4. System Architecture

```
                       [ GitHub Repository (Public) ]
                                      |
         +----------------------------+----------------------------+
         |                                                         |
         v                                                         v
[ GitHub Actions Cron ]                                 [ Cloudflare Pages ]
  (Runs every 20 min)                                    (Global Edge CDN)
         |                                                         |
         +--> Scrapes top fixtures & streams                       |
         +--> Writes `frontend/public/data/matches.json` --------->| Pure Stream Cinema SPA
         +--> Generates & Publishes Top 3-5 Blogger Articles       | (HLS / Iframe / VIP 4K)
                     |                                             |
                     v                                             |
           [ Blogger Main Hub ]                                    |
        (kora-live-to.blogspot.com)                                |
      - Top 3-5 Matches Highlights & Summaries                     |
      - Embedded Video Goals (High Dwell Time: 3-6m)               |
      - Adsterra Units Active (Popunder, SocialBar, Banners)       |
                     |                                             |
                     +---- "Watch Stream" Button ----------------->+
                     |<--- "Back to Blogger Hub" Button -----------+
```

---

## 5. Detailed Component Specifications

### 5.1 Blogger High-Dwell-Time Content Engine
- **Target Posts:** Top 3–5 trending matches per day determined by `LEAGUE_WEIGHTS` and `TOP_CLUBS` scoring in `scripts/auto_blogger_publisher.py`.
- **Pre-Match Template:**
  - Full match metadata: Channel, Commentator, Stadium, Referee, Starting 11, Kickoff times across Arab capitals (KSA, Cairo, UAE, Morocco, GMT).
  - Google Schema.org `SportsEvent` JSON-LD.
  - Streaming CTA button linking to `https://<cloudflare-pages-domain>/match/{id}`.
- **Post-Match Summary & Video Highlights Template:**
  - Responsive embedded highlight player (YouTube / Dailymotion / official club embed).
  - Match timeline with visual icons: Goals ⚽, Yellow Cards 🟨, Red Cards 🟥, Substitutions 🔄.
  - Full tactical match summary (800+ words) to maximize reading time.
  - Interactive "من هو رجل المباراة؟" (Player of the Match) poll widget for viewer participation.

### 5.2 Cloudflare Pure Stream Cinema SPA (`frontend/`)
- **Index View (`/`):**
  - Clean slate of today's live and upcoming matches with instant status chips (الكل, مباشر الآن, لم تبدأ, انتهت).
  - Distraction-free: No heavy blog articles or dead admin panels.
- **Match Stream Cinema (`/match/:id`):**
  - Responsive 16:9 video player supporting HLS (`.m3u8`), Clappr/m3u8, and sandboxed iframes with `referrerPolicy="no-referrer"`.
  - **Server Switching Bar:**
    - Server 1 (HD)
    - Server 2 (Medium / Low Latency)
    - **VIP Server 4K (Adsterra Smartlink):** Amber glowing pill linking to `https://budgetezy.org/4/ae626546295ba9dbdec2ea24a521084c`.
  - **Tactical Pitch View:** Interactive tactical field displaying real player lineups and formations.
  - **Sticky Loop-Back Header/Footer:**
    - `🌐 عودة إلى كورة لايف (الأخبار وملخصات الأهداف)` linking back to `https://kora-live-to.blogspot.com`.
- **Data Loading:**
  - Loads initial slate and stream URLs from static `/data/matches.json`.
  - Client-side polling refreshes live scores and match minutes every 30 seconds directly from public endpoints.

### 5.3 GitHub Actions Workflow (`.github/workflows/sync_and_publish.yml`)
- **Trigger:** Cron schedule `*/20 * * * *` (every 20 minutes) + manual `workflow_dispatch`.
- **Job Steps:**
  1. Checkout public repository.
  2. Set up Python 3.12 environment.
  3. Execute `scripts/auto_blogger_publisher.py` with top 3–5 trending matches filter.
  4. Scrape active streams and generate `frontend/public/data/matches.json`.
  5. Commit updated `matches.json` and article cache (`data/published_articles.json`) back to the repo.
  6. Deploy frontend build to Cloudflare Pages via Direct Upload (`cloudflare/pages-action` or GitHub Pages).

---

## 6. What's Left to the Builder
- Refactoring `frontend/src/App.jsx` to load static `/data/matches.json` with client-side live polling fallback.
- Updating `scripts/auto_blogger_publisher.py` with the 3–5 match rate-limiting and video embed template.
- Creating the GitHub Actions workflow file `.github/workflows/sync_and_publish.yml`.
- Providing instructions for connecting Cloudflare Pages and GitHub repository.
