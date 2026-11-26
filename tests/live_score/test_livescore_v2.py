"""
Tests for the v2 livescoreFootball public API adapter and the TTL catalog.

The fixtures below mirror real payloads from
``https://worldcup26.ir/get/soccer`` (ESPN-style scoreboards and summaries)
without hitting the network.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import json
import threading
import sys
from typing import Any, Optional

_src_path = str(Path(__file__).resolve().parents[2] / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

import pytest

from live_score.adapters.fallback import FallbackSoccerClient
from live_score.adapters.livescore_v2 import (
    ESPN_CORE_BASE,
    FixtureRef,
    EspnSoccerClient,
    LiveScoreV2Client,
    LiveScoreV2Error,
)
from live_score.api.catalog import LiveFixturesCatalog
from live_score.domain.models import League, Match, MatchDetail, MatchStatus, StreamServer, Team
from live_score.domain.resolver import TeamAliasMatcher

NOW = datetime(2026, 11, 19, 9, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fake HTTP layer
# ---------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeSession:
    """Routes upstream URLs to canned payloads and counts requests."""

    def __init__(
        self,
        fixtures: dict[str, Any],
        summary: Optional[dict[str, Any]] = None,
        standings: Optional[dict[str, Any]] = None,
        fail: bool = False,
        scoreboards: Optional[dict[str, dict[str, Any]]] = None,
    ) -> None:
        self.fixtures = fixtures
        self.summary = summary or {}
        self.standings = standings or {}
        self.fail = fail
        self.scoreboards = scoreboards or {}
        self.urls: list[str] = []

    def get(self, url: str, timeout: float = 12.0) -> FakeResponse:
        self.urls.append(url)
        if self.fail:
            raise LiveScoreV2Error("upstream down")
        if "/standings" in url:
            return FakeResponse(self.standings)
        if "/summary" in url or "/events/" in url:
            return FakeResponse(self.summary)
        if "/scoreboard" in url:
            for day, payload in self.scoreboards.items():
                if f"dates={day}" in url:
                    return FakeResponse(payload)
            return FakeResponse({"events": []})
        return FakeResponse(self.fixtures)


def _team_payload(team_id: str, name: str, logo: str = "") -> dict[str, Any]:
    return {
        "id": team_id,
        "displayName": name,
        "logo": logo,
        "logos": [{"href": logo}] if logo else [],
    }


def _competitor(side: str, team: dict[str, Any], score: Any = "") -> dict[str, Any]:
    return {"homeAway": side, "score": score, "team": team}


def _fixture_payload() -> dict[str, Any]:
    return {
        "league": {
            "id": "700",
            "name": "English Premier League",
            "logo": "https://cdn.example/eng1.png",
        },
        "events": [
            {
                "id": "401879233",
                "date": "2026-11-21T12:30:00.000Z",
                "competitions": [
                    {
                        "id": "401879233",
                        "date": "2026-11-21T12:30:00.000Z",
                        "status": {
                            "clock": 0,
                            "type": {"name": "STATUS_SCHEDULED", "state": "pre"},
                        },
                        "venue": {"fullName": "Etihad Stadium"},
                        "competitors": [
                            _competitor(
                                "home",
                                _team_payload("382", "Manchester City", "https://cdn.example/mci.png"),
                                "2",
                            ),
                            _competitor(
                                "away", _team_payload("359", "Arsenal"), "1"
                            ),
                        ],
                    }
                ],
            }
        ],
    }


def _roster_player(name: str, jersey: str, abbreviation: str) -> dict[str, Any]:
    return {
        "starter": True,
        "jersey": jersey,
        "athlete": {"id": name.replace(" ", "-"), "displayName": name},
        "position": {"abbreviation": abbreviation},
    }


def _home_roster() -> list[dict[str, Any]]:
    return [
        _roster_player("David Raya", "1", "G"),
        _roster_player("Ben White", "4", "RB"),
        _roster_player("Cristhian Mosquera", "3", "CD-R"),
        _roster_player("Gabriel Magalhaes", "6", "CD-L"),
        _roster_player("Riccardo Calafiori", "33", "LB"),
        _roster_player("Declan Rice", "41", "LM"),
        _roster_player("Myles Lewis-Skelly", "49", "RM"),
        _roster_player("Martin Odegaard", "8", "AM"),
        _roster_player("Christos Tzolis", "17", "AM-L"),
        _roster_player("Bukayo Saka", "7", "AM-R"),
        _roster_player("Kai Havertz", "29", "F"),
    ]


def _summary_payload() -> dict[str, Any]:
    return {
        "header": {
            "id": "401879301",
            "season": {"year": 2026},
            "league": {"id": "700", "name": "English Premier League"},
            "competitions": [
                {
                    "id": "401879301",
                    "date": "2026-11-21T12:30:00.000Z",
                    "status": {
                        "clock": 5400,
                        "type": {"name": "STATUS_FULL_TIME", "state": "post"},
                    },
                    "competitors": [
                        _competitor("home", _team_payload("359", "Arsenal"), "3"),
                        _competitor("away", _team_payload("382", "Manchester City"), "0"),
                    ],
                }
            ],
        },
        "rosters": [
            {
                "homeAway": "home",
                "formation": "4-2-3-1",
                "roster": _home_roster(),
            },
            {
                "homeAway": "away",
                "formation": "4-3-3",
                "roster": [
                    _roster_player("Ederson", "31", "G"),
                    _roster_player("Kyle Walker", "2", "RB"),
                    _roster_player("Ruben Dias", "3", "CD-R"),
                    _roster_player("Nathan Ake", "6", "CD-L"),
                    _roster_player("Josko Gvardiol", "24", "LB"),
                    _roster_player("Rodri", "16", "DM"),
                    _roster_player("Bernardo Silva", "20", "CM"),
                    _roster_player("Kevin De Bruyne", "17", "AM"),
                    _roster_player("Phil Foden", "47", "LW"),
                    _roster_player("Erling Haaland", "9", "F"),
                    _roster_player("Jack Grealish", "10", "LW"),
                ],
            },
        ],
        "keyEvents": [
            {
                "id": "1",
                "type": {"text": "Goal"},
                "clock": {"value": 874, "displayValue": "15'"},
                "team": {"id": "359"},
                "scoringPlay": True,
                "athletesInvolved": [{"displayName": "Kai Havertz"}],
            },
            {
                "id": "2",
                "type": {"text": "Yellow Card"},
                "clock": {"displayValue": "30'"},
                "yellowCard": True,
                "athletesInvolved": [{"displayName": "Rodri"}],
            },
            {
                "id": "3",
                "type": {"text": "Substitution"},
                "clock": {"displayValue": "60'"},
                "athletesInvolved": [
                    {"displayName": "Bukayo Saka"},
                    {"displayName": "Leandro Trossard"},
                ],
            },
            {
                "id": "4",
                "type": {"text": "Kickoff"},
                "clock": {"displayValue": "1'"},
            },
        ],
        "boxscore": {
            "teams": [
                {
                    "homeAway": "home",
                    "statistics": [
                        {"name": "possessionPct", "displayValue": "64.5"},
                        {"name": "totalShots", "displayValue": "17"},
                    ],
                },
                {
                    "homeAway": "away",
                    "statistics": [
                        {"name": "possessionPct", "displayValue": "35.5"},
                        {"name": "totalShots", "displayValue": "6"},
                    ],
                },
            ]
        },
        "gameInfo": {
            "venue": {"fullName": "Emirates Stadium"},
            "officials": [
                {
                    "fullName": "Thomas Bramall",
                    "position": {"name": "Referee"},
                }
            ],
        },
    }


def _standings_payload() -> dict[str, Any]:
    return {
        "children": [
            {
                "standings": {
                    "entries": [
                        {
                            "rank": 1,
                            "team": {"displayName": "Arsenal"},
                            "stats": [
                                {"name": "gamesPlayed", "displayValue": "10"},
                                {"name": "wins", "displayValue": "9"},
                                {"name": "ties", "displayValue": "0"},
                                {"name": "losses", "displayValue": "1"},
                                {"name": "pointsFor", "displayValue": "15"},
                                {"name": "pointsAgainst", "displayValue": "5"},
                                {"name": "points", "displayValue": "27"},
                            ],
                        },
                        {
                            "rank": 2,
                            "team": {"displayName": "Manchester City"},
                            "stats": [
                                {"name": "gamesPlayed", "displayValue": "10"},
                                {"name": "wins", "displayValue": "8"},
                                {"name": "ties", "displayValue": "1"},
                                {"name": "losses", "displayValue": "1"},
                                {"name": "pointsFor", "displayValue": "24"},
                                {"name": "pointsAgainst", "displayValue": "9"},
                                {"name": "points", "displayValue": "25"},
                            ],
                        },
                    ]
                }
            }
        ]
    }


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

def test_fetch_window_maps_fixtures_to_domain_models() -> None:
    session = FakeSession(_fixture_payload())
    client = LiveScoreV2Client(session=session, leagues=["eng.1"])

    matches = client.fetch_window(date(2026, 11, 17), date(2026, 11, 21))

    assert len(matches) == 1
    match = matches[0]
    assert match.id == "401879233"
    assert match.home_team.name_ar == "مانشستر سيتي"
    assert match.away_team.name_ar == "أرسنال"
    assert match.home_score == 2
    assert match.away_score == 1
    assert match.status == MatchStatus.SCHEDULED
    assert match.league.name_ar == "الدوري الإنجليزي الممتاز"
    assert match.stadium == "Etihad Stadium"
    assert match.source_ref == "eng.1:401879233"
    assert match.kickoff_time == datetime(2026, 11, 21, 12, 30, tzinfo=timezone.utc)
    assert "from=20261117" in session.urls[0]
    assert "to=20261121" in session.urls[0]


def test_fetch_window_raises_when_every_league_fails() -> None:
    client = LiveScoreV2Client(
        session=FakeSession(_fixture_payload(), fail=True), leagues=["eng.1", "esp.1"]
    )

    with pytest.raises(LiveScoreV2Error):
        client.fetch_window(date(2026, 11, 17), date(2026, 11, 21))


def test_fetch_window_tolerates_partial_league_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    client = LiveScoreV2Client(
        session=FakeSession(_fixture_payload()), leagues=["eng.1", "esp.1"]
    )

    def fake_fixtures(slug: str, start: date, end: date) -> list[dict[str, Any]]:
        if slug == "esp.1":
            raise LiveScoreV2Error("esp.1 unavailable")
        return _fixture_payload()["events"]

    monkeypatch.setattr(client, "fetch_fixtures", fake_fixtures)

    matches = client.fetch_window(date(2026, 11, 17), date(2026, 11, 21))
    assert [match.id for match in matches] == ["401879233"]


def test_fetch_detail_maps_lineups_events_stats_and_standings() -> None:
    session = FakeSession(
        _fixture_payload(), summary=_summary_payload(), standings=_standings_payload()
    )
    client = LiveScoreV2Client(session=session, leagues=["eng.1"])
    base = client.fetch_window(date(2026, 11, 17), date(2026, 11, 21))[0]

    detail = client.fetch_detail("eng.1", base.id, base)

    assert detail.home_formation == "4-2-3-1"
    assert detail.away_formation == "4-3-3"
    assert len(detail.home_lineup) == 11
    assert len(detail.away_lineup) == 11
    assert {player.grid_position.split(":")[0] for player in detail.home_lineup} == {
        "1",
        "2",
        "3",
        "4",
        "5",
    }
    # Goalkeeper is the first row, and every starter has a shirt number.
    goalkeeper = next(player for player in detail.home_lineup if player.position == "GK")
    assert goalkeeper.name == "David Raya"
    assert goalkeeper.grid_position.startswith("1:")
    assert all(player.number > 0 for player in detail.home_lineup)

    assert [event.type for event in detail.events] == [
        "goal",
        "yellow_card",
        "substitution",
    ]
    assert detail.events[0].minute == 15
    assert detail.events[0].player_name == "Kai Havertz"
    assert detail.events[0].description_ar == "هدف"
    assert detail.events[1].description_ar == "بطاقة صفراء"

    assert detail.stats["possessionPct"]["home"] == 64.5
    assert detail.stats["possessionPct"]["away"] == 35.5
    assert detail.stats["possessionPct"]["unit"] == "%"

    arsenal_row = detail.standings[0]
    assert arsenal_row["position"] == 1
    assert arsenal_row["team_name_ar"] == "أرسنال"
    assert arsenal_row["played"] == 10
    assert arsenal_row["drawn"] == 0
    assert arsenal_row["goals_for"] == 15
    assert arsenal_row["points"] == 27
    assert arsenal_row["is_away"] is True
    assert arsenal_row["is_home"] is False

    assert detail.match.stadium == "Emirates Stadium"
    assert detail.match.referee == "Thomas Bramall"


def test_event_mapping_reads_participants_when_athletes_involved_is_absent() -> None:
    summary = _summary_payload()
    summary["keyEvents"] = [
        {
            "id": "10",
            "type": {"text": "Goal"},
            "clock": {"displayValue": "28'"},
            "team": {"id": "874"},
            "scoringPlay": True,
            "text": (
                "Goal! Corinthians 1, Botafogo 0. Kaio César (Corinthians) left footed "
                "shot from the centre of the box. Assisted by Vitinho."
            ),
            "participants": [
                {"athlete": {"displayName": "Kaio"}},
                {"athlete": {"displayName": "Vitinho"}},
            ],
        },
        {
            "id": "11",
            "type": {"text": "Substitution"},
            "clock": {"displayValue": "45'"},
            "text": "Substitution, Botafogo. Kaio Pantaleão replaces Arthur Chaves.",
            "participants": [
                {"athlete": {"displayName": "Kaio"}},
                {"athlete": {"displayName": "Arthur Chaves"}},
            ],
        },
    ]
    session = FakeSession(
        _fixture_payload(), summary=summary, standings=_standings_payload()
    )
    client = LiveScoreV2Client(session=session, leagues=["eng.1"])
    base = client.fetch_window(date(2026, 11, 17), date(2026, 11, 21))[0]

    detail = client.fetch_detail("eng.1", base.id, base)

    assert detail.events[0].player_name == "Kaio César"
    assert detail.events[0].description_ar == "هدف • صناعة Vitinho"
    assert detail.events[1].player_name == "Kaio Pantaleão"
    assert detail.events[1].description_ar == "تبديل • خروج Arthur Chaves"


def test_fetch_detail_survives_standings_failure() -> None:
    session = FakeSession(_fixture_payload(), summary=_summary_payload())
    session.standings = None
    original_get = session.get

    def get(url: str, timeout: float = 12.0) -> FakeResponse:
        if "/standings" in url:
            raise LiveScoreV2Error("standings down")
        return original_get(url, timeout)

    session.get = get  # type: ignore[assignment]
    client = LiveScoreV2Client(session=session, leagues=["eng.1"])
    base = client.fetch_window(date(2026, 11, 17), date(2026, 11, 21))[0]

    detail = client.fetch_detail("eng.1", base.id, base)
    assert detail.standings == []
    assert len(detail.home_lineup) == 11


def test_fetch_standings_prefers_the_group_containing_the_match_teams() -> None:
    def entry(rank: int, name: str) -> dict[str, Any]:
        return {
            "rank": rank,
            "team": {"displayName": name},
            "stats": [
                {"name": "gamesPlayed", "displayValue": "10"},
                {"name": "wins", "displayValue": "6"},
                {"name": "ties", "displayValue": "2"},
                {"name": "losses", "displayValue": "2"},
                {"name": "pointsFor", "displayValue": "18"},
                {"name": "pointsAgainst", "displayValue": "9"},
                {"name": "points", "displayValue": "20"},
            ],
        }

    session = FakeSession(_fixture_payload())
    session.standings = {
        "children": [
            {
                "standings": {
                    "entries": [entry(1, "Corinthians"), entry(2, "Palmeiras")]
                }
            },
            {"standings": {"entries": [entry(1, "Flamengo"), entry(2, "Botafogo")]}},
        ]
    }
    client = LiveScoreV2Client(session=session, leagues=["eng.1"])

    rows = client.fetch_standings(
        "bra.1", 2026, home_name="Botafogo", away_name="Flamengo"
    )

    assert [row["team_name_ar"] for row in rows] == ["فلامنغو", "بوتافوغو"]
    assert rows[0]["is_away"] is True
    assert rows[1]["is_home"] is True


@pytest.mark.parametrize(
    ("state", "name", "expected"),
    [
        ("pre", "STATUS_SCHEDULED", MatchStatus.SCHEDULED),
        ("in", "STATUS_IN_PROGRESS", MatchStatus.IN_PLAY),
        ("in", "STATUS_HALFTIME", MatchStatus.HALFTIME),
        ("in", "STATUS_EXTRA_TIME", MatchStatus.EXTRA_TIME),
        ("in", "STATUS_PENALTIES", MatchStatus.PENALTIES),
        ("post", "STATUS_FULL_TIME", MatchStatus.FINISHED),
        ("pre", "STATUS_POSTPONED", MatchStatus.POSTPONED),
        ("post", "STATUS_CANCELED", MatchStatus.POSTPONED),
    ],
)
def test_status_mapping(state: str, name: str, expected: MatchStatus) -> None:
    payload = {"type": {"state": state, "name": name}}
    assert LiveScoreV2Client._map_status(payload) == expected


def test_fixture_ref_round_trip() -> None:
    ref = FixtureRef("eng.1", "401879233")
    assert ref.source_ref == "eng.1:401879233"
    assert FixtureRef.parse(ref.source_ref) == ref
    assert FixtureRef.parse("broken") is None
    assert FixtureRef.parse(None) is None


def test_arabic_lookup_ignores_accents_and_club_suffixes() -> None:
    assert TeamAliasMatcher.get_arabic_name("Grémio") == "غريميو"
    assert TeamAliasMatcher.get_arabic_name("Atletico Madrid") == "أتلتيكو مدريد"
    assert TeamAliasMatcher.get_arabic_name("Velez Sarsfield") == "فيليز سارسفيلد"
    assert TeamAliasMatcher.get_arabic_name("Some Unknown Club") is None


def test_arabic_lookup_covers_brazilian_club_spellings() -> None:
    assert TeamAliasMatcher.get_arabic_name("Coritiba") == "كوريتيبا"
    assert TeamAliasMatcher.get_arabic_name("Remo") == "ريمو"
    assert TeamAliasMatcher.get_arabic_name("Chapecoense") == "شابيكوينسي"
    assert (
        TeamAliasMatcher.get_arabic_name("Athletico Paranaense")
        == "أتلتيكو بارانينسي"
    )
    assert TeamAliasMatcher.get_arabic_name("Atletico Mineiro") == "أتلتيكو مينيرو"
    assert TeamAliasMatcher.get_arabic_name("Troyes") == "تروا"


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def _match(match_id: str, score: int = 0) -> Match:
    return Match(
        id=match_id,
        home_team=Team(id="1", name_ar="أرسنال", name_en="Arsenal"),
        away_team=Team(id="2", name_ar="تشيلسي", name_en="Chelsea"),
        league=League(
            id="700",
            name_ar="الدوري الإنجليزي الممتاز",
            name_en="English Premier League",
        ),
        status=MatchStatus.IN_PLAY,
        kickoff_time=NOW,
        home_score=score,
        away_score=0,
        source_ref=f"eng.1:{match_id}",
    )


class FakeCatalogClient:
    def __init__(self, matches: list[Match], detail: Optional[MatchDetail] = None) -> None:
        self.matches = matches
        self.detail = detail
        self.fail = False
        self.window_calls = 0
        self.detail_calls = 0

    def fetch_window(self, start: Any, end: Any, leagues: Any = None) -> list[Match]:
        self.window_calls += 1
        if self.fail:
            raise LiveScoreV2Error("upstream down")
        return [match.model_copy(deep=True) for match in self.matches]

    def fetch_detail(self, league_slug: str, event_id: str, match: Any = None) -> MatchDetail:
        self.detail_calls += 1
        if self.fail:
            raise LiveScoreV2Error("summary down")
        detail = self.detail.model_copy(deep=True)
        if match is not None:
            detail.match = match
        return detail


def _detail(match: Match) -> MatchDetail:
    return MatchDetail(
        match=match,
        events=[],
        home_formation="4-3-3",
        away_formation="4-2-3-1",
    )


def test_catalog_caches_fixtures_between_ttl_windows() -> None:
    match = _match("401879233")
    fake = FakeCatalogClient([match], detail=_detail(match))
    catalog = LiveFixturesCatalog(
        fake, ["eng.1"], ttl_seconds=20, background_refresh=False
    )

    assert len(catalog.fixtures(NOW)) == 1
    assert len(catalog.fixtures(NOW + timedelta(seconds=10))) == 1
    assert fake.window_calls == 1
    assert len(catalog.fixtures(NOW + timedelta(seconds=21))) == 1
    assert fake.window_calls == 2


def test_catalog_refreshes_in_background_once_a_snapshot_exists() -> None:
    class NotifyingClient(FakeCatalogClient):
        def __init__(self, matches: list[Match], detail: Optional[MatchDetail] = None) -> None:
            super().__init__(matches, detail)
            self.refreshed = threading.Event()

        def fetch_window(self, start: Any, end: Any, leagues: Any = None) -> list[Match]:
            result = super().fetch_window(start, end, leagues)
            self.refreshed.set()
            return result

    match = _match("401879233")
    fake = NotifyingClient([match], detail=_detail(match))
    catalog = LiveFixturesCatalog(fake, ["eng.1"], ttl_seconds=20)

    catalog.fixtures(NOW)
    assert fake.refreshed.wait(timeout=2)
    fake.refreshed.clear()

    # Stale reads return immediately while the refresh runs behind the request.
    catalog.fixtures(NOW + timedelta(seconds=30))
    assert fake.refreshed.wait(timeout=2)
    assert fake.window_calls == 2


def test_catalog_hydrates_details_lazily_and_reuses_cache() -> None:
    match = _match("401879233")
    fake = FakeCatalogClient([match], detail=_detail(match))
    catalog = LiveFixturesCatalog(
        fake,
        ["eng.1"],
        ttl_seconds=20,
        detail_ttl_seconds=20,
        background_refresh=False,
    )

    detail = catalog.get_detail("401879233", NOW)
    assert detail is not None
    assert detail.home_formation == "4-3-3"
    assert fake.detail_calls == 1

    catalog.get_detail("401879233", NOW + timedelta(seconds=10))
    assert fake.detail_calls == 1

    catalog.get_detail("401879233", NOW + timedelta(seconds=21))
    assert fake.detail_calls == 2
    assert catalog.get_detail("missing", NOW) is None


def test_catalog_overlays_fresh_scores_on_cached_details() -> None:
    match = _match("401879233", score=0)
    fake = FakeCatalogClient([match], detail=_detail(match))
    catalog = LiveFixturesCatalog(fake, ["eng.1"], ttl_seconds=20, detail_ttl_seconds=300)
    catalog.get_detail("401879233", NOW)

    fake.matches = [_match("401879233", score=2)]
    catalog.refresh(NOW + timedelta(seconds=21), force=True)
    detail = catalog.get_detail("401879233", NOW + timedelta(seconds=22))

    assert detail is not None
    assert detail.match.home_score == 2
    assert fake.detail_calls == 1  # summary still cached


def test_catalog_keeps_stale_snapshot_when_refresh_fails() -> None:
    match = _match("401879233")
    fake = FakeCatalogClient([match], detail=_detail(match))
    catalog = LiveFixturesCatalog(
        fake,
        ["eng.1"],
        ttl_seconds=20,
        retry_after_failure=60,
        background_refresh=False,
    )
    catalog.fixtures(NOW)

    fake.fail = True
    fixtures = catalog.fixtures(NOW + timedelta(seconds=30))
    assert len(fixtures) == 1
    status = catalog.status()
    assert status["data_source"] == "live"
    assert "upstream down" in status["last_error"]

    # The failure backoff stops hammering the upstream.
    catalog.fixtures(NOW + timedelta(seconds=40))
    assert fake.window_calls == 2


def test_catalog_falls_back_to_demo_when_upstream_is_unavailable() -> None:
    demo_match = _match("demo-1")
    fake = FakeCatalogClient([], detail=_detail(demo_match))
    fake.fail = True
    catalog = LiveFixturesCatalog(
        fake,
        ["eng.1"],
        demo_loader=lambda now: [MatchDetail(match=demo_match)],
    )

    fixtures = catalog.fixtures(NOW)
    assert [item.match.id for item in fixtures] == ["demo-1"]
    status = catalog.status()
    assert status["data_source"] == "demo"
    assert status["matches"] == 1


def test_catalog_returns_base_detail_when_hydration_fails() -> None:
    match = _match("401879233")
    fake = FakeCatalogClient([match], detail=_detail(match))
    catalog = LiveFixturesCatalog(
        fake, ["eng.1"], ttl_seconds=20, background_refresh=False
    )
    catalog.fixtures(NOW)

    fake.fail = True
    detail = catalog.get_detail("401879233", NOW + timedelta(seconds=5))
    assert detail is not None
    assert detail.home_lineup == []
    assert detail.match.id == "401879233"


def test_seed_demo_returns_immediately_and_allows_live_refresh() -> None:
    demo_match = _match("demo-1")
    fake = FakeCatalogClient([], detail=_detail(demo_match))
    fake.fail = True
    catalog = LiveFixturesCatalog(
        fake,
        ["eng.1"],
        background_refresh=False,
        demo_loader=lambda now: [MatchDetail(match=demo_match)],
    )

    catalog.seed_demo(NOW)
    assert fake.window_calls == 0  # no blocking upstream call at startup

    fixtures = catalog.fixtures(NOW + timedelta(seconds=1))
    assert fake.window_calls == 1  # the live refresh was still attempted
    assert [item.match.id for item in fixtures] == ["demo-1"]
    assert catalog.status()["data_source"] == "demo"


def test_catalog_persists_and_reloads_the_last_live_snapshot(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "fixtures.json"
    match = _match("401879233")
    fake = FakeCatalogClient([match], detail=_detail(match))
    catalog = LiveFixturesCatalog(
        fake,
        ["eng.1"],
        ttl_seconds=20,
        background_refresh=False,
        snapshot_path=str(snapshot),
        clock=lambda: NOW,
    )
    catalog.fixtures(NOW)

    assert snapshot.exists()
    saved = json.loads(snapshot.read_text(encoding="utf-8"))
    assert saved["saved_at"]
    assert saved["matches"][0]["id"] == "401879233"

    offline = FakeCatalogClient([], detail=_detail(match))
    offline.fail = True
    restored = LiveFixturesCatalog(
        offline,
        ["eng.1"],
        ttl_seconds=20,
        background_refresh=False,
        snapshot_path=str(snapshot),
        clock=lambda: NOW + timedelta(seconds=30),
        demo_loader=lambda now: [MatchDetail(match=_match("demo-1"))],
    )

    fixtures = restored.fixtures(NOW + timedelta(seconds=30))
    assert offline.window_calls == 1  # a refresh was attempted and failed
    assert [item.match.id for item in fixtures] == ["401879233"]
    status = restored.status()
    assert status["data_source"] == "live"
    assert "upstream down" in status["last_error"]



def test_catalog_ignores_expired_snapshots(tmp_path: Path) -> None:
    snapshot = tmp_path / "fixtures.json"
    saved_at = datetime.now(timezone.utc) - timedelta(hours=48)
    snapshot.write_text(
        json.dumps(
            {
                "saved_at": saved_at.isoformat().replace("+00:00", "Z"),
                "matches": [_match("old-1").model_dump(mode="json")],
            }
        ),
        encoding="utf-8",
    )

    demo_match = _match("demo-1")
    offline = FakeCatalogClient([], detail=_detail(demo_match))
    offline.fail = True
    catalog = LiveFixturesCatalog(
        offline,
        ["eng.1"],
        snapshot_path=str(snapshot),
        snapshot_max_age_hours=36,
        demo_loader=lambda now: [MatchDetail(match=demo_match)],
    )

    fixtures = catalog.fixtures(NOW)
    assert [item.match.id for item in fixtures] == ["demo-1"]
    assert catalog.status()["data_source"] == "demo"


def test_standings_requests_are_reused_between_detail_refreshes() -> None:
    session = FakeSession(
        _fixture_payload(),
        summary=_summary_payload(),
        standings=_standings_payload(),
    )
    client = LiveScoreV2Client(
        session=session, leagues=["eng.1"], standings_ttl=300
    )

    client.fetch_standings("eng.1", 2026)
    rows = client.fetch_standings(
        "eng.1", 2026, home_name="Manchester City", away_name="Arsenal"
    )

    assert sum("/standings" in url for url in session.urls) == 1
    assert rows[0]["is_away"] is True
    assert rows[1]["is_home"] is True


# ---------------------------------------------------------------------------
# ESPN fallback provider
# ---------------------------------------------------------------------------

def _espn_event(
    event_id: str, kickoff: str = "2026-11-21T12:30:00.000Z"
) -> dict[str, Any]:
    return {
        "id": event_id,
        "date": kickoff,
        "competitions": [
            {
                "id": event_id,
                "date": kickoff,
                "status": {
                    "clock": 0,
                    "type": {"name": "STATUS_SCHEDULED", "state": "pre"},
                },
                "competitors": [
                    _competitor("home", _team_payload("382", "Manchester City"), "0"),
                    _competitor("away", _team_payload("359", "Arsenal"), "0"),
                ],
            }
        ],
    }


def _scoreboard_payload(events: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "leagues": [
            {
                "id": "700",
                "name": "English Premier League",
                "logos": [{"href": "https://cdn.example/eng1.png"}],
            }
        ],
        "events": events,
    }


def test_espn_client_fetches_each_day_and_dedupes_events() -> None:
    session = FakeSession(
        {},
        scoreboards={
            "20261119": _scoreboard_payload([_espn_event("401841316")]),
            "20261120": _scoreboard_payload(
                [_espn_event("401879233"), _espn_event("401841316")]
            ),
        },
    )
    client = EspnSoccerClient(session=session, leagues=["bra.1"])

    matches = client.fetch_window(date(2026, 11, 19), date(2026, 11, 20))

    assert [match.id for match in matches] == ["401841316", "401879233"]
    assert all(match.league.name_en == "English Premier League" for match in matches)
    assert all(match.league.name_ar == "الدوري البرازيلي" for match in matches)
    assert all(match.league.logo_url == "https://cdn.example/eng1.png" for match in matches)
    assert sum("/scoreboard" in url for url in session.urls) == 2


def test_espn_client_reuses_cached_scoreboards() -> None:
    session = FakeSession(
        {}, scoreboards={"20261119": _scoreboard_payload([_espn_event("1")])}
    )
    client = EspnSoccerClient(session=session, leagues=["eng.1"])

    client.fetch_window(date(2026, 11, 19), date(2026, 11, 19))
    client.fetch_window(date(2026, 11, 19), date(2026, 11, 19))

    assert len(session.urls) == 1


def test_espn_client_hydrates_details_through_the_summary_route() -> None:
    session = FakeSession(
        {},
        summary=_summary_payload(),
        standings=_standings_payload(),
        scoreboards={"20261121": _scoreboard_payload([_espn_event("401879233")])},
    )
    client = EspnSoccerClient(session=session, leagues=["eng.1"])
    base = client.fetch_window(date(2026, 11, 21), date(2026, 11, 21))[0]

    detail = client.fetch_detail("eng.1", base.id, base)

    assert any("/summary?event=401879233" in url for url in session.urls)
    assert len(detail.home_lineup) == 11
    assert detail.home_formation == "4-2-3-1"
    assert detail.stats["possessionPct"]["home"] == 64.5
    assert detail.standings[0]["team_name_ar"] == "أرسنال"


def test_espn_standings_use_the_core_api_host() -> None:
    session = FakeSession({}, standings=_standings_payload())
    client = EspnSoccerClient(session=session, leagues=["eng.1"])

    rows = client.fetch_standings("eng.1", 2026)

    assert rows[0]["team_name_ar"] == "أرسنال"
    assert any(
        url.startswith(ESPN_CORE_BASE) and "/standings" in url
        for url in session.urls
    )


class _StubProvider:
    def __init__(
        self,
        matches: Optional[list[Match]] = None,
        detail: Optional[MatchDetail] = None,
        fail: bool = False,
        leagues: tuple[str, ...] = ("eng.1",),
    ) -> None:
        self.leagues = leagues
        self.matches = matches or []
        self.detail = detail
        self.fail = fail
        self.window_calls = 0
        self.detail_calls = 0

    def fetch_window(
        self, start: Any, end: Any, leagues: Any = None
    ) -> list[Match]:
        self.window_calls += 1
        if self.fail:
            raise LiveScoreV2Error("primary down")
        return list(self.matches)

    def fetch_detail(
        self, league_slug: str, event_id: str, match: Any = None
    ) -> Any:
        self.detail_calls += 1
        if self.fail:
            raise LiveScoreV2Error("primary down")
        return self.detail


def test_fallback_switches_to_secondary_and_skips_the_primary_during_cooldown() -> None:
    now = [0.0]
    match = _match("401879233")
    primary = _StubProvider(fail=True)
    secondary = _StubProvider(matches=[match])
    client = FallbackSoccerClient(
        primary, secondary, cooldown_seconds=300, clock=lambda: now[0]
    )

    assert client.leagues == ("eng.1",)
    assert client.fetch_window(date(2026, 11, 19), date(2026, 11, 21)) == [match]
    assert primary.window_calls == 1
    assert secondary.window_calls == 1

    now[0] = 120.0
    assert client.fetch_window(date(2026, 11, 19), date(2026, 11, 21)) == [match]
    assert primary.window_calls == 1  # skipped during the cooldown
    assert secondary.window_calls == 2

    now[0] = 301.0
    client.fetch_window(date(2026, 11, 19), date(2026, 11, 21))
    assert primary.window_calls == 2  # retried after the cooldown


def test_fallback_returns_to_the_primary_once_it_recovers() -> None:
    now = [0.0]
    primary_match = _match("primary-1")
    secondary_match = _match("secondary-1")
    primary = _StubProvider(matches=[primary_match], fail=True)
    secondary = _StubProvider(matches=[secondary_match])
    client = FallbackSoccerClient(
        primary, secondary, cooldown_seconds=300, clock=lambda: now[0]
    )

    assert client.fetch_window(date(2026, 11, 19), date(2026, 11, 19)) == [
        secondary_match
    ]

    primary.fail = False
    now[0] = 301.0
    assert client.fetch_window(date(2026, 11, 19), date(2026, 11, 19)) == [
        primary_match
    ]
    assert secondary.window_calls == 1


def test_fallback_switches_details_to_the_secondary() -> None:
    match = _match("401879233")
    detail = _detail(match)
    primary = _StubProvider(fail=True)
    secondary = _StubProvider(detail=detail)
    client = FallbackSoccerClient(primary, secondary, clock=lambda: 0.0)

    assert client.fetch_detail("eng.1", match.id, match) is detail
    assert primary.detail_calls == 1
    assert secondary.detail_calls == 1


def test_fallback_reports_both_provider_failures() -> None:
    primary = _StubProvider(fail=True)
    secondary = _StubProvider(fail=True)
    client = FallbackSoccerClient(primary, secondary, clock=lambda: 0.0)

    with pytest.raises(LiveScoreV2Error, match="primary and fallback providers failed"):
        client.fetch_window(date(2026, 11, 19), date(2026, 11, 19))


def test_catalog_uses_injected_clock_for_snapshot_expiry(tmp_path: Path) -> None:
    snapshot = tmp_path / "fixtures.json"
    saved_at = NOW - timedelta(hours=48)
    snapshot.write_text(
        json.dumps(
            {
                "saved_at": saved_at.isoformat().replace("+00:00", "Z"),
                "matches": [_match("old-1").model_dump(mode="json")],
            }
        ),
        encoding="utf-8",
    )

    demo_match = _match("demo-1")
    offline = FakeCatalogClient([], detail=_detail(demo_match))
    offline.fail = True
    catalog = LiveFixturesCatalog(
        offline,
        ["eng.1"],
        snapshot_path=str(snapshot),
        snapshot_max_age_hours=36,
        clock=lambda: NOW,
        demo_loader=lambda now: [MatchDetail(match=demo_match)],
    )

    fixtures = catalog.fixtures(NOW)
    assert [item.match.id for item in fixtures] == ["demo-1"]
    assert catalog.status()["data_source"] == "demo"


def test_catalog_overlay_preserves_summary_stadium_and_referee() -> None:
    match = _match("401879233")
    match.stadium = None
    match.referee = None
    detail_with_venue = _detail(match)
    detail_with_venue.match.stadium = "Etihad Stadium"
    detail_with_venue.match.referee = "Michael Oliver"

    fake = FakeCatalogClient([match], detail=detail_with_venue)
    catalog = LiveFixturesCatalog(
        fake,
        ["eng.1"],
        ttl_seconds=100,
        detail_ttl_seconds=100,
        background_refresh=False,
        clock=lambda: NOW,
    )

    # First detail fetch calls upstream client and populates cache
    first = catalog.get_detail("401879233", NOW)
    assert first is not None
    assert first.match.stadium == "Etihad Stadium"
    assert first.match.referee == "Michael Oliver"

    # Simulate base match score update from fixture refresh (where stadium/referee are None)
    updated_base = _match("401879233")
    updated_base.home_score = 3
    updated_base.away_score = 1
    updated_base.stadium = None
    updated_base.referee = None
    fake.matches = [updated_base]
    catalog._publish_live([updated_base], NOW)

    # Subsequent cached get_detail within detail_ttl overlays updated score but preserves stadium/referee
    cached = catalog.get_detail("401879233", NOW + timedelta(seconds=10))
    assert cached is not None
    assert cached.match.home_score == 3
    assert cached.match.away_score == 1
    assert cached.match.stadium == "Etihad Stadium"
    assert cached.match.referee == "Michael Oliver"


def test_catalog_lazily_merges_scraped_streams_and_tolerates_scraper_errors() -> None:
    match = _match("401879233")
    fake = FakeCatalogClient([match], detail=_detail(match))

    class FakeScraper:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []
            self.fail = False

        def fetch_stream_servers(self, home: str, away: str) -> list[StreamServer]:
            self.calls.append((home, away))
            if self.fail:
                raise RuntimeError("Scraper network error")
            return [
                StreamServer(
                    id="srv_scraped_1",
                    server_name="سيرفر مباشر",
                    url="https://scraper.example/live",
                    type="iframe",
                )
            ]

    scraper = FakeScraper()
    catalog = LiveFixturesCatalog(
        fake,
        ["eng.1"],
        scraper=scraper,
        scraper_ttl_seconds=60,
        background_refresh=False,
        clock=lambda: NOW,
    )

    # fixtures() does NOT trigger scraping (lazy)
    fixtures = catalog.fixtures(NOW)
    assert len(fixtures) == 1
    assert len(scraper.calls) == 0

    # get_detail() triggers scraping lazily with Arabic team names
    detail = catalog.get_detail("401879233", NOW)
    assert detail is not None
    assert len(scraper.calls) == 1
    assert scraper.calls[0] == (match.home_team.name_ar, match.away_team.name_ar)
    assert any(s.url == "https://scraper.example/live" for s in detail.match.stream_servers)

    # Scraper failure does not break match detail
    scraper.fail = True
    # Query with another timestamp past scraper TTL to trigger refresh
    detail_err = catalog.get_detail("401879233", NOW + timedelta(seconds=70))
    assert detail_err is not None
    assert detail_err.match.id == match.id


def test_build_live_client_defaults_to_espn_primary_and_honors_explicit_url() -> None:
    from live_score.adapters.fallback import FallbackSoccerClient
    from live_score.adapters.livescore_v2 import DEFAULT_BASE_URL
    from live_score.api.fixtures import _build_live_client

    # 1. Default (empty string / unset): ESPN is primary, worldcup26.ir is secondary
    default_client = _build_live_client("")
    assert isinstance(default_client, FallbackSoccerClient)
    assert isinstance(default_client.primary, EspnSoccerClient)
    assert isinstance(default_client.secondary, LiveScoreV2Client)
    assert default_client.secondary.base_url == DEFAULT_BASE_URL

    # 2. Explicit custom URL: custom URL is primary, ESPN is secondary
    custom_client = _build_live_client("https://custom-sports.example/api")
    assert isinstance(custom_client, FallbackSoccerClient)
    assert isinstance(custom_client.primary, LiveScoreV2Client)
    assert custom_client.primary.base_url == "https://custom-sports.example/api"
    assert isinstance(custom_client.secondary, EspnSoccerClient)

