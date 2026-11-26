"""
Tests for Upstream Ingestion Adapters:
1. LiveScoreFootballClient: Ingestion from rezarahiminia/livescoreFootball REST API schema.
2. PortalScraperAdapter: Parsing live streaming embeds, server tabs, and HLS streams.
"""

from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any
from unittest.mock import MagicMock

# Ensure src directory is in sys.path
_src_path = str(Path(__file__).resolve().parents[2] / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

import pytest
import requests

from live_score.adapters import LiveScoreFootballClient, PortalScraperAdapter
from live_score.domain.models import (
    Match,
    MatchDetail,
    MatchStatus,
    StreamServer,
)


# ============================================================================
# LiveScoreFootballClient Fixtures & Tests
# ============================================================================

@pytest.fixture
def mock_today_matches_payload() -> list[dict[str, Any]]:
    return [
        {
            "id": "match_pl_101",
            "home_team": {
                "id": "team_che",
                "name": "Chelsea",
                "logo": "https://img.example/chelsea.png",
            },
            "away_team": {
                "id": "team_liv",
                "name": "Liverpool",
                "logo": "https://img.example/liverpool.png",
            },
            "competition": {
                "id": "pl",
                "name": "Premier League",
                "round": "Round 12",
                "logo": "https://img.example/pl.png",
            },
            "status": "LIVE",
            "elapsed": 68,
            "home_score": 2,
            "away_score": 1,
            "kickoff_time": "2026-11-20T19:00:00Z",
            "stadium": "Stamford Bridge",
            "referee": "Michael Oliver",
        },
        {
            "id": "match_laliga_102",
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "competition": "La Liga",
            "status": "SCHEDULED",
            "kickoff_time": "2026-11-20T21:00:00Z",
        },
    ]


@pytest.fixture
def mock_match_detail_payload() -> dict[str, Any]:
    return {
        "id": "match_pl_101",
        "home_team": {
            "id": "team_che",
            "name": "Chelsea",
            "logo": "https://img.example/chelsea.png",
        },
        "away_team": {
            "id": "team_liv",
            "name": "Liverpool",
            "logo": "https://img.example/liverpool.png",
        },
        "competition": {
            "id": "pl",
            "name": "Premier League",
            "round": "Round 12",
        },
        "status": "IN_PLAY",
        "elapsed": 75,
        "home_score": 2,
        "away_score": 1,
        "kickoff_time": "2026-11-20T19:00:00Z",
        "lineups": {
            "home": [
                {
                    "id": "p_che_20",
                    "name": "Cole Palmer",
                    "number": 20,
                    "position": "MF",
                    "is_starter": True,
                    "grid_position": "3:2",
                },
                {
                    "id": "p_che_1",
                    "name": "Robert Sanchez",
                    "number": 1,
                    "position": "GK",
                    "is_starter": True,
                    "grid_position": "1:1",
                },
            ],
            "away": [
                {
                    "id": "p_liv_11",
                    "name": "Mohamed Salah",
                    "number": 11,
                    "position": "FW",
                    "is_starter": True,
                    "grid_position": "4:3",
                }
            ],
        },
        "events": [
            {
                "id": "ev_1",
                "minute": 24,
                "type": "goal",
                "player_name": "Cole Palmer",
                "team_id": "team_che",
                "description_ar": "هدف لصالح تشيلسي بواسطة كول بالمر",
            },
            {
                "id": "ev_2",
                "minute": 45,
                "type": "yellow_card",
                "player_name": "Alexis Mac Allister",
                "team_id": "team_liv",
            },
        ],
        "stats": {
            "possession": {"home": 56, "away": 44},
            "shots_on_target": {"home": 7, "away": 5},
        },
    }


def test_livescore_client_fetch_today_matches(mock_today_matches_payload):
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_today_matches_payload
    mock_session.get.return_value = mock_response

    client = LiveScoreFootballClient(base_url="http://mock-livescore-api", session=mock_session)
    matches = client.fetch_today_matches()

    assert len(matches) == 2
    match1 = matches[0]
    assert isinstance(match1, Match)
    assert match1.id == "match_pl_101"
    # Team names normalized to Arabic display names
    assert match1.home_team.name_ar == "تشيلسي"
    assert match1.home_team.name_en == "Chelsea"
    assert match1.away_team.name_ar == "ليفربول"
    assert match1.away_team.name_en == "Liverpool"
    assert match1.home_team.logo_url == "https://img.example/chelsea.png"
    # Status and score
    assert match1.status == MatchStatus.IN_PLAY
    assert match1.is_live is True
    assert match1.elapsed_time == 68
    assert match1.home_score == 2
    assert match1.away_score == 1
    assert match1.kickoff_time.tzinfo is not None

    match2 = matches[1]
    assert match2.id == "match_laliga_102"
    assert match2.home_team.name_ar == "ريال مدريد"
    assert match2.away_team.name_ar == "برشلونة"
    assert match2.status == MatchStatus.SCHEDULED
    assert match2.is_live is False


def test_livescore_client_fetch_today_matches_enveloped_responses():
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "success",
        "data": [
            {
                "id": "match_envelope_1",
                "home_team": "Arsenal",
                "away_team": "Tottenham Hotspur",
                "competition": "Premier League",
                "status": "FT",
                "home_score": 3,
                "away_score": 1,
                "kickoff_time": "2026-11-20T16:00:00Z",
            }
        ]
    }
    mock_session.get.return_value = mock_response

    client = LiveScoreFootballClient(base_url="http://mock-api", session=mock_session)
    matches = client.fetch_today_matches()

    assert len(matches) == 1
    assert matches[0].home_team.name_ar == "أرسنال"
    assert matches[0].away_team.name_ar == "توتنهام"
    assert matches[0].status == MatchStatus.FINISHED


def test_livescore_client_fetch_match_detail(mock_match_detail_payload):
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_match_detail_payload
    mock_session.get.return_value = mock_response

    client = LiveScoreFootballClient(base_url="http://mock-api", session=mock_session)
    detail = client.fetch_match_detail("match_pl_101")

    assert detail is not None
    assert isinstance(detail, MatchDetail)
    assert detail.match.id == "match_pl_101"
    assert detail.match.home_team.name_ar == "تشيلسي"

    # Lineups (English names rendered in Latin as per Option B)
    assert len(detail.home_lineup) == 2
    assert detail.home_lineup[0].name == "Cole Palmer"
    assert detail.home_lineup[0].number == 20
    assert detail.home_lineup[0].position == "MF"
    assert detail.home_lineup[0].is_starter is True
    assert detail.home_lineup[0].grid_position == "3:2"

    assert len(detail.away_lineup) == 1
    assert detail.away_lineup[0].name == "Mohamed Salah"

    # Timeline events
    assert len(detail.events) == 2
    assert detail.events[0].minute == 24
    assert detail.events[0].type == "goal"
    assert detail.events[0].player_name == "Cole Palmer"
    assert detail.events[0].description_ar == "هدف لصالح تشيلسي بواسطة كول بالمر"

    # Stats
    assert detail.stats["possession"]["home"] == 56


def test_livescore_client_error_handling_timeout_and_bad_payload():
    mock_session = MagicMock()
    mock_session.get.side_effect = requests.exceptions.Timeout("Connection timed out")

    client = LiveScoreFootballClient(base_url="http://timeout-api", session=mock_session)
    # Must gracefully return empty list, not raise
    matches = client.fetch_today_matches()
    assert matches == []

    # Match detail timeout should gracefully return None
    detail = client.fetch_match_detail("match_timeout")
    assert detail is None

    # Malformed JSON or 500 error
    bad_response = MagicMock()
    bad_response.status_code = 500
    bad_response.json.side_effect = ValueError("Invalid JSON response")
    mock_session.get.side_effect = None
    mock_session.get.return_value = bad_response

    assert client.fetch_today_matches() == []
    assert client.fetch_match_detail("match_bad") is None


def test_livescore_client_status_mapping_variations():
    client = LiveScoreFootballClient(base_url="http://mock-api", session=MagicMock())

    status_cases = [
        ("LIVE", MatchStatus.IN_PLAY),
        ("IN_PLAY", MatchStatus.IN_PLAY),
        ("1H", MatchStatus.IN_PLAY),
        ("2H", MatchStatus.IN_PLAY),
        ("HT", MatchStatus.HALFTIME),
        ("HALFTIME", MatchStatus.HALFTIME),
        ("ET", MatchStatus.EXTRA_TIME),
        ("EXTRA_TIME", MatchStatus.EXTRA_TIME),
        ("PEN", MatchStatus.PENALTIES),
        ("PENALTIES", MatchStatus.PENALTIES),
        ("FT", MatchStatus.FINISHED),
        ("FINISHED", MatchStatus.FINISHED),
        ("POSTPONED", MatchStatus.POSTPONED),
        ("CANCELLED", MatchStatus.POSTPONED),
        ("SCHEDULED", MatchStatus.SCHEDULED),
        ("NS", MatchStatus.SCHEDULED),
        ("UNKNOWN_STATUS", MatchStatus.SCHEDULED),
    ]

    for raw, expected in status_cases:
        assert client.normalize_status(raw) == expected


def test_livescore_client_arabic_alias_upstream_matching():
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "id": "match_mena_1",
            "home_team": "البلوز",  # Arabic nickname for Chelsea
            "away_team": "الريدز",   # Arabic nickname for Liverpool
            "competition": "UEFA Champions League",
            "status": "LIVE",
            "kickoff_time": "2026-11-20T20:00:00Z",
        }
    ]
    mock_session.get.return_value = mock_response

    client = LiveScoreFootballClient(base_url="http://mock-api", session=mock_session)
    matches = client.fetch_today_matches()

    assert len(matches) == 1
    assert matches[0].home_team.name_en == "Chelsea"
    assert matches[0].home_team.name_ar == "تشيلسي"
    assert matches[0].away_team.name_en == "Liverpool"
    assert matches[0].away_team.name_ar == "ليفربول"


# ============================================================================
# PortalScraperAdapter Fixtures & Tests
# ============================================================================

@pytest.fixture
def sample_portal_html() -> str:
    return """
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head><title>مشاهدة مباراة تشيلسي وليفربول بث مباشر</title></head>
    <body>
        <div class="match-stream-box">
            <div class="server-tabs">
                <button class="server-btn active" data-url="https://live.koracity.tv/embed/ch1" data-quality="multi">سيرفر 1 - متعدد الجودات</button>
                <button class="server-btn" data-url="https://hd.streamhub.to/live/ch1" data-quality="hd">سيرفر 2 - HD</button>
                <button class="server-btn" data-url="https://sd.streamhub.to/live/mobile" data-quality="sd">سيرفر 3 - ضعيف للهواتف</button>
                <a class="server-btn" href="https://www.youtube.com/embed/dQw4w9WgXcQ">سيرفر 4 - يوتيوب</a>
            </div>
            <div class="player-container">
                <iframe src="https://live.koracity.tv/embed/ch1" width="100%" height="450" frameborder="0" allowfullscreen></iframe>
            </div>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_hls_html() -> str:
    return """
    <div class="video-player">
        <video id="hls-player" controls>
            <source src="https://live.streaming-cdn.com/hls/match_stream.m3u8" type="application/x-mpegURL">
        </video>
    </div>
    """


def test_portal_scraper_parse_stream_embeds(sample_portal_html):
    scraper = PortalScraperAdapter()
    servers = scraper.parse_stream_embeds(sample_portal_html)

    # 4 distinct servers (the active iframe matches Server 1 URL, so deduplication keeps 4 unique)
    assert len(servers) == 4

    server_map = {s.server_name: s for s in servers}

    # Server 1 - Multi quality
    s1 = server_map["سيرفر 1 - متعدد الجودات"]
    assert s1.url == "https://live.koracity.tv/embed/ch1"
    assert s1.type == "iframe"
    assert s1.quality == "multiquality"
    assert s1.is_active is True
    # Sandboxed for iframe security
    assert "allow-scripts" in s1.sandbox
    assert "allow-same-origin" in s1.sandbox

    # Server 2 - HD
    s2 = server_map["سيرفر 2 - HD"]
    assert s2.url == "https://hd.streamhub.to/live/ch1"
    assert s2.type == "iframe"
    assert s2.quality == "hd"

    # Server 3 - SD
    s3 = server_map["سيرفر 3 - ضعيف للهواتف"]
    assert s3.url == "https://sd.streamhub.to/live/mobile"
    assert s3.type == "iframe"
    assert s3.quality == "sd"

    # Server 4 - YouTube
    s4 = server_map["سيرفر 4 - يوتيوب"]
    assert s4.url == "https://www.youtube.com/embed/dQw4w9WgXcQ"
    assert s4.type == "iframe"
    assert s4.quality == "youtube"


def test_portal_scraper_parse_direct_hls_stream(sample_hls_html):
    scraper = PortalScraperAdapter()
    servers = scraper.parse_stream_embeds(sample_hls_html)

    assert len(servers) == 1
    srv = servers[0]
    assert srv.url == "https://live.streaming-cdn.com/hls/match_stream.m3u8"
    assert srv.type == "m3u8"
    assert srv.is_active is True


def test_portal_scraper_zero_video_proxying_direct_urls():
    """Verify scraper emits clean, direct client-facing URLs without proxying."""
    html = """
    <div class="embed">
        <iframe src="https://direct.cdn.provider.tv/play/match42"></iframe>
    </div>
    """
    scraper = PortalScraperAdapter()
    servers = scraper.parse_stream_embeds(html)
    assert len(servers) == 1
    assert servers[0].url == "https://direct.cdn.provider.tv/play/match42"
    # Never proxy through internal endpoints
    assert "/proxy" not in servers[0].url
    assert "localhost" not in servers[0].url


def test_portal_scraper_deduplication():
    """Ensure duplicate URLs in buttons and iframes are resolved to one StreamServer."""
    html = """
    <button data-url="https://live.stream.org/embed">سيرفر 1</button>
    <a href="https://live.stream.org/embed">سيرفر 1 مكرر</a>
    <iframe src="https://live.stream.org/embed"></iframe>
    """
    scraper = PortalScraperAdapter()
    servers = scraper.parse_stream_embeds(html)
    assert len(servers) == 1
    assert servers[0].url == "https://live.stream.org/embed"


def test_portal_scraper_fetch_stream_servers_network(sample_portal_html):
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = sample_portal_html
    mock_session.get.return_value = mock_response

    scraper = PortalScraperAdapter(base_url="https://kora-portal.example", session=mock_session)
    servers = scraper.fetch_stream_servers("تشيلسي", "ليفربول")

    assert len(servers) == 4
    mock_session.get.assert_called_once()


def test_portal_scraper_error_handling_timeout_and_malformed():
    mock_session = MagicMock()
    mock_session.get.side_effect = requests.exceptions.ConnectTimeout("Connection refused")

    scraper = PortalScraperAdapter(base_url="https://broken-portal.example", session=mock_session)
    # Must gracefully return empty list
    servers = scraper.fetch_stream_servers("ريال مدريد", "برشلونة")
    assert servers == []

    # Malformed HTML, None, empty string should not crash
    assert scraper.parse_stream_embeds("") == []
    assert scraper.parse_stream_embeds(None) == []
    assert scraper.parse_stream_embeds("<<<<not valid html<<<>>>>///") == []


def test_livescore_client_preserves_zero_elapsed_time():
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "success",
        "data": [
            {
                "id": "match_kickoff_zero",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "competition": "Premier League",
                "status": "IN_PLAY",
                "home_score": 0,
                "away_score": 0,
                "elapsed": 0,
                "kickoff_time": "2026-11-20T16:00:00Z",
            }
        ],
    }
    mock_session.get.return_value = mock_response

    client = LiveScoreFootballClient(base_url="http://mock-api", session=mock_session)
    matches = client.fetch_today_matches()

    assert len(matches) == 1
    assert matches[0].elapsed_time == 0


def test_portal_scraper_ignores_plain_navigation_links():
    html = """
    <div>
        <a href="https://portal.example/about">عن الموقع</a>
        <a href="https://portal.example/news">أخبار الرياضة</a>
        <a href="https://stream.example/embed/ch1" class="server-btn">سيرفر 1 - بث مباشر</a>
        <button data-url="https://player.example/embed/2">سيرفر 2</button>
    </div>
    """
    scraper = PortalScraperAdapter()
    servers = scraper.parse_stream_embeds(html)
    assert len(servers) == 2
    assert [s.url for s in servers] == [
        "https://stream.example/embed/ch1",
        "https://player.example/embed/2",
    ]

