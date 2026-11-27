# -*- coding: utf-8 -*-
"""Arabic Facebook Reels script, 3-second viral hook, caption, and Edge-TTS voiceover generator."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

import requests

from src.live_score.domain.facebook_caption import (
    DEFAULT_BLOGGER_URL,
    build_match_hashtags,
    format_cairo_mecca_times,
)

DEFAULT_REEL_VOICE = "ar-EG-ShakirNeural"
FALLBACK_REEL_VOICE = "ar-SA-HamedNeural"

_FOTMOB_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
_AR_TO_EN_CLUB = {
    "ريال مدريد": "Real Madrid",
    "برشلونة": "Barcelona",
    "ليفربول": "Liverpool",
    "مانشستر سيتي": "Manchester City",
    "مانشستر يونايتد": "Manchester United",
    "أرسنال": "Arsenal",
    "تشيلسي": "Chelsea",
    "نوتنغهام فورست": "Nottingham Forest",
    "بايرن ميونخ": "Bayern Munich",
    "باريس سان جيرمان": "Paris Saint-Germain",
    "إنتر ميلان": "Inter",
    "ميلان": "AC Milan",
    "يوفنتوس": "Juventus",
    "الاتحاد": "Al-Ittihad",
    "الهلال": "Al-Hilal",
    "النصر": "Al-Nassr",
    "الأهلي": "Al Ahly",
    "الزمالك": "Zamalek",
}


def fetch_club_star_player(team_name: str, *, team_name_en: str = "") -> dict[str, str]:
    """Fetch a star attacker/midfielder transparent cutout PNG from FotMob for a club."""
    query = (team_name_en or _AR_TO_EN_CLUB.get(team_name.strip(), "") or team_name).strip()
    if not query:
        return {"name": "", "image_url": ""}
    try:
        sr = requests.get(
            "https://www.fotmob.com/api/data/search/suggest",
            params={"term": query},
            headers=_FOTMOB_HEADERS,
            timeout=6,
        )
        if sr.status_code != 200:
            return {"name": "", "image_url": ""}
        team_id = None
        for grp in sr.json() or []:
            for sug in grp.get("suggestions") or []:
                if sug.get("type") == "team":
                    team_id = sug.get("id")
                    break
            if team_id:
                break
        if not team_id:
            return {"name": "", "image_url": ""}

        tr = requests.get(
            f"https://www.fotmob.com/api/data/teams?id={team_id}",
            headers=_FOTMOB_HEADERS,
            timeout=6,
        )
        if tr.status_code != 200:
            return {"name": "", "image_url": ""}
        squad_sections = (tr.json().get("squad") or {}).get("squad") or []

        def _rank_section(sec: Mapping[str, Any]) -> int:
            title = str(sec.get("title") or "").lower()
            if "attack" in title or "forward" in title:
                return 0
            if "midfield" in title:
                return 1
            if "defend" in title:
                return 2
            return 3

        ordered = sorted(squad_sections, key=_rank_section)
        for sec in ordered:
            for member in (sec.get("members") or [])[:5]:
                pid = member.get("id")
                if not pid:
                    continue
                img_url = f"https://images.fotmob.com/image_resources/playerimages/{pid}.png"
                if requests.head(img_url, headers=_FOTMOB_HEADERS, timeout=4).status_code == 200:
                    return {"name": str(member.get("name") or ""), "image_url": img_url}
    except Exception:
        return {"name": "", "image_url": ""}
    return {"name": "", "image_url": ""}


def _sanitize_tts_text(text: str) -> str:
    """Normalize text for Edge-TTS Arabic voices (avoid colons/English acronyms that cause NoAudioReceived)."""
    cleaned = text
    cleaned = re.sub(r"beIN\s*SPORTS(?:\s*HD|\s*Xtra\s*\d*)?", "بي إن سبورتس", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bSSC(?:\s*\d*)?\b", "إس إس سي", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[A-Za-z0-9_]+", " ", cleaned)
    cleaned = cleaned.replace("؟", "، ").replace("!", "، ").replace(":", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _extract_goal_events(events: Any, *, limit: int = 6) -> list[dict[str, str]]:
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
        return []
    goals: list[dict[str, str]] = []
    for ev in events:
        if not isinstance(ev, Mapping):
            continue
        ev_type = str(ev.get("type") or ev.get("event_type") or "").lower()
        if "goal" not in ev_type and "هدف" not in ev_type and not ev.get("is_goal"):
            continue
        player = str(ev.get("player") or ev.get("player_name") or ev.get("scorer") or "").strip()
        minute = str(ev.get("minute") or ev.get("time") or "").strip()
        side = str(ev.get("team_side") or ev.get("side") or "home").lower()
        if player or minute:
            goals.append({"player": player or "هدف", "minute": minute, "side": side})
        if len(goals) >= limit:
            break
    return goals


def _extract_stat_bars(stats: Any, *, limit: int = 4) -> list[dict[str, str]]:
    if not isinstance(stats, Sequence) or isinstance(stats, (str, bytes)):
        return []
    bars: list[dict[str, str]] = []
    for st in stats:
        if not isinstance(st, Mapping):
            continue
        label = str(st.get("label_ar") or st.get("label") or st.get("name") or "").strip()
        home_v = str(st.get("home") or st.get("home_value") or "0").strip()
        away_v = str(st.get("away") or st.get("away_value") or "0").strip()
        if label:
            bars.append({"label": label, "home": home_v, "away": away_v})
        if len(bars) >= limit:
            break
    return bars


def build_reel_script(
    match: Mapping[str, Any],
    *,
    stage: str = "pre_match",
    blogger_url: str = DEFAULT_BLOGGER_URL,
) -> dict[str, Any]:
    """Build 4-scene vertical Reel script, link-free description, and first comment."""
    home = str(match.get("home_team") or "").strip()
    away = str(match.get("away_team") or "").strip()
    comp = str(match.get("competition") or "مواجهة كبرى").strip()
    channel = str(match.get("channel") or "beIN SPORTS HD").strip()
    venue = str(match.get("venue") or match.get("stadium") or "ملعب اللقاء").strip()
    commentator = str(match.get("commentator") or "").strip()
    times = format_cairo_mecca_times(match.get("kickoff_time"))
    h_score = match.get("home_score") or 0
    a_score = match.get("away_score") or 0
    goal_events = _extract_goal_events(match.get("events"))
    stat_bars = _extract_stat_bars(match.get("stats"))
    hashtags = " ".join(build_match_hashtags(match, stage=stage))

    if stage == "post_match":
        hook_text = f"ملخص قمة {home} و{away}.. من كان نجم اللقاء؟"
        info_primary = f"{home} {h_score} - {a_score} {away}"
        info_secondary = f"{comp} • {venue}"
        engagement_prompt = f"من يستحق لقب رجل المباراة بين نجوم {home} و{away}؟"
        cta_text = "ملخص الأهداف والإحصائيات الكاملة في أول تعليق"

        scorers_speech = ""
        if goal_events:
            names = "، ".join(g["player"] for g in goal_events[:3] if g["player"])
            if names:
                scorers_speech = f" وسجل الأهداف {names}. "

        voiceover_raw = (
            f"نتيجة وإحصائيات قمة {home} ضد {away} في {comp}. "
            f"انتهت المباراة بنتيجة {h_score} مقابل {a_score}.{scorers_speech} "
            f"شاركنا رأيك في التعليقات، من يستحق لقب رجل المباراة، "
            f"ورابط الملخص والأهداف الكامل موجود الآن في أول تعليق."
        )
        goals_lines = (
            [f"⚽ {g['player']} ({g['minute']})" if g["minute"] else f"⚽ {g['player']}" for g in goal_events]
            if goal_events
            else []
        )
        description = "\n".join(
            [
                f"🏁 صافرة النهاية | {home} ({h_score}) 🆚 ({a_score}) {away}",
                f"🏆 {comp} | 🏟️ {venue}",
                *goals_lines,
                "",
                f"👇 {cta_text}",
                f"💬 {engagement_prompt}",
                "",
                hashtags,
            ]
        )
        first_comment = f"🎥 ملخص وأهداف {home} ضد {away} وإحصائيات اللقاء كاملة:\n{blogger_url}"
    else:
        hook_text = f"من يحسم قمة {home} ضد {away} اليوم؟"
        info_primary = f"{times['cairo']} القاهرة  |  {times['mecca']} مكة"
        info_secondary = f"{comp} • {channel}"
        engagement_prompt = f"اكتب توقعك للنتيجة قبل صافرة البداية في التعليقات!"
        cta_text = "رابط التشكيلة الرسمية والمتابعة المباشرة في أول تعليق"
        voiceover_raw = (
            f"من يحسم قمة {home} ضد {away} اليوم، "
            f"مواجهة نارية في {comp} تنطلق بتوقيت القاهرة ومكة على قناة {channel}. "
            f"اكتب توقعك للنتيجة الآن في التعليقات، "
            f"ورابط التشكيلة الرسمية والمتابعة المباشرة موجود في أول تعليق."
        )
        description = "\n".join(
            [
                f"🔥 {hook_text}",
                f"🏆 {comp} | ⏰ {info_primary}",
                f"📺 {channel}",
                "",
                f"👇 {cta_text}",
                f"💬 {engagement_prompt}",
                "",
                hashtags,
            ]
        )
        first_comment = f"🔗 التشكيلة الرسمية والنتيجة المباشرة لمباراة {home} ضد {away}:\n{blogger_url}"

    return {
        "stage": stage,
        "home_team": home,
        "away_team": away,
        "home_logo": str(match.get("home_logo") or ""),
        "away_logo": str(match.get("away_logo") or ""),
        "home_player_img": str(match.get("home_player_img") or ""),
        "home_player_name": str(match.get("home_player_name") or ""),
        "away_player_img": str(match.get("away_player_img") or ""),
        "away_player_name": str(match.get("away_player_name") or ""),
        "competition": comp,
        "channel": channel,
        "venue": venue,
        "commentator": commentator,
        "home_score": int(h_score),
        "away_score": int(a_score),
        "goal_events": goal_events,
        "stat_bars": stat_bars,
        "hook_text": hook_text,
        "info_primary": info_primary,
        "info_secondary": info_secondary,
        "engagement_prompt": engagement_prompt,
        "cta_text": cta_text,
        "voiceover_text": _sanitize_tts_text(voiceover_raw),
        "description": description,
        "first_comment": first_comment,
    }


async def _synthesize_async(text: str, out_path: Path, voice: str) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(str(out_path))


def synthesize_reel_voiceover(
    text: str,
    out_mp3_path: Path,
    *,
    voice: str = DEFAULT_REEL_VOICE,
) -> Path | None:
    """Generate Arabic MP3 voiceover via edge-tts with clean fallback; removes 0-byte files."""
    out_mp3_path.parent.mkdir(parents=True, exist_ok=True)
    clean_text = _sanitize_tts_text(text) or "قمة كروية منتظرة اليوم على كورة لايف."

    for candidate_voice in (voice, FALLBACK_REEL_VOICE):
        try:
            asyncio.run(_synthesize_async(clean_text, out_mp3_path, candidate_voice))
            if out_mp3_path.exists() and out_mp3_path.stat().st_size > 0:
                return out_mp3_path
        except Exception:
            if out_mp3_path.exists() and out_mp3_path.stat().st_size == 0:
                out_mp3_path.unlink(missing_ok=True)
    return None
