# -*- coding: utf-8 -*-
"""Automated Facebook Reels (9:16 Remotion + Edge-TTS) Renderer & Graph API Publisher."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import requests

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.auto_blogger_publisher import (
    PUBLISHED_CACHE_PATH,
    _get_setting,
    get_top_trending_matches,
    load_env_vars,
    load_published_articles,
)
from scripts.auto_facebook_publisher import (
    _is_match_due_for_auto_post,
    _resolve_blogger_link,
    load_fb_cache,
    save_fb_cache,
)
from src.live_score.domain.facebook_reel_script import (
    build_reel_script,
    fetch_club_star_player,
    synthesize_reel_voiceover,
)

VIDEO_REELS_DIR = ROOT / "video_reels"
REELS_ASSETS_DIR = ROOT / "assets" / "facebook_reels"
REELS_CACHE_PATH = ROOT / "data" / "published_facebook_reels.json"


def _npx_executable() -> str:
    return shutil.which("npx.cmd") or shutil.which("npx") or "npx"


def render_match_reel_mp4(
    script_payload: Mapping[str, Any],
    out_mp4_path: Path,
    *,
    audio_path: Path | None = None,
    remotion_dir: Path = VIDEO_REELS_DIR,
    duration_seconds: int = 18,
) -> Path:
    """Render a 1080x1920 H.264/AAC MP4 Reel via Remotion CLI."""
    out_mp4_path = out_mp4_path.resolve()
    out_mp4_path.parent.mkdir(parents=True, exist_ok=True)
    public_dir = remotion_dir / "public"
    public_dir.mkdir(parents=True, exist_ok=True)

    audio_file_name = ""
    if audio_path and audio_path.exists():
        target_audio = public_dir / audio_path.name
        if audio_path.resolve() != target_audio.resolve():
            shutil.copyfile(audio_path, target_audio)
        audio_file_name = audio_path.name

    props = {
        "stage": script_payload["stage"],
        "home_team": script_payload["home_team"],
        "away_team": script_payload["away_team"],
        "home_logo": script_payload["home_logo"],
        "away_logo": script_payload["away_logo"],
        "home_player_img": script_payload.get("home_player_img", ""),
        "home_player_name": script_payload.get("home_player_name", ""),
        "away_player_img": script_payload.get("away_player_img", ""),
        "away_player_name": script_payload.get("away_player_name", ""),
        "competition": script_payload["competition"],
        "channel": script_payload["channel"],
        "venue": script_payload.get("venue", ""),
        "commentator": script_payload.get("commentator", ""),
        "home_score": script_payload["home_score"],
        "away_score": script_payload["away_score"],
        "goal_events": script_payload.get("goal_events", []),
        "stat_bars": script_payload.get("stat_bars", []),
        "hook_text": script_payload["hook_text"],
        "info_primary": script_payload["info_primary"],
        "info_secondary": script_payload["info_secondary"],
        "engagement_prompt": script_payload["engagement_prompt"],
        "cta_text": script_payload["cta_text"],
        "audio_file": audio_file_name,
        "duration_seconds": duration_seconds,
    }
    props_path = out_mp4_path.with_suffix(".props.json")
    props_path.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")

    cmd = [
        _npx_executable(),
        "remotion",
        "render",
        "src/index.ts",
        "MatchReel",
        str(out_mp4_path),
        f"--props={props_path}",
        "--codec=h264",
        "--audio-codec=aac",
    ]
    proc = subprocess.run(cmd, cwd=str(remotion_dir), capture_output=True, text=True, timeout=240)
    if proc.returncode != 0 or not out_mp4_path.exists():
        raise RuntimeError(f"Remotion render failed ({proc.returncode}): {proc.stderr or proc.stdout}")
    return out_mp4_path


def publish_reel_with_first_comment(
    *,
    page_id: str,
    access_token: str,
    video_path: Path,
    description: str,
    first_comment: str,
    api_version: str = "v25.0",
) -> dict[str, str]:
    """Upload MP4 Reel via Meta Graph API 3-step video_reels flow and post link in first comment."""
    if "http://" in description or "https://" in description:
        raise ValueError("Algorithm safety guard: Reel description must not contain URLs.")

    base_url = f"https://graph.facebook.com/{api_version}/{page_id}/video_reels"

    # Step 1: Initialize upload session
    start_resp = requests.post(
        base_url,
        data={"upload_phase": "start", "access_token": access_token},
        timeout=30,
    )
    start_data = start_resp.json() if start_resp.content else {}
    if start_resp.status_code != 200 or not start_data.get("video_id") or not start_data.get("upload_url"):
        err_msg = start_data.get("error", {}).get("message") or f"HTTP {start_resp.status_code}"
        raise RuntimeError(f"Facebook Reel start phase failed: {err_msg}")

    video_id = str(start_data["video_id"])
    upload_url = str(start_data["upload_url"])

    # Step 2: Upload binary MP4 bytes to rupload.facebook.com
    video_bytes = video_path.read_bytes()
    up_resp = requests.post(
        upload_url,
        headers={
            "Authorization": f"OAuth {access_token}",
            "offset": "0",
            "file_size": str(len(video_bytes)),
        },
        data=video_bytes,
        timeout=180,
    )
    if up_resp.status_code not in (200, 201):
        raise RuntimeError(f"Facebook Reel binary upload failed: HTTP {up_resp.status_code} {up_resp.text}")

    # Step 3: Finish and publish Reel
    fin_resp = requests.post(
        base_url,
        data={
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": description,
            "access_token": access_token,
        },
        timeout=60,
    )
    fin_data = fin_resp.json() if fin_resp.content else {}
    if fin_resp.status_code != 200:
        err_msg = fin_data.get("error", {}).get("message") or f"HTTP {fin_resp.status_code}"
        raise RuntimeError(f"Facebook Reel finish phase failed: {err_msg}")

    post_id = str(fin_data.get("post_id") or video_id)
    comment_id = ""
    if post_id and first_comment.strip():
        c_resp = requests.post(
            f"https://graph.facebook.com/{api_version}/{post_id}/comments",
            data={"message": first_comment, "access_token": access_token},
            timeout=30,
        )
        c_data = c_resp.json() if c_resp.content else {}
        if c_resp.status_code == 200:
            comment_id = str(c_data.get("id") or "")

    return {"video_id": video_id, "post_id": post_id, "comment_id": comment_id}


def run_facebook_reels_publisher(
    *,
    mode: str = "auto",
    match_id: str | None = None,
    limit: int = 5,
    dry_run: bool = False,
    out_dir: Path = REELS_ASSETS_DIR,
    reels_cache_path: Path = REELS_CACHE_PATH,
    blogger_cache_path: Path = PUBLISHED_CACHE_PATH,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Generate MP4 Reels + Edge-TTS voiceover and publish to Facebook Reels."""
    current_now = now or datetime.now(timezone.utc)
    if current_now.tzinfo is None:
        current_now = current_now.replace(tzinfo=timezone.utc)
    utc_now = current_now.astimezone(timezone.utc)
    today_str = utc_now.strftime("%Y-%m-%d")

    matches = get_top_trending_matches(limit=limit, now=current_now)
    if not matches:
        return {"ok": False, "posted": False, "status_message": "لم يتم العثور على مباريات اليوم.", "reels": []}

    if mode == "match":
        selected = [next((m for m in matches if str(m["id"]) == str(match_id)), matches[0])] if match_id else [matches[0]]
    elif mode == "results":
        finished = [m for m in matches if m.get("status") == "FINISHED" or m.get("stage") == "post_match"]
        selected = [dict(finished[0], stage="post_match")] if finished else [dict(matches[0], stage="post_match")]
    elif mode == "auto":
        selected = [m for m in matches if _is_match_due_for_auto_post(m, utc_now)]
    else:
        selected = list(matches)

    if not selected:
        return {
            "ok": True,
            "posted": False,
            "skipped": True,
            "posted_count": 0,
            "reels": [],
            "status_message": "لا توجد مباريات ترند ضمن نافذة الـ 30 دقيقة قبل الانطلاق حالياً.",
        }

    blogger_cache = load_published_articles(blogger_cache_path)
    reels_cache = load_fb_cache(reels_cache_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    env_vars = load_env_vars()
    page_id = _get_setting("FB_PAGE_ID", env_vars)
    access_token = _get_setting("FB_PAGE_ACCESS_TOKEN", env_vars)

    results: list[dict[str, Any]] = []
    for match in selected:
        mid = str(match["id"])
        stage = str(match.get("stage") or ("post_match" if match.get("status") == "FINISHED" else "pre_match"))
        cache_key = f"reel:{mid}:{stage}:{today_str}"

        blogger_url = _resolve_blogger_link(mid, stage, blogger_cache)
        enriched_match = dict(match)
        if not enriched_match.get("home_player_img"):
            hp = fetch_club_star_player(
                str(enriched_match.get("home_team") or ""),
                team_name_en=str(enriched_match.get("home_team_en") or ""),
            )
            enriched_match["home_player_img"] = hp["image_url"]
            enriched_match["home_player_name"] = hp["name"]
        if not enriched_match.get("away_player_img"):
            ap = fetch_club_star_player(
                str(enriched_match.get("away_team") or ""),
                team_name_en=str(enriched_match.get("away_team_en") or ""),
            )
            enriched_match["away_player_img"] = ap["image_url"]
            enriched_match["away_player_name"] = ap["name"]
        script_payload = build_reel_script(enriched_match, stage=stage, blogger_url=blogger_url)

        if not dry_run and page_id and access_token and cache_key in reels_cache.get("posts", {}):
            existing = reels_cache["posts"][cache_key]
            results.append(
                {
                    "ok": True,
                    "posted": False,
                    "skipped": True,
                    "already_published": True,
                    "cache_key": cache_key,
                    "video_path": existing.get("video_path"),
                    "video_id": existing.get("video_id"),
                }
            )
            continue

        mp3_path = out_dir / f"reel_{mid}_{stage}_{today_str}.mp3"
        mp4_path = out_dir / f"reel_{mid}_{stage}_{today_str}.mp4"
        audio_file = synthesize_reel_voiceover(script_payload["voiceover_text"], mp3_path)
        render_match_reel_mp4(script_payload, mp4_path, audio_path=audio_file)

        if dry_run or not (page_id and access_token):
            results.append(
                {
                    "ok": True,
                    "posted": False,
                    "skipped": True,
                    "cache_key": cache_key,
                    "video_path": str(mp4_path),
                    "description": script_payload["description"],
                    "first_comment": script_payload["first_comment"],
                }
            )
            continue

        pub = publish_reel_with_first_comment(
            page_id=page_id,
            access_token=access_token,
            video_path=mp4_path,
            description=script_payload["description"],
            first_comment=script_payload["first_comment"],
        )
        reels_cache.setdefault("posts", {})[cache_key] = {
            "video_id": pub["video_id"],
            "post_id": pub["post_id"],
            "comment_id": pub["comment_id"],
            "video_path": str(mp4_path),
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
        save_fb_cache(reels_cache, reels_cache_path)
        results.append(
            {
                "ok": True,
                "posted": True,
                "skipped": False,
                "cache_key": cache_key,
                "video_path": str(mp4_path),
                "video_id": pub["video_id"],
                "post_id": pub["post_id"],
                "comment_id": pub["comment_id"],
            }
        )

    posted_count = sum(1 for r in results if r.get("posted"))
    if dry_run or not (page_id and access_token):
        msg = f"تم تجهيز {len(results)} فيديو Reel محلياً بالصوت العربي والهوك."
    elif posted_count:
        msg = f"تم نشر {posted_count} فيديو Reel جديد على صفحة فيسبوك!"
    else:
        msg = f"جميع فيديوهات Reels ({len(results)}) منشورة مسبقاً لليوم."

    return {
        "ok": True,
        "posted": posted_count > 0,
        "posted_count": posted_count,
        "reels": results,
        "video_path": results[-1].get("video_path") if results else None,
        "status_message": msg,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Kora Live Automated Facebook Reels Publisher")
    parser.add_argument("--mode", choices=["auto", "trending_matches", "match", "results"], default="auto")
    parser.add_argument("--match-id", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    res = run_facebook_reels_publisher(mode=args.mode, match_id=args.match_id, dry_run=args.dry_run)
    print(f"[*] {res['status_message']}")
    if res.get("video_path"):
        print(f"[✓] Reel MP4: {res['video_path']}")


if __name__ == "__main__":
    main()
