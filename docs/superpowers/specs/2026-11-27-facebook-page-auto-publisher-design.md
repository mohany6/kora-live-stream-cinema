# Design Specification: Automated Facebook Page Growth & Match Poster Publisher

**Date:** 2026-11-27  
**Status:** PROPOSED FOR USER APPROVAL  
**Target Repository:** `football-live-score-platform`  
**Target Properties:**  
- **Facebook Page:** Official Page for **كورة لايف (Kora Live)**  
- **Destination Hub (First-Comment Link):** `https://kora-live-to.blogspot.com/` (Adsterra-approved)  
- **Stream Cinema:** `https://kora-stream-cinema.pages.dev/`

---

## 1. Intent & The Why

The user wants to create and grow an official **Facebook Page** for the football platform that posts **today's matches, trending matchups, and goal/result updates**, builds a loyal following, and drives steady, high-CPM traffic to the Blogger hub (`kora-live-to.blogspot.com`) and Google Search signals.

Web research and Meta platform policies establish three non-negotiable rules for sports pages in 2025–2026:
1. **Links in First Comment Only:** Facebook's feed algorithm suppresses posts containing external URLs in the caption. High-reach pages publish **native visual graphics + engaging Arabic questions** in the caption, then post the article link in the **first comment**.
2. **Zero Copyrighted Video Clips:** Meta's automated Rights Manager fingerprints TV broadcasts (even cropped, flipped, or framed) and bans pages rapidly. Goal updates and match coverage on Facebook must use **custom visual scorecards/graphics** and send fans to the Blogger article for embedded highlights and live match coverage.
3. **Zero App Review Required for Own Page:** Posting to a Page administered by the app owner via the Meta Graph API (`pages_manage_posts`, `pages_read_engagement`, `pages_show_list`) does **not** require Meta App Review.

---

## 2. Goals, Non-Goals & Anti-Goals

### Goals
- Automatically generate **Cyber-Stadium branded 1200×1200 PNG match posters** in Python with properly connected Arabic RTL typography and team crests:
  1. **Daily Schedule Poster (`daily_slate`):** Top 4–5 matches of the day with Mecca/Cairo kickoff times and broadcast channels.
  2. **Pre-Match Trending VS Poster (`pre_match`):** Home vs Away crests, league badge, kickoff time, channel, and prediction prompt.
  3. **Post-Match Result / Goal Summary Poster (`post_match`):** Final scoreline, goal scorers/minutes summary, and prompt linking to highlights on Blogger.
- Automatically publish the poster to the Facebook Page via Graph API (`/{page_id}/photos`) and immediately attach the Blogger article URL (or Blogger homepage fallback) in the **first comment** (`/{post_id}/comments`).
- Run automatically every 20 minutes inside `.github/workflows/sync_and_publish.yml` with strict deduplication (`data/published_facebook.json`) and daily post caps so the page never spams followers.
- Provide a step-by-step Arabic setup guide (`docs/FACEBOOK_PAGE_SETUP.md`) for creating the Page, optimizing name/bio/CTA button, and obtaining the long-lived Page Access Token.

### Non-Goals
- Posting raw TV broadcast video clips or live video streams directly to Facebook.
- Building a Meta App for third-party/stranger users (only the owner's Page is targeted).
- Paid Facebook Ads or Boosted Posts.

### Anti-Goals
- Never include external URLs (`http://` / `https://`) in the main Facebook post `message` caption (only in the first comment).
- Never use spammy engagement bait (*"اعمل لايك لو بتحب..."*) that triggers Meta's engagement-bait demotion; use genuine football questions instead.
- Never crash the GitHub Actions workflow if `FB_PAGE_ID` or `FB_PAGE_ACCESS_TOKEN` secrets are not yet configured (fail-open skip with clear log message).

---

## 3. Constraints & Technical Decisions

- **Arabic Typography Rendering (Headless Chrome / Edge HTML-to-PNG):** Rather than raw Pillow (which requires `libraqm`/`harfbuzz` C-libraries and struggles with mixed Arabic RTL + English channel labels), the poster generator renders a fixed `1200×1200` Cyber-Stadium HTML/CSS template (`<html lang="ar" dir="rtl">` + Google Fonts *Cairo* & *Chakra Petch* + real ESPN team logos) and snaps a crisp PNG via `chrome.exe` / `msedge.exe` / `google-chrome` `--headless=new --screenshot`. Zero extra Python binary dependencies are needed on Windows or GitHub Actions `ubuntu-latest`.
- **One-Button Local Runner + CI Mode (`publish_facebook_today.bat`):** Double-clicking `publish_facebook_today.bat` runs `scripts/auto_facebook_publisher.py`. If `FB_PAGE_ID` and `FB_PAGE_ACCESS_TOKEN` are configured, it posts automatically via Graph API (`v25.0`) + adds the first comment; if not yet configured, it still generates the PNG poster, saves `today_caption.txt` + `today_comment.txt`, copies the Arabic caption to the Windows clipboard, and opens the output folder so the user can post in 10 seconds without errors.
- **Rate Limits & Deduplication:** Store published `(post_type, target_id, stage, date)` keys in `data/published_facebook.json` (committed back to the repo by GitHub Actions alongside `data/published_articles.json`). Cap daily automated Facebook posts (e.g., 1 `daily_slate` + top 3 `pre_match` + top 3 `post_match`).
- **Blogger Post URL Capture:** Enhance `publish_article_via_blogger_api()` in `scripts/auto_blogger_publisher.py` to persist the returned Blogger post `url` in `data/published_articles.json` when available so the Facebook first comment links directly to the matching article, falling back to `https://kora-live-to.blogspot.com/` otherwise.

---

## 4. Approaches Considered

| Approach | Description | Trade-offs | Verdict |
|---|---|---|---|
| **1. Full Automation: HTML-to-PNG (Headless Chrome) + Graph API + First-Comment Linker** | Generate 1200×1200 Cyber-Stadium PNGs via Headless Chrome/Edge, upload via `/{page_id}/photos`, post Blogger URL in `/{post_id}/comments`, runnable by 1-click `.bat` or GitHub Actions. | Requires one-time Meta Developer App + Page Token setup for full auto-posting (and still outputs ready-to-paste PNG + clipboard caption locally without tokens); zero extra Python binary deps. | **SELECTED** |
| **2. Local Poster Generator + Manual Meta Business Suite** | Generate PNGs and captions locally, schedule manually in Meta Business Suite. | Zero Meta API setup, but requires daily manual effort and misses real-time post-match results. | Rejected |
| **3. Text-Only Link Posts via Graph API** | Post plain text + Blogger URL directly in post body via Graph API. | Fast to build, but heavily penalized by Facebook's link-reach algorithm. | Rejected |

---

## 5. Architecture & Module Design

1. **`src/live_score/domain/facebook_poster.py`**
   - Pure HTML/CSS poster builder + headless browser renderer (`chrome.exe` / `msedge.exe` / `google-chrome`):
     - `build_daily_schedule_poster_html(matches, date_label) -> str`
     - `build_match_poster_html(match, stage) -> str`
     - `render_poster_png(html_content, out_path) -> Path`
   - Uses Cyber-Stadium dark theme (`#050811`, `#10b981`, `#06b6d4`), Cairo + Chakra Petch fonts, and ESPN club crests with automatic fallback crest on image load error.
2. **`src/live_score/domain/facebook_caption.py`**
   - Pure copy generators:
     - `build_facebook_post_copy(kind, *, match=None, matches=None, blogger_url="https://kora-live-to.blogspot.com/") -> dict` returning `{"caption": str, "first_comment": str}`
     - Guarantees `http://` and `https://` never appear in `caption`, while `first_comment` contains the target Blogger URL + clear Arabic CTA.
3. **`scripts/auto_facebook_publisher.py`**
   - Reads trending matches via `get_top_trending_matches()` and Blogger article URLs from `data/published_articles.json`.
   - Manages `data/published_facebook.json` deduplication cache.
   - Uploads PNG to `https://graph.facebook.com/v27.0/{page_id}/photos` with `published=true` and `caption`, then posts `first_comment` to `https://graph.facebook.com/v27.0/{post_id}/comments`.
   - Supports `--dry-run` / `--preview` to generate sample posters locally into `data/fb_posters/` without posting.
4. **Desktop GUI & 1-Button Launcher (`scripts/facebook_studio_gui.py` + `publish_facebook_today.bat`)**
   - Dark Cyber-Stadium `tkinter` GUI (`كورة لايف — استوديو النشر الآلي لفيسبوك`) launched by double-clicking `publish_facebook_today.bat`:
     - Select `جدول اليوم` or any specific trending match from today's slate.
     - Single action button to generate the `1200×1200` PNG poster, algorithm-safe Arabic caption, and first-comment Blogger link, and publish automatically via Graph API when `FB_PAGE_ID` + `FB_PAGE_ACCESS_TOKEN` are configured (or copy/save locally when unconfigured).
     - Dedicated 1-click Copy Caption, Copy First Comment, Open Poster Folder, and `.env` Credentials Settings fields.
5. **Integration & Workflow (`scripts/auto_blogger_publisher.py`, `.github/workflows/sync_and_publish.yml`)**
   - Record Blogger `url` in `published_articles.json` when published via Blogger API v3.
   - Add `Publish match posters to Facebook Page` step after Blogger publishing in `sync_and_publish.yml` with `FB_PAGE_ID` and `FB_PAGE_ACCESS_TOKEN` secrets, and stage `data/published_facebook.json` in the git commit step.
5. **Setup Guide (`docs/FACEBOOK_PAGE_SETUP.md`)**
   - Concise Arabic guide covering Page creation, profile/cover setup, Meta Developer App creation, Graph API Explorer token exchange, and adding `FB_PAGE_ID` + `FB_PAGE_ACCESS_TOKEN` to GitHub Secrets.
