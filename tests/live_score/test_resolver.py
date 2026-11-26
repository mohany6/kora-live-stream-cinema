"""
Tests for Core Domain Models and Priority Ingestion Resolver.
Covers:
1. Domain model schemas and validation (Match, Team, League, StreamServer, MatchEvent, LineupPlayer, MatchDetail, MatchStatus)
2. Admin override taking full precedence over API and scraper updates.
3. API taking precedence over scraper updates when no admin override is present.
4. Stream servers from scraper being merged when API match has no stream servers.
5. TeamAliasMatcher resolving common Arabic names and handling unknown names gracefully.
"""

from datetime import datetime, timezone
from pathlib import Path
import sys

# Ensure src directory is in sys.path
_src_path = str(Path(__file__).resolve().parents[2] / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

import pytest

from live_score.domain.models import (
    Match,
    Team,
    League,
    StreamServer,
    MatchEvent,
    LineupPlayer,
    MatchDetail,
    MatchStatus,
)
from live_score.domain.resolver import (
    PriorityResolver,
    TeamAliasMatcher,
)


@pytest.fixture
def sample_teams():
    home = Team(id="team_che", name_ar="تشيلسي", name_en="Chelsea", logo_url="https://img.example/chelsea.png")
    away = Team(id="team_liv", name_ar="ليفربول", name_en="Liverpool", logo_url="https://img.example/liverpool.png")
    return home, away


@pytest.fixture
def sample_league():
    return League(
        id="eng_pl",
        name_ar="الدوري الإنجليزي الممتاز",
        name_en="Premier League",
        round="الجولة 12",
        logo_url="https://img.example/pl.png",
    )


def test_domain_models_creation(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    server = StreamServer(
        id="srv_1",
        server_name="سيرفر 1 - متعدد الجودات",
        url="https://stream.example/feed.m3u8",
        type="m3u8",
        is_active=True,
        quality="1080p",
    )

    match = Match(
        id="match_101",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.SCHEDULED,
        kickoff_time=kickoff,
        home_score=0,
        away_score=0,
        stream_servers=[server],
        channel="beIN Sports 1",
        commentator="حفيظ دراجي",
        stadium="Stamford Bridge",
        referee="Michael Oliver",
    )

    assert match.id == "match_101"
    assert match.home_team.name_ar == "تشيلسي"
    assert match.away_team.name_en == "Liverpool"
    assert match.status == MatchStatus.SCHEDULED
    assert len(match.stream_servers) == 1
    assert match.stream_servers[0].type == "m3u8"
    assert match.is_admin_override is False


def test_match_detail_with_lineup_and_events(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    match = Match(
        id="match_102",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=1,
        away_score=0,
        elapsed_time=24,
    )

    player = LineupPlayer(
        id="p_1",
        name="Cole Palmer",
        number=20,
        position="MF",
        is_starter=True,
        grid_position="3:2",
    )

    event = MatchEvent(
        id="ev_1",
        minute=24,
        type="goal",
        player_name="Cole Palmer",
        team_id="team_che",
        description_ar="هدف سجله كول بالمر بعد تمريرة متقنة",
    )

    detail = MatchDetail(
        match=match,
        home_lineup=[player],
        away_lineup=[],
        events=[event],
        stats={"possession": {"home": 58, "away": 42}},
    )

    assert detail.match.id == "match_102"
    assert detail.home_lineup[0].name == "Cole Palmer"
    assert detail.events[0].type == "goal"
    assert detail.stats["possession"]["home"] == 58


def test_priority_resolver_admin_overrides_api_and_scraper(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    # API says 1-0, 55th minute, IN_PLAY
    api_match = Match(
        id="match_100",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=1,
        away_score=0,
        elapsed_time=55,
        channel="beIN Sports 1",
    )

    # Scraper says 1-1, 56th minute
    scraped_server = StreamServer(
        server_name="Scraped Server 1",
        url="https://scraped.stream/live1",
        type="iframe",
    )
    scraped_match = Match(
        id="match_100",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=1,
        away_score=1,
        elapsed_time=56,
        stream_servers=[scraped_server],
    )

    # Admin emergency override says 2-0, FINISHED, custom stream server
    admin_server = StreamServer(
        server_name="Admin Verified Server",
        url="https://admin.stream/verified",
        type="m3u8",
    )
    admin_override = Match(
        id="match_100",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.FINISHED,
        kickoff_time=kickoff,
        home_score=2,
        away_score=0,
        elapsed_time=90,
        stream_servers=[admin_server],
        channel="beIN Sports 1 Premium",
        commentator="عصام الشوالي",
        is_admin_override=True,
    )

    resolved = PriorityResolver.resolve(
        api_match=api_match,
        scraped_match=scraped_match,
        admin_override=admin_override,
    )

    assert resolved.home_score == 2
    assert resolved.away_score == 0
    assert resolved.status == MatchStatus.FINISHED
    assert resolved.is_admin_override is True
    assert resolved.channel == "beIN Sports 1 Premium"
    assert resolved.commentator == "عصام الشوالي"
    assert len(resolved.stream_servers) == 1
    assert resolved.stream_servers[0].server_name == "Admin Verified Server"


def test_priority_resolver_api_takes_precedence_over_scraper(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    # API match has authoritative score and status
    api_match = Match(
        id="match_200",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=2,
        away_score=1,
        elapsed_time=75,
        channel="beIN Sports 2",
    )

    # Scraped match has stale or conflicting score
    scraped_match = Match(
        id="match_200",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=1,
        away_score=1,
        elapsed_time=70,
    )

    resolved = PriorityResolver.resolve(
        api_match=api_match,
        scraped_match=scraped_match,
        admin_override=None,
    )

    assert resolved.home_score == 2
    assert resolved.away_score == 1
    assert resolved.elapsed_time == 75
    assert resolved.channel == "beIN Sports 2"
    assert resolved.is_admin_override is False


def test_priority_resolver_merges_stream_servers_when_api_has_none(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    # API match has no stream servers
    api_match = Match(
        id="match_300",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=0,
        away_score=0,
        stream_servers=[],
    )

    scraped_server1 = StreamServer(
        server_name="سيرفر 1 - سريع",
        url="https://live.kora.com/s1.m3u8",
        type="m3u8",
    )
    scraped_server2 = StreamServer(
        server_name="سيرفر 2 - هاتف",
        url="https://live.kora.com/s2_embed",
        type="iframe",
    )
    scraped_match = Match(
        id="match_300",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=0,
        away_score=0,
        stream_servers=[scraped_server1, scraped_server2],
    )

    resolved = PriorityResolver.resolve(
        api_match=api_match,
        scraped_match=scraped_match,
        admin_override=None,
    )

    assert len(resolved.stream_servers) == 2
    assert resolved.stream_servers[0].server_name == "سيرفر 1 - سريع"
    assert resolved.stream_servers[1].server_name == "سيرفر 2 - هاتف"


def test_priority_resolver_merges_unique_servers_when_both_have_streams(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    api_server = StreamServer(
        server_name="API Official Stream",
        url="https://api.streams/official.m3u8",
        type="m3u8",
    )
    api_match = Match(
        id="match_350",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=1,
        away_score=1,
        stream_servers=[api_server],
    )

    scraped_duplicate = StreamServer(
        server_name="Duplicate Official Stream",
        url="https://api.streams/official.m3u8",
        type="m3u8",
    )
    scraped_new = StreamServer(
        server_name="Scraped Backup Server",
        url="https://scraper.streams/backup.m3u8",
        type="m3u8",
    )
    scraped_match = Match(
        id="match_350",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=1,
        away_score=1,
        stream_servers=[scraped_duplicate, scraped_new],
    )

    resolved = PriorityResolver.resolve(
        api_match=api_match,
        scraped_match=scraped_match,
        admin_override=None,
    )

    # Should keep official stream first, and add the distinct backup stream (ignoring exact URL duplicate)
    assert len(resolved.stream_servers) == 2
    urls = [s.url for s in resolved.stream_servers]
    assert urls == ["https://api.streams/official.m3u8", "https://scraper.streams/backup.m3u8"]


def test_priority_resolver_single_source_fallbacks(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    single_match = Match(
        id="match_400",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.SCHEDULED,
        kickoff_time=kickoff,
    )

    # API only
    res_api = PriorityResolver.resolve(api_match=single_match, scraped_match=None, admin_override=None)
    assert res_api.id == "match_400"
    assert res_api.is_admin_override is False

    # Scraped only
    res_scraped = PriorityResolver.resolve(api_match=None, scraped_match=single_match, admin_override=None)
    assert res_scraped.id == "match_400"
    assert res_scraped.is_admin_override is False

    # Admin only
    res_admin = PriorityResolver.resolve(api_match=None, scraped_match=None, admin_override=single_match)
    assert res_admin.id == "match_400"
    assert res_admin.is_admin_override is True

    # None provided
    with pytest.raises(ValueError, match="At least one match source must be provided"):
        PriorityResolver.resolve(api_match=None, scraped_match=None, admin_override=None)


def test_team_alias_matcher_common_teams():
    assert TeamAliasMatcher.match_team("تشيلسي") == "Chelsea"
    assert TeamAliasMatcher.match_team("ريال مدريد") == "Real Madrid"
    assert TeamAliasMatcher.match_team("ليفربول") == "Liverpool"
    assert TeamAliasMatcher.match_team("باريس سان جيرمان") == "Paris Saint-Germain"
    assert TeamAliasMatcher.match_team("مانشستر سيتي") == "Manchester City"
    assert TeamAliasMatcher.match_team("مانشستر يونايتد") == "Manchester United"
    assert TeamAliasMatcher.match_team("برشلونة") == "Barcelona"
    assert TeamAliasMatcher.match_team("بايرن ميونخ") == "Bayern Munich"
    assert TeamAliasMatcher.match_team("الأهلي") == "Al Ahly"
    assert TeamAliasMatcher.match_team("الزمالك") == "Zamalek"
    assert TeamAliasMatcher.match_team("الهلال") == "Al Hilal"
    assert TeamAliasMatcher.match_team("النصر") == "Al Nassr"


def test_team_alias_matcher_normalization_and_diacritics():
    # Diacritics (tashkeel)
    assert TeamAliasMatcher.match_team("رِيَال مَدْرِيد") == "Real Madrid"
    assert TeamAliasMatcher.match_team("لِيفَرْبُول") == "Liverpool"

    # Leading / trailing whitespace
    assert TeamAliasMatcher.match_team("  تشيلسي  ") == "Chelsea"

    # Prefix stripping (نادي, فريق)
    assert TeamAliasMatcher.match_team("نادي تشيلسي") == "Chelsea"
    assert TeamAliasMatcher.match_team("فريق برشلونة") == "Barcelona"
    assert TeamAliasMatcher.match_team("نادي الأهلي") == "Al Ahly"

    # Alef variations (أ, إ, آ, ا)
    assert TeamAliasMatcher.match_team("ارسنال") == "Arsenal"
    assert TeamAliasMatcher.match_team("أرسنال") == "Arsenal"
    assert TeamAliasMatcher.match_team("انتر ميلان") == "Inter Milan"
    assert TeamAliasMatcher.match_team("إنتر ميلان") == "Inter Milan"


def test_team_alias_matcher_unknown_and_empty_graceful():
    assert TeamAliasMatcher.match_team("فريق مجهول غير مسجل") is None
    assert TeamAliasMatcher.match_team("") is None
    assert TeamAliasMatcher.match_team("   ") is None
    assert TeamAliasMatcher.match_team(None) is None


def test_team_alias_matcher_custom_registration():
    matcher = TeamAliasMatcher()
    matcher.register_alias("فريق السحاب التجريبي", "Cloud FC")
    assert TeamAliasMatcher.match_team("فريق السحاب التجريبي") == "Cloud FC"


def test_match_status_enum_values():
    expected_statuses = {
        "SCHEDULED",
        "IN_PLAY",
        "HALFTIME",
        "EXTRA_TIME",
        "PENALTIES",
        "FINISHED",
        "POSTPONED",
    }
    actual_statuses = {status.value for status in MatchStatus}
    assert actual_statuses == expected_statuses


def test_match_is_live_property(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    def make_match(status: MatchStatus) -> Match:
        return Match(
            id="test_live",
            home_team=home,
            away_team=away,
            league=sample_league,
            status=status,
            kickoff_time=kickoff,
        )

    # Live statuses
    assert make_match(MatchStatus.IN_PLAY).is_live is True
    assert make_match(MatchStatus.HALFTIME).is_live is True
    assert make_match(MatchStatus.EXTRA_TIME).is_live is True
    assert make_match(MatchStatus.PENALTIES).is_live is True

    # Non-live statuses
    assert make_match(MatchStatus.SCHEDULED).is_live is False
    assert make_match(MatchStatus.FINISHED).is_live is False
    assert make_match(MatchStatus.POSTPONED).is_live is False


def test_priority_resolver_admin_preserves_streams_when_admin_servers_empty(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    scraper_stream = StreamServer(
        server_name="Existing Scraper Stream",
        url="https://live.stream/channel1.m3u8",
        type="m3u8",
    )
    scraped_match = Match(
        id="match_500",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=0,
        away_score=0,
        stream_servers=[scraper_stream],
    )

    # Admin emergency score override without changing stream URLs
    admin_override = Match(
        id="match_500",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=1,
        away_score=0,
        stream_servers=[],  # Admin didn't alter streams
        is_admin_override=True,
    )

    resolved = PriorityResolver.resolve(
        api_match=None,
        scraped_match=scraped_match,
        admin_override=admin_override,
    )

    assert resolved.home_score == 1
    assert resolved.is_admin_override is True
    assert len(resolved.stream_servers) == 1
    assert resolved.stream_servers[0].server_name == "Existing Scraper Stream"


def test_channel_stream_mapper_be_in_sports():
    from live_score.domain.resolver import ChannelStreamMapper
    assert ChannelStreamMapper.normalize_slug("beIN SPORTS 1 HD") == "bein-sports-hd-1"
    assert ChannelStreamMapper.normalize_slug("بي ان سبورت 2") == "bein-sports-hd-2"
    assert ChannelStreamMapper.normalize_slug("beIN SPORTS XTRA 1") == "bein-sports-xtra-1"
    assert ChannelStreamMapper.normalize_slug("اكسترا 2") == "bein-sports-xtra-2"
    assert ChannelStreamMapper.normalize_slug("Unknown Channel") is None

    servers = ChannelStreamMapper.get_servers("beIN SPORTS 1 HD")
    assert len(servers) == 3
    assert servers[0].type == "m3u8"
    assert "akhbarnewscdn.store" in servers[0].url
    assert servers[1].url == "/api/v1/stream/player/bein-sports-hd-1"
    assert servers[2].url == "/api/v1/stream/player/bein-sports-hd-1?serv=1"
    assert servers[1].type == "iframe"
    assert "allow-scripts" in servers[1].sandbox
    assert "allow-forms" in servers[1].sandbox


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
    assert len(res_imminent.stream_servers) == 3
    assert res_imminent.stream_servers[0].type == "m3u8"

    # 3. Match IN_PLAY -> Hydrated
    live_match = Match(
        id="m_live",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=datetime(2026, 11, 25, 17, 30, tzinfo=timezone.utc),
        channel="beIN SPORTS 4 HD",
    )
    assert should_hydrate_channel_stream(live_match, now=now) is True
    res_live = PriorityResolver.resolve(api_match=live_match, now=now)
    assert len(res_live.stream_servers) == 2
    assert res_live.stream_servers[0].url == "/api/v1/stream/player/bein-sports-hd-4"

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



