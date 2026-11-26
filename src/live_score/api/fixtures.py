"""Fixture sources for the API.

The hosted livescoreFootball API is the default source.  Set
``LIVE_SCORE_API_URL=demo`` (or point the variable at a compatible self-hosted
instance) to change that.  When the upstream is unreachable the catalog keeps
its last good snapshot, then falls back to a deterministic Arabic demo
matchday so the RTL frontend can always boot.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from live_score.adapters.fallback import FallbackSoccerClient
from live_score.adapters.scraper_adapter import PortalScraperAdapter
from live_score.adapters.livescore_v2 import (
    DEFAULT_BASE_URL,
    DEFAULT_LEAGUE_SLUGS,
    EspnSoccerClient,
    LiveScoreV2Client,
)
from live_score.api.catalog import LiveFixturesCatalog
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

logger = logging.getLogger(__name__)


def _team(team_id: str, name_ar: str, name_en: str) -> Team:
    return Team(id=team_id, name_ar=name_ar, name_en=name_en)


def _league(
    league_id: str,
    name_ar: str,
    name_en: str,
    round_name: str,
) -> League:
    return League(
        id=league_id,
        name_ar=name_ar,
        name_en=name_en,
        round=round_name,
    )


def _streams() -> list[StreamServer]:
    return [
        StreamServer(
            id="srv_demo_1",
            server_name="سيرفر 1 - متعدد الجودات",
            url="https://live.example/embed/clasico/multi",
            type="iframe",
            quality="multiquality",
        ),
        StreamServer(
            id="srv_demo_2",
            server_name="سيرفر 2 - HD",
            url="https://live.example/embed/clasico/hd",
            type="iframe",
            quality="hd",
        ),
        StreamServer(
            id="srv_demo_3",
            server_name="سيرفر 3 - يوتيوب",
            url="https://www.youtube.com/embed/demo-clasico",
            type="iframe",
            quality="youtube",
        ),
        StreamServer(
            id="srv_demo_4",
            server_name="سيرفر 4 - ضعيف للهواتف",
            url="https://live.example/hls/clasico-mobile.m3u8",
            type="m3u8",
            quality="sd",
            sandbox=None,
        ),
    ]


def _real_madrid_lineup() -> list[LineupPlayer]:
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


def _barcelona_lineup() -> list[LineupPlayer]:
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


def _clasico_events() -> list[MatchEvent]:
    return [
        MatchEvent(
            id="ev_demo_1",
            minute=12,
            type="goal",
            player_name="Kylian Mbappe",
            team_id="real_madrid",
            description_ar="هدف افتتاحي لريال مدريد بعد هجمة مرتدة سريعة",
        ),
        MatchEvent(
            id="ev_demo_2",
            minute=28,
            type="yellow_card",
            player_name="Ronald Araujo",
            team_id="barcelona",
            description_ar="بطاقة صفراء بسبب عرقلة متعمدة",
        ),
        MatchEvent(
            id="ev_demo_3",
            minute=41,
            type="goal",
            player_name="Robert Lewandowski",
            team_id="barcelona",
            description_ar="هدف التعادل لبرشلونة من ضربة رأس",
        ),
        MatchEvent(
            id="ev_demo_4",
            minute=55,
            type="var",
            player_name="Jude Bellingham",
            team_id="real_madrid",
            description_ar="مراجعة تقنية الفيديو تؤكد صحة هدف الريال",
        ),
        MatchEvent(
            id="ev_demo_5",
            minute=63,
            type="goal",
            player_name="Jude Bellingham",
            team_id="real_madrid",
            description_ar="هدف التقدم لريال مدريد في الشوط الثاني",
        ),
        MatchEvent(
            id="ev_demo_6",
            minute=66,
            type="substitution",
            player_name="Lamine Yamal",
            team_id="barcelona",
            description_ar="تبديل هجومي لبرشلونة بحثاً عن التعادل",
        ),
    ]


def _clasico_stats() -> dict[str, dict[str, object]]:
    return {
        "possession": {"label_ar": "الاستحواذ", "home": 58, "away": 42, "unit": "%"},
        "shots": {"label_ar": "التسديدات", "home": 14, "away": 9, "unit": ""},
        "shots_on_target": {"label_ar": "التسديدات على المرمى", "home": 6, "away": 4, "unit": ""},
        "corners": {"label_ar": "الركنيات", "home": 5, "away": 2, "unit": ""},
        "fouls": {"label_ar": "الأخطاء", "home": 9, "away": 13, "unit": ""},
        "offsides": {"label_ar": "التسلل", "home": 2, "away": 1, "unit": ""},
    }


def _la_liga_table() -> list[dict[str, object]]:
    return [
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
        {
            "position": 3,
            "team_name_ar": "أتلتيكو مدريد",
            "played": 12,
            "won": 8,
            "drawn": 3,
            "lost": 1,
            "goals_for": 24,
            "goals_against": 11,
            "points": 27,
        },
        {
            "position": 4,
            "team_name_ar": "أتلتيك بلباو",
            "played": 12,
            "won": 7,
            "drawn": 3,
            "lost": 2,
            "goals_for": 21,
            "goals_against": 12,
            "points": 24,
        },
    ]


def build_demo_fixtures(now: datetime | None = None) -> list[MatchDetail]:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    real = _team("real_madrid", "ريال مدريد", "Real Madrid")
    barca = _team("barcelona", "برشلونة", "Barcelona")
    hilal = _team("al_hilal", "الهلال", "Al Hilal")
    nassr = _team("al_nassr", "النصر", "Al Nassr")
    liverpool = _team("liverpool", "ليفربول", "Liverpool")
    city = _team("man_city", "مانشستر سيتي", "Manchester City")
    wydad = _team("wydad", "الوداد", "Wydad AC")
    raja = _team("raja", "الرجاء", "Raja CA")

    la_liga = _league("la_liga", "الدوري الإسباني", "La Liga", "الجولة 12")
    saudi = _league("saudi_pl", "دوري روشن السعودي", "Saudi Pro League", "الجولة 10")
    premier = _league("premier_league", "الدوري الإنجليزي الممتاز", "Premier League", "الجولة 12")
    botola = _league("botola", "البطولة المغربية", "Botola Pro", "الجولة 9")

    clasico = Match(
        id="match_clasico",
        home_team=real,
        away_team=barca,
        league=la_liga,
        status=MatchStatus.IN_PLAY,
        kickoff_time=now - timedelta(minutes=68),
        home_score=2,
        away_score=1,
        elapsed_time=68,
        stream_servers=_streams(),
        channel="beIN Sports 1",
        commentator="عصام الشوالي",
        stadium="سانتياغو برنابيو",
        referee="ماتيو لاهوز",
    )

    hilal_nassr = Match(
        id="match_hilal_nassr",
        home_team=hilal,
        away_team=nassr,
        league=saudi,
        status=MatchStatus.SCHEDULED,
        kickoff_time=now + timedelta(hours=2),
        home_score=0,
        away_score=0,
        stream_servers=[
            StreamServer(
                id="srv_hilal_1",
                server_name="سيرفر 1 - SSC",
                url="https://live.example/embed/hilal-nassr/ssc",
                type="iframe",
                quality="hd",
            )
        ],
        channel="SSC 1",
        commentator="فهد العتيبي",
        stadium="ملعب المملكة أرينا",
        referee="محمد الهويش",
    )

    liverpool_city = Match(
        id="match_liverpool_city",
        home_team=liverpool,
        away_team=city,
        league=premier,
        status=MatchStatus.FINISHED,
        kickoff_time=now - timedelta(hours=3),
        home_score=1,
        away_score=1,
        elapsed_time=90,
        channel="beIN Sports 2",
        commentator="حفيظ دراجي",
        stadium="أنفيلد",
        referee="مايكل أوليفر",
    )

    moroccan_derby = Match(
        id="match_moroccan_derby",
        home_team=wydad,
        away_team=raja,
        league=botola,
        status=MatchStatus.POSTPONED,
        kickoff_time=now + timedelta(hours=4),
        home_score=0,
        away_score=0,
        stadium="مركب محمد الخامس",
        referee="المهدي الشرقاوي",
    )

    return [
        MatchDetail(
            match=clasico,
            home_lineup=_real_madrid_lineup(),
            away_lineup=_barcelona_lineup(),
            events=_clasico_events(),
            stats=_clasico_stats(),
            standings=_la_liga_table(),
        ),
        MatchDetail(match=hilal_nassr),
        MatchDetail(match=liverpool_city),
        MatchDetail(match=moroccan_derby),
    ]


def _build_live_client(base_url: str):
    """Build the upstream client, defaulting to ESPN as primary with worldcup26.ir as secondary."""
    fallback_mode = os.getenv("LIVE_SCORE_ESPN_FALLBACK", "on").strip().lower()
    fallback_enabled = fallback_mode not in {"off", "0", "false", "no"}

    clean_url = (base_url or "").strip()
    if clean_url:
        primary = LiveScoreV2Client(base_url=clean_url)
        if fallback_enabled:
            return FallbackSoccerClient(primary, EspnSoccerClient())
        return primary

    # Default: ESPN is primary, worldcup26.ir is secondary
    primary = EspnSoccerClient()
    if fallback_enabled:
        return FallbackSoccerClient(primary, LiveScoreV2Client(base_url=DEFAULT_BASE_URL))
    return primary


def create_catalog(now: datetime | None = None) -> Optional[LiveFixturesCatalog]:
    """Build the live catalog, or ``None`` when demo mode is forced."""
    now = now or datetime.now(timezone.utc)
    configured = os.getenv("LIVE_SCORE_API_URL", "").strip()
    if configured.lower() == "demo":
        return None

    raw_leagues = os.getenv("LIVE_SCORE_LEAGUES", "").strip()
    leagues = tuple(
        slug.strip() for slug in raw_leagues.split(",") if slug.strip()
    ) or DEFAULT_LEAGUE_SLUGS

    snapshot_mode = os.getenv("LIVE_SCORE_SNAPSHOT", "on").strip().lower()
    snapshot_path: Optional[str] = None
    if snapshot_mode not in {"off", "0", "false", "no"}:
        snapshot_path = (
            os.getenv(
                "LIVE_SCORE_SNAPSHOT_PATH", "data/live_fixtures_snapshot.json"
            ).strip()
            or None
        )
    try:
        snapshot_max_age = float(
            os.getenv("LIVE_SCORE_SNAPSHOT_MAX_AGE_HOURS", "36")
        )
    except ValueError:
        snapshot_max_age = 36.0

    scraper_url = os.getenv("LIVE_SCORE_SCRAPER_URL", "").strip()
    scraper = PortalScraperAdapter(base_url=scraper_url) if scraper_url else None

    catalog = LiveFixturesCatalog(
        _build_live_client(configured),
        leagues,
        demo_loader=build_demo_fixtures,
        snapshot_path=snapshot_path,
        snapshot_max_age_hours=snapshot_max_age,
        scraper=scraper,
    )
    # Never block startup on the upstream: publish the demo slate immediately,
    # then swap in live fixtures as soon as the background refresh lands.
    catalog.seed_demo(now)
    catalog.refresh(now)
    return catalog


def load_fixtures(now: datetime | None = None) -> list[MatchDetail]:
    """Load the current slate, falling back to the demo matchday when needed."""
    now = now or datetime.now(timezone.utc)
    catalog = create_catalog(now)
    if catalog is None:
        return build_demo_fixtures(now)
    return catalog.fixtures(now)
