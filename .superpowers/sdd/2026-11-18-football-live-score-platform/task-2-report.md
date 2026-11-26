# Task 2 Report: Upstream Ingestion Adapters (livescoreFootball client & Scraper stub)

**Date:** 2026-11-18  
**Status:** Completed (DONE)  
**Task ID:** Task 2  
**Project:** Arabic Football Live Score & Streaming Platform  

---

## 1. Overview & Objectives
Task 2 delivers the ingestion adapters connecting external football data feeds and streaming portal scrapers into our core domain:
- **`LiveScoreFootballClient`**: Integrates with the open-source `rezarahiminia/livescoreFootball` REST API schema. Maps fixtures, scores, clock tickers, competition metadata, lineups (Latin/English names adhering to Option B), and match event timelines into internal `Match` and `MatchDetail` schemas.
- **`PortalScraperAdapter`**: Parses raw HTML from live stream portals to extract server tabs (`سيرفر 1 - متعدد الجودات`, `سيرفر 2 - HD`, `سيرفر 3 - ضعيف للهواتف`, `سيرفر 4 - يوتيوب`), iframes, and direct `.m3u8` HLS streams.
- **Enforced Architectural Constraints**:
  - Direct client-facing URLs (Zero video proxying).
  - Client-side iframe sandboxing permissions (`allow-scripts allow-same-origin allow-presentation`).
  - Automatic quality categorization (`multiquality`, `hd`, `sd`, `youtube`).
  - Seamless team alias resolution via `TeamAliasMatcher` to attach authentic Arabic display names.
  - Resilient error handling on timeouts, network errors, and malformed HTML/JSON.

---

## 2. Files Created & Modified

### Created Files
- `src/live_score/adapters/__init__.py`: Adapter package exports for `LiveScoreFootballClient` and `PortalScraperAdapter`.
- `src/live_score/adapters/livescore_client.py`: Implementation of the `LiveScoreFootballClient` interacting with the open-source livescoreFootball REST API.
- `src/live_score/adapters/scraper_adapter.py`: Implementation of `PortalScraperAdapter` parsing streaming embeds, tabs, and direct HLS links.
- `tests/live_score/test_adapters.py`: 12 unit test cases validating client and scraper functionality across realistic and degraded edge cases.

### Modified Files
- `src/live_score/domain/models.py`: Added `sandbox: Optional[str] = "allow-scripts allow-same-origin allow-presentation"` to `StreamServer`.
- `src/live_score/domain/resolver.py`: Added `_CANONICAL_ARABIC` dictionary and `get_arabic_name` method to `TeamAliasMatcher` for bidirectional Arabic <-> English resolution.

---

## 3. Implementation Details

### 1. `LiveScoreFootballClient`
- **Schema Mapping**:
  - Extracts match identifier (`id`, `_id`, or UUID fallback).
  - Normalizes teams via `_resolve_team`: parses both nested objects (`{"name": "Chelsea", "logo": "..."}`) and string names (`"Chelsea"`). Matches Arabic nicknames (e.g. `البلوز` -> `Chelsea`) or resolves English names to standard Arabic display names (e.g. `Chelsea` -> `تشيلسي`).
  - Competition mapping: maps English league names (`Premier League`, `La Liga`, `Champions League`, etc.) to canonical Arabic tournament names (`الدوري الإنجليزي الممتاز`, `الدوري الإسباني`, `دوري أبطال أوروبا`).
  - Status normalization: maps diverse status strings (`LIVE`, `1H`, `2H`, `HT`, `ET`, `PEN`, `FT`, `POSTPONED`, `SCHEDULED`) to standard `MatchStatus` enums.
  - Kickoff normalization: parses ISO 8601 strings and UNIX timestamps into timezone-aware UTC `datetime` objects.
- **Match Detail, Lineups & Events**:
  - Lineups: extracts starting XI and bench players with Latin/English names (Option B), jersey numbers, and standardized positions (`GK`, `DF`, `MF`, `FW`).
  - Events: extracts timeline items (goals, yellow/red cards, substitutions, VAR checks) with minute and Arabic descriptions.
  - Stats: extracts comparative match metrics (ball possession %, shots on target, etc.).
- **Graceful Error Recovery**:
  - Handles network timeouts (`requests.exceptions.Timeout`), connection drops, HTTP 404/500, or invalid JSON, returning empty lists `[]` or `None` without unhandled exceptions.

### 2. `PortalScraperAdapter`
- **Embed & Tab Parsing**:
  - Parses streaming server tabs and buttons with `data-url`, `data-src`, `data-embed`, `data-stream`, and `href`.
  - Captures server tab display names (e.g. `سيرفر 1 - متعدد الجودات`, `سيرفر 2 - HD`, `سيرفر 3 - ضعيف للهواتف`, `سيرفر 4 - يوتيوب`).
  - Parses standalone `<iframe>` tags and direct `<video>`/`<source>` `.m3u8` streams.
- **Zero Video Proxying**:
  - Emits direct client-facing URLs without proxy wrapping. Relative URLs are resolved via `urljoin` when `base_url` is provided.
- **Iframe Sandboxing**:
  - Sets `sandbox="allow-scripts allow-same-origin allow-presentation"` on all iframe-type stream servers for client security.
- **Quality Classification**:
  - Auto-categorizes into `multiquality`, `hd`, `sd`, and `youtube` based on explicit attributes or contextual text cues (`متعدد`, `HD`, `ضعيف للهواتف`, `يوتيوب`).
- **Deduplication**:
  - Discards duplicate stream URLs across multiple tabs and active iframes, retaining the first richly-labeled server.

---

## 4. Verification & Test Execution

### Failing Test Verification (Step 2)
```text
tests\live_score\test_adapters.py:21: in <module>
    from live_score.adapters import LiveScoreFootballClient, PortalScraperAdapter
E   ModuleNotFoundError: No module named 'live_score.adapters'
```

### Passing Test Verification (Step 4)
Executed command:
```powershell
.\venv\Scripts\pytest.exe tests/live_score -v
```

### Test Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.12.16, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\Mohany\Desktop\fc27_radar_manager_project\venv\Scripts\python.exe
cachedir: .pytest_cache
PySide6 6.12.0 -- Qt runtime 6.12.0 -- Qt compiled 6.12.0
rootdir: C:\Users\Mohany\Desktop\fc27_radar_manager_project
configfile: pytest.ini
plugins: anyio-4.16.0, qt-4.5.0
collecting ... collected 26 items

tests/live_score/test_adapters.py::test_livescore_client_fetch_today_matches PASSED [  3%]
tests/live_score/test_adapters.py::test_livescore_client_fetch_today_matches_enveloped_responses PASSED [  7%]
tests/live_score/test_adapters.py::test_livescore_client_fetch_match_detail PASSED [ 11%]
tests/live_score/test_adapters.py::test_livescore_client_error_handling_timeout_and_bad_payload PASSED [ 15%]
tests/live_score/test_adapters.py::test_livescore_client_status_mapping_variations PASSED [ 19%]
tests/live_score/test_adapters.py::test_livescore_client_arabic_alias_upstream_matching PASSED [ 23%]
tests/live_score/test_adapters.py::test_portal_scraper_parse_stream_embeds PASSED [ 26%]
tests/live_score/test_adapters.py::test_portal_scraper_parse_direct_hls_stream PASSED [ 30%]
tests/live_score/test_adapters.py::test_portal_scraper_zero_video_proxying_direct_urls PASSED [ 34%]
tests/live_score/test_adapters.py::test_portal_scraper_deduplication PASSED [ 38%]
tests/live_score/test_adapters.py::test_portal_scraper_fetch_stream_servers_network PASSED [ 42%]
tests/live_score/test_adapters.py::test_portal_scraper_error_handling_timeout_and_malformed PASSED [ 46%]
tests/live_score/test_resolver.py::test_domain_models_creation PASSED    [ 50%]
tests/live_score/test_resolver.py::test_match_detail_with_lineup_and_events PASSED [ 53%]
tests/live_score/test_resolver.py::test_priority_resolver_admin_overrides_api_and_scraper PASSED [ 57%]
tests/live_score/test_resolver.py::test_priority_resolver_api_takes_precedence_over_scraper PASSED [ 61%]
tests/live_score/test_resolver.py::test_priority_resolver_merges_stream_servers_when_api_has_none PASSED [ 65%]
tests/live_score/test_resolver.py::test_priority_resolver_merges_unique_servers_when_both_have_streams PASSED [ 69%]
tests/live_score/test_resolver.py::test_priority_resolver_single_source_fallbacks PASSED [ 73%]
tests/live_score/test_resolver.py::test_team_alias_matcher_common_teams PASSED [ 76%]
tests/live_score/test_resolver.py::test_team_alias_matcher_normalization_and_diacritics PASSED [ 80%]
tests/live_score/test_resolver.py::test_team_alias_matcher_unknown_and_empty_graceful PASSED [ 84%]
tests/live_score/test_resolver.py::test_team_alias_matcher_custom_registration PASSED [ 88%]
tests/live_score/test_resolver.py::test_match_status_enum_values PASSED  [ 92%]
tests/live_score/test_resolver.py::test_match_is_live_property PASSED    [ 96%]
tests/live_score/test_resolver.py::test_priority_resolver_admin_preserves_streams_when_admin_servers_empty PASSED [100%]

============================= 26 passed in 0.61s ==============================
```

---

## 5. Conclusion
Task 2 is complete and verified with 100% test passing rate. The upstream ingestion layer is ready to feed live scores, lineups, and stream servers into Task 3 (Admin CMS & Match REST API).
