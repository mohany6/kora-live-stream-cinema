# -*- coding: utf-8 -*-
"""Algorithm-safe Arabic Facebook caption & first-comment builders for Kora Live."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

DEFAULT_BLOGGER_URL = "https://kora-live-to.blogspot.com/"

_CAIRO_TZ = ZoneInfo("Africa/Cairo")
_MECCA_TZ = ZoneInfo("Asia/Riyadh")

_AR_WEEKDAYS = {
    0: "الإثنين",
    1: "الثلاثاء",
    2: "الأربعاء",
    3: "الخميس",
    4: "الجمعة",
    5: "السبت",
    6: "الأحد",
}

_AR_MONTHS = {
    1: "يناير",
    2: "فبراير",
    3: "مارس",
    4: "أبريل",
    5: "مايو",
    6: "يونيو",
    7: "يوليو",
    8: "أغسطس",
    9: "سبتمبر",
    10: "أكتوبر",
    11: "نوفمبر",
    12: "ديسمبر",
}


def _format_ar_12h(dt: datetime) -> str:
    hour = dt.hour % 12 or 12
    suffix = "ص" if dt.hour < 12 else "م"
    return f"{hour:02d}:{dt.minute:02d} {suffix}"


def format_cairo_mecca_times(kickoff_raw: Any) -> dict[str, str]:
    """Convert an ISO kickoff timestamp or datetime to formatted Cairo & Mecca 12h Arabic strings."""
    dt: datetime | None = None
    if isinstance(kickoff_raw, datetime):
        dt = kickoff_raw
    elif isinstance(kickoff_raw, str) and kickoff_raw.strip():
        try:
            dt = datetime.fromisoformat(kickoff_raw.strip().replace("Z", "+00:00"))
        except ValueError:
            dt = None

    if dt is None:
        return {"mecca": "يحدد لاحقاً", "cairo": "يحدد لاحقاً"}

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return {
        "mecca": _format_ar_12h(dt.astimezone(_MECCA_TZ)),
        "cairo": _format_ar_12h(dt.astimezone(_CAIRO_TZ)),
    }


def format_arabic_date_label(now: datetime | None = None) -> str:
    """Return a clean Arabic date header like 'الجمعة 27 نوفمبر' in Mecca time."""
    cur = now or datetime.now(timezone.utc)
    if cur.tzinfo is None:
        cur = cur.replace(tzinfo=timezone.utc)
    local_dt = cur.astimezone(_MECCA_TZ)
    return f"{_AR_WEEKDAYS[local_dt.weekday()]} {local_dt.day} {_AR_MONTHS[local_dt.month]}"


def _strip_urls(text: str) -> str:
    return text.replace("https://", "").replace("http://", "")


def build_daily_schedule_copy(
    matches: Sequence[Mapping[str, Any]],
    *,
    date_label: str | None = None,
    blogger_url: str = DEFAULT_BLOGGER_URL,
) -> dict[str, str]:
    """Generate link-free Facebook daily schedule caption + Blogger link in first comment."""
    label = date_label or format_arabic_date_label()
    lines: list[str] = [f"🔥 جدول قمم ومباريات اليوم ({label}) — لا تفوّت المتعة الكروية! ⚽✨", ""]

    top_teams: list[str] = []
    for m in matches[:5]:
        home = str(m.get("home_team") or "")
        away = str(m.get("away_team") or "")
        comp = str(m.get("competition") or "بطولة كبرى")
        ch = str(m.get("channel") or "beIN SPORTS HD")
        times = format_cairo_mecca_times(m.get("kickoff_time"))
        lines.append(f"🏆 {comp}:")
        lines.append(f"⚽ {home} 🆚 {away}")
        lines.append(f"⏰ {times['cairo']} القاهرة | {times['mecca']} مكة • 📺 {ch}")
        lines.append("")
        if len(top_teams) < 2 and home:
            top_teams.append(home)

    lines.append("👇 رابط جدول المباريات المحدّث لحظة بلحظة والتشكيلات الرسمية في أول تعليق!")
    lines.append("")
    if len(top_teams) >= 2:
        lines.append(f"💬 شاركنا توقعك في التعليقات: ما أكثر مواجهة تنتظرها اليوم بين {top_teams[0]} و{top_teams[1]}؟ 👇🔥")
    else:
        lines.append("💬 شاركنا توقعك لنتائج مباريات اليوم في التعليقات! 👇🔥")
    lines.append("")
    lines.append("#كورة_لايف #مباريات_اليوم #نتائج_مباشرة #كرة_القدم")

    caption = _strip_urls("\n".join(lines))
    target_url = (blogger_url or DEFAULT_BLOGGER_URL).strip()
    first_comment = (
        "🔗 لمتابعة النتائج الحية لحظة بلحظة، التشكيلات الرسمية، وملخصات الأهداف فور انتهاء كل مباراة:\n"
        f"{target_url}"
    )
    return {"caption": caption, "first_comment": first_comment}


def _sanitize_hashtag_token(raw: str) -> str:
    """Convert team or league names into clean Facebook-compatible hashtag tokens."""
    cleaned = re.sub(r"[^\w]+", "_", str(raw or "").strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned


def build_match_hashtags(
    match: Mapping[str, Any],
    *,
    stage: str = "pre_match",
) -> list[str]:
    """Generate distinct, match-specific hashtags for a single trending fixture."""
    home = str(match.get("home_team") or "").strip()
    away = str(match.get("away_team") or "").strip()
    comp = str(match.get("competition") or "").strip()

    home_tag = _sanitize_hashtag_token(home)
    away_tag = _sanitize_hashtag_token(away)
    pair_tag = _sanitize_hashtag_token(f"{home}_{away}") if (home_tag and away_tag) else ""
    comp_tag = _sanitize_hashtag_token(comp)

    stage_tags = (
        ["ملخص_المباراة", "أهداف_اليوم"]
        if stage == "post_match"
        else ["مباريات_اليوم", "توقعات_المباريات"]
    )
    raw_tokens = [home_tag, away_tag, pair_tag, comp_tag, *stage_tags, "كورة_لايف"]

    seen: set[str] = set()
    tags: list[str] = []
    for token in raw_tokens:
        if not token or token in seen:
            continue
        seen.add(token)
        tags.append(f"#{token}")
    return tags


def build_match_copy(
    match: Mapping[str, Any],
    *,
    stage: str = "pre_match",
    blogger_url: str = DEFAULT_BLOGGER_URL,
) -> dict[str, str]:
    """Generate link-free Facebook caption + first comment for a single pre-match or post-match card."""
    home = str(match.get("home_team") or "")
    away = str(match.get("away_team") or "")
    comp = str(match.get("competition") or "مواجهة كبرى")
    ch = str(match.get("channel") or "beIN SPORTS HD")
    times = format_cairo_mecca_times(match.get("kickoff_time"))
    h_score = match.get("home_score") or 0
    a_score = match.get("away_score") or 0
    hashtags_line = " ".join(build_match_hashtags(match, stage=stage))

    if stage == "post_match":
        caption_lines = [
            f"🏁 صافرة النهاية | {home} ({h_score}) 🆚 ({a_score}) {away} 🔥⚽",
            f"🏆 {comp}",
            "",
            "👇 ملخص وأهداف المباراة وإحصائيات اللقاء كاملة في أول تعليق!",
            "",
            f"💬 برأيك من يستحق لقب رجل المباراة بين نجوم {home} و{away}؟ شاركنا رأيك! 👇",
            "",
            hashtags_line,
        ]
        comment_prefix = "🎥 لمتابعة ملخص وأهداف المباراة وتفاصيل اللقاء كاملة:"
    else:
        caption_lines = [
            f"🔥 قمة منتظرة اليوم | {home} 🆚 {away} ⚽✨",
            f"🏆 {comp}",
            f"⏰ {times['cairo']} بتوقيت القاهرة | {times['mecca']} بتوقيت مكة",
            f"📺 القناة الناقلة: {ch}",
            "",
            "👇 رابط التشكيلة الرسمية ومتابعة اللقاء لحظة بلحظة في أول تعليق!",
            "",
            f"💬 توقعك للنتيجة قبل صافرة البداية؟ كم تتوقع أن تنتهي مواجهة {home} ضد {away}؟ 👇🔥",
            "",
            hashtags_line,
        ]
        comment_prefix = "🔗 لمتابعة التشكيلة الرسمية والنتيجة المباشرة لحظة بلحظة:"

    target_url = (blogger_url or DEFAULT_BLOGGER_URL).strip()
    return {
        "caption": _strip_urls("\n".join(caption_lines)),
        "first_comment": f"{comment_prefix}\n{target_url}",
    }


def build_daily_results_copy(
    matches: Sequence[Mapping[str, Any]],
    *,
    date_label: str | None = None,
    blogger_url: str = DEFAULT_BLOGGER_URL,
) -> dict[str, str]:
    """Generate link-free Facebook caption + first comment summarizing today's final match results."""
    label = date_label or format_arabic_date_label()
    lines: list[str] = [f"🏁 حصاد ونتائج مباريات اليوم ({label}) — أرقام وإثارة حتى صافرة النهاية! 🔥⚽", ""]

    for m in matches[:5]:
        home = str(m.get("home_team") or "")
        away = str(m.get("away_team") or "")
        comp = str(m.get("competition") or "بطولة كبرى")
        h_score = int(m.get("home_score") or 0)
        a_score = int(m.get("away_score") or 0)
        lines.append(f"🏆 {comp}:")
        lines.append(f"✅ {home} ({h_score}) 🆚 ({a_score}) {away}")
        lines.append("")

    lines.append("👇 ملخصات الأهداف والترتيب المحدّث وإحصائيات كل مباراة في أول تعليق!")
    lines.append("")
    lines.append("💬 ما أكثر نتيجة فاجأتك اليوم، ومن هو نجم الجولة برأيك؟ شاركنا في التعليقات! 👇🔥")
    lines.append("")
    lines.append("#كورة_لايف #نتائج_مباريات_اليوم #أهداف_اليوم #كرة_القدم")

    target_url = (blogger_url or DEFAULT_BLOGGER_URL).strip()
    first_comment = (
        "🎥 لمتابعة ملخصات وأهداف مباريات اليوم وجداول الترتيب المحدّثة:\n"
        f"{target_url}"
    )
    return {"caption": _strip_urls("\n".join(lines)), "first_comment": first_comment}
