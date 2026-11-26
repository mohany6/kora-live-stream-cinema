# Serverless Blogger Hub & Stream Cinema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the football live score platform into a 100% serverless, zero-maintenance system: automated high-dwell-time content (news, match summaries, video highlights) on Blogger to maximize Adsterra revenue, and a pure match streaming cinema SPA hosted on Cloudflare Pages.

**Architecture:** A scheduled GitHub Actions cron workflow running on a public repository scrapes top fixtures and active streams every 20 minutes, generates static `data/matches.json` for the Cloudflare Pages SPA, and publishes top 3–5 high-dwell-time articles to Blogger with video embeds and Google SportsEvent schema. The React frontend is streamlined into a distraction-free streaming player with multi-servers, VIP Smartlink, and loop-back navigation to Blogger.

**Tech Stack:** Python 3.12, GitHub Actions (CI/CD cron), React 18, Vite 6, Tailwind CSS, HLS.js, Pytest, Vitest.

**Spec:** `docs/superpowers/specs/2026-11-26-serverless-blogger-stream-cinema-design.md`

## Global Constraints
- Target Blogger blog domain: `kora-live-to.blogspot.com` (Adsterra Account ID: `6226474`).
- Adsterra Smartlink URL: `https://budgetezy.org/4/ae626546295ba9dbdec2ea24a521084c`.
- Public GitHub repository: zero runner minute limits for scheduled cron jobs.
- Zero local backend requirement: Cloudflare Pages must serve static assets and fetch data from static JSON with client-side polling.
- Strictly limit automated Blogger articles to the Top 3 to 5 trending matches per day to prevent Blogger anti-spam triggers.

## Review Focus
- **Video highlights embeds broken or blocked:** Test that generated highlight embeds use resilient sandbox fallbacks with YouTube / DailyMotion / Twitter iframe formatting.
- **Blogger rate-limit / duplication:** Test that `published_articles.json` cache stops duplicate posts on subsequent 20-minute cron runs.
- **Cloudflare Pages SPA missing data:** Test that `App.jsx` handles initial load when `matches.json` has 0 matches or fails network fetch without crashing.
- **Client-side live polling failures:** Test that score polling catches network errors silently without blanking active stream video players.
- **VIP 4K Server link persistence:** Test that the VIP Smartlink button is always present in stream server tabs regardless of scraped server counts.

---

### Task 1: Top 3-5 Matches Scraper & High-Dwell-Time Content Generator

**Files:**
- Modify: `src/live_score/domain/article_generator.py`
- Modify: `scripts/auto_blogger_publisher.py`
- Test: `tests/test_article_generator.py`

**Interfaces:**
- Consumes: Match dictionary with teams, league, kickoff, stadium, channel, referee, status, score, events, and highlights.
- Produces: `generate_blogger_article(match, stage="pre_match"|"post_match") -> dict[str, str]` returning `title`, `content` (HTML with video embed and Schema.org), and `labels`.

- [ ] **Step 1: Write failing tests for pre-match and post-match content generation**

```python
def test_generate_blogger_article_post_match_with_video_embed():
    match = {
        "id": "match_101",
        "home_team": "ريال مدريد",
        "away_team": "برشلونة",
        "home_score": 3,
        "away_score": 1,
        "status": "FINISHED",
        "competition": "الدوري الإسباني",
        "highlight_embed_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "events": [
            {"minute": 15, "player_name": "فينيسيوس", "type": "goal", "team_name_ar": "ريال مدريد"},
            {"minute": 42, "player_name": "ليفاندوفسكي", "type": "goal", "team_name_ar": "برشلونة"},
        ]
    }
    article = generate_blogger_article(match, stage="post_match")
    assert "أهداف وملخص مباراة ريال مدريد وبرشلونة" in article["title"]
    assert "iframe" in article["content"]
    assert "فينيسيوس" in article["content"]
    assert "أهداف اليوم" in article["labels"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_article_generator.py`  
Expected: FAIL (argument `stage` or highlight embed missing)

- [ ] **Step 3: Implement post-match highlights & 800+ word tactical template in `article_generator.py` and top 3–5 filter in `auto_blogger_publisher.py`**

Support `stage="pre_match"` (stream link + Schema.org + lineups) and `stage="post_match"` (video player embed + goals timeline + tactical review + poll widget). Cap daily matches processed to top 5 in `get_top_trending_matches(limit=5)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_article_generator.py`  
Expected: PASS

- [ ] **Step 5: Verify all pytest tests pass**

Run: `.\.venv\Scripts\python.exe -m pytest`  
Expected: PASS with 0 failures

---

### Task 2: Static Matches JSON Stream Exporter

**Files:**
- Create: `scripts/export_static_streams.py`
- Test: `tests/test_static_stream_exporter.py`

**Interfaces:**
- Consumes: `create_catalog(now).fixture_map(now)`
- Produces: `frontend/public/data/matches.json` containing normalized match list with active stream servers, channels, and kickoff times.

- [ ] **Step 1: Write failing test for `export_static_streams`**

```python
def test_export_static_streams_generates_valid_json(tmp_path):
    output_path = tmp_path / "matches.json"
    count = export_static_matches_json(target_path=output_path)
    assert count >= 0
    assert output_path.exists()
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert "matches" in data
    assert "updated_at" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_static_stream_exporter.py`  
Expected: FAIL (module not found)

- [ ] **Step 3: Implement `export_static_matches_json` in `scripts/export_static_streams.py`**

Write a script that reads today's fixtures and discovered stream servers, structures them cleanly into a JSON format matching what `frontend/src/App.jsx` expects, and writes to `frontend/public/data/matches.json`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_static_stream_exporter.py`  
Expected: PASS

---

### Task 3: Refactor React Frontend to Pure Stream Cinema SPA

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/lib/api.js`
- Modify: `frontend/src/components/StreamPlayerContainer.jsx`
- Modify: `frontend/src/components/MatchDetailHybrid.jsx`
- Test: `frontend/src/AppStreamCinema.test.jsx`

**Interfaces:**
- Consumes: `/data/matches.json` (static fetch) + direct public polling for live minutes/scores.
- Produces: Pure Stream Cinema UI without dead admin or serverless errors, featuring the VIP 4K Server button and floating Blogger return link.

- [ ] **Step 1: Write failing test for pure stream cinema mode**

```jsx
it("loads matches from static data and provides floating Blogger Hub return link", async () => {
  render(<App />);
  const returnLinks = await screen.findAllByText(/الموقع الرئيسي \(بلوجر\)/);
  expect(returnLinks.length).toBeGreaterThan(0);
  expect(screen.queryByTestId("admin-panel-toggle")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test` (with Node in PATH)  
Expected: FAIL (`admin-panel-toggle` still found)

- [ ] **Step 3: Refactor `App.jsx` and `api.js` for pure stream cinema**

- Point `fetchTodayMatches` to `/data/matches.json` with fallback.
- Remove `AdminPanel` import and toggle button.
- Maintain status filter chips (الكل, مباشر الآن, لم تبدأ, انتهت).
- Maintain floating Blogger Hub return header and footer.
- Ensure `StreamPlayerContainer` renders VIP 4K Smartlink tab.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm run test`  
Expected: PASS

- [ ] **Step 5: Build production bundle with Vite**

Run: `npm run build`  
Expected: PASS with clean `dist/` output

---

### Task 4: Serverless GitHub Actions Cron Workflow

**Files:**
- Create: `.github/workflows/sync_and_publish.yml`
- Test: `tests/test_github_workflow_syntax.py`

**Interfaces:**
- Consumes: GitHub Secrets: `BLOGGER_CLIENT_SECRETS`, `BLOGGER_BLOG_ID`, `CLOUDFLARE_API_TOKEN`.
- Produces: Scheduled execution every 20 minutes (`*/20 * * * *`) that updates `frontend/public/data/matches.json` and runs Blogger publisher.

- [ ] **Step 1: Write failing test for workflow file existence and YAML validity**

```python
def test_sync_and_publish_workflow_valid():
    wf_path = Path(".github/workflows/sync_and_publish.yml")
    assert wf_path.exists()
    content = wf_path.read_text(encoding="utf-8")
    assert "schedule" in content
    assert "cron" in content
    assert "export_static_streams" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_github_workflow_syntax.py`  
Expected: FAIL (file does not exist)

- [ ] **Step 3: Create `.github/workflows/sync_and_publish.yml`**

Include:
- Schedule cron `*/20 * * * *` and `workflow_dispatch`.
- Setup Python 3.12.
- Install dependencies (`pip install -r requirements.txt`).
- Run `scripts/export_static_streams.py`.
- Run `scripts/auto_blogger_publisher.py`.
- Auto-commit updated `matches.json` to the repo.
- Deploy `frontend/dist` to Cloudflare Pages via `cloudflare/pages-action` or GitHub Pages.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_github_workflow_syntax.py`  
Expected: PASS

---

### Task 5: End-to-End Suite Verification & Documentation

**Files:**
- Create: `docs/SERVERLESS_SETUP.md` (Step-by-step guide for setting up Cloudflare Pages and GitHub repository secrets).
- Verify: All Vitest and Pytest test suites.

- [ ] **Step 1: Run complete Vitest suite**

Run: `npm run test`  
Expected: 100% PASS

- [ ] **Step 2: Run complete Pytest suite**

Run: `.\.venv\Scripts\python.exe -m pytest`  
Expected: 100% PASS (175+ tests passing, 0 failures)

- [ ] **Step 3: Generate production build**

Run: `npm run build`  
Expected: PASS

- [ ] **Step 4: Write `docs/SERVERLESS_SETUP.md`**

Provide crystal-clear instructions for:
- Creating the public GitHub repo and pushing code.
- Adding secrets (`BLOGGER_BLOG_ID`, `CLOUDFLARE_API_TOKEN`).
- Connecting Cloudflare Pages for instant automatic deployment.
