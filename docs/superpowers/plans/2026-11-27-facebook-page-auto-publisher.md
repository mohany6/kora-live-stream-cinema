# Facebook Page Auto-Publisher & Desktop Studio GUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 1-button Desktop GUI (`publish_facebook_today.bat` -> `scripts/facebook_studio_gui.py`) and 24/7 GitHub Actions Facebook Page publisher (`scripts/auto_facebook_publisher.py`) that generates Cyber-Stadium `1200×1200` Arabic match posters via Headless Chrome/Edge and posts them with link-free captions + Blogger links in the first comment.

**Architecture:** Domain modules `facebook_caption.py` (Cairo/Mecca formatting, link-free Arabic captions, first-comment links) and `facebook_poster.py` (HTML/CSS Cyber-Stadium generator + Headless Chrome/Edge PNG renderer) feed `scripts/auto_facebook_publisher.py` (Graph API `v25.0` two-step photo + first-comment upload + `data/published_facebook.json` deduplication) and `scripts/facebook_studio_gui.py` (Cyber-Stadium `tkinter` desktop app).

**Tech Stack:** Python 3.12, `tkinter` (stdlib), `zoneinfo` (stdlib), `requests`, Headless Chrome/Edge CLI (`--headless=new --screenshot`), Facebook Graph API `v25.0`, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-27-facebook-page-auto-publisher-design.md`

## Global Constraints
- Zero URLs (`http://` / `https://`) allowed inside the main Facebook `caption` text; URLs go strictly in `first_comment`.
- Zero extra Python binary dependencies (`Pillow`/`libraqm` not required); poster PNGs render via HTML/CSS + Headless Chrome/Edge.
- Fail-open in CI when `FB_PAGE_ID` or `FB_PAGE_ACCESS_TOKEN` is unset (no workflow failures).
- `auto_blogger_publisher.py` keeps full backward compatibility with all existing tests.

## Review Focus
1. Mixed Arabic + English text (`SSC 1 HD`, `beIN SPORTS`) renders cleanly RTL in poster HTML and captions.
2. Missing or failing ESPN club logos fall back gracefully without breaking poster rendering.
3. Missing `FB_PAGE_ID` / `FB_PAGE_ACCESS_TOKEN` never crashes CI or the GUI; local mode saves PNG + copies caption.
4. Graph API `/{page_id}/photos` returning only `id` (without `post_id`) still posts the first comment cleanly.
5. `timezone`-naive or malformed `kickoff_time` ISO strings degrade safely without raising `ValueError`.

---

### Task 1: Facebook Caption & First-Comment Builder (`src/live_score/domain/facebook_caption.py`)
- [x] **Step 1:** Write failing tests in `tests/test_facebook_publisher.py` verifying zero URLs in `caption`, Blogger URL in `first_comment`, and Cairo/Mecca kickoff formatting.
- [x] **Step 2:** Implement `src/live_score/domain/facebook_caption.py` (`build_daily_schedule_copy`, `build_match_copy`).
- [x] **Step 3:** Run `pytest tests/test_facebook_publisher.py` to verify pass.

### Task 2: Cyber-Stadium HTML-to-PNG Poster Renderer (`src/live_score/domain/facebook_poster.py`)
- [x] **Step 1:** Add failing tests in `tests/test_facebook_publisher.py` for `build_daily_schedule_poster_html`, `build_match_poster_html`, and `render_poster_png` (mocked browser subprocess + real Chrome smoke check).
- [x] **Step 2:** Implement `src/live_score/domain/facebook_poster.py` supporting both `daily_slate` and single-match `pre_match`/`post_match` cards.
- [x] **Step 3:** Run `pytest tests/test_facebook_publisher.py` to verify pass.

### Task 3: Graph API Publisher, Deduplication Cache & Blogger URL Capture (`scripts/auto_facebook_publisher.py`)
- [x] **Step 1:** Add tests for `publish_photo_with_first_comment` (mocked `requests.post` for `/photos` + `/comments`), deduplication cache (`published_facebook.json`), and graceful skip when credentials are absent.
- [x] **Step 2:** Implement `scripts/auto_facebook_publisher.py` and optionally record Blogger `url` in `scripts/auto_blogger_publisher.py`.
- [x] **Step 3:** Run `pytest tests/test_facebook_publisher.py tests/test_auto_blogger_publisher.py`.

### Task 4: Desktop GUI (`scripts/facebook_studio_gui.py`), 1-Click `.bat`, Setup Guide & Workflow
- [x] **Step 1:** Implement `scripts/facebook_studio_gui.py` (Cyber-Stadium `tkinter` GUI) and `publish_facebook_today.bat`.
- [x] **Step 2:** Update `.github/workflows/sync_and_publish.yml` and write `docs/FACEBOOK_PAGE_SETUP.md`.
- [x] **Step 3:** Verify full test suite (`pytest`) and live dry-run poster generation.
