# Task 1 Report: Core Domain Models & Priority Data Resolver

**Date:** 2026-11-18  
**Status:** Completed (DONE)  
**Task ID:** Task 1  
**Project:** Arabic Football Live Score & Streaming Platform  

---

## 1. Overview & Objectives
Task 1 establishes the core domain entities and priority resolution engine for the Arabic Football Live Score platform:
- Implemented strongly-typed Pydantic v2 domain schemas modeling teams, leagues, streaming servers, match events, lineups, and match aggregations.
- Enforced the 3-tier data precedence hierarchy: `Admin Override > Sports API / Open Backend > Scraper Ingestion`.
- Designed and verified `TeamAliasMatcher` to normalize scraped Arabic club names (diacritics, prefix stripping, alef/taa normalization) to official standard team names.
- Followed Test-Driven Development (TDD): authored failing tests, verified collection/import failure, implemented the models and resolver, and confirmed 100% test passage.

---

## 2. Files Created & Modified

### Created Files
- `src/live_score/__init__.py`: Package entrypoint for the live score system.
- `src/live_score/domain/__init__.py`: Domain package exports exposing models and resolver utilities.
- `src/live_score/domain/models.py`: Pydantic v2 schemas:
  - `MatchStatus`: Enum (`SCHEDULED`, `IN_PLAY`, `HALFTIME`, `EXTRA_TIME`, `PENALTIES`, `FINISHED`, `POSTPONED`).
  - `Team`: Arabic display name, official English standard name, logo URL.
  - `League`: Competition name (AR/EN), round info, logo URL.
  - `StreamServer`: Stream embeds/HLS URLs, server names, active flag, quality indicators.
  - `MatchEvent`: Timeline event items (goals, yellow/red cards, substitutions, VAR decisions).
  - `LineupPlayer`: Pitch player model adhering to Option B (Latin/English characters).
  - `Match`: Core match entity with scores, timing ticker, `is_live` property, and admin override flags.
  - `MatchDetail`: Hybrid match center aggregate containing match, pitch lineups, and match statistics.
- `src/live_score/domain/resolver.py`:
  - `PriorityResolver`: Resolves matches using `Admin Override > Sports API > Scraped Streams`. Preserves existing stream servers during admin score overrides and merges unique stream links.
  - `TeamAliasMatcher`: Comprehensive Arabic alias normalization engine with pre-compiled European/Arab clubs mapping and dynamic alias registration.
- `tests/live_score/test_resolver.py`: 14 unit test cases covering validation, admin precedence, API precedence, server merging, fallbacks, Arabic text normalization, and graceful handling of unknown entities.

### Modified Files / Configuration
- `pytest.ini`: Configured `pythonpath = . src` for automated test discovery and execution.
- `conftest.py` & `tests/conftest.py`: Added root and `src` path verification for pytest execution.

---

## 3. Implementation Details

### Priority Resolution Logic
`PriorityResolver.resolve(api_match, scraped_match, admin_override) -> Match`:
1. **Admin Override Present:** Full precedence. If admin override does not supply stream servers (e.g. emergency score fix only), candidate stream servers from API and Scraper are retained without data loss. `is_admin_override` is strictly set to `True`.
2. **API Present (No Admin Override):** API takes precedence for score, status, and match clock. Scraper stream servers are merged (deduplicating identical URLs). Broadcast metadata (channel, commentator) is enriched from scraper if absent from API.
3. **Scraper Fallback:** When only scraped data exists, it acts as the primary source with `is_admin_override = False`.
4. **Validation:** Raises `ValueError` if all inputs are `None`.

### Arabic Text Normalization & Alias Matching
`TeamAliasMatcher.match_team(arabic_name) -> Optional[str]`:
- **Diacritics Removal:** Strips all Arabic tashkeel (`[\u064B-\u065F\u0670]`).
- **Alef Normalization:** Maps `[إأآٱ]` to standard bare `ا`.
- **Yaa Normalization:** Maps `ى` to `ي`.
- **Prefix Stripping:** Strips generic club prefixes (`^(نادي|فريق)\s+`).
- **Taa Marbouta:** Normalized tolerance (`ة` -> `ه`).
- **Suffix Fallback:** Handles country/region qualifiers (e.g. `المصري`, `السعودي`, `الرياضي`).
- **Graceful Failure:** Returns `None` for unmapped or empty strings without breaking ingestion.
- **Dynamic Registration:** Allows runtime alias learning via `TeamAliasMatcher.register_alias(...)`.

---

## 4. Verification & Test Execution
Tests were run via:
```powershell
.\venv\Scripts\pytest.exe tests/live_score/test_resolver.py -v
```

### Results
```text
tests/live_score/test_resolver.py::test_domain_models_creation PASSED    [  7%]
tests/live_score/test_resolver.py::test_match_detail_with_lineup_and_events PASSED [ 14%]
tests/live_score/test_resolver.py::test_priority_resolver_admin_overrides_api_and_scraper PASSED [ 21%]
tests/live_score/test_resolver.py::test_priority_resolver_api_takes_precedence_over_scraper PASSED [ 28%]
tests/live_score/test_resolver.py::test_priority_resolver_merges_stream_servers_when_api_has_none PASSED [ 35%]
tests/live_score/test_resolver.py::test_priority_resolver_merges_unique_servers_when_both_have_streams PASSED [ 42%]
tests/live_score/test_resolver.py::test_priority_resolver_single_source_fallbacks PASSED [ 50%]
tests/live_score/test_resolver.py::test_team_alias_matcher_common_teams PASSED [ 57%]
tests/live_score/test_resolver.py::test_team_alias_matcher_normalization_and_diacritics PASSED [ 64%]
tests/live_score/test_resolver.py::test_team_alias_matcher_unknown_and_empty_graceful PASSED [ 71%]
tests/live_score/test_resolver.py::test_team_alias_matcher_custom_registration PASSED [ 78%]
tests/live_score/test_resolver.py::test_match_status_enum_values PASSED  [ 85%]
tests/live_score/test_resolver.py::test_match_is_live_property PASSED    [ 92%]
tests/live_score/test_resolver.py::test_priority_resolver_admin_preserves_streams_when_admin_servers_empty PASSED [100%]

============================= 14 passed in 0.58s ==============================
```

---

## 5. Conclusion
Task 1 is complete and verified with pristine test output. The domain layer is ready to support Task 2 (Upstream Ingestion Adapters) and Task 3 (Admin CMS & Match REST APIs).
