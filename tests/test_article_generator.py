# -*- coding: utf-8 -*-
"""Unit tests for pre/post-match Blogger article generation, trending cap, and deduplication."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import scripts.auto_blogger_publisher as publisher
from live_score.domain.models import League, Match, MatchDetail, MatchEvent, MatchStatus, Team
from src.live_score.domain.article_generator import generate_blogger_article


def _strip_html(raw_html: str) -> str:
    return re.sub(r"<[^>]+>", " ", raw_html)


def test_generate_blogger_article_pre_match_full_details():
    match = {
        "id": "match_100",
        "home_team": "ريال مدريد",
        "away_team": "برشلونة",
        "competition": "الدوري الإسباني",
        "kickoff_time": "2026-11-26T20:00:00Z",
        "venue": "سانتياغو برنابيو",
        "referee": "خيسوس خيل مانزانو",
        "channel": "beIN Sports 1 HD",
        "commentator": "عصام الشوالي",
        "home_formation": "4-3-3",
        "away_formation": "4-2-3-1",
        "home_lineup": [
            {"name": "Thibaut Courtois", "number": 1, "position": "GK"},
            {"name": "Kylian Mbappe", "number": 9, "position": "FW"},
        ],
        "away_lineup": [
            {"name": "Marc-Andre ter Stegen", "number": 1, "position": "GK"},
            {"name": "Robert Lewandowski", "number": 9, "position": "FW"},
        ],
    }

    article = generate_blogger_article(
        match,
        platform_base_url="https://stream.koralive.pages.dev",
        stage="pre_match",
    )

    assert (
        article["title"]
        == "مشاهدة مباراة ريال مدريد وبرشلونة بث مباشر اليوم في الدوري الإسباني | يلا شوت كورة لايف"
    )
    assert article["labels"] == ["بث مباشر", "الدوري الإسباني", "مباريات اليوم"]

    content = article["content"]
    assert '"@type": "SportsEvent"' in content
    assert "سانتياغو برنابيو" in content
    assert "خيسوس خيل مانزانو" in content
    assert "beIN Sports 1 HD" in content
    assert "عصام الشوالي" in content
    assert "Thibaut Courtois" in content
    assert "Robert Lewandowski" in content
    assert "4-3-3" in content
    assert "https://stream.koralive.pages.dev/match/match_100" in content
    assert 'rel="noopener noreferrer"' in content
    # Anti-takedown: pre-match must never leak raw streams or video iframes
    assert ".m3u8" not in content
    assert "<iframe" not in content.lower()


def test_generate_blogger_article_post_match_with_video_embed_timeline_and_poll():
    match = {
        "id": "match_101",
        "home_team": "ريال مدريد",
        "away_team": "برشلونة",
        "home_team_id": "rm",
        "away_team_id": "fcb",
        "home_score": 3,
        "away_score": 1,
        "status": "FINISHED",
        "competition": "الدوري الإسباني",
        "kickoff_time": "2026-11-26T20:00:00Z",
        "venue": "سانتياغو برنابيو",
        "referee": "خيل مانزانو",
        "channel": "beIN Sports 1 HD",
        "commentator": "حفيظ دراجي",
        "highlight_embed_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "home_formation": "4-3-3",
        "away_formation": "4-2-3-1",
        "events": [
            {"minute": 15, "player_name": "فينيسيوس جونيور", "type": "goal", "team_name_ar": "ريال مدريد"},
            {"minute": 32, "player_name": "أراوخو", "type": "yellow_card", "team_name_ar": "برشلونة"},
            {"minute": 42, "player_name": "ليفاندوفسكي", "type": "goal", "team_name_ar": "برشلونة"},
            {"minute": 68, "player_name": "جافي", "type": "red_card", "team_name_ar": "برشلونة"},
            {"minute": 75, "player_name": "لامين يامال", "type": "substitution", "team_name_ar": "برشلونة"},
        ],
        "stats": {
            "possession": {"label_ar": "الاستحواذ", "home": 56, "away": 44, "unit": "%"},
            "shots": {"label_ar": "التسديدات", "home": 16, "away": 8, "unit": ""},
        },
        "standings": [
            {"position": 1, "team_name_ar": "ريال مدريد", "played": 14, "points": 34, "is_home": True, "is_away": False},
            {"position": 2, "team_name_ar": "برشلونة", "played": 14, "points": 30, "is_home": False, "is_away": True},
        ],
    }

    article = generate_blogger_article(
        match,
        platform_base_url="https://stream.koralive.pages.dev",
        stage="post_match",
    )

    assert (
        article["title"]
        == "أهداف وملخص مباراة ريال مدريد (3 - 1) برشلونة في الدوري الإسباني وتفاصيل القمة"
    )
    assert article["labels"] == ["أهداف وملخصات", "أهداف اليوم", "الدوري الإسباني"]

    content = article["content"]
    # 16:9 responsive highlight iframe with sandbox and no-referrer
    assert "<iframe" in content
    assert "padding-bottom: 56.25%" in content
    assert "https://www.youtube.com/embed/dQw4w9WgXcQ" in content
    assert 'referrerpolicy="no-referrer"' in content
    assert "sandbox=" in content

    # Visual match timeline icons
    assert "⚽" in content
    assert "🟨" in content
    assert "🟥" in content
    assert "🔄" in content
    assert "فينيسيوس جونيور" in content
    assert "ليفاندوفسكي" in content

    # Comprehensive 800+ word tactical review section
    tactical_match = re.search(r'<article id="kora-tactical-review".*?</article>', content, re.S)
    assert tactical_match is not None
    tactical_words = _strip_html(tactical_match.group(0)).split()
    assert len(tactical_words) >= 800

    # Interactive POTM poll widget
    assert "من هو رجل المباراة؟" in content
    assert "kora-poll-option" in content
    assert "localStorage" in content


@pytest.mark.parametrize(
    ("raw_url", "expected_src"),
    [
        ("https://www.youtube.com/watch?v=abc123XYZ", "https://www.youtube.com/embed/abc123XYZ?rel=0"),
        ("https://youtu.be/abc123XYZ", "https://www.youtube.com/embed/abc123XYZ?rel=0"),
        ("https://www.dailymotion.com/video/x8abcde_highlights", "https://www.dailymotion.com/embed/video/x8abcde"),
        ("https://x.com/realmadrid/status/1234567890", "https://twitframe.com/show?url="),
    ],
)
def test_post_match_normalizes_video_highlight_embeds(raw_url: str, expected_src: str):
    match = {
        "id": "match_norm",
        "home_team": "الأهلي",
        "away_team": "الزمالك",
        "competition": "الدوري المصري",
        "home_score": 2,
        "away_score": 0,
        "highlight_embed_url": raw_url,
    }
    article = generate_blogger_article(match, stage="post_match")
    assert expected_src in article["content"]


def test_post_match_fallback_youtube_wrapper_and_min_word_count():
    match = {
        "id": "match_fallback",
        "home_team": "الأهلي",
        "away_team": "الزمالك",
        "competition": "الدوري",
        "home_score": 1,
        "away_score": 1,
    }
    article = generate_blogger_article(match, stage="post_match")
    content = article["content"]
    assert "kora-highlights-player" in content
    assert "https://www.youtube.com/embed?listType=search&amp;list=" in content
    assert "https://www.youtube.com/results?search_query=" in content

    tactical_match = re.search(r'<article id="kora-tactical-review".*?</article>', content, re.S)
    assert tactical_match is not None
    assert len(_strip_html(tactical_match.group(0)).split()) >= 800


def test_post_match_blocks_javascript_highlight_url_xss():
    match = {
        "id": "match_xss",
        "home_team": "Team <script>alert(1)</script>",
        "away_team": "Away",
        "competition": "League",
        "highlight_embed_url": "javascript:alert(1)",
    }
    article = generate_blogger_article(match, stage="post_match")
    assert "javascript:alert(1)" not in article["content"]
    assert "<script>alert(1)</script>" not in article["content"]


def test_invalid_stage_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported article stage"):
        generate_blogger_article({"id": "m1"}, stage="invalid_stage")


# ---------------------------------------------------------------------------
# Auto-publisher: Top 3-5 capping & `published_articles.json` deduplication
# ---------------------------------------------------------------------------

def _make_detail(
    match_id: str,
    home_ar: str,
    away_ar: str,
    league_ar: str,
    kickoff: datetime,
    status: MatchStatus = MatchStatus.SCHEDULED,
    home_score: int = 0,
    away_score: int = 0,
) -> MatchDetail:
    match = Match(
        id=match_id,
        home_team=Team(id=f"{match_id}_h", name_ar=home_ar, name_en=home_ar),
        away_team=Team(id=f"{match_id}_a", name_ar=away_ar, name_en=away_ar),
        league=League(id=f"{match_id}_l", name_ar=league_ar, name_en=league_ar),
        status=status,
        kickoff_time=kickoff,
        home_score=home_score,
        away_score=away_score,
        events=[],
    )
    events = (
        [MatchEvent(minute=22, type="goal", player_name="Test Scorer", team_id=f"{match_id}_h")]
        if status == MatchStatus.FINISHED
        else []
    )
    return MatchDetail(match=match, events=events)


class _StubCatalog:
    def __init__(self, details: list[MatchDetail]) -> None:
        self._map = {d.match.id: d for d in details}

    def fixture_map(self, now=None):
        return dict(self._map)

    def get_detail(self, match_id: str, now=None):
        return self._map.get(match_id)


def test_get_top_trending_matches_strictly_caps_to_5_today(monkeypatch):
    now = datetime(2026, 11, 26, 14, 0, tzinfo=timezone.utc)
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)

    details = [
        _make_detail("m1", "ريال مدريد", "برشلونة", "الدوري الإسباني", now + timedelta(hours=2), MatchStatus.IN_PLAY),
        _make_detail("m2", "ليفربول", "مانشستر سيتي", "الدوري الإنجليزي الممتاز", now + timedelta(hours=3)),
        _make_detail("m3", "بايرن ميونخ", "بوروسيا دورتموند", "دوري أبطال أوروبا", now + timedelta(hours=4)),
        _make_detail("m4", "الهلال", "النصر", "دوري أبطال أوروبا", now + timedelta(hours=1), MatchStatus.FINISHED, 2, 1),
        _make_detail("m5", "الأهلي", "الزمالك", "الدوري المصري", now + timedelta(hours=5)),
        _make_detail("m6", "فياريال", "جيرونا", "الدوري الإسباني", now + timedelta(hours=6)),
        _make_detail("m7", "إيفرتون", "برينتفورد", "الدوري الإنجليزي الممتاز", now + timedelta(hours=6)),
        # Out-of-date or postponed matches must be excluded
        _make_detail("m_yest", "ريال مدريد", "أرسنال", "دوري أبطال أوروبا", yesterday, MatchStatus.IN_PLAY),
        _make_detail("m_tom", "برشلونة", "تشيلسي", "دوري أبطال أوروبا", tomorrow, MatchStatus.SCHEDULED),
        _make_detail("m_post", "نابولي", "ميلان", "الدوري الإيطالي", now + timedelta(hours=1), MatchStatus.POSTPONED),
    ]

    monkeypatch.setattr(publisher, "create_catalog", lambda _now=None: _StubCatalog(details))

    # Even if caller passes limit=10, hard cap is 5 and only today's active/finished matches qualify
    top = publisher.get_top_trending_matches(limit=10, now=now)
    assert len(top) == 5
    returned_ids = {item["id"] for item in top}
    assert returned_ids.isdisjoint({"m_yest", "m_tom", "m_post"})

    # Finished match today gets stage="post_match"
    m4_item = next((item for item in top if item["id"] == "m4"), None)
    assert m4_item is not None
    assert m4_item["stage"] == "post_match"
    assert m4_item["home_score"] == 2
    assert m4_item["away_score"] == 1


def test_run_auto_publisher_deduplicates_across_cron_runs_and_transitions_stages(tmp_path, monkeypatch):
    now = datetime(2026, 11, 26, 14, 0, tzinfo=timezone.utc)
    details = [
        _make_detail("m1", "ريال مدريد", "برشلونة", "الدوري الإسباني", now + timedelta(hours=1), MatchStatus.SCHEDULED),
        _make_detail("m2", "ليفربول", "مانشستر سيتي", "الدوري الإنجليزي الممتاز", now + timedelta(hours=2), MatchStatus.SCHEDULED),
        _make_detail("m3", "الهلال", "النصر", "دوري روشن السعودي", now + timedelta(hours=3), MatchStatus.SCHEDULED),
        _make_detail("m4", "الأهلي", "الزمالك", "الدوري المصري", now + timedelta(hours=4), MatchStatus.SCHEDULED),
        _make_detail("m5", "بايرن ميونخ", "بوروسيا دورتموند", "دوري أبطال أوروبا", now + timedelta(hours=5), MatchStatus.SCHEDULED),
        _make_detail("m6", "أرسنال", "تشيلسي", "الدوري الإنجليزي الممتاز", now + timedelta(hours=6), MatchStatus.SCHEDULED),
    ]

    catalog = _StubCatalog(details)
    monkeypatch.setattr(publisher, "create_catalog", lambda _now=None: catalog)
    monkeypatch.setattr(
        publisher,
        "load_env_vars",
        lambda: {"SMTP_USER": "bot@example.com", "SMTP_PASSWORD": "secret", "BLOGGER_PUBLISH_EMAIL": "pub@blogger.com"},
    )

    sent_emails: list[tuple[str, str]] = []
    monkeypatch.setattr(
        publisher,
        "publish_article_via_email",
        lambda title, html_content: sent_emails.append((title, html_content)) or True,
    )
    monkeypatch.setattr(publisher, "publish_article_via_blogger_api", lambda *args, **kwargs: None)

    cache_path = tmp_path / "published_articles.json"
    out_dir = tmp_path / "daily_articles"

    # Run 1: publishes top 5 pre_match articles
    first_run = publisher.run_auto_publisher(
        limit=5,
        cache_path=cache_path,
        output_dir=out_dir,
        platform_base_url="https://stream.example.pages.dev",
        now=now,
        open_browser=False,
    )
    assert len(first_run) == 5
    assert len(sent_emails) == 5
    assert cache_path.exists()

    # Run 2 (20 minutes later, same state): deduplication blocks all duplicates, including m6 due to daily cap 5
    second_run = publisher.run_auto_publisher(
        limit=5,
        cache_path=cache_path,
        output_dir=out_dir,
        platform_base_url="https://stream.example.pages.dev",
        now=now + timedelta(minutes=20),
        open_browser=False,
    )
    assert second_run == []
    assert len(sent_emails) == 5

    # Transition m1 from SCHEDULED -> FINISHED
    details[0] = _make_detail(
        "m1", "ريال مدريد", "برشلونة", "الدوري الإسباني", now + timedelta(hours=1), MatchStatus.FINISHED, 3, 1
    )
    catalog._map["m1"] = details[0]

    # Run 3: publishes ONLY m1 post_match article; m2..m5 pre_match remain deduplicated; m6 still capped
    third_run = publisher.run_auto_publisher(
        limit=5,
        cache_path=cache_path,
        output_dir=out_dir,
        platform_base_url="https://stream.example.pages.dev",
        now=now + timedelta(hours=3),
        open_browser=False,
    )
    assert len(third_run) == 1
    assert third_run[0]["match_id"] == "m1"
    assert third_run[0]["stage"] == "post_match"
    assert len(sent_emails) == 6
    assert "أهداف وملخص مباراة ريال مدريد (3 - 1) برشلونة" in sent_emails[-1][0]

    cached = json.loads(cache_path.read_text(encoding="utf-8"))
    assert "m1:pre_match" in cached["articles"]
    assert "m1:post_match" in cached["articles"]


def test_run_auto_publisher_does_not_cache_on_delivery_failure(tmp_path, monkeypatch):
    now = datetime(2026, 11, 26, 14, 0, tzinfo=timezone.utc)
    details = [
        _make_detail("m1", "ريال مدريد", "برشلونة", "الدوري الإسباني", now + timedelta(hours=1)),
    ]
    monkeypatch.setattr(publisher, "create_catalog", lambda _now=None: _StubCatalog(details))
    monkeypatch.setattr(
        publisher,
        "load_env_vars",
        lambda: {"SMTP_USER": "bot@example.com", "SMTP_PASSWORD": "secret", "BLOGGER_PUBLISH_EMAIL": "pub@blogger.com"},
    )
    monkeypatch.setattr(publisher, "publish_article_via_blogger_api", lambda *args, **kwargs: None)
    monkeypatch.setattr(publisher, "publish_article_via_email", lambda *args, **kwargs: False)

    cache_path = tmp_path / "published_articles.json"
    out_dir = tmp_path / "daily_articles"
    results = publisher.run_auto_publisher(
        cache_path=cache_path,
        output_dir=out_dir,
        now=now,
        open_browser=False,
    )
    assert len(results) == 1
    assert results[0]["published"] is False
    assert not publisher.is_article_published(publisher.load_published_articles(cache_path), "m1", "pre_match")


def test_publish_article_via_blogger_api_sends_labels(monkeypatch):
    captured: dict = {}

    class _FakeResp:
        def raise_for_status(self):
            return None

    def _fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResp()

    monkeypatch.setattr(
        publisher,
        "load_env_vars",
        lambda: {"BLOGGER_BLOG_ID": "blog123", "BLOGGER_ACCESS_TOKEN": "tok-abc"},
    )
    monkeypatch.setattr(publisher.requests, "post", _fake_post)

    ok = publisher.publish_article_via_blogger_api(
        "Test Title",
        "<p>Body</p>",
        labels=["أهداف وملخصات", "أهداف اليوم", "الدوري الإسباني"],
    )
    assert ok is True
    assert captured["url"] == "https://www.googleapis.com/blogger/v3/blogs/blog123/posts/"
    assert captured["headers"]["Authorization"] == "Bearer tok-abc"
    assert captured["json"]["labels"] == ["أهداف وملخصات", "أهداف اليوم", "الدوري الإسباني"]


def test_load_published_articles_handles_corrupt_json(tmp_path):
    bad_path = tmp_path / "published_articles.json"
    bad_path.write_text("{corrupt json", encoding="utf-8")
    loaded = publisher.load_published_articles(bad_path)
    assert loaded == {"articles": {}}


def test_highlight_embed_normalizer_exact_domain_matching():
    match = {
        "id": "m_dropbox",
        "home_team": "Team A",
        "away_team": "Team B",
        "competition": "Cup",
        "highlight_embed_url": "https://www.dropbox.com/s/123/goal.mp4",
    }
    article = generate_blogger_article(match, stage="post_match")
    # Must NOT rewrite dropbox.com to twitframe
    assert "twitframe.com" not in article["content"]
    assert "https://www.dropbox.com/s/123/goal.mp4" in article["content"]


def test_resolve_blogger_access_token_prioritizes_refresh_token(monkeypatch):
    secrets = json.dumps({
        "token": "stale-token",
        "client_id": "cid",
        "client_secret": "csec",
        "refresh_token": "reftok",
    })

    class _Resp:
        def raise_for_status(self):
            return None
        def json(self):
            return {"access_token": "fresh-refreshed-token"}

    monkeypatch.setattr(publisher.requests, "post", lambda *a, **kw: _Resp())
    tok = publisher._resolve_blogger_access_token(
        env_vars={"BLOGGER_CLIENT_SECRETS": secrets}
    )
    assert tok == "fresh-refreshed-token"

