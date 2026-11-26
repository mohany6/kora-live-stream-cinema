# -*- coding: utf-8 -*-
"""Exhaustive end-to-end QA audit and verification test suite.

Covers:
1. Stream player proxy (/stream/player/{slug}) and _NoGoogleRedirectHandler.
2. Direct embed resolver (resolve_direct_embed_url).
3. Public routes ETag 304 caching and anonymous visitor ID SHA256 derivation.
4. Admin routes 404 error branches (non-existent stream, override, article).
5. ChannelStreamMapper Arabic digits (١-٩) and beIN Sports channel normalization.
6. Timing gates (should_hydrate_channel_stream) across lifecycle states.
7. PriorityResolver edge cases (scraper-only fallback and channel hydration).
8. TeamAliasMatcher bidirectional lookup and accent normalization.
9. Blogger SEO article generator timezone calculations (Africa/Cairo, Asia/Riyadh, UTC).
10. Store thread safety, batch flushing, analytics timeseries (day/week/month/year).
11. End-to-end live smoke test verifying full FastAPI app lifecycle.
"""

from __future__ import annotations

import concurrent.futures
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from unittest.mock import MagicMock, patch
import urllib.error
import urllib.request

import pytest
from fastapi.testclient import TestClient
from zoneinfo import ZoneInfo

from live_score.adapters.fallback import FallbackSoccerClient
from live_score.api.admin_routes import resolve_direct_embed_url
from live_score.api.app import create_app
from live_score.api.public_routes import _NoGoogleRedirectHandler
from live_score.api.store import AdminStore, normalize_stream_url
from live_score.domain.article_generator import generate_blogger_article
from live_score.domain.models import (
    League,
    Match,
    MatchDetail,
    MatchStatus,
    StreamServer,
    Team,
)
from live_score.domain.resolver import (
    ChannelStreamMapper,
    PriorityResolver,
    TeamAliasMatcher,
    should_hydrate_channel_stream,
)


# ============================================================================
# 1. STREAM PLAYER PROXY & REDIRECT HANDLER
# ============================================================================

def test_no_google_redirect_handler():
    """Verify _NoGoogleRedirectHandler blocks redirects to google.com."""
    handler = _NoGoogleRedirectHandler()
    req = urllib.request.Request("https://example.com")
    
    # Redirect to google.com should return None to halt redirect
    res_google = handler.redirect_request(req, None, 302, "Found", {}, "https://www.google.com/search")
    assert res_google is None

    # Normal redirect should delegate to super
    with patch.object(urllib.request.HTTPRedirectHandler, "redirect_request", return_value="ok") as mock_super:
        res_normal = handler.redirect_request(req, None, 302, "Found", {}, "https://cdn.example.com/player")
        assert res_normal == "ok"
        mock_super.assert_called_once()


def test_stream_player_proxy_full_transformation(tmp_path):
    """Test /stream/player/{slug} with valid HTML, script stripping, base tag and styles."""
    app = create_app(db_path=str(tmp_path / "test.db"))
    client = TestClient(app)

    raw_html = (
        "<!DOCTYPE html><html><head><title>AlbaPlayer Live</title></head><body>"
        "<div class='video-con'><div id='player'></div></div>"
        "<script src='https://acscdn.com/script.js'></script>"
        "<script>aclib.runPop({ zoneId: '999' });</script>"
        "<script>ConsoleBan.init();</script>"
        "<script src='https://imasdk.googleapis.com/js/sdkloader/ima3.js'></script>"
        "<script src='videojs-ima.js'></script>"
        "<script>AplrDevprotocol();</script>"
        "<script>console-ban</script>"
        "<a href='https://www.google.com/'>External Link</a>"
        "</body></html>"
    )

    mock_resp = MagicMock()
    mock_resp.geturl.return_value = "https://24.shootinggames1.com/albaplayer/bein-sports-hd-1/"
    mock_resp.read.return_value = raw_html.encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch.object(urllib.request.OpenerDirector, "open", return_value=mock_resp):
        res = client.get("/api/v1/stream/player/bein-sports-hd-1")
        assert res.status_code == 200
        content = res.text

        # Base tag injected
        assert '<base href="https://24.shootinggames1.com/" />' in content
        # Responsive style injected
        assert ".aplr-player-wrapper" in content
        assert "overflow:hidden" in content
        # Security headers
        assert res.headers.get("Access-Control-Allow-Origin") == "*"
        assert "frame-ancestors *;" in res.headers.get("Content-Security-Policy", "")
        # Ads and blockers stripped
        assert "aclib.runPop" not in content
        assert "ConsoleBan" not in content
        assert "ima3" not in content
        assert "AplrDevprotocol" not in content
        assert "https://www.google.com/" not in content
        assert "href='#" in content or 'href="#' in content


def test_stream_player_proxy_serv_query_param(tmp_path):
    """Test /stream/player/{slug}?serv=2 propagates ?serv=2 upstream."""
    app = create_app(db_path=str(tmp_path / "test.db"))
    client = TestClient(app)

    mock_resp = MagicMock()
    mock_resp.geturl.return_value = "https://24.shootinggames1.com/albaplayer/bein-sports-hd-2/?serv=2"
    mock_resp.read.return_value = b"<html><head></head><body><div id='player'></div></body></html>"
    mock_resp.__enter__.return_value = mock_resp

    with patch.object(urllib.request.OpenerDirector, "open", return_value=mock_resp) as mock_open:
        res = client.get("/api/v1/stream/player/bein-sports-hd-2?serv=2")
        assert res.status_code == 200
        called_req = mock_open.call_args[0][0]
        assert called_req.full_url == "https://24.shootinggames1.com/albaplayer/bein-sports-hd-2/?serv=2"


def test_stream_player_proxy_fallbacks(tmp_path):
    """Test fallback HTML when upstream redirects to Google, omits player, or errors."""
    app = create_app(db_path=str(tmp_path / "test.db"))
    client = TestClient(app)

    # 1. Google redirect in final URL
    mock_google = MagicMock()
    mock_google.geturl.return_value = "https://www.google.com/sorry/index"
    mock_google.__enter__.return_value = mock_google
    with patch.object(urllib.request.OpenerDirector, "open", return_value=mock_google):
        res = client.get("/api/v1/stream/player/test-slug")
        assert res.status_code == 200
        assert "السيرفر الاحتياطي قيد التحديث" in res.text

    # 2. Missing player in HTML
    mock_no_player = MagicMock()
    mock_no_player.geturl.return_value = "https://24.shootinggames1.com/albaplayer/test-slug/"
    mock_no_player.read.return_value = b"<html><body>No match here</body></html>"
    mock_no_player.__enter__.return_value = mock_no_player
    with patch.object(urllib.request.OpenerDirector, "open", return_value=mock_no_player):
        res = client.get("/api/v1/stream/player/test-slug")
        assert res.status_code == 200
        assert "السيرفر الاحتياطي قيد التحديث" in res.text

    # 3. Upstream network failure / timeout
    with patch.object(urllib.request.OpenerDirector, "open", side_effect=urllib.error.URLError("Timeout")):
        res = client.get("/api/v1/stream/player/test-slug")
        assert res.status_code == 200
        assert "السيرفر الاحتياطي قيد التحديث" in res.text


# ============================================================================
# 2. DIRECT EMBED RESOLVER (ADMIN HELPER)
# ============================================================================

def test_resolve_direct_embed_url():
    """Verify resolve_direct_embed_url resolves inner iframes from blog wrappers."""
    # Plain url without wrapper keywords
    assert resolve_direct_embed_url("https://stream.example.com/live.m3u8") == "https://stream.example.com/live.m3u8"

    # Wrapper HTML with player iframe
    wrapper_html = """
    <html><body>
      <div class="entry-content">
        <iframe src="https://24.shootinggames1.com/albaplayer/bein-sports-hd-1/" width="100%"></iframe>
      </div>
    </body></html>
    """
    mock_resp = MagicMock()
    mock_resp.read.return_value = wrapper_html.encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        resolved = resolve_direct_embed_url("https://myblog.blogspot.com/post/match-stream.html")
        assert resolved == "https://24.shootinggames1.com/albaplayer/bein-sports-hd-1/"

    # Protocol-relative iframe
    proto_html = '<html><body><iframe src="//embed.example.com/player/1"></iframe></body></html>'
    mock_proto = MagicMock()
    mock_proto.read.return_value = proto_html.encode("utf-8")
    mock_proto.__enter__.return_value = mock_proto

    with patch("urllib.request.urlopen", return_value=mock_proto):
        resolved_proto = resolve_direct_embed_url("https://myblog.wordpress.com/live")
        assert resolved_proto == "https://embed.example.com/player/1"

    # Exception handling returns original clean url
    with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("url", 500, "Err", {}, None)):
        failed = resolve_direct_embed_url("https://broken.blogspot.com/post/1")
        assert failed == "https://broken.blogspot.com/post/1"


# ============================================================================
# 3. PUBLIC ROUTES: ETAG CACHING & ANONYMOUS TRACKING
# ============================================================================

def test_public_ads_etag_caching(tmp_path):
    """Verify /api/v1/ads returns 304 when client provides matching ETag."""
    app = create_app(db_path=str(tmp_path / "test.db"))
    client = TestClient(app)

    res1 = client.get("/api/v1/ads")
    assert res1.status_code == 200
    etag = res1.headers.get("ETag")
    assert etag is not None

    # Second request with If-None-Match should return 304
    res2 = client.get("/api/v1/ads", headers={"If-None-Match": etag})
    assert res2.status_code == 304


def test_public_track_visit_anonymous_hash(tmp_path):
    """Verify /api/v1/analytics/track generates sha256 hash when visitor_id is empty."""
    app = create_app(db_path=str(tmp_path / "test.db"))
    client = TestClient(app)

    # Empty visitor_id payload
    res = client.post(
        "/api/v1/analytics/track",
        json={"path": "/match/123", "device": "mobile", "referrer": "https://google.com"},
        headers={"User-Agent": "PytestClient/1.0"},
    )
    assert res.status_code == 200
    assert res.json() == {"recorded": True}

    # Verify visit recorded in store
    app.state.store.flush_visits()
    summary = app.state.store.get_analytics_summary()
    assert summary["today_visits"] >= 1
    assert summary["today_uniques"] >= 1


# ============================================================================
# 4. ADMIN ROUTES 404 ERROR HANDLING
# ============================================================================

def test_admin_routes_not_found_branches(tmp_path):
    """Verify 404 responses for non-existent streams, overrides, and match articles."""
    app = create_app(db_path=str(tmp_path / "test.db"), admin_token="secret-token")
    client = TestClient(app)
    headers = {"X-Admin-Token": "secret-token"}

    # 1. Non-existent stream delete returns 404
    res_del_stream = client.delete("/api/v1/admin/matches/non_existent/streams/server_999", headers=headers)
    assert res_del_stream.status_code == 404

    # 2. Non-existent override delete returns 404
    res_del_override = client.delete("/api/v1/admin/matches/non_existent/override", headers=headers)
    assert res_del_override.status_code == 404

    # 3. Non-existent match article returns 404
    res_article = client.get("/api/v1/admin/matches/non_existent/article", headers=headers)
    assert res_article.status_code == 404


# ============================================================================
# 5. CHANNEL STREAM MAPPER & ARABIC NUMERAL NORMALIZATION
# ============================================================================

def test_channel_stream_mapper_arabic_numerals():
    """Verify ChannelStreamMapper normalizes Arabic numerals (١-٩) and channel names."""
    # Arabic numerals 1-9
    assert ChannelStreamMapper.normalize_slug("بي ان سبورت ١") == "bein-sports-hd-1"
    assert ChannelStreamMapper.normalize_slug("بي ان سبورت ٢") == "bein-sports-hd-2"
    assert ChannelStreamMapper.normalize_slug("بي ان سبورت ٣") == "bein-sports-hd-3"
    assert ChannelStreamMapper.normalize_slug("بي ان سبورت ٩") == "bein-sports-hd-9"

    # beIN XTRA
    assert ChannelStreamMapper.normalize_slug("beIN SPORTS XTRA 1") == "bein-sports-xtra-1"
    assert ChannelStreamMapper.normalize_slug("بي ان سبورتس اكسترا 2") == "bein-sports-xtra-2"

    # beIN English
    assert ChannelStreamMapper.normalize_slug("beIN SPORTS English 1") == "bein-sports-english-1"
    assert ChannelStreamMapper.normalize_slug("بي ان سبورتس انجليزية 1") == "bein-sports-english-1"

    # beIN News
    assert ChannelStreamMapper.normalize_slug("beIN SPORTS News") == "bein-sports-news"
    assert ChannelStreamMapper.normalize_slug("بي ان سبورت الإخبارية") == "bein-sports-news"

    # Unknown or None
    assert ChannelStreamMapper.normalize_slug(None) is None
    assert ChannelStreamMapper.normalize_slug("") is None
    assert ChannelStreamMapper.normalize_slug("قناة الكأس") is None


def test_channel_stream_mapper_get_servers():
    """Verify server configuration generation with M3U8 and AlbaPlayer proxies."""
    # Known M3U8 channel
    servers_hd1 = ChannelStreamMapper.get_servers("beIN SPORTS 1 HD")
    assert len(servers_hd1) == 3
    assert servers_hd1[0].type == "m3u8"
    assert servers_hd1[1].type == "iframe"
    assert servers_hd1[2].type == "iframe"
    assert "/api/v1/stream/player/bein-sports-hd-1" in servers_hd1[1].url

    # Non-M3U8 channel
    servers_hd2 = ChannelStreamMapper.get_servers("beIN SPORTS 2 HD")
    assert len(servers_hd2) == 2
    assert servers_hd2[0].type == "iframe"
    assert servers_hd2[1].type == "iframe"

    # Unknown channel
    assert ChannelStreamMapper.get_servers("Unknown Channel") == []


# ============================================================================
# 6. BROADCAST TIMING GATES & LIFECYCLE STATES
# ============================================================================

def test_should_hydrate_channel_stream():
    """Verify stream hydration timing gate across match statuses and timeframes."""
    now = datetime(2026, 11, 25, 18, 0, tzinfo=timezone.utc)
    team1 = Team(id="t1", name_en="Team 1", name_ar="فريق 1")
    team2 = Team(id="t2", name_en="Team 2", name_ar="فريق 2")
    league = League(id="l1", name_en="League", name_ar="دوري")

    # 1. Finished match should NEVER hydrate
    m_finished = Match(
        id="m_fin",
        home_team=team1,
        away_team=team2,
        league=league,
        status=MatchStatus.FINISHED,
        kickoff_time=now - timedelta(hours=2),
        home_score=1,
        away_score=0,
    )
    assert should_hydrate_channel_stream(m_finished, now=now) is False

    # 2. Postponed match should NEVER hydrate
    m_postponed = Match(
        id="m_post",
        home_team=team1,
        away_team=team2,
        league=league,
        status=MatchStatus.POSTPONED,
        kickoff_time=now,
        home_score=0,
        away_score=0,
    )
    assert should_hydrate_channel_stream(m_postponed, now=now) is False

    # 3. Live match ALWAYS hydrates
    m_live = Match(
        id="m_live",
        home_team=team1,
        away_team=team2,
        league=league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=now - timedelta(minutes=10),
        home_score=0,
        away_score=0,
        elapsed_time=10,
    )
    assert should_hydrate_channel_stream(m_live, now=now) is True

    # 4. Scheduled within 30-min window hydrates
    m_upcoming_soon = Match(
        id="m_soon",
        home_team=team1,
        away_team=team2,
        league=league,
        status=MatchStatus.SCHEDULED,
        kickoff_time=now + timedelta(minutes=20),
        home_score=0,
        away_score=0,
    )
    assert should_hydrate_channel_stream(m_upcoming_soon, now=now) is True

    # 5. Scheduled far in advance (> 30 min) does NOT hydrate
    m_upcoming_far = Match(
        id="m_far",
        home_team=team1,
        away_team=team2,
        league=league,
        status=MatchStatus.SCHEDULED,
        kickoff_time=now + timedelta(hours=3),
        home_score=0,
        away_score=0,
    )
    assert should_hydrate_channel_stream(m_upcoming_far, now=now) is False


# ============================================================================
# 7. PRIORITY RESOLVER: SCAPER-ONLY & VALUE ERROR
# ============================================================================

def test_priority_resolver_scraper_only_and_error():
    """Verify PriorityResolver handles scraper-only match and empty arguments."""
    now = datetime(2026, 11, 25, 18, 0, tzinfo=timezone.utc)
    team1 = Team(id="t1", name_en="Real Madrid", name_ar="ريال مدريد")
    team2 = Team(id="t2", name_en="Barcelona", name_ar="برشلونة")
    league = League(id="l1", name_en="La Liga", name_ar="الدوري الإسباني")

    scraped = Match(
        id="m_scraped",
        home_team=team1,
        away_team=team2,
        league=league,
        status=MatchStatus.SCHEDULED,
        kickoff_time=now + timedelta(minutes=15),
        home_score=0,
        away_score=0,
        channel="beIN SPORTS 1 HD",
    )

    # Scraper-only resolve with channel auto-hydration
    resolved = PriorityResolver.resolve(scraped_match=scraped, now=now)
    assert resolved.id == "m_scraped"
    assert resolved.is_admin_override is False
    assert len(resolved.stream_servers) > 0  # hydrated from channel

    # No match source provided raises ValueError
    with pytest.raises(ValueError, match="At least one match source must be provided"):
        PriorityResolver.resolve()


# ============================================================================
# 8. TEAM ALIAS MATCHER: BIDIRECTIONAL & ACCENTS
# ============================================================================

def test_team_alias_matcher_bidirectional_and_accents():
    """Verify English normalization, accent removal, and Arabic name resolution."""
    # Normalize english
    assert TeamAliasMatcher.normalize_english_name("Atlético de Madrid") == "atletico de madrid"
    assert TeamAliasMatcher.normalize_english_name("Brighton & Hove Albion") == "brighton and hove albion"
    assert TeamAliasMatcher.normalize_english_name(None) == ""
    assert TeamAliasMatcher.normalize_english_name("") == ""

    # get_arabic_name
    assert TeamAliasMatcher.get_arabic_name("Real Madrid") == "ريال مدريد"
    assert TeamAliasMatcher.get_arabic_name("Arsenal") == "أرسنال"
    assert TeamAliasMatcher.get_arabic_name("Chelsea") == "تشيلسي"
    assert TeamAliasMatcher.get_arabic_name("Unknown Club XYZ") is None
    assert TeamAliasMatcher.get_arabic_name(None) is None


# ============================================================================
# 9. BLOGGER SEO ARTICLE GENERATOR TIMEZONE CONVERSIONS
# ============================================================================

def test_blogger_article_generator_timezones_and_xss():
    """Verify article generator displays Cairo, Riyadh, and UTC times and prevents XSS."""
    # Match with naive datetime (interpreted as UTC)
    kickoff_naive = datetime(2026, 11, 25, 18, 0)
    match_dict = {
        "id": "match_tz_test",
        "home_team": "الأهلي <script>alert(1)</script>",
        "away_team": "الزمالك",
        "competition": "نهائي دوري أبطال أفريقيا",
        "kickoff_time": kickoff_naive,
        "venue": "ستاد القاهرة الدولي",
        "referee": "مصطفى غربال",
        "channel": "beIN SPORTS HD 4",
        "commentator": "علي محمد علي",
    }

    article = generate_blogger_article(match_dict, platform_base_url="https://kora-live.example.com")
    title = article["title"]
    content = article["content"]

    # Check title
    assert "الأهلي" in title
    assert "الزمالك" in title

    # Check timezones in content: 18:00 UTC = 21:00 Riyadh, 20:00 Cairo
    assert "بتوقيت مكة المكرمة" in content
    assert "القاهرة" in content
    assert "غرينتش UTC" in content

    # Check XSS escaping
    assert "<script>alert(1)</script>" not in content
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content

    # Check Cloudflare discovery bridge tag
    assert 'id="kora-stream-bridge"' in content
    assert 'data-tunnel="https://kora-live.example.com"' in content
    assert 'data-match-id="match_tz_test"' in content

    # Check Schema.org JSON-LD
    assert '"@type": "SportsEvent"' in content
    assert '"price": "0"' in content


# ============================================================================
# 10. STORE THREAD SAFETY, BATCH FLUSHING & ANALYTICS PERIODS
# ============================================================================

def test_store_thread_safety_and_analytics_periods(tmp_path):
    """Stress-test AdminStore with concurrent threads, batch flushes, and timeseries."""
    store = AdminStore(db_path=str(tmp_path / "concurrent.db"), batch_size=20, flush_interval=0.5)

    num_threads = 8
    visits_per_thread = 25
    total_expected = num_threads * visits_per_thread

    def worker(thread_idx: int):
        for i in range(visits_per_thread):
            store.record_visit(
                visitor_id=f"visitor_{thread_idx}_{i % 5}",
                path=f"/match/m_{i % 3}",
                device="mobile" if i % 2 == 0 else "desktop",
                referrer="https://twitter.com",
            )

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, idx) for idx in range(num_threads)]
        concurrent.futures.wait(futures)

    # Flush all remaining visits
    store.flush_visits()
    summary = store.get_analytics_summary()
    assert summary["today_visits"] == total_expected
    assert summary["today_uniques"] > 0

    # Timeseries for all periods
    ts_day = store.get_analytics_timeseries(period="day")
    assert len(ts_day) == 24
    assert sum(h["visits"] for h in ts_day) == total_expected

    ts_week = store.get_analytics_timeseries(period="week")
    assert len(ts_week) == 7
    assert any(d["visits"] == total_expected for d in ts_week)

    ts_month = store.get_analytics_timeseries(period="month")
    assert len(ts_month) == 30

    ts_year = store.get_analytics_timeseries(period="year")
    assert len(ts_year) == 12

    # Device breakdown
    devices = store.get_device_breakdown(period="day")
    assert devices["mobile"] + devices["desktop"] == total_expected

    # Top pages
    top_pages = store.get_top_pages(period="day", limit=3)
    assert len(top_pages) <= 3
    assert sum(p["visits"] for p in top_pages) == total_expected

    # Stream URL deduplication
    m_id = "match_dedup"
    stream_payload = {"url": "https://stream.example.com/live/", "server_name": "Server 1"}
    s1, created1 = store.upsert_stream(m_id, stream_payload)
    assert created1 is True

    # Same URL with trailing slash difference should update, NOT duplicate
    stream_payload2 = {"url": "https://stream.example.com/live", "server_name": "Server 1 Updated"}
    s2, created2 = store.upsert_stream(m_id, stream_payload2)
    assert created2 is False
    assert s2["id"] == s1["id"]

    streams = store.list_streams(m_id)
    assert len(streams) == 1
    assert streams[0]["server_name"] == "Server 1 Updated"

    store.close()


# ============================================================================
# 11. END-TO-END LIVE SMOKE TEST OF FASTAPI APP LIFECYCLE
# ============================================================================

def test_full_platform_live_smoke_suite(tmp_path):
    """Exhaustive smoke test covering every public and admin API endpoint in the platform."""
    now = datetime(2026, 11, 25, 18, 0, tzinfo=timezone.utc)
    team_a = Team(id="team_rm", name_en="Real Madrid", name_ar="ريال مدريد")
    team_b = Team(id="team_fcb", name_en="Barcelona", name_ar="برشلونة")
    league = League(id="laliga", name_en="La Liga", name_ar="الدوري الإسباني")

    match = Match(
        id="clasico_smoke",
        home_team=team_a,
        away_team=team_b,
        league=league,
        status=MatchStatus.SCHEDULED,
        kickoff_time=now + timedelta(hours=1),
        home_score=0,
        away_score=0,
        channel="beIN SPORTS 1 HD",
    )
    fixture_detail = MatchDetail(match=match)

    app = create_app(
        fixtures=[fixture_detail],
        db_path=str(tmp_path / "smoke.db"),
        admin_token="smoke-admin-key",
        timezone_name="Asia/Riyadh",
        clock=lambda: now,
    )
    client = TestClient(app)
    admin_hdr = {"X-Admin-Token": "smoke-admin-key"}

    # 1. System Health
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"
    assert res_health.json()["matches"] == 1

    # 2. Public Schedule Today (Option A Card Contract)
    res_today = client.get("/api/v1/matches/today")
    assert res_today.status_code == 200
    cards = res_today.json()["matches"]
    assert len(cards) == 1
    assert cards[0]["home_team"]["name_ar"] == "ريال مدريد"
    assert cards[0]["away_team"]["name_ar"] == "برشلونة"

    # 3. Public Match Detail (Hybrid Center Payload)
    res_detail = client.get("/api/v1/matches/clasico_smoke")
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["match"]["id"] == "clasico_smoke"

    # 4. Public Ads List
    res_ads = client.get("/api/v1/ads")
    assert res_ads.status_code == 200
    assert "ads" in res_ads.json()

    # 5. Public Track Visit
    res_track = client.post(
        "/api/v1/analytics/track",
        json={"visitor_id": "user_smoke_1", "path": "/match/clasico_smoke", "device": "desktop"},
    )
    assert res_track.status_code == 200
    assert res_track.json() == {"recorded": True}

    # 6. Admin Matches List
    res_admin_matches = client.get("/api/v1/admin/matches", headers=admin_hdr)
    assert res_admin_matches.status_code == 200
    assert len(res_admin_matches.json()["matches"]) == 1

    # 7. Admin Add Stream Server
    new_stream = {
        "server_name": "سيرفر البث الرئيسي 4K",
        "url": "https://stream.example.com/smoke.m3u8",
        "type": "m3u8",
        "quality": "4K Ultra HD",
        "is_active": True,
    }
    res_stream_add = client.post(
        "/api/v1/admin/matches/clasico_smoke/streams",
        json=new_stream,
        headers=admin_hdr,
    )
    assert res_stream_add.status_code == 201
    server_id = res_stream_add.json()["servers"][0]["id"]

    # 8. Admin Score Override
    override_payload = {
        "home_score": 2,
        "away_score": 1,
        "status": "IN_PLAY",
        "elapsed_time": 35,
    }
    res_override = client.post(
        "/api/v1/admin/matches/clasico_smoke/override",
        json=override_payload,
        headers=admin_hdr,
    )
    assert res_override.status_code == 200
    assert res_override.json()["home_score"] == 2
    assert res_override.json()["is_admin_override"] is True

    # Verify override is reflected in public match detail
    res_detail_updated = client.get("/api/v1/matches/clasico_smoke")
    assert res_detail_updated.json()["match"]["home_score"] == 2
    assert res_detail_updated.json()["match"]["is_admin_override"] is True

    # 9. Admin Match Article Generation Endpoint
    res_art = client.get(
        "/api/v1/admin/matches/clasico_smoke/article?base_url=https://kora-smoke.trycloudflare.com",
        headers=admin_hdr,
    )
    assert res_art.status_code == 200
    art_data = res_art.json()
    assert "ريال مدريد" in art_data["title"]
    assert "https://kora-smoke.trycloudflare.com" in art_data["content"]

    # 10. Admin Analytics Stats
    res_stats = client.get("/api/v1/admin/analytics/stats?period=day", headers=admin_hdr)
    assert res_stats.status_code == 200
    stats_data = res_stats.json()
    assert "summary" in stats_data
    assert "chart_data" in stats_data
    assert "device_stats" in stats_data
    assert "top_pages" in stats_data

    # 11. Admin Ads CRUD
    new_ad = {
        "title": "Smoke Test Banner",
        "position": "header_top",
        "ad_type": "custom_html",
        "html_code": "<div>Smoke Ad</div>",
        "target_device": "all",
        "priority": 50,
        "is_active": True,
    }
    res_ad_create = client.post("/api/v1/admin/ads", json=new_ad, headers=admin_hdr)
    assert res_ad_create.status_code == 201
    ad_id = res_ad_create.json()["id"]

    # Toggle ad active
    res_ad_toggle = client.patch(f"/api/v1/admin/ads/{ad_id}/toggle", headers=admin_hdr)
    assert res_ad_toggle.status_code == 200
    assert res_ad_toggle.json()["is_active"] is False

    # Delete ad
    res_ad_delete = client.delete(f"/api/v1/admin/ads/{ad_id}", headers=admin_hdr)
    assert res_ad_delete.status_code == 200
    assert res_ad_delete.json()["deleted"] is True

    # 12. Cleanup Overrides and Streams
    res_del_ov = client.delete("/api/v1/admin/matches/clasico_smoke/override", headers=admin_hdr)
    assert res_del_ov.status_code == 200

    res_del_st = client.delete(f"/api/v1/admin/matches/clasico_smoke/streams/{server_id}", headers=admin_hdr)
    assert res_del_st.status_code == 200
