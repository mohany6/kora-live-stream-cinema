"""
Tests for the public match schedule / hybrid detail API and the admin CMS
stream + manual score override endpoints.

Contract under test:
- GET  /api/v1/matches/today          -> RTL "Option A" schedule cards
- GET  /api/v1/matches/{id}           -> hybrid detail (servers, lineups, events, stats, standings)
- POST /api/v1/admin/matches/{id}/streams
- DELETE /api/v1/admin/matches/{id}/streams/{server_id}
- POST /api/v1/admin/matches/{id}/override
- DELETE /api/v1/admin/matches/{id}/override
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

_src_path = str(Path(__file__).resolve().parents[2] / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

import pytest
from fastapi.testclient import TestClient

from live_score.api.app import create_app
from live_score.api.catalog import LiveFixturesCatalog
from live_score.api.store import AdminStore
from live_score.domain.models import (
    League,
    LineupPlayer,
    Match,
    MatchDetail,
    MatchEvent,
    MatchStatus,
    StreamServer,
    Team,
)

FIXED_NOW = datetime(2026, 11, 18, 16, 0, tzinfo=timezone.utc)  # 19:00 in Riyadh
ADMIN_TOKEN = "test-admin-token"
ADMIN_HEADERS = {"X-Admin-Token": ADMIN_TOKEN}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def real_madrid():
    return Team(id="real", name_ar="ريال مدريد", name_en="Real Madrid")


@pytest.fixture
def barcelona():
    return Team(id="barca", name_ar="برشلونة", name_en="Barcelona")


@pytest.fixture
def la_liga():
    return League(
        id="laliga",
        name_ar="الدوري الإسباني",
        name_en="La Liga",
        round="الجولة 12",
    )


def _make_match(
    match_id: str,
    home: Team,
    away: Team,
    league: League,
    status: MatchStatus,
    kickoff: datetime,
    home_score: int = 0,
    away_score: int = 0,
    elapsed: int | None = None,
    servers: list[StreamServer] | None = None,
) -> Match:
    return Match(
        id=match_id,
        home_team=home,
        away_team=away,
        league=league,
        status=status,
        kickoff_time=kickoff,
        home_score=home_score,
        away_score=away_score,
        elapsed_time=elapsed,
        stream_servers=servers or [],
        channel="beIN Sports 1",
        commentator="عصام الشوالي",
        stadium="Santiago Bernabéu",
        referee="Mateu Lahoz",
    )


def _home_lineup() -> list[LineupPlayer]:
    return [
        LineupPlayer(name="Thibaut Courtois", number=1, position="GK", grid_position="1:1"),
        LineupPlayer(name="Dani Carvajal", number=2, position="DF", grid_position="2:1"),
        LineupPlayer(name="Eder Militao", number=3, position="DF", grid_position="2:2"),
        LineupPlayer(name="Antonio Rudiger", number=4, position="DF", grid_position="2:3"),
        LineupPlayer(name="Ferland Mendy", number=23, position="DF", grid_position="2:4"),
        LineupPlayer(name="Aurelien Tchouameni", number=18, position="MF", grid_position="3:2"),
        LineupPlayer(name="Federico Valverde", number=15, position="MF", grid_position="3:3"),
        LineupPlayer(name="Jude Bellingham", number=5, position="MF", grid_position="4:2"),
        LineupPlayer(name="Vinicius Junior", number=7, position="FW", grid_position="5:1"),
        LineupPlayer(name="Kylian Mbappe", number=9, position="FW", grid_position="5:2"),
        LineupPlayer(name="Rodrygo", number=11, position="FW", grid_position="5:3"),
    ]


def _away_lineup() -> list[LineupPlayer]:
    return [
        LineupPlayer(name="Marc-Andre ter Stegen", number=1, position="GK", grid_position="1:1"),
        LineupPlayer(name="Jules Kounde", number=23, position="DF", grid_position="2:1"),
        LineupPlayer(name="Ronald Araujo", number=4, position="DF", grid_position="2:2"),
        LineupPlayer(name="Pau Cubarsi", number=2, position="DF", grid_position="2:3"),
        LineupPlayer(name="Alejandro Balde", number=3, position="DF", grid_position="2:4"),
        LineupPlayer(name="Frenkie de Jong", number=21, position="MF", grid_position="3:2"),
        LineupPlayer(name="Pedri", number=8, position="MF", grid_position="3:3"),
        LineupPlayer(name="Lamine Yamal", number=19, position="FW", grid_position="4:1"),
        LineupPlayer(name="Dani Olmo", number=20, position="MF", grid_position="4:2"),
        LineupPlayer(name="Raphinha", number=11, position="FW", grid_position="4:3"),
        LineupPlayer(name="Robert Lewandowski", number=9, position="FW", grid_position="5:2"),
    ]


def _servers() -> list[StreamServer]:
    return [
        StreamServer(
            id="srv_1",
            server_name="سيرفر 1 - متعدد الجودات",
            url="https://live.example/embed/1",
            type="iframe",
            quality="multiquality",
        ),
        StreamServer(
            id="srv_2",
            server_name="سيرفر 2 - يوتيوب",
            url="https://www.youtube.com/embed/demo",
            type="iframe",
            quality="youtube",
        ),
    ]


def _live_detail(home, away, league) -> MatchDetail:
    return MatchDetail(
        match=_make_match(
            "match_live",
            home,
            away,
            league,
            MatchStatus.IN_PLAY,
            FIXED_NOW - timedelta(minutes=68),
            home_score=2,
            away_score=1,
            elapsed=68,
            servers=_servers(),
        ),
        home_lineup=_home_lineup(),
        away_lineup=_away_lineup(),
        events=[
            MatchEvent(
                minute=12,
                type="goal",
                player_name="Kylian Mbappe",
                team_id="real",
                description_ar="هدف افتتاحي لريال مدريد",
            ),
            MatchEvent(
                minute=41,
                type="goal",
                player_name="Robert Lewandowski",
                team_id="barca",
                description_ar="هدف التعادل لبرشلونة",
            ),
            MatchEvent(
                minute=63,
                type="yellow_card",
                player_name="Ronald Araujo",
                team_id="barca",
                description_ar="بطاقة صفراء",
            ),
            MatchEvent(
                minute=66,
                type="goal",
                player_name="Jude Bellingham",
                team_id="real",
                description_ar="هدف التقدم لريال مدريد",
            ),
        ],
        stats={
            "possession": {"label_ar": "الاستحواذ", "home": 58, "away": 42, "unit": "%"},
            "shots": {"label_ar": "التسديدات", "home": 14, "away": 9, "unit": ""},
            "shots_on_target": {"label_ar": "على المرمى", "home": 6, "away": 4, "unit": ""},
            "corners": {"label_ar": "الركنيات", "home": 5, "away": 2, "unit": ""},
        },
        standings=[
            {
                "position": 1,
                "team_name_ar": "ريال مدريد",
                "played": 12,
                "won": 10,
                "drawn": 1,
                "lost": 1,
                "goals_for": 28,
                "goals_against": 10,
                "points": 31,
                "is_home": True,
                "is_away": False,
            },
            {
                "position": 2,
                "team_name_ar": "برشلونة",
                "played": 12,
                "won": 9,
                "drawn": 2,
                "lost": 1,
                "goals_for": 30,
                "goals_against": 13,
                "points": 29,
                "is_home": False,
                "is_away": True,
            },
        ],
    )


def _scheduled_detail(home, away, league) -> MatchDetail:
    return MatchDetail(
        match=_make_match(
            "match_upcoming",
            home,
            away,
            league,
            MatchStatus.SCHEDULED,
            FIXED_NOW + timedelta(hours=2),
        )
    )


def _finished_detail(home, away, league) -> MatchDetail:
    return MatchDetail(
        match=_make_match(
            "match_finished",
            home,
            away,
            league,
            MatchStatus.FINISHED,
            FIXED_NOW - timedelta(hours=3),
            home_score=1,
            away_score=1,
            elapsed=90,
        )
    )


def _postponed_detail(home, away, league) -> MatchDetail:
    return MatchDetail(
        match=_make_match(
            "match_postponed",
            home,
            away,
            league,
            MatchStatus.POSTPONED,
            FIXED_NOW + timedelta(hours=4),
        )
    )


@pytest.fixture
def fixtures(real_madrid, barcelona, la_liga):
    return [
        _live_detail(real_madrid, barcelona, la_liga),
        _scheduled_detail(real_madrid, barcelona, la_liga),
        _finished_detail(real_madrid, barcelona, la_liga),
        _postponed_detail(real_madrid, barcelona, la_liga),
    ]


@pytest.fixture
def app_factory(fixtures, tmp_path):
    def _build(db_name: str = "live_score_test.db", fixture_list=None):
        return create_app(
            fixtures=fixture_list if fixture_list is not None else fixtures,
            db_path=str(tmp_path / db_name),
            admin_token=ADMIN_TOKEN,
            clock=lambda: FIXED_NOW,
            timezone_name="Asia/Riyadh",
        )

    return _build


@pytest.fixture
def client(app_factory):
    app = app_factory()
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def test_public_today_returns_rtl_option_a_card_contract(client):
    response = client.get("/api/v1/matches/today")
    assert response.status_code == 200

    payload = response.json()
    assert payload["date"] == "2026-11-18"
    assert payload["timezone"] == "Asia/Riyadh"
    assert payload["timezone_label_ar"] == "بتوقيت مكة المكرمة"

    matches = payload["matches"]
    assert len(matches) == 4
    live = next(m for m in matches if m["id"] == "match_live")

    assert live["home_team"]["name_ar"] == "ريال مدريد"
    assert live["away_team"]["name_ar"] == "برشلونة"
    assert live["league"]["name_ar"] == "الدوري الإسباني"
    assert live["status"] == "IN_PLAY"
    assert live["status_label_ar"] == "مباشر الآن"
    assert live["home_score"] == 2
    assert live["away_score"] == 1
    assert live["elapsed_time"] == 68
    assert live["live_minute_label"] == "68'"
    assert live["competition_subtitle"] == "الدوري الإسباني • الجولة 12"
    assert live["kickoff_time_local"] == "17:52"
    assert live["kickoff_date_local"] == "2026-11-18"
    assert live["kickoff_time_utc"].startswith("2026-11-18T14:52:00")
    assert live["countdown_seconds"] is None
    assert live["is_admin_override"] is False


def test_public_today_state_labels_and_upcoming_countdown(client):
    response = client.get("/api/v1/matches/today")
    matches = {m["id"]: m for m in response.json()["matches"]}

    upcoming = matches["match_upcoming"]
    assert upcoming["status_label_ar"] == "لم تبدأ"
    assert upcoming["countdown_seconds"] == 7200
    assert upcoming["live_minute_label"] is None

    finished = matches["match_finished"]
    assert finished["status_label_ar"] == "انتهت"
    assert finished["countdown_seconds"] is None

    postponed = matches["match_postponed"]
    assert postponed["status_label_ar"] == "مؤجلة"


def test_public_today_filters_by_local_date_and_rejects_bad_timezone(client):
    empty = client.get("/api/v1/matches/today", params={"date": "2026-11-19"})
    assert empty.status_code == 200
    assert empty.json()["matches"] == []

    bad_tz = client.get("/api/v1/matches/today", params={"tz": "Mars/Olympus"})
    assert bad_tz.status_code == 400


def test_public_match_detail_returns_hybrid_center_payload(client):
    response = client.get("/api/v1/matches/match_live")
    assert response.status_code == 200
    payload = response.json()

    assert payload["match"]["id"] == "match_live"
    assert payload["match"]["home_score"] == 2
    assert payload["match"]["channel"] == "beIN Sports 1"
    assert payload["match"]["commentator"] == "عصام الشوالي"

    assert len(payload["servers"]) == 2
    assert payload["servers"][0]["server_name"] == "سيرفر 1 - متعدد الجودات"
    assert payload["servers"][0]["type"] == "iframe"
    assert "allow-scripts" in payload["servers"][0]["sandbox"]

    assert len(payload["home_lineup"]) == 11
    assert payload["home_lineup"][0]["name"] == "Thibaut Courtois"
    assert len(payload["away_lineup"]) == 11
    assert payload["away_lineup"][9]["name"] == "Raphinha"

    assert len(payload["events"]) == 4
    assert payload["events"][0]["type"] == "goal"

    stats = {row["key"]: row for row in payload["stats"]}
    assert stats["possession"]["label_ar"] == "الاستحواذ"
    assert stats["possession"]["home"] == 58
    assert stats["possession"]["unit"] == "%"

    assert len(payload["standings"]) == 2
    assert payload["standings"][0]["team_name_ar"] == "ريال مدريد"
    assert payload["standings"][0]["is_home"] is True


def test_public_match_detail_unknown_match_returns_404(client):
    response = client.get("/api/v1/matches/does_not_exist")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Admin authentication
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "headers",
    [{}, {"X-Admin-Token": "wrong-token"}],
)
def test_admin_endpoints_require_valid_token(client, headers):
    response = client.post(
        "/api/v1/admin/matches/match_live/streams",
        headers=headers,
        json={
            "server_name": "سيرفر اختبار",
            "url": "https://live.example/embed/test",
            "type": "iframe",
        },
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Admin stream management
# ---------------------------------------------------------------------------

def test_admin_stream_override_endpoint_adds_and_edits_servers(client):
    created = client.post(
        "/api/v1/admin/matches/match_live/streams",
        headers=ADMIN_HEADERS,
        json={
            "server_name": "سيرفر 3 - احتياطي",
            "url": "https://backup.example/embed/3",
            "type": "iframe",
            "quality": "hd",
        },
    )
    assert created.status_code == 201
    created_payload = created.json()
    assert created_payload["match_id"] == "match_live"
    assert len(created_payload["servers"]) == 3
    assert created_payload["servers"][0]["server_name"] == "سيرفر 3 - احتياطي"
    assert created_payload["servers"][0]["is_active"] is True

    detail = client.get("/api/v1/matches/match_live").json()
    assert len(detail["servers"]) == 3
    assert detail["servers"][0]["url"] == "https://backup.example/embed/3"

    # Editing the same URL must update the existing row, not duplicate it.
    edited = client.post(
        "/api/v1/admin/matches/match_live/streams",
        headers=ADMIN_HEADERS,
        json={
            "server_name": "سيرفر 3 - محدث",
            "url": "https://backup.example/embed/3",
            "type": "iframe",
            "quality": "sd",
            "is_active": False,
        },
    )
    assert edited.status_code == 201
    servers = edited.json()["servers"]
    assert len(servers) == 3
    assert servers[0]["server_name"] == "سيرفر 3 - محدث"
    assert servers[0]["quality"] == "sd"
    assert servers[0]["is_active"] is False


def test_admin_stream_deletion_restores_previous_fallback(client):
    created = client.post(
        "/api/v1/admin/matches/match_live/streams",
        headers=ADMIN_HEADERS,
        json={
            "server_name": "سيرفر مؤقت",
            "url": "https://backup.example/embed/temp",
            "type": "m3u8",
        },
    ).json()
    temp_id = created["servers"][0]["id"]

    deleted = client.delete(
        f"/api/v1/admin/matches/match_live/streams/{temp_id}",
        headers=ADMIN_HEADERS,
    )
    assert deleted.status_code == 200
    assert len(deleted.json()["servers"]) == 2

    missing = client.delete(
        "/api/v1/admin/matches/match_live/streams/not-a-server",
        headers=ADMIN_HEADERS,
    )
    assert missing.status_code == 404


def test_admin_stream_payload_validation(client):
    bad_scheme = client.post(
        "/api/v1/admin/matches/match_live/streams",
        headers=ADMIN_HEADERS,
        json={
            "server_name": "خبيث",
            "url": "javascript:alert(1)",
            "type": "iframe",
        },
    )
    assert bad_scheme.status_code == 422

    bad_type = client.post(
        "/api/v1/admin/matches/match_live/streams",
        headers=ADMIN_HEADERS,
        json={
            "server_name": "نوع خاطئ",
            "url": "https://live.example/embed/rtmp",
            "type": "rtmp",
        },
    )
    assert bad_type.status_code == 422

    unknown_match = client.post(
        "/api/v1/admin/matches/nope/streams",
        headers=ADMIN_HEADERS,
        json={
            "server_name": "سيرفر",
            "url": "https://live.example/embed/x",
            "type": "iframe",
        },
    )
    assert unknown_match.status_code == 404


# ---------------------------------------------------------------------------
# Admin manual score override
# ---------------------------------------------------------------------------

def test_admin_manual_score_override_persists_and_beats_api_sync(app_factory):
    app = app_factory()
    with TestClient(app) as client:
        override = client.post(
            "/api/v1/admin/matches/match_live/override",
            headers=ADMIN_HEADERS,
            json={
                "home_score": 3,
                "away_score": 0,
                "status": "FINISHED",
                "elapsed_time": 90,
                "commentator": "معلق احتياطي",
            },
        )
        assert override.status_code == 200
        payload = override.json()
        assert payload["home_score"] == 3
        assert payload["away_score"] == 0
        assert payload["status"] == "FINISHED"
        assert payload["status_label_ar"] == "انتهت"
        assert payload["is_admin_override"] is True
        assert payload["commentator"] == "معلق احتياطي"

        # An automated API sync changes the underlying fixture...
        api_match = app.state.fixtures["match_live"].match
        api_match.home_score = 1
        api_match.away_score = 1
        api_match.status = MatchStatus.IN_PLAY
        api_match.elapsed_time = 70

        # ...but the admin override still wins on the public endpoint.
        live = client.get("/api/v1/matches/match_live").json()["match"]
        assert live["home_score"] == 3
        assert live["away_score"] == 0
        assert live["status"] == "FINISHED"

    # A brand-new app process sharing the same SQLite file keeps the override.
    restarted_app = app_factory(db_name="live_score_test.db")
    with TestClient(restarted_app) as restarted_client:
        live = restarted_client.get("/api/v1/matches/match_live").json()["match"]
        assert live["home_score"] == 3
        assert live["away_score"] == 0
        assert live["status"] == "FINISHED"
        assert live["is_admin_override"] is True


def test_admin_override_clear_restores_api_values(client):
    client.post(
        "/api/v1/admin/matches/match_live/override",
        headers=ADMIN_HEADERS,
        json={"home_score": 5, "away_score": 4, "status": "FINISHED"},
    )
    cleared = client.delete(
        "/api/v1/admin/matches/match_live/override",
        headers=ADMIN_HEADERS,
    )
    assert cleared.status_code == 200

    live = client.get("/api/v1/matches/match_live").json()["match"]
    assert live["home_score"] == 2
    assert live["away_score"] == 1
    assert live["status"] == "IN_PLAY"
    assert live["is_admin_override"] is False


def test_admin_override_payload_validation(client):
    negative = client.post(
        "/api/v1/admin/matches/match_live/override",
        headers=ADMIN_HEADERS,
        json={"home_score": -1},
    )
    assert negative.status_code == 422

    bad_status = client.post(
        "/api/v1/admin/matches/match_live/override",
        headers=ADMIN_HEADERS,
        json={"status": "ABANDONED_FOREVER"},
    )
    assert bad_status.status_code == 422

    unknown_match = client.post(
        "/api/v1/admin/matches/nope/override",
        headers=ADMIN_HEADERS,
        json={"home_score": 1},
    )
    assert unknown_match.status_code == 404


def test_admin_store_allows_same_server_id_across_different_matches(tmp_path):
    store = AdminStore(str(tmp_path / "test.db"))
    store.upsert_stream("match_a", {"id": "srv_shared", "server_name": "سيرفر أ", "url": "https://srv.example/a", "type": "iframe"})
    store.upsert_stream("match_b", {"id": "srv_shared", "server_name": "سيرفر ب", "url": "https://srv.example/b", "type": "m3u8"})

    streams_a = store.list_streams("match_a")
    streams_b = store.list_streams("match_b")
    assert len(streams_a) == 1
    assert len(streams_b) == 1
    assert streams_a[0]["id"] == "srv_shared"
    assert streams_a[0]["url"] == "https://srv.example/a"
    assert streams_b[0]["id"] == "srv_shared"
    assert streams_b[0]["url"] == "https://srv.example/b"

    # Deleting from match_a does not affect match_b
    assert store.delete_stream("match_a", "srv_shared") is True
    assert len(store.list_streams("match_a")) == 0
    assert len(store.list_streams("match_b")) == 1
    store.close()


def test_admin_store_migrates_legacy_single_pk_schema_preserving_rows(tmp_path):
    import sqlite3
    db_file = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute(
        """
        CREATE TABLE admin_streams (
            server_id TEXT PRIMARY KEY,
            match_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO admin_streams VALUES
        ('srv_1', 'match_1', '{"id": "srv_1", "url": "https://legacy.example/1", "server_name": "سيرفر 1"}', 0, '2026-11-20T12:00:00Z'),
        ('srv_2', 'match_2', '{"id": "srv_2", "url": "https://legacy.example/2", "server_name": "سيرفر 2"}', 0, '2026-11-20T12:00:00Z')
        """
    )
    conn.commit()
    conn.close()

    # Opening with AdminStore should migrate the schema
    store = AdminStore(str(db_file))
    streams_1 = store.list_streams("match_1")
    streams_2 = store.list_streams("match_2")
    assert len(streams_1) == 1
    assert streams_1[0]["url"] == "https://legacy.example/1"
    assert len(streams_2) == 1
    assert streams_2[0]["url"] == "https://legacy.example/2"

    # Now inserting srv_1 under match_2 should succeed because PK is (match_id, server_id)
    store.upsert_stream("match_2", {"id": "srv_1", "server_name": "سيرفر مشترك", "url": "https://legacy.example/shared", "type": "iframe"})
    updated_streams_2 = store.list_streams("match_2")
    assert len(updated_streams_2) == 2
    store.close()


def test_admin_endpoints_work_on_dynamically_refreshed_catalog_matches(tmp_path):
    class DynClient:
        def __init__(self, match):
            self.match = match
        def fetch_window(self, start, end, leagues=None):
            return [self.match]
        def fetch_detail(self, league_slug, event_id, match=None):
            return MatchDetail(match=self.match)

    dyn_match = Match(
        id="live-999",
        source_ref="esp.1:999",
        home_team=Team(id="h", name_ar="فريق أ", name_en="Team A"),
        away_team=Team(id="a", name_ar="فريق ب", name_en="Team B"),
        league=League(id="l", name_ar="الدوري", name_en="League"),
        status=MatchStatus.IN_PLAY,
        kickoff_time=FIXED_NOW,
        home_score=1,
        away_score=0,
    )
    dyn_client = DynClient(dyn_match)
    catalog = LiveFixturesCatalog(
        client=dyn_client,
        leagues=["esp.1"],
        background_refresh=False,
        clock=lambda: FIXED_NOW,
    )
    catalog.refresh(FIXED_NOW)

    app = create_app(
        fixtures=[],
        db_path=str(tmp_path / "dyn.db"),
        admin_token=ADMIN_TOKEN,
        clock=lambda: FIXED_NOW,
        timezone_name="Asia/Riyadh",
    )
    app.state.catalog = catalog

    with TestClient(app) as test_client:
        # Override dynamically refreshed catalog match
        override_res = test_client.post(
            "/api/v1/admin/matches/live-999/override",
            headers=ADMIN_HEADERS,
            json={"home_score": 4},
        )
        assert override_res.status_code == 200
        assert override_res.json()["home_score"] == 4

        # Add stream to dynamically refreshed catalog match
        stream_res = test_client.post(
            "/api/v1/admin/matches/live-999/streams",
            headers=ADMIN_HEADERS,
            json={"server_name": "سيرفر خاص", "url": "https://stream.example/live", "type": "iframe"},
        )
        assert stream_res.status_code == 201

        # Public detail reflects both
        detail_res = test_client.get("/api/v1/matches/live-999")
        assert detail_res.status_code == 200
        data = detail_res.json()
        assert data["match"]["home_score"] == 4
        assert any(s["url"] == "https://stream.example/live" for s in data["servers"])


def test_admin_list_matches_requires_auth_and_returns_streams_and_override_state(client):
    # Unauthenticated must 401
    unauth = client.get("/api/v1/admin/matches")
    assert unauth.status_code == 401

    # Apply an override and a stream to match_live
    client.post(
        "/api/v1/admin/matches/match_live/override",
        headers=ADMIN_HEADERS,
        json={"home_score": 5, "commentator": "معلق محدث"},
    )
    client.post(
        "/api/v1/admin/matches/match_live/streams",
        headers=ADMIN_HEADERS,
        json={"server_name": "سيرفر الإدارة", "url": "https://admin.example/live", "type": "iframe"},
    )

    res = client.get("/api/v1/admin/matches", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    payload = res.json()
    assert "matches" in payload
    assert payload["timezone"] == "Asia/Riyadh"

    live = next(m for m in payload["matches"] if m["match"]["id"] == "match_live")
    assert live["match"]["home_score"] == 5
    assert live["override"] is not None
    assert live["override"]["home_score"] == 5
    assert len(live["admin_server_ids"]) > 0
    assert any(s["url"] == "https://admin.example/live" for s in live["servers"])

    # Test filtering by date
    res_date = client.get("/api/v1/admin/matches?date=2026-11-18", headers=ADMIN_HEADERS)
    assert res_date.status_code == 200
    assert len(res_date.json()["matches"]) > 0

    res_empty_date = client.get("/api/v1/admin/matches?date=2025-01-01", headers=ADMIN_HEADERS)
    assert res_empty_date.status_code == 200
    assert len(res_empty_date.json()["matches"]) == 0

    # Test filtering by query q (Arabic and English)
    res_q_en = client.get("/api/v1/admin/matches?q=Madrid", headers=ADMIN_HEADERS)
    assert res_q_en.status_code == 200
    assert len(res_q_en.json()["matches"]) > 0

    res_q_ar = client.get("/api/v1/admin/matches?q=مدريد", headers=ADMIN_HEADERS)
    assert res_q_ar.status_code == 200
    assert len(res_q_ar.json()["matches"]) > 0

    res_q_none = client.get("/api/v1/admin/matches?q=UnknownTeamXYZ", headers=ADMIN_HEADERS)
    assert res_q_none.status_code == 200
    assert len(res_q_none.json()["matches"]) == 0


def test_public_match_detail_respects_tz_query_param_and_rejects_bad_tz(client):
    # FIXED_NOW is 16:00 UTC. match_live kickoff is FIXED_NOW - 68m = 14:52 UTC.
    res_utc = client.get("/api/v1/matches/match_live?tz=UTC")
    assert res_utc.status_code == 200
    assert res_utc.json()["match"]["kickoff_time_local"] == "14:52"

    res_riyadh = client.get("/api/v1/matches/match_live?tz=Asia/Riyadh")
    assert res_riyadh.status_code == 200
    assert res_riyadh.json()["match"]["kickoff_time_local"] == "17:52"

    res_bad = client.get("/api/v1/matches/match_live?tz=Invalid/Zone")
    assert res_bad.status_code == 400


