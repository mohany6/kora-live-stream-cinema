# Blogger Hub, High-Yield Adsterra Monetization, Anti-Takedown Architecture & Homepage Content Upgrades Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the football live score platform into a Blogger-centric, anti-takedown protected live hub with all 6 Adsterra ad units fully monetized, rich homepage SEO/dwell-time upgrades, bidirectional Arabic team alias resolution, and automated self-healing Cloudflare tunnel discovery.

**Architecture:** Blogger (`kora-live-to.blogspot.com`) serves as the permanent, legal, and SEO-rich public anchor with high dwell time. The local FastAPI service serves clean, proxied streaming embeds via Cloudflare Tunnel. The theme dynamically discovers active tunnel URLs via a same-origin Blogger feed bridge, hydrates stream players in memory on user interaction, and renders full Adsterra ads (Popunder with 20m persistent cap, SocialBar, 728x90/320x50 billboard, 160x600 skyscrapers, in-feed native ads, and rotated VIP Smartlinks).

**Tech Stack:** Python 3.12, FastAPI, pytest, Blogger Theme XML Engine, JavaScript (ES6), Adsterra Publisher SDK, BeautifulSoup/RegEx, ZoneInfo.

**Spec:** `docs/superpowers/specs/2026-11-25-blogger-hub-monetization-redesign-design.md`

## Global Constraints
- Target repository: `C:\Users\Mohany\Desktop\football-live-score-platform`.
- Adsterra publisher account: ID `6226474` for domain `kora-live-to.blogspot.com`.
- Python virtual environment: `.\.venv\Scripts\python.exe`.
- All backend tests run with: `Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform"; .\.venv\Scripts\python.exe -m pytest`.
- Zero Cumulative Layout Shift (CLS): Explicit minimum height styling for all ad containers.
- Googlebot Cleanliness: Raw article HTML must contain no direct pirated video iframes or hardcoded `.m3u8` links.
- No popup spam: Popunder strictly capped at 1 occurrence per 20 minutes per visitor via `localStorage`.

## Review Focus
1. **Bidirectional Match Misses**: Arabic club names scraped from upstream (e.g. `غلطة سراي`, `ريال بيتيس`, `سيلتا فيغو`) must map to their canonical standard names, and English names must map back to clean Arabic.
2. **VideoJS Inadvertent Stripping**: Video player initialization (`const player = videojs(...)`) must not be stripped by ad removal regexes.
3. **Database Flusher Thread Leak**: `AdminStore.close()` must cleanly signal `_stop_flusher`, flush visits, and close the SQLite connection without raising `ProgrammingError`.
4. **Timezone DST Shift**: Kickoff formatting in Cairo must account for Egyptian Daylight Saving Time without fixed `+2` hour offsets.
5. **Popunder Cross-Tab Abuse**: Opening multiple tabs or navigating pages must not trigger repeated popunders if visited within 20 minutes.

---

### Task 1: Bidirectional Arabic Team Alias Resolution

**Files:**
- Modify: `src/live_score/domain/resolver.py:219-246,684-697`
- Test: `tests/live_score/test_resolver_bidirectional.py`

**Interfaces:**
- Consumes: `TeamAliasMatcher._BASE_ALIASES`, `TeamAliasMatcher._CANONICAL_ARABIC`
- Produces: `TeamAliasMatcher.match_team(name: str) -> Optional[str]` and `TeamAliasMatcher.get_arabic_name(name: str) -> Optional[str]`

- [ ] **Step 1: Write the failing tests**

Create `tests/live_score/test_resolver_bidirectional.py`:
```python
from live_score.domain.resolver import TeamAliasMatcher

def test_match_team_inverted_canonical():
    assert TeamAliasMatcher.match_team("غلطة سراي") == "Galatasaray"
    assert TeamAliasMatcher.match_team("ريال بيتيس") == "Real Betis"
    assert TeamAliasMatcher.match_team("سيلتا فيغو") == "Celta Vigo"
    assert TeamAliasMatcher.match_team("برايتون") == "Brighton & Hove Albion"
    assert TeamAliasMatcher.match_team("فولفسبورغ") == "VfL Wolfsburg"

def test_get_arabic_name_fallback_base():
    assert TeamAliasMatcher.get_arabic_name("Sabah FK") == "صباح إف كيه"
    assert TeamAliasMatcher.get_arabic_name("Viking FK") == "فايكنغ"
    assert TeamAliasMatcher.get_arabic_name("Slavia Prague") == "سلافيا براغ"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform"; .\.venv\Scripts\python.exe -m pytest tests/live_score/test_resolver_bidirectional.py`
Expected: FAIL (returns `None` for Galatasaray, Real Betis, Sabah FK, etc.)

- [ ] **Step 3: Implement bidirectional matching in `src/live_score/domain/resolver.py`**

1. In `_get_normalized_base()`:
   After initializing `base` from `_BASE_ALIASES`, iterate over `_CANONICAL_ARABIC.items()`:
   ```python
   for en_name, ar_name in cls._CANONICAL_ARABIC.items():
       norm_ar = cls.normalize_text(ar_name)
       if norm_ar not in base:
           base[norm_ar] = en_name
   ```
2. In `get_arabic_name(cls, standard_name: Optional[str]) -> Optional[str]`:
   If `standard_name` is not found in `_CANONICAL_ARABIC`, check reverse lookup in `_BASE_ALIASES` or add missing clubs.
3. Reset `_NORMALIZED_BASE = None` when updating aliases to bust stale caches.

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform"; .\.venv\Scripts\python.exe -m pytest tests/live_score/test_resolver_bidirectional.py`
Expected: PASS

- [ ] **Step 5: Run existing resolver tests to ensure zero regressions**

Run: `Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform"; .\.venv\Scripts\python.exe -m pytest tests/live_score/test_resolver.py`
Expected: 16 passed.

- [ ] **Step 6: Commit changes**

```powershell
git add src/live_score/domain/resolver.py tests/live_score/test_resolver_bidirectional.py
git commit -m "fix(resolver): add bidirectional canonical team alias matching"
```

---

### Task 2: API & Storage Defect Fixes & Timezone Handling

**Files:**
- Modify: `src/live_score/api/store.py:75-80,779-783`
- Modify: `src/live_score/api/public_routes.py:235-245`
- Modify: `src/live_score/domain/article_generator.py:41-51`
- Modify: `scripts/auto_blogger_publisher.py:53-65`
- Test: `tests/live_score/test_store_flusher.py`
- Test: `tests/live_score/test_player_proxy.py`

**Interfaces:**
- Consumes: `AdminStore.close()`, `stream_player_proxy`, `score_match_trend`
- Produces: Safe DB shutdown, uncorrupted video player HTML, timezone-aware kickoff formatting

- [ ] **Step 1: Write the failing tests**

Create `tests/live_score/test_store_flusher.py`:
```python
import tempfile
from pathlib import Path
from live_score.api.store import AdminStore

def test_store_close_stops_flusher():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        store = AdminStore(db_path)
        store.record_visit("visitor1", "/test", "desktop", "")
        store.close()
        assert store._stop_flusher.is_set()
        assert not store._flusher_thread.is_alive()
```

Create `tests/live_score/test_player_proxy.py`:
```python
from live_score.api.public_routes import stream_player_proxy

def test_videojs_player_preserved_in_proxy():
    # Verify regex does not strip core player initialization
    sample_html = """
    <html><head></head><body>
      <script>const player = videojs('video-player', { autoplay: true });</script>
      <script>aclib.runPop({ zoneId: '123' });</script>
    </body></html>
    """
    import re
    # Strip popunder
    cleaned = re.sub(r"<script[^>]*>\s*aclib\.runPop.*?</script>", "", sample_html, flags=re.DOTALL | re.IGNORECASE)
    assert "videojs('video-player'" in cleaned
    assert "aclib.runPop" not in cleaned
```

- [ ] **Step 2: Run test to verify it passes/fails**

Run: `Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform"; .\.venv\Scripts\python.exe -m pytest tests/live_score/test_store_flusher.py tests/live_score/test_player_proxy.py`

- [ ] **Step 3: Fix `store.py`, `public_routes.py`, `article_generator.py`, and `auto_blogger_publisher.py`**

1. In `src/live_score/api/store.py`:
   Remove redundant duplicate `close(self)` method at line 779. Ensure line 75 `close(self)` is the sole definition and joins `_flusher_thread` gracefully.
2. In `src/live_score/api/public_routes.py`:
   Remove the regex that targets `const player = videojs(` at line 240. Only strip popunder / aclib and ConsoleBan scripts.
3. In `src/live_score/domain/article_generator.py`:
   Replace hardcoded `+ timedelta(hours=2)` with `from zoneinfo import ZoneInfo`:
   ```python
   cairo_dt = kickoff_dt.astimezone(ZoneInfo("Africa/Cairo"))
   ksa_dt = kickoff_dt.astimezone(ZoneInfo("Asia/Riyadh"))
   utc_dt = kickoff_dt.astimezone(timezone.utc)
   display_time = f"{ksa_dt.strftime('%H:%M')} مكة المكرمة ({cairo_dt.strftime('%H:%M')} القاهرة - {utc_dt.strftime('%H:%M')} غرينتش)"
   ```
4. In `scripts/auto_blogger_publisher.py`:
   In `score_match_trend(match_obj, target_date_str)`:
   Award +200 points for `status_val in {"IN_PLAY", "HALFTIME", "EXTRA_TIME", "PENALTIES"}`.

- [ ] **Step 4: Run tests to verify all pass**

Run: `Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform"; .\.venv\Scripts\python.exe -m pytest tests/live_score/test_store_flusher.py tests/live_score/test_player_proxy.py tests/live_score/test_store_analytics.py`
Expected: PASS

- [ ] **Step 5: Commit changes**

```powershell
git add src/live_score/api/store.py src/live_score/api/public_routes.py src/live_score/domain/article_generator.py scripts/auto_blogger_publisher.py tests/live_score/test_store_flusher.py tests/live_score/test_player_proxy.py
git commit -m "fix(api): fix store flusher cleanup, preserve videojs in proxy, and fix DST timezones"
```

---

### Task 3: Blogger Theme Redesign with Full Adsterra Units & Homepage Upgrades

**Files:**
- Modify: `scripts/build_modern_blogger_theme.py`
- Modify: `blogger_theme/kora_pro_blogger_theme.xml`
- Modify: `blogger_theme/theme_preview.html`
- Test: `tests/test_blogger_theme_ads.py`

**Interfaces:**
- Consumes: All 6 Adsterra approved tags, MULTI_DAY_DATA, CSS_STYLES
- Produces: `kora_pro_blogger_theme.xml` and `theme_preview.html` with responsive billboard, skyscrapers, native ads, popunder cap, live status chips, league carousel, and FAQ schema.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_blogger_theme_ads.py`:
```python
from pathlib import Path
from scripts.build_modern_blogger_theme import build_blogger_xml, build_preview_html

def test_theme_contains_all_adsterra_units():
    xml = build_blogger_xml()
    # Popunder with capitalhospitals
    assert "https://capitalhospitals.org/1/9d3379bfa7b20556e0328830cd7e5e7f" in xml
    # SocialBar
    assert "https://czernik.org/14/4d85a8908516d9c268b82f4a5df10c8a" in xml
    # 728x90 Billboard & 320x50 Mobile keys
    assert "6703ea03ffb309455182c593d4e6ea81" in xml
    assert "1cdf29d3af257663a92ffa6b5207a68a" in xml
    # 160x600 Skyscraper key
    assert "bee904d3f2a415fcd8e41f64598a9680" in xml
    # Native banner container
    assert "container-f1180bd1a9f13152d2247022e3f6f1b0" in xml
    # Smartlinks
    assert "budgetezy.org/4/ae626546295ba9dbdec2ea24a521084c" in xml
    assert "asiafilm.org/4/67d5c06c56eb1c96b2ff42f4dc88412e" in xml

def test_theme_contains_homepage_content_upgrades():
    xml = build_blogger_xml()
    # Live status filter chips
    assert "data-filter=\"live\"" in xml or "live-filter-chips" in xml
    # League carousel
    assert "league-filter-carousel" in xml or "data-league" in xml
    # FAQ Schema / Semantic SEO section
    assert "FAQPage" in xml
    assert "كورة لايف - جدول مباريات اليوم وبث مباشر" in xml
    # In-page stream modal
    assert "koraStreamModal" in xml or "stream-modal-overlay" in xml
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform"; .\.venv\Scripts\python.exe -m pytest tests/test_blogger_theme_ads.py`
Expected: FAIL (missing popunder, 160x600, FAQ schema, status chips)

- [ ] **Step 3: Update `scripts/build_modern_blogger_theme.py` and generate XML & Preview**

1. **Popunder & Frequency Capping**:
   Inject JS orchestrator in `<head>` that monitors `localStorage.getItem('kora_pop_ts')` and attaches single-click listener.
2. **Skyscraper 160x600 Sidebars**:
   Add fixed `.desktop-side-banner.left-gutter` and `.desktop-side-banner.right-gutter` rendered conditionally on `@media (min-width: 1320px)`.
3. **Live Status Filter Chips**:
   Add filter pills: `[الكل] [🔴 مباشر الآن] [⏳ القادمة] [🏁 المنتهية]`. Bind client-side filter logic in JS.
4. **League Navigation Carousel**:
   Add horizontal carousel with icons for Champions League, Premier League, LaLiga, Saudi Pro League, Serie A.
5. **In-Feed Native Banner**:
   Position after match card #3 in `renderMatchCards()`.
6. **Smartlink Rotation**:
   Rotate BudgetEzy and AsiaFilm on "سيرفر 2 VIP فائق السرعة" buttons.
7. **Semantic SEO Section & FAQ Accordion**:
   Add 400-word SEO text block with 4-question expandable accordion and Schema.org `FAQPage` JSON-LD.
8. **In-Page Stream Modal**:
   Add `#koraStreamModal` overlay with responsive iframe player, server switchers, and close button.
9. Run `generate_blogger_xml()` and `generate_theme_preview()` to write updated `blogger_theme/kora_pro_blogger_theme.xml` and `blogger_theme/theme_preview.html`.

- [ ] **Step 4: Run tests to verify all pass**

Run: `Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform"; .\.venv\Scripts\python.exe -m pytest tests/test_blogger_theme_ads.py tests/test_blogger_theme_build.py tests/test_blogger_theme_generator.py`
Expected: ALL PASS

- [ ] **Step 5: Commit changes**

```powershell
git add scripts/build_modern_blogger_theme.py blogger_theme/kora_pro_blogger_theme.xml blogger_theme/theme_preview.html tests/test_blogger_theme_ads.py
git commit -m "feat(theme): integrate full adsterra suite, status filters, and seo faq section"
```

---

### Task 4: Dynamic Tunnel Discovery & Post-Player In-Theme Delivery

**Files:**
- Modify: `scripts/build_modern_blogger_theme.py`
- Modify: `src/live_score/domain/article_generator.py`
- Modify: `scripts/auto_blogger_publisher.py`
- Test: `tests/test_tunnel_discovery_bridge.py`

**Interfaces:**
- Consumes: Blogger Atom feed (`/feeds/posts/default?alt=json&max-results=1`), active tunnel URL from `data/tunnel_url.txt`
- Produces: `localStorage.getItem('kora_active_tunnel')`, clean article HTML with bridge metadata and zero raw pirated iframes.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tunnel_discovery_bridge.py`:
```python
from live_score.domain.article_generator import generate_blogger_article

def test_article_generator_embeds_bridge_metadata():
    match = {
        "id": "401915378",
        "home_team": "ريال مدريد",
        "away_team": "بايرن ميونخ",
        "competition": "دوري أبطال أوروبا",
        "channel": "beIN SPORTS 1 HD",
    }
    art = generate_blogger_article(match, platform_base_url="https://active-tunnel.trycloudflare.com")
    content = art["content"]
    # Verify metadata bridge marker exists
    assert 'id="kora-stream-bridge"' in content
    assert 'data-tunnel="https://active-tunnel.trycloudflare.com"' in content
    # Verify NO raw pirated m3u8 or raw iframe in static HTML source (Googlebot safe!)
    assert ".m3u8" not in content
    assert "<iframe" not in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform"; .\.venv\Scripts\python.exe -m pytest tests/test_tunnel_discovery_bridge.py`

- [ ] **Step 3: Implement Feed Bridge and in-post player container**

1. In `src/live_score/domain/article_generator.py`:
   - Inject the invisible bridge element:
     `<div id="kora-stream-bridge" data-tunnel="{platform_base_url}" style="display:none;"></div>`.
   - Replace any static iframe with the dynamic player trigger container `<div id="kora-player-mount" data-match-id="{match_id}">...</div>`.
2. In `scripts/build_modern_blogger_theme.py`:
   - In theme JavaScript, implement `initTunnelDiscovery()`:
     ```javascript
     function initTunnelDiscovery() {
       fetch('/feeds/posts/default?alt=json&max-results=1')
         .then(function(r){ return r.json(); })
         .then(function(d){
           var entry = d.feed && d.feed.entry && d.feed.entry[0];
           if (entry && entry.content && entry.content.$t) {
             var m = entry.content.$t.match(/data-tunnel="([^"]+)"/);
             if (m && m[1]) {
               localStorage.setItem('kora_active_tunnel', m[1]);
               PLATFORM_URL = m[1];
             }
           }
         }).catch(function(){});
     }
     ```
   - In post view (`b:if cond='data:view.isPost'`), mount the responsive player container and server tabs.
3. Regenerate XML and preview files.

- [ ] **Step 4: Run tests to verify all pass**

Run: `Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform"; .\.venv\Scripts\python.exe -m pytest tests/test_tunnel_discovery_bridge.py`
Expected: PASS

- [ ] **Step 5: Commit changes**

```powershell
git add src/live_score/domain/article_generator.py scripts/build_modern_blogger_theme.py blogger_theme/kora_pro_blogger_theme.xml tests/test_tunnel_discovery_bridge.py
git commit -m "feat(bridge): implement same-origin feed bridge and safe dynamic player mount"
```

---

### Task 5: Automated Backup & Disaster Recovery Script

**Files:**
- Create: `scripts/backup_blogger_content.py`
- Test: `tests/test_backup_script.py`

**Interfaces:**
- Consumes: Public Blogger feed (`https://kora-live-to.blogspot.com/feeds/posts/default?alt=json&max-results=500`), `blogger_theme/kora_pro_blogger_theme.xml`
- Produces: `data/backups/blogger_backup_YYYY-MM-DD.json`, `data/backups/theme_backup_YYYY-MM-DD.xml`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_backup_script.py`:
```python
from pathlib import Path
from scripts.backup_blogger_content import backup_local_and_feed

def test_backup_creates_archive(tmp_path):
    theme_file = tmp_path / "test_theme.xml"
    theme_file.write_text("<xml>test</xml>", encoding="utf-8")
    backup_dir = tmp_path / "backups"
    
    res = backup_local_and_feed(
        blog_url="https://kora-live-to.blogspot.com",
        theme_path=theme_file,
        output_dir=backup_dir,
        fetch_remote=False
    )
    assert res["theme_backup"].exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform"; .\.venv\Scripts\python.exe -m pytest tests/test_backup_script.py`

- [ ] **Step 3: Implement `scripts/backup_blogger_content.py`**

- Fetch JSON feed from `https://kora-live-to.blogspot.com/feeds/posts/default?alt=json&max-results=500`.
- Save timestamped dump to `data/backups/blogger_posts_YYYY-MM-DD.json`.
- Copy current `kora_pro_blogger_theme.xml` to `data/backups/theme_backup_YYYY-MM-DD.xml`.
- Provide CLI entrypoint with `--fetch-remote` flag (default True).

- [ ] **Step 4: Run test to verify it passes**

Run: `Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform"; .\.venv\Scripts\python.exe -m pytest tests/test_backup_script.py`
Expected: PASS

- [ ] **Step 5: Commit changes**

```powershell
git add scripts/backup_blogger_content.py tests/test_backup_script.py
git commit -m "feat(backup): implement automated blogger json feed and theme backup script"
```

---

### Task 6: Full Regression Verification & Live Test Run

**Files:**
- Test: All unit and integration test suites

- [ ] **Step 1: Run the full test suite**

Run: `Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform"; .\.venv\Scripts\python.exe -m pytest -q`
Expected: 150+ passed with 0 failures.

- [ ] **Step 2: Re-generate final Blogger XML and Preview files**

Run: `Set-Location "C:\Users\Mohany\Desktop\football-live-score-platform"; .\.venv\Scripts\python.exe scripts/build_modern_blogger_theme.py`
Expected: `[✓] Ultra-Modern Blogger Theme XML successfully built.`

- [ ] **Step 3: Verify git status is clean**

Run: `git status`
Expected: Clean working tree.
