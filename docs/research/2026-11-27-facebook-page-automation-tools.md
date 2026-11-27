# Research Notes: Free Tools for Automated Arabic Football Facebook Page Graphics & Publishing

**Date:** 2026-11-27  
**Context:** `football-live-score-platform` (`kora-live-to.blogspot.com` + Facebook Page `كورة لايف - Kora Live`)

---

## 1. HTML-to-PNG Rendering for Arabic RTL Sports Posters

| Tool | Arabic RTL & Mixed Text (`SSC 1 HD`) | Setup / Dependencies | Verdict |
|---|---|---|---|
| **Pillow (`PIL`)** | Poor without `libraqm` + `fribidi` + `harfbuzz` C-libraries, `arabic-reshaper`, `python-bidi`, and bundled Arabic TTFs. Mixed LTR/RTL strings and flexbox layouts are fragile. | Heavy native deps on Windows & Linux CI. | Rejected |
| **Headless Chrome / Edge CLI** | **Native browser rendering (`<html lang="ar" dir="rtl">`)** with Google Fonts (*Cairo* / *Chakra Petch*), CSS Flexbox/Grid, glassmorphism, and remote club logos (`a.espncdn.com`). | **Zero extra Python packages.** Chrome (`chrome.exe`) or Edge (`msedge.exe`) is pre-installed on Windows, and `google-chrome` is pre-installed on GitHub Actions `ubuntu-latest`. | **Selected** |
| **Playwright (`playwright`)** | Identical Chromium rendering quality with explicit `networkidle` auto-waiting. | Requires `pip install playwright` + `playwright install chromium` (~150MB browser download). | Optional fallback if browser binary absent |

**Primary Source Verification:** Verified directly on Windows (`C:\Program Files\Google\Chrome\Application\chrome.exe --headless=new --window-size=1200,1200 --virtual-time-budget=6000 --screenshot=...`) rendering `assets/facebook/today_matches_2026-11-27.png` with 100% accurate Arabic ligatures and all 10 ESPN PNG logos.

---

## 2. Facebook Page Publishing & Link-Reach Rules (Meta Graph API)

1. **Algorithmic Link Penalty:** Meta's feed ranking demotes posts with outbound URLs in the caption. Best practice is **photo + engaging Arabic question in the caption**, with the Blogger URL posted in the **first comment**.
2. **Graph API Two-Step Flow (Meta Graph API Docs):**
   - **Step 1 (Photo Post):** `POST https://graph.facebook.com/v25.0/{page_id}/photos` with `caption`, `published="true"`, `access_token={PAGE_ACCESS_TOKEN}`, and `files={"source": open(png_path, "rb")}`. Response includes `post_id` (or `id`).
   - **Step 2 (First Comment):** `POST https://graph.facebook.com/v25.0/{post_id}/comments` with `message={FIRST_COMMENT_TEXT}` and `access_token={PAGE_ACCESS_TOKEN}`.
3. **Permissions & App Review:**
   - Required scopes: `pages_manage_posts`, `pages_read_engagement`, `pages_show_list` (plus `pages_manage_engagement` for comment management).
   - **Own-Page Exemption:** Posting exclusively to a Page owned/administered by the Meta App admin does **not** require Meta App Review.
   - Must use a **Page Access Token** (obtained from `/me/accounts`), never a User Access Token (which fails with OAuth error 190 / permissions error).
4. **Copyright / Rights Manager Safety:** Never upload TV broadcast video clips or live streams to Facebook; use generated Cyber-Stadium scorecards/match posters and link to the Blogger hub in the first comment.
