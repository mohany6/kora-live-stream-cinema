# AlbaPlayer Live Stream Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically link televised matches to verified AlbaPlayer multi-server live video streams (`https://24.shootinggames1.com/albaplayer/{slug}/?serv={n}`) inside the interactive Match Center, strictly activated 30 minutes before kickoff and during live matches.

**Architecture:** A `ChannelStreamMapper` normalizes Arabic/English TV channel names into verified AlbaPlayer channel slugs (`bein-sports-hd-1..9`, `bein-sports-xtra-1..2`). `PriorityResolver.resolve()` evaluates match lifecycle state and timing (active only if `is_live` or `now >= kickoff_time - 30min` and not `FINISHED`), hydrating `StreamServer` embeds on-the-fly without polluting database snapshots. `StreamPlayerContainer.jsx` embeds the player in a sandboxed iframe with `referrerPolicy="no-referrer"`.

**Tech Stack:** Python 3.12 (FastAPI, Pydantic v2, Pytest), React 18 (Vite, Vitest, Testing Library).

**Spec:** `docs/superpowers/specs/2026-11-25-albaplayer-stream-integration-design.md`

## Global Constraints

- **DMCA / Origin Safety:** Never host raw video stream files on origin or tunnel; embed via sandboxed iframe with `referrerPolicy="no-referrer"`.
- **Admin Priority:** Admin override streams must always take 100% precedence over automated channel streams.
- **Timing Gate:** Automatic stream hydration must remain inactive until exactly 30 minutes prior to kickoff, and deactivate upon match finish (`FINISHED`).
- **Verified Slugs Only:** Only map verified upstream slugs (`bein-sports-hd-{n}`, `bein-sports-xtra-{n}`). Unmapped channels return empty list (`[]`) to display the clean placeholder.
- **Test Integrity:** Pytest (139/139) and Vitest (50/50) suites must remain 100% green.

## Review Focus

1. **Unknown or Untelevised Channels:** Matches with unknown channels or `channel=None` must return `[]` and not crash or produce invalid 404 URLs.
2. **Timezone Accuracy in Timing Gate:** Kickoff comparison must compare UTC/aware datetimes correctly against `now` without naive-vs-aware `TypeError`.
3. **Postponed Matches:** Matches with status `POSTPONED` must not hydrate automatic live streams.
4. **Admin Empty Stream Override:** If an admin explicitly overrides a match with an empty stream list (`stream_servers=[]`), the resolver must not override it with automated AlbaPlayer streams.
5. **Iframe Sandbox Security:** The iframe in `StreamPlayerContainer.jsx` must include `allow-forms allow-same-origin allow-scripts` without allowing top navigation.

---

### Task 1: Implement `ChannelStreamMapper` in Domain Resolver

**Files:**
- Modify: `src/live_score/domain/resolver.py`
- Test: `tests/live_score/test_resolver.py`

**Interfaces:**
- Produces: `ChannelStreamMapper.normalize_slug(channel_name: str) -> Optional[str]`
- Produces: `ChannelStreamMapper.get_servers(channel_name: str) -> list[StreamServer]`

- [ ] **Step 1: Write the failing tests for `ChannelStreamMapper`**

In `tests/live_score/test_resolver.py`:
```python
def test_channel_stream_mapper_be_in_sports():
    from live_score.domain.resolver import ChannelStreamMapper
    assert ChannelStreamMapper.normalize_slug("beIN SPORTS 1 HD") == "bein-sports-hd-1"
    assert ChannelStreamMapper.normalize_slug("بي ان سبورت 2") == "bein-sports-hd-2"
    assert ChannelStreamMapper.normalize_slug("beIN SPORTS XTRA 1") == "bein-sports-xtra-1"
    assert ChannelStreamMapper.normalize_slug("اكسترا 2") == "bein-sports-xtra-2"
    assert ChannelStreamMapper.normalize_slug("Unknown Channel") is None

    servers = ChannelStreamMapper.get_servers("beIN SPORTS 1 HD")
    assert len(servers) == 2
    assert servers[0].url == "https://24.shootinggames1.com/albaplayer/bein-sports-hd-1/?serv=0"
    assert servers[1].url == "https://24.shootinggames1.com/albaplayer/bein-sports-hd-1/?serv=1"
    assert servers[0].type == "iframe"
    assert "allow-scripts" in servers[0].sandbox
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest.exe tests/live_score/test_resolver.py::test_channel_stream_mapper_be_in_sports -v`
Expected: FAIL with `ImportError: cannot import name 'ChannelStreamMapper'`

- [ ] **Step 3: Implement `ChannelStreamMapper` in `src/live_score/domain/resolver.py`**

Add `ChannelStreamMapper` class with regex normalization for beIN Sports 1-9 and XTRA 1-2, producing 2 `StreamServer` instances (`serv=0`, `serv=1`).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest.exe tests/live_score/test_resolver.py::test_channel_stream_mapper_be_in_sports -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/live_score/domain/resolver.py tests/live_score/test_resolver.py
git commit -m "feat: implement ChannelStreamMapper for AlbaPlayer channels"
```

---

### Task 2: Implement Lifecycle Timing Gate & Auto-Hydration in `PriorityResolver`

**Files:**
- Modify: `src/live_score/domain/resolver.py`
- Test: `tests/live_score/test_resolver.py`

**Interfaces:**
- Consumes: `ChannelStreamMapper.get_servers(channel_name: str) -> list[StreamServer]`
- Produces: `should_hydrate_channel_stream(match: Match, now: Optional[datetime] = None, window_minutes: int = 30) -> bool`
- Modifies: `PriorityResolver.resolve(api_match, scraped_match, admin_override, now=None) -> Match`

- [ ] **Step 1: Write the failing tests for timing gate and resolver hydration**

In `tests/live_score/test_resolver.py`:
```python
def test_priority_resolver_timing_gate_and_hydration(sample_teams, sample_league):
    from live_score.domain.resolver import PriorityResolver, should_hydrate_channel_stream
    home, away = sample_teams
    now = datetime(2026, 11, 25, 18, 0, tzinfo=timezone.utc)

    # 1. Match in future (> 30 mins) -> Not hydrated
    future_match = Match(
        id="m_future",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.SCHEDULED,
        kickoff_time=datetime(2026, 11, 25, 20, 0, tzinfo=timezone.utc),
        channel="beIN SPORTS 1 HD",
    )
    assert should_hydrate_channel_stream(future_match, now=now) is False
    res_future = PriorityResolver.resolve(api_match=future_match, now=now)
    assert len(res_future.stream_servers) == 0

    # 2. Match within 30 mins -> Hydrated
    imminent_match = Match(
        id="m_imminent",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.SCHEDULED,
        kickoff_time=datetime(2026, 11, 25, 18, 20, tzinfo=timezone.utc),
        channel="beIN SPORTS 1 HD",
    )
    assert should_hydrate_channel_stream(imminent_match, now=now) is True
    res_imminent = PriorityResolver.resolve(api_match=imminent_match, now=now)
    assert len(res_imminent.stream_servers) == 2
    assert "albaplayer" in res_imminent.stream_servers[0].url

    # 3. Match IN_PLAY -> Hydrated
    live_match = Match(
        id="m_live",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=datetime(2026, 11, 25, 17, 30, tzinfo=timezone.utc),
        channel="beIN SPORTS 2 HD",
    )
    assert should_hydrate_channel_stream(live_match, now=now) is True
    res_live = PriorityResolver.resolve(api_match=live_match, now=now)
    assert len(res_live.stream_servers) == 2

    # 4. Match FINISHED -> Not hydrated
    finished_match = Match(
        id="m_fin",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.FINISHED,
        kickoff_time=datetime(2026, 11, 25, 16, 0, tzinfo=timezone.utc),
        channel="beIN SPORTS 1 HD",
    )
    assert should_hydrate_channel_stream(finished_match, now=now) is False
    res_fin = PriorityResolver.resolve(api_match=finished_match, now=now)
    assert len(res_fin.stream_servers) == 0

    # 5. Admin override takes precedence even if empty
    admin_match = Match(
        id="m_admin",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=datetime(2026, 11, 25, 17, 30, tzinfo=timezone.utc),
        channel="beIN SPORTS 1 HD",
        is_admin_override=True,
        stream_servers=[],
    )
    res_admin = PriorityResolver.resolve(api_match=live_match, admin_override=admin_match, now=now)
    assert len(res_admin.stream_servers) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest.exe tests/live_score/test_resolver.py::test_priority_resolver_timing_gate_and_hydration -v`
Expected: FAIL

- [ ] **Step 3: Implement timing gate & resolver auto-hydration in `src/live_score/domain/resolver.py`**

- Add `should_hydrate_channel_stream`.
- In `PriorityResolver.resolve`, accept optional `now: Optional[datetime] = None`.
- When `not resolved.stream_servers and resolved.channel and not admin_override`:
  - If `should_hydrate_channel_stream(resolved, now=now)`:
    - Attach `ChannelStreamMapper.get_servers(resolved.channel)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest.exe tests/live_score/test_resolver.py::test_priority_resolver_timing_gate_and_hydration -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/live_score/domain/resolver.py tests/live_score/test_resolver.py
git commit -m "feat: gate AlbaPlayer stream hydration to 30m before kickoff and live matches"
```

---

### Task 3: Verify API Presenter Integration & Frontend Sandbox Attributes

**Files:**
- Modify: `src/live_score/api/presenters.py`
- Modify: `frontend/src/components/StreamPlayerContainer.jsx`
- Test: `frontend/src/components/__tests__/StreamPlayerContainer.test.jsx`

**Interfaces:**
- Consumes: `PriorityResolver.resolve`
- Frontend verifies: `<iframe sandbox="allow-forms allow-same-origin allow-scripts" referrerPolicy="no-referrer" ... />`

- [ ] **Step 1: Write test in frontend for AlbaPlayer iframe attributes**

In `frontend/src/components/__tests__/StreamPlayerContainer.test.jsx`:
```javascript
it("renders AlbaPlayer iframe with allow-forms sandbox and no-referrer policy", () => {
  const albaServers = [
    {
      id: "alba_1",
      server_name: "سيرفر 1 - AlbaPlayer",
      url: "https://24.shootinggames1.com/albaplayer/bein-sports-hd-1/?serv=0",
      type: "iframe",
      sandbox: "allow-forms allow-same-origin allow-scripts",
      is_active: true,
    },
  ];
  render(<StreamPlayerContainer servers={albaServers} channel="beIN SPORTS 1 HD" />);
  const iframe = screen.getByTestId("stream-iframe");
  expect(iframe).toHaveAttribute("src", "https://24.shootinggames1.com/albaplayer/bein-sports-hd-1/?serv=0");
  expect(iframe).toHaveAttribute("sandbox", expect.stringContaining("allow-forms"));
  expect(iframe).toHaveAttribute("referrerPolicy", "no-referrer");
});
```

- [ ] **Step 2: Run frontend test to verify current status**

Run: `node.exe node_modules/vitest/vitest.mjs run frontend/src/components/__tests__/StreamPlayerContainer.test.jsx`

- [ ] **Step 3: Update `StreamPlayerContainer.jsx` & `presenters.py`**

- In `StreamPlayerContainer.jsx`, ensure `DEFAULT_SANDBOX` includes `allow-forms allow-same-origin allow-scripts allow-presentation` and `referrerPolicy="no-referrer"` is always preserved.
- In `src/live_score/api/presenters.py`, pass `now=None` into `PriorityResolver.resolve` to let it evaluate current UTC time during API response construction.

- [ ] **Step 4: Run frontend and backend tests to verify pass**

Run:
```bash
node.exe node_modules/vitest/vitest.mjs run
.venv\Scripts\pytest.exe -q
```
Expected: PASS (Vitest 50/50, Pytest 139/139).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/StreamPlayerContainer.jsx frontend/src/components/__tests__/StreamPlayerContainer.test.jsx src/live_score/api/presenters.py
git commit -m "feat: support AlbaPlayer sandbox and verify presenter resolution"
```

---

### Task 4: Full End-to-End Verification & Live Test

**Files:**
- Test: All suites and live endpoint check

- [ ] **Step 1: Run complete Pytest test suite**

Run: `.venv\Scripts\pytest.exe -q`
Expected: 139+ passed (0 failures).

- [ ] **Step 2: Run complete Vitest test suite**

Run: `node.exe node_modules/vitest/vitest.mjs run`
Expected: 50+ passed (0 failures).

- [ ] **Step 3: Verify live API endpoint with a test match**

Verify that a match starting in 15 minutes with channel `beIN SPORTS 1 HD` returns `stream_servers` populated with AlbaPlayer `serv=0` and `serv=1`.
Verify that opening the match in the platform player displays the working iframe and server switcher pills.

- [ ] **Step 4: Final commit**

```bash
git commit --allow-empty -m "chore: verify AlbaPlayer integration passes 100% of test suites"
```
