### Task 2: Upstream Ingestion Adapters (livescoreFootball client & Scraper stub)

**Files:**
- Create: `src/live_score/adapters/livescore_client.py`
- Create: `src/live_score/adapters/scraper_adapter.py`
- Create: `src/live_score/adapters/__init__.py`
- Test: `tests/live_score/test_adapters.py`

**Interfaces:**
- Consumes: `src/live_score/domain/models.py` (`Match`, `Team`, `League`, `StreamServer`, `MatchStatus`, `MatchDetail`)
- Consumes: `src/live_score/domain/resolver.py` (`TeamAliasMatcher`)
- Produces: `LiveScoreFootballClient(base_url: str, session: Optional[Any] = None)`
  - `fetch_today_matches() -> list[Match]`
  - `fetch_match_detail(match_id: str) -> Optional[MatchDetail]`
- Produces: `PortalScraperAdapter(base_url: str = "")`
  - `parse_stream_embeds(html_content: str) -> list[StreamServer]`
  - `fetch_stream_servers(home_team: str, away_team: str) -> list[StreamServer]`

**Global Constraints & Spec Requirements:**
- Open-Source Provider Integration: Interacts with the `rezarahiminia/livescoreFootball` REST API schema:
  - Maps upstream fields (`home_team`, `away_team`, `home_score`, `away_score`, `status`, `elapsed`, `competition`, `events`, `lineups`) to internal `Match` and `MatchDetail` schemas.
  - Normalizes team names using `TeamAliasMatcher` to attach Arabic display names when known.
- Scraper Ingestion:
  - Extracts streaming URLs from HTML embeds (`iframe` src attributes, direct `.m3u8` links, and server buttons).
  - Categorizes stream quality: `multiquality`, `hd`, `sd`, `youtube`.
  - Sandboxing: Marks all iframe streams with sandbox permissions.
  - Zero video proxying: Emits direct client-facing URLs.

- [ ] **Step 1: Write failing tests in `tests/live_score/test_adapters.py`**
Include:
1. `LiveScoreFootballClient` parsing today's matches from mock API JSON payloads into `Match` models.
2. `LiveScoreFootballClient` parsing lineups and timeline events into `MatchDetail`.
3. `PortalScraperAdapter` parsing HTML snippets containing iframes and server tabs (`سيرفر 1`, `سيرفر 2`, YouTube embeds) into `StreamServer` objects.
4. Error handling on network timeout or malformed JSON/HTML gracefully returning empty lists without unhandled exceptions.

- [ ] **Step 2: Run test to verify it fails**
Run: `.\venv\Scripts\pytest.exe tests/live_score/test_adapters.py -v`
Expected: FAIL with module import / class missing error.

- [ ] **Step 3: Implement `livescore_client.py` and `scraper_adapter.py`**
Use `requests` or `urllib` / mockable sessions.
Implement `LiveScoreFootballClient` and `PortalScraperAdapter`.

- [ ] **Step 4: Run test to verify it passes**
Run: `.\venv\Scripts\pytest.exe tests/live_score/test_adapters.py -v`
Expected: PASS with pristine output.
