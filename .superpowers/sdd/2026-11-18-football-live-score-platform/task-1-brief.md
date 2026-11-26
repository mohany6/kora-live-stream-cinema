### Task 1: Core Domain Models & Priority Data Resolver

**Files:**
- Create: `src/live_score/domain/models.py`
- Create: `src/live_score/domain/resolver.py`
- Test: `tests/live_score/test_resolver.py`

**Interfaces:**
- Produces: `Match`, `Team`, `League`, `StreamServer`, `MatchEvent`, `LineupPlayer`, `MatchDetail`, `MatchStatus`
- Produces: `PriorityResolver.resolve(api_match: Optional[Match], scraped_match: Optional[Match], admin_override: Optional[Match]) -> Match`
- Produces: `TeamAliasMatcher.match_team(arabic_name: str) -> Optional[str]`

**Global Constraints & Spec Requirements:**
- MatchStatus enum: `SCHEDULED`, `IN_PLAY`, `HALFTIME`, `EXTRA_TIME`, `PENALTIES`, `FINISHED`, `POSTPONED`
- Priority order: `Admin Override` > `Sports API / Open Backend` > `Scraper Ingestion`
- TeamAliasMatcher must normalize common Arabic names to official standard team names (e.g., `تشيلسي` -> `Chelsea`, `ريال مدريد` -> `Real Madrid`, `ليفربول` -> `Liverpool`, `باريس سان جيرمان` -> `Paris Saint-Germain`)
- Player names on lineup must remain in English/Latin characters (Option B), competition copy in Arabic.

- [x] **Step 1: Write the failing test for PriorityResolver and TeamAliasMatcher**
Write comprehensive unit tests in `tests/live_score/test_resolver.py` testing:
1. Admin override taking full precedence over API and scraper updates.
2. API taking precedence over scraper updates when no admin override is present.
3. Stream servers from scraper being merged when API match has no stream servers.
4. TeamAliasMatcher resolving common Arabic names and handling unknown names gracefully.

- [x] **Step 2: Run test to verify it fails**
Run: `.\venv\Scripts\pytest.exe tests/live_score/test_resolver.py -v`
Expected: FAIL with module import / definition error.

- [x] **Step 3: Implement domain models and resolver logic**
Implement `src/live_score/domain/models.py` using Pydantic v2.
Implement `src/live_score/domain/resolver.py` with `PriorityResolver` and `TeamAliasMatcher`.

- [x] **Step 4: Run test to verify it passes**
Run: `.\venv\Scripts\pytest.exe tests/live_score/test_resolver.py -v`
Expected: PASS with pristine output.
