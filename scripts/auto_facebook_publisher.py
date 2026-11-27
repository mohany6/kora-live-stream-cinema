# -*- coding: utf-8 -*-
"""Automated Facebook Page Poster & First-Comment Publisher (Graph API v25.0 + Local 1-Click Mode)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
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
from src.live_score.domain.facebook_caption import (
    DEFAULT_BLOGGER_URL,
    build_daily_results_copy,
    build_daily_schedule_copy,
    build_match_copy,
    format_arabic_date_label,
)
from src.live_score.domain.facebook_poster import (
    build_daily_results_poster_html,
    build_daily_schedule_poster_html,
    build_match_poster_html,
    render_poster_png,
)
from src.live_score.domain.facebook_reel_script import fetch_club_star_player

FB_CACHE_PATH = ROOT / "data" / "published_facebook.json"
FB_ASSETS_DIR = ROOT / "assets" / "facebook"
FB_GRAPH_VERSION = "v25.0"


def load_fb_cache(cache_path: Path = FB_CACHE_PATH) -> dict[str, Any]:
    """Load Facebook deduplication cache safely."""
    if not cache_path.exists():
        return {"posts": {}}
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("posts"), dict):
            return data
    except (OSError, ValueError, TypeError):
        pass
    return {"posts": {}}


def save_fb_cache(cache_data: Mapping[str, Any], cache_path: Path = FB_CACHE_PATH) -> None:
    """Persist Facebook deduplication cache atomically."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path.with_name(cache_path.name + ".tmp")
    tmp.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, cache_path)


def save_fb_credentials_to_env(page_id: str, access_token: str, env_path: Path | None = None) -> Path:
    """Persist FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN cleanly into .env without clobbering other keys."""
    target = env_path or (ROOT / ".env")
    lines: list[str] = []
    if target.exists():
        lines = target.read_text(encoding="utf-8").splitlines()

    updates = {
        "FB_PAGE_ID": page_id.strip(),
        "FB_PAGE_ACCESS_TOKEN": access_token.strip(),
    }
    seen: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}")
                seen.add(k)
                continue
        new_lines.append(line)
    for k, v in updates.items():
        if k not in seen:
            new_lines.append(f"{k}={v}")

    target.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
    return target


def publish_photo_with_first_comment(
    *,
    page_id: str,
    access_token: str,
    image_path: Path,
    caption: str,
    first_comment: str,
    api_version: str = FB_GRAPH_VERSION,
) -> dict[str, Any]:
    """Upload PNG poster to /{page_id}/photos and attach Blogger link in /{post_id}/comments."""
    photo_url = f"https://graph.facebook.com/{api_version}/{page_id}/photos"
    with open(image_path, "rb") as img_file:
        resp = requests.post(
            photo_url,
            data={"caption": caption, "published": "true", "access_token": access_token},
            files={"source": (image_path.name, img_file, "image/png")},
            timeout=30,
        )

    photo_data = resp.json() if resp.content else {}
    if resp.status_code != 200:
        err_msg = photo_data.get("error", {}).get("message") or f"HTTP {resp.status_code}"
        raise RuntimeError(f"Facebook photo upload failed: {err_msg}")

    post_id = str(photo_data.get("post_id") or photo_data.get("id") or "")
    comment_id = ""
    if post_id and first_comment.strip():
        comment_url = f"https://graph.facebook.com/{api_version}/{post_id}/comments"
        c_resp = requests.post(
            comment_url,
            data={"message": first_comment, "access_token": access_token},
            timeout=20,
        )
        c_data = c_resp.json() if c_resp.content else {}
        if c_resp.status_code == 200:
            comment_id = str(c_data.get("id") or "")

    return {"post_id": post_id, "comment_id": comment_id, "photo_id": str(photo_data.get("id") or "")}


def _resolve_blogger_link(match_id: str | None, stage: str, blogger_cache: Mapping[str, Any]) -> str:
    if match_id:
        articles = blogger_cache.get("articles") or {}
        entry = articles.get(f"{match_id}:{stage}") or articles.get(f"{match_id}:pre_match")
        if isinstance(entry, Mapping) and entry.get("url"):
            return str(entry["url"])
    return DEFAULT_BLOGGER_URL


def _parse_kickoff_utc(raw_kickoff: Any) -> datetime | None:
    if not raw_kickoff:
        return None
    try:
        dt = datetime.fromisoformat(str(raw_kickoff).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _is_match_due_for_auto_post(
    match: Mapping[str, Any],
    now_utc: datetime,
    *,
    lead_minutes: int = 30,
) -> bool:
    """Return True when a match should be posted in auto mode (post-match, or <=30m before kickoff)."""
    status = str(match.get("status") or "").upper()
    stage = str(match.get("stage") or ("post_match" if status == "FINISHED" else "pre_match"))
    if stage == "post_match" or status == "FINISHED":
        return True
    kickoff_utc = _parse_kickoff_utc(match.get("kickoff_time"))
    if kickoff_utc is None:
        return True
    return (kickoff_utc - now_utc) <= timedelta(minutes=lead_minutes)


def _daily_results_ready(matches: list[dict[str, Any]], now_utc: datetime) -> bool:
    """Return True once today's matches have finished (or late evening >= 22:00 UTC with finished results)."""
    if not matches:
        return False
    finished = [m for m in matches if m.get("status") == "FINISHED"]
    if len(finished) == len(matches):
        return True
    return now_utc.hour >= 22 and len(finished) >= 1


def _run_single_facebook_post(
    *,
    mode: str,
    matches: list[dict[str, Any]],
    today_str: str,
    date_lbl: str,
    match_id: str | None,
    dry_run: bool,
    out_dir: Path,
    fb_cache: dict[str, Any],
    fb_cache_path: Path,
    blogger_cache: Mapping[str, Any],
    page_id: str,
    access_token: str,
) -> dict[str, Any]:
    if mode == "match":
        base_match = next((m for m in matches if str(m["id"]) == str(match_id)), matches[0]) if match_id else matches[0]
        target_match = dict(base_match)
        if not target_match.get("home_player_img"):
            target_match["home_player_img"] = fetch_club_star_player(
                str(target_match.get("home_team") or ""),
                team_name_en=str(target_match.get("home_team_en") or ""),
            )["image_url"]
        if not target_match.get("away_player_img"):
            target_match["away_player_img"] = fetch_club_star_player(
                str(target_match.get("away_team") or ""),
                team_name_en=str(target_match.get("away_team_en") or ""),
            )["image_url"]
        stage = str(target_match.get("stage") or ("post_match" if target_match.get("status") == "FINISHED" else "pre_match"))
        cache_key = f"match:{target_match['id']}:{stage}:{today_str}"
        html = build_match_poster_html(target_match, stage=stage)
        poster_path = out_dir / f"match_{target_match['id']}_{stage}_{today_str}.png"
        copy = build_match_copy(
            target_match,
            stage=stage,
            blogger_url=_resolve_blogger_link(str(target_match["id"]), stage, blogger_cache),
        )
    elif mode == "daily_results":
        finished = [m for m in matches if m.get("status") == "FINISHED"]
        chosen = finished if finished else matches
        cache_key = f"daily_results:{today_str}"
        html = build_daily_results_poster_html(chosen, date_label=date_lbl)
        poster_path = out_dir / f"today_results_{today_str}.png"
        copy = build_daily_results_copy(chosen, date_label=date_lbl, blogger_url=DEFAULT_BLOGGER_URL)
    else:
        cache_key = f"daily_slate:{today_str}"
        html = build_daily_schedule_poster_html(matches, date_label=date_lbl)
        poster_path = out_dir / f"today_matches_{today_str}.png"
        copy = build_daily_schedule_copy(matches, date_label=date_lbl, blogger_url=DEFAULT_BLOGGER_URL)

    render_poster_png(html, poster_path)
    (out_dir / "latest_caption.txt").write_text(copy["caption"], encoding="utf-8")
    (out_dir / "latest_first_comment.txt").write_text(copy["first_comment"], encoding="utf-8")

    if dry_run or not (page_id and access_token):
        msg = "تم تجهيز البوستر والنص محلياً (وضع المعاينة — أضف FB_PAGE_ID و FB_PAGE_ACCESS_TOKEN للنشر الآلي)."
        return {
            "ok": True,
            "posted": False,
            "skipped": True,
            "cache_key": cache_key,
            "poster_path": str(poster_path),
            "caption": copy["caption"],
            "first_comment": copy["first_comment"],
            "matches": matches,
            "status_message": msg,
        }

    if cache_key in fb_cache.get("posts", {}):
        return {
            "ok": True,
            "posted": False,
            "skipped": True,
            "already_published": True,
            "cache_key": cache_key,
            "poster_path": str(poster_path),
            "caption": copy["caption"],
            "first_comment": copy["first_comment"],
            "matches": matches,
            "status_message": f"تم نشر هذا المنشور مسبقاً ({cache_key}).",
        }

    res = publish_photo_with_first_comment(
        page_id=page_id,
        access_token=access_token,
        image_path=poster_path,
        caption=copy["caption"],
        first_comment=copy["first_comment"],
    )
    fb_cache.setdefault("posts", {})[cache_key] = {
        "post_id": res["post_id"],
        "comment_id": res["comment_id"],
        "poster_path": str(poster_path),
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    save_fb_cache(fb_cache, fb_cache_path)

    return {
        "ok": True,
        "posted": True,
        "cache_key": cache_key,
        "poster_path": str(poster_path),
        "caption": copy["caption"],
        "first_comment": copy["first_comment"],
        "post_id": res["post_id"],
        "comment_id": res["comment_id"],
        "matches": matches,
        "status_message": f"تم النشر على صفحة فيسبوك وإضافة رابط الموقع في أول تعليق! (Post ID: {res['post_id']})",
    }


def _run_trending_matches_posts(
    *,
    matches: Sequence[Mapping[str, Any]],
    today_str: str,
    date_lbl: str,
    dry_run: bool,
    out_dir: Path,
    fb_cache: dict[str, Any],
    fb_cache_path: Path,
    blogger_cache: Mapping[str, Any],
    page_id: str | None,
    access_token: str | None,
    only_due_matches: bool = False,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Generate or publish one individual post per trending match with match-specific hashtags."""
    eligible = (
        [m for m in matches if _is_match_due_for_auto_post(m, now_utc)]
        if (only_due_matches and now_utc is not None)
        else list(matches)
    )
    if not eligible:
        return {
            "ok": True,
            "posted": False,
            "skipped": True,
            "posted_count": 0,
            "posts": [],
            "poster_path": None,
            "caption": "",
            "first_comment": "",
            "matches": list(matches),
            "status_message": "لا توجد مباريات ترند ضمن نافذة الـ 30 دقيقة قبل الانطلاق حالياً.",
        }

    posts: list[dict[str, Any]] = []
    for match in eligible:
        posts.append(
            _run_single_facebook_post(
                mode="match",
                matches=matches,
                today_str=today_str,
                date_lbl=date_lbl,
                match_id=str(match["id"]),
                dry_run=dry_run,
                out_dir=out_dir,
                fb_cache=fb_cache,
                fb_cache_path=fb_cache_path,
                blogger_cache=blogger_cache,
                page_id=page_id,
                access_token=access_token,
            )
        )

    posted_count = sum(1 for p in posts if p.get("posted"))
    last = posts[-1]
    if dry_run or not (page_id and access_token):
        msg = f"تم تجهيز {len(posts)} منشورات لمباريات الترند محلياً (هاشتاجات مخصصة لكل مباراة)."
    elif posted_count:
        msg = f"تم نشر {posted_count} منشور جديد لمباريات الترند (إجمالي {len(posts)} مباراة) بهاشتاجات منفصلة!"
    else:
        msg = f"جميع منشورات مباريات الترند ({len(posts)}) منشورة مسبقاً لليوم."

    return {
        "ok": True,
        "posted": posted_count > 0,
        "skipped": posted_count == 0,
        "posted_count": posted_count,
        "posts": posts,
        "poster_path": last.get("poster_path"),
        "caption": last.get("caption", ""),
        "first_comment": last.get("first_comment", ""),
        "matches": list(matches),
        "status_message": msg,
    }


def run_facebook_publisher(
    *,
    mode: str = "daily_slate",
    match_id: str | None = None,
    limit: int = 5,
    dry_run: bool = False,
    out_dir: Path = FB_ASSETS_DIR,
    fb_cache_path: Path = FB_CACHE_PATH,
    blogger_cache_path: Path = PUBLISHED_CACHE_PATH,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Generate poster + caption/first-comment and publish via Graph API if configured.

    When ``mode='auto'``, publishes ``daily_slate`` once per day, one post per trending match
    with separate hashtags, and ``daily_results`` once per day after today's trending matches finish.
    """
    current_now = now or datetime.now(timezone.utc)
    if current_now.tzinfo is None:
        current_now = current_now.replace(tzinfo=timezone.utc)
    utc_now = current_now.astimezone(timezone.utc)
    today_str = utc_now.strftime("%Y-%m-%d")
    date_lbl = format_arabic_date_label(current_now)

    matches = get_top_trending_matches(limit=limit, now=current_now)
    if not matches:
        return {"ok": False, "posted": False, "status_message": "لم يتم العثور على مباريات اليوم.", "matches": []}

    blogger_cache = load_published_articles(blogger_cache_path)
    fb_cache = load_fb_cache(fb_cache_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    env_vars = load_env_vars()
    page_id = _get_setting("FB_PAGE_ID", env_vars)
    access_token = _get_setting("FB_PAGE_ACCESS_TOKEN", env_vars)

    if mode == "trending_matches":
        return _run_trending_matches_posts(
            matches=matches,
            today_str=today_str,
            date_lbl=date_lbl,
            dry_run=dry_run,
            out_dir=out_dir,
            fb_cache=fb_cache,
            fb_cache_path=fb_cache_path,
            blogger_cache=blogger_cache,
            page_id=page_id,
            access_token=access_token,
        )

    if mode == "auto":
        slate_res = _run_single_facebook_post(
            mode="daily_slate",
            matches=matches,
            today_str=today_str,
            date_lbl=date_lbl,
            match_id=None,
            dry_run=dry_run,
            out_dir=out_dir,
            fb_cache=fb_cache,
            fb_cache_path=fb_cache_path,
            blogger_cache=blogger_cache,
            page_id=page_id,
            access_token=access_token,
        )
        trending_res = _run_trending_matches_posts(
            matches=matches,
            today_str=today_str,
            date_lbl=date_lbl,
            dry_run=dry_run,
            out_dir=out_dir,
            fb_cache=fb_cache,
            fb_cache_path=fb_cache_path,
            blogger_cache=blogger_cache,
            page_id=page_id,
            access_token=access_token,
            only_due_matches=True,
            now_utc=utc_now,
        )
        results_res: dict[str, Any] | None = None
        if _daily_results_ready(matches, utc_now):
            results_res = _run_single_facebook_post(
                mode="daily_results",
                matches=matches,
                today_str=today_str,
                date_lbl=date_lbl,
                match_id=None,
                dry_run=dry_run,
                out_dir=out_dir,
                fb_cache=fb_cache,
                fb_cache_path=fb_cache_path,
                blogger_cache=blogger_cache,
                page_id=page_id,
                access_token=access_token,
            )
        final = results_res if (results_res and results_res.get("posted")) else (trending_res if trending_res.get("posted") else slate_res)
        final["daily_slate"] = slate_res
        final["trending_posts"] = trending_res["posts"]
        final["daily_results"] = results_res
        return final

    return _run_single_facebook_post(
        mode=mode,
        matches=matches,
        today_str=today_str,
        date_lbl=date_lbl,
        match_id=match_id,
        dry_run=dry_run,
        out_dir=out_dir,
        fb_cache=fb_cache,
        fb_cache_path=fb_cache_path,
        blogger_cache=blogger_cache,
        page_id=page_id,
        access_token=access_token,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Kora Live Automated Facebook Page Publisher")
    parser.add_argument(
        "--mode",
        choices=["auto", "daily_slate", "daily_results", "trending_matches", "match"],
        default="daily_slate",
    )
    parser.add_argument("--match-id", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run_facebook_publisher(mode=args.mode, match_id=args.match_id, dry_run=args.dry_run)
    print(f"[*] {result['status_message']}")
    if result.get("poster_path"):
        print(f"[✓] Poster PNG: {result['poster_path']}")


if __name__ == "__main__":
    main()
