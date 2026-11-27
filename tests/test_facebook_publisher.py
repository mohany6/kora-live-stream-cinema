# -*- coding: utf-8 -*-
"""Tests for Facebook Page caption builder, Cyber-Stadium HTML poster renderer, and Graph API publisher."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.live_score.domain.facebook_caption import (
    DEFAULT_BLOGGER_URL,
    build_daily_results_copy,
    build_daily_schedule_copy,
    build_match_copy,
    format_cairo_mecca_times,
)
from src.live_score.domain.facebook_poster import (
    build_daily_results_poster_html,
    build_daily_schedule_poster_html,
    build_match_poster_html,
    render_poster_png,
)


SAMPLE_MATCHES = [
    {
        "id": "401879225",
        "home_team": "نوتنغهام فورست",
        "away_team": "تشيلسي",
        "home_logo": "https://a.espncdn.com/i/teamlogos/soccer/500/393.png",
        "away_logo": "https://a.espncdn.com/i/teamlogos/soccer/500/363.png",
        "competition": "الدوري الإنجليزي الممتاز",
        "kickoff_time": "2026-11-27T20:00:00+00:00",
        "channel": "beIN SPORTS Xtra 1",
        "status": "SCHEDULED",
        "home_score": 0,
        "away_score": 0,
    },
    {
        "id": "401900873",
        "home_team": "الاتحاد",
        "away_team": "نيوم",
        "home_logo": None,
        "away_logo": None,
        "competition": "دوري روشن السعودي",
        "kickoff_time": "2026-11-27T17:30:00+00:00",
        "channel": "SSC 1 HD",
        "status": "FINISHED",
        "home_score": 3,
        "away_score": 1,
    },
]


def test_format_cairo_mecca_times_handles_valid_and_malformed_inputs():
    times = format_cairo_mecca_times("2026-11-27T20:00:00+00:00")
    assert times["mecca"] == "11:00 م"
    assert times["cairo"] == "10:00 م"

    # Naive ISO string and malformed fallback should never raise
    naive = format_cairo_mecca_times("2026-11-27T17:30:00")
    assert naive["mecca"] == "08:30 م"
    bad = format_cairo_mecca_times("invalid-time")
    assert bad["mecca"] == "يحدد لاحقاً"


def test_facebook_captions_have_zero_urls_and_place_link_in_first_comment():
    daily = build_daily_schedule_copy(SAMPLE_MATCHES)
    assert "http://" not in daily["caption"]
    assert "https://" not in daily["caption"]
    assert "نوتنغهام فورست" in daily["caption"]
    assert "تشيلسي" in daily["caption"]
    assert DEFAULT_BLOGGER_URL in daily["first_comment"]

    pre = build_match_copy(SAMPLE_MATCHES[0], stage="pre_match", blogger_url="https://kora-live-to.blogspot.com/2026/11/forest.html")
    assert "http://" not in pre["caption"] and "https://" not in pre["caption"]
    assert "https://kora-live-to.blogspot.com/2026/11/forest.html" in pre["first_comment"]

    post = build_match_copy(SAMPLE_MATCHES[1], stage="post_match")
    assert "http://" not in post["caption"] and "https://" not in post["caption"]
    assert "3" in post["caption"] and "1" in post["caption"]
    assert DEFAULT_BLOGGER_URL in post["first_comment"]


def test_poster_html_builders_include_rtl_teams_and_fallback_logos():
    daily_html = build_daily_schedule_poster_html(SAMPLE_MATCHES, date_label="الجمعة 27 نوفمبر")
    assert 'dir="rtl"' in daily_html
    assert "نوتنغهام فورست" in daily_html
    assert "11:00 م" in daily_html
    assert "beIN SPORTS Xtra 1" in daily_html

    post_html = build_match_poster_html(SAMPLE_MATCHES[1], stage="post_match")
    assert 'dir="rtl"' in post_html
    assert "الاتحاد" in post_html
    assert "3" in post_html and "1" in post_html
    assert "flaticon.com" in post_html


def test_render_poster_png_invokes_headless_browser_and_writes_file(tmp_path: Path):
    out_png = tmp_path / "poster.png"

    def fake_run(cmd, **kwargs):
        # Extract --screenshot=<path> and create a dummy PNG file
        for arg in cmd:
            if str(arg).startswith("--screenshot="):
                Path(str(arg).split("=", 1)[1]).write_bytes(b"\x89PNG\r\n\x1a\n")
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("src.live_score.domain.facebook_poster.find_headless_browser", return_value="chrome.exe"):
        with patch("src.live_score.domain.facebook_poster.subprocess.run", side_effect=fake_run) as mock_run:
            result = render_poster_png("<html><body>Hi</body></html>", out_png)
            assert result == out_png
            assert out_png.exists()
            assert mock_run.called


def test_publish_photo_with_first_comment_calls_photos_then_comments(tmp_path: Path):
    from scripts.auto_facebook_publisher import publish_photo_with_first_comment

    img = tmp_path / "card.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    photo_resp = MagicMock(status_code=200, content=b'{"id":"111","post_id":"999_111"}')
    photo_resp.json.return_value = {"id": "111", "post_id": "999_111"}
    comment_resp = MagicMock(status_code=200, content=b'{"id":"999_111_222"}')
    comment_resp.json.return_value = {"id": "999_111_222"}

    with patch("scripts.auto_facebook_publisher.requests.post", side_effect=[photo_resp, comment_resp]) as mock_post:
        res = publish_photo_with_first_comment(
            page_id="999",
            access_token="tok_page",
            image_path=img,
            caption="جدول مباريات اليوم",
            first_comment="https://kora-live-to.blogspot.com/",
        )
        assert res["post_id"] == "999_111"
        assert res["comment_id"] == "999_111_222"
        assert mock_post.call_count == 2
        assert "/999/photos" in mock_post.call_args_list[0].args[0]
        assert "/999_111/comments" in mock_post.call_args_list[1].args[0]


def test_run_facebook_publisher_skips_gracefully_without_credentials(tmp_path: Path, monkeypatch):
    from scripts.auto_facebook_publisher import run_facebook_publisher

    monkeypatch.delenv("FB_PAGE_ID", raising=False)
    monkeypatch.delenv("FB_PAGE_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr("scripts.auto_facebook_publisher.load_env_vars", lambda: {})
    monkeypatch.setattr("scripts.auto_facebook_publisher.get_top_trending_matches", lambda **kw: SAMPLE_MATCHES)

    def fake_render(html, out_path, **kw):
        Path(out_path).write_bytes(b"\x89PNG\r\n\x1a\n")
        return Path(out_path)

    monkeypatch.setattr("scripts.auto_facebook_publisher.render_poster_png", fake_render)

    res = run_facebook_publisher(
        mode="daily_slate",
        out_dir=tmp_path / "out",
        fb_cache_path=tmp_path / "fb_cache.json",
        blogger_cache_path=tmp_path / "blogger_cache.json",
    )
    assert res["ok"] is True
    assert res["posted"] is False
    assert res["skipped"] is True
    assert Path(res["poster_path"]).exists()
    assert (tmp_path / "out" / "latest_caption.txt").exists()
    assert (tmp_path / "out" / "latest_first_comment.txt").exists()


def test_daily_results_copy_and_poster_html():
    res_copy = build_daily_results_copy(SAMPLE_MATCHES, date_label="الجمعة 27 نوفمبر")
    assert "http://" not in res_copy["caption"] and "https://" not in res_copy["caption"]
    assert "3" in res_copy["caption"] and "1" in res_copy["caption"]
    assert DEFAULT_BLOGGER_URL in res_copy["first_comment"]

    res_html = build_daily_results_poster_html(SAMPLE_MATCHES, date_label="الجمعة 27 نوفمبر")
    assert "نتائج مباريات" in res_html
    assert "3 - 1" in res_html


def test_match_copy_has_separate_per_match_hashtags():
    from src.live_score.domain.facebook_caption import build_match_hashtags

    m1_tags = build_match_hashtags(SAMPLE_MATCHES[0], stage="pre_match")
    m2_tags = build_match_hashtags(SAMPLE_MATCHES[1], stage="post_match")

    assert "#نوتنغهام_فورست" in m1_tags
    assert "#تشيلسي" in m1_tags
    assert "#نوتنغهام_فورست_تشيلسي" in m1_tags
    assert "#الدوري_الإنجليزي_الممتاز" in m1_tags
    assert "#ريال_مدريد" not in m1_tags

    assert "#الاتحاد" in m2_tags
    assert "#نيوم" in m2_tags
    assert "#الاتحاد_نيوم" in m2_tags
    assert "#دوري_روشن_السعودي" in m2_tags
    assert "#ملخص_المباراة" in m2_tags
    assert "#تشيلسي" not in m2_tags

    c1 = build_match_copy(SAMPLE_MATCHES[0], stage="pre_match")
    c2 = build_match_copy(SAMPLE_MATCHES[1], stage="post_match")
    assert "#نوتنغهام_فورست_تشيلسي" in c1["caption"]
    assert "#الاتحاد_نيوم" in c2["caption"]
    assert "http://" not in c1["caption"] and "https://" not in c1["caption"]
    assert "http://" not in c2["caption"] and "https://" not in c2["caption"]


def test_trending_matches_mode_publishes_separate_posts_per_match(tmp_path: Path, monkeypatch):
    from scripts.auto_facebook_publisher import run_facebook_publisher

    monkeypatch.setattr(
        "scripts.auto_facebook_publisher.load_env_vars",
        lambda: {"FB_PAGE_ID": "999", "FB_PAGE_ACCESS_TOKEN": "tok"},
    )
    monkeypatch.setattr("scripts.auto_facebook_publisher.get_top_trending_matches", lambda **kw: SAMPLE_MATCHES)
    monkeypatch.setattr("scripts.auto_facebook_publisher.render_poster_png", lambda h, p, **kw: Path(p).write_bytes(b"PNG") or Path(p))

    published_calls: list[dict[str, str]] = []

    def fake_publish(*, image_path, caption, first_comment, **kw):
        published_calls.append({"image": Path(image_path).name, "caption": caption, "comment": first_comment})
        return {"post_id": f"999_{len(published_calls)}", "comment_id": f"c_{len(published_calls)}", "photo_id": "1"}

    monkeypatch.setattr("scripts.auto_facebook_publisher.publish_photo_with_first_comment", fake_publish)

    fb_cache = tmp_path / "fb_cache.json"
    res = run_facebook_publisher(
        mode="trending_matches",
        out_dir=tmp_path / "out",
        fb_cache_path=fb_cache,
        blogger_cache_path=tmp_path / "b_cache.json",
    )
    assert res["ok"] is True
    assert res["posted"] is True
    assert res["posted_count"] == 2
    assert len(res["posts"]) == 2
    assert "#نوتنغهام_فورست_تشيلسي" in published_calls[0]["caption"]
    assert "#الاتحاد_نيوم" not in published_calls[0]["caption"]
    assert "#الاتحاد_نيوم" in published_calls[1]["caption"]
    assert "#نوتنغهام_فورست_تشيلسي" not in published_calls[1]["caption"]

    # Second run on same day with same stages skips duplicates
    res_dup = run_facebook_publisher(
        mode="trending_matches",
        out_dir=tmp_path / "out",
        fb_cache_path=fb_cache,
        blogger_cache_path=tmp_path / "b_cache.json",
    )
    assert res_dup["posted_count"] == 0
    assert len(published_calls) == 2


def test_auto_mode_publishes_slate_then_results_when_matches_finish(tmp_path: Path, monkeypatch):
    from datetime import datetime, timezone
    from scripts.auto_facebook_publisher import run_facebook_publisher

    monkeypatch.setattr(
        "scripts.auto_facebook_publisher.load_env_vars",
        lambda: {"FB_PAGE_ID": "999", "FB_PAGE_ACCESS_TOKEN": "tok"},
    )
    monkeypatch.setattr("scripts.auto_facebook_publisher.render_poster_png", lambda h, p, **kw: Path(p).write_bytes(b"PNG") or Path(p))

    posted_modes: list[str] = []

    def fake_publish(*, image_path, **kw):
        posted_modes.append(Path(image_path).name)
        return {"post_id": f"999_{len(posted_modes)}", "comment_id": f"c_{len(posted_modes)}", "photo_id": "1"}

    monkeypatch.setattr("scripts.auto_facebook_publisher.publish_photo_with_first_comment", fake_publish)

    fb_cache = tmp_path / "fb_cache.json"
    b_cache = tmp_path / "b_cache.json"
    out_dir = tmp_path / "out"

    # Morning run (09:00 UTC): posts daily_slate + already-finished m2; skips m1 (kickoff 20:00 UTC > 30m away)
    monkeypatch.setattr("scripts.auto_facebook_publisher.get_top_trending_matches", lambda **kw: SAMPLE_MATCHES)
    res1 = run_facebook_publisher(
        mode="auto",
        out_dir=out_dir,
        fb_cache_path=fb_cache,
        blogger_cache_path=b_cache,
        now=datetime(2026, 11, 27, 9, 0, tzinfo=timezone.utc),
    )
    assert res1["daily_slate"]["posted"] is True
    assert len(res1["trending_posts"]) == 1
    assert res1["trending_posts"][0]["cache_key"].startswith("match:401900873:post_match:")
    assert res1["daily_results"] is None
    assert len(posted_modes) == 2

    # Pre-match window (19:35 UTC, 25m before m1 kickoff at 20:00 UTC): posts pre_match for m1
    res_pre = run_facebook_publisher(
        mode="auto",
        out_dir=out_dir,
        fb_cache_path=fb_cache,
        blogger_cache_path=b_cache,
        now=datetime(2026, 11, 27, 19, 35, tzinfo=timezone.utc),
    )
    assert res_pre["daily_slate"]["posted"] is False
    assert any(p["posted"] and p["cache_key"].startswith("match:401879225:pre_match:") for p in res_pre["trending_posts"])
    assert len(posted_modes) == 3

    # Evening run (22:30 UTC): all matches finished -> posts post_match for m1 + daily_results
    all_finished = [dict(m, status="FINISHED", home_score=2, away_score=0) for m in SAMPLE_MATCHES]
    monkeypatch.setattr("scripts.auto_facebook_publisher.get_top_trending_matches", lambda **kw: all_finished)
    res2 = run_facebook_publisher(
        mode="auto",
        out_dir=out_dir,
        fb_cache_path=fb_cache,
        blogger_cache_path=b_cache,
        now=datetime(2026, 11, 27, 22, 30, tzinfo=timezone.utc),
    )
    assert res2["daily_slate"]["posted"] is False
    assert res2["trending_posts"][0]["posted"] is True
    assert res2["trending_posts"][1]["posted"] is False
    assert res2["daily_results"]["posted"] is True
    assert len(posted_modes) == 5
    assert "today_matches_" in posted_modes[0]
    assert "match_401879225_pre_match_" in posted_modes[2]
    assert "today_results_" in posted_modes[-1]


def test_pre_match_poster_and_caption_include_live_squads():
    with_squad = dict(
        SAMPLE_MATCHES[0],
        home_formation="4-3-3",
        away_formation="4-2-3-1",
        home_lineup=[
            {"name": "Matz Sels", "number": 26, "position": "GK", "is_starter": True},
            {"name": "Chris Wood", "number": 11, "position": "FW", "is_starter": True},
        ],
        away_lineup=[
            {"name": "Robert Sanchez", "number": 1, "position": "GK", "is_starter": True},
            {"name": "Cole Palmer", "number": 20, "position": "MF", "is_starter": True},
        ],
    )
    copy = build_match_copy(with_squad, stage="pre_match")
    assert "التشكيلة الرسمية للمباراة" in copy["caption"]
    assert "Chris Wood" in copy["caption"]
    assert "Cole Palmer" in copy["caption"]
    assert "4-3-3" in copy["caption"]

    html = build_match_poster_html(with_squad, stage="pre_match")
    assert "squads-grid" in html
    assert "Chris Wood" in html
    assert "Cole Palmer" in html
    assert "4-2-3-1" in html
