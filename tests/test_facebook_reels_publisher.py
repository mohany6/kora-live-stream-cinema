# -*- coding: utf-8 -*-
"""Tests for automated Facebook Reels script, Edge-TTS hook, 3-step Graph API upload, and 30m schedule."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.live_score.domain.facebook_caption import DEFAULT_BLOGGER_URL
from src.live_score.domain.facebook_reel_script import build_reel_script

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
        "home_logo": "",
        "away_logo": "",
        "competition": "دوري روشن السعودي",
        "kickoff_time": "2026-11-27T17:30:00+00:00",
        "channel": "SSC 1",
        "status": "FINISHED",
        "home_score": 3,
        "away_score": 1,
    },
]


def test_build_reel_script_has_hook_no_urls_in_description_and_match_hashtags():
    pre = build_reel_script(SAMPLE_MATCHES[0], stage="pre_match")
    detailed_post = dict(
        SAMPLE_MATCHES[1],
        venue="ملعب الجوهرة المشعة",
        events=[{"type": "goal", "player": "كريم بنزيما", "minute": "24'", "team_side": "home"}],
        stats=[{"label_ar": "الاستحواذ", "home": "58%", "away": "42%"}],
    )
    post = build_reel_script(detailed_post, stage="post_match")

    assert "http://" not in pre["description"] and "https://" not in pre["description"]
    assert "http://" not in post["description"] and "https://" not in post["description"]
    assert DEFAULT_BLOGGER_URL in pre["first_comment"]
    assert DEFAULT_BLOGGER_URL in post["first_comment"]
    assert "#نوتنغهام_فورست_تشيلسي" in pre["description"]
    assert "#الاتحاد_نيوم" in post["description"]
    assert "أول تعليق" in pre["voiceover_text"]
    assert "3" in post["info_primary"] and "1" in post["info_primary"]
    assert post["goal_events"] == [{"player": "كريم بنزيما", "minute": "24'", "side": "home"}]
    assert post["stat_bars"] == [{"label": "الاستحواذ", "home": "58%", "away": "42%"}]
    assert "كريم بنزيما" in post["description"]


def test_publish_reel_with_first_comment_executes_3_step_upload_and_comment(tmp_path: Path):
    from scripts.auto_facebook_reels_publisher import publish_reel_with_first_comment

    mp4 = tmp_path / "sample.mp4"
    mp4.write_bytes(b"FAKE_MP4_BYTES")

    start_resp = MagicMock(status_code=200)
    start_resp.json.return_value = {"video_id": "vid_123", "upload_url": "https://rupload.facebook.com/video-upload/vid_123"}
    up_resp = MagicMock(status_code=200)
    fin_resp = MagicMock(status_code=200)
    fin_resp.json.return_value = {"success": True, "post_id": "999_456"}
    comment_resp = MagicMock(status_code=200)
    comment_resp.json.return_value = {"id": "456_789"}

    with patch("scripts.auto_facebook_reels_publisher.requests.post", side_effect=[start_resp, up_resp, fin_resp, comment_resp]) as m_post:
        res = publish_reel_with_first_comment(
            page_id="999",
            access_token="tok",
            video_path=mp4,
            description="🔥 قمة اليوم #تشيلسي",
            first_comment="https://kora-live-to.blogspot.com/test",
        )

    assert res == {"video_id": "vid_123", "post_id": "999_456", "comment_id": "456_789"}
    assert m_post.call_count == 4

    with pytest.raises(ValueError, match="must not contain URLs"):
        publish_reel_with_first_comment(
            page_id="999",
            access_token="tok",
            video_path=mp4,
            description="Watch at https://evil.example.com",
            first_comment="ok",
        )


def test_auto_reels_publisher_respects_30m_window_and_dedup(tmp_path: Path, monkeypatch):
    from scripts.auto_facebook_reels_publisher import run_facebook_reels_publisher

    monkeypatch.setattr(
        "scripts.auto_facebook_reels_publisher.load_env_vars",
        lambda: {"FB_PAGE_ID": "999", "FB_PAGE_ACCESS_TOKEN": "tok"},
    )
    monkeypatch.setattr("scripts.auto_facebook_reels_publisher.get_top_trending_matches", lambda **kw: SAMPLE_MATCHES)
    monkeypatch.setattr("scripts.auto_facebook_reels_publisher.synthesize_reel_voiceover", lambda text, p, **kw: None)

    rendered: list[str] = []

    def fake_render(script_payload, out_mp4_path, **kw):
        Path(out_mp4_path).write_bytes(b"MP4")
        rendered.append(Path(out_mp4_path).name)
        return Path(out_mp4_path)

    monkeypatch.setattr("scripts.auto_facebook_reels_publisher.render_match_reel_mp4", fake_render)

    published: list[str] = []

    def fake_pub(**kw):
        published.append(Path(kw["video_path"]).name)
        return {"video_id": f"v_{len(published)}", "post_id": f"p_{len(published)}", "comment_id": f"c_{len(published)}"}

    monkeypatch.setattr("scripts.auto_facebook_reels_publisher.publish_reel_with_first_comment", fake_pub)

    cache = tmp_path / "reels_cache.json"
    b_cache = tmp_path / "b_cache.json"
    out_dir = tmp_path / "reels_out"

    # 09:00 UTC: m1 is 11h away (skipped), m2 is FINISHED (posted)
    res_morning = run_facebook_reels_publisher(
        mode="auto",
        out_dir=out_dir,
        reels_cache_path=cache,
        blogger_cache_path=b_cache,
        now=datetime(2026, 11, 27, 9, 0, tzinfo=timezone.utc),
    )
    assert res_morning["posted_count"] == 1
    assert len(published) == 1
    assert "401900873_post_match" in published[0]

    # 19:35 UTC: m1 is 25m before kickoff -> pre_match Reel posted; m2 skipped (already published)
    res_pre = run_facebook_reels_publisher(
        mode="auto",
        out_dir=out_dir,
        reels_cache_path=cache,
        blogger_cache_path=b_cache,
        now=datetime(2026, 11, 27, 19, 35, tzinfo=timezone.utc),
    )
    assert res_pre["posted_count"] == 1
    assert len(published) == 2
    assert "401879225_pre_match" in published[1]
