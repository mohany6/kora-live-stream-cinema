"""Blogger SEO article generator for pre-match previews and post-match highlights."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import parse_qs, quote_plus, urlparse
from zoneinfo import ZoneInfo

ADSTERRA_SMARTLINK_URL = "https://budgetezy.org/4/ae626546295ba9dbdec2ea24a521084c"

_EVENT_META: dict[str, tuple[str, str, str]] = {
    "goal": ("⚽", "هدف", "#10b981"),
    "yellow_card": ("🟨", "بطاقة صفراء", "#eab308"),
    "red_card": ("🟥", "بطاقة حمراء", "#ef4444"),
    "substitution": ("🔄", "تبديل", "#3b82f6"),
    "var": ("📺", "تقنية الفيديو VAR", "#8b5cf6"),
}

_POSITION_LABELS_AR: dict[str, str] = {
    "GK": "حارس مرمى",
    "DF": "مدافع",
    "MF": "وسط",
    "FW": "مهاجم",
}


def _attr(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field uniformly from either a Mapping or an object instance."""
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _parse_kickoff_times(raw_kickoff: Any) -> tuple[str, str]:
    """Convert raw kickoff value to ISO-8601 string and multi-timezone Arabic display."""
    kickoff_dt: datetime | None = None
    if isinstance(raw_kickoff, datetime):
        kickoff_dt = raw_kickoff
        kickoff_iso = raw_kickoff.isoformat()
    elif isinstance(raw_kickoff, str):
        kickoff_iso = raw_kickoff
        try:
            kickoff_dt = datetime.fromisoformat(raw_kickoff.replace("Z", "+00:00"))
        except ValueError:
            kickoff_dt = None
    elif hasattr(raw_kickoff, "isoformat"):
        kickoff_dt = raw_kickoff
        kickoff_iso = raw_kickoff.isoformat()
    else:
        kickoff_iso = str(raw_kickoff)

    if kickoff_dt is not None:
        try:
            if getattr(kickoff_dt, "tzinfo", None) is None:
                kickoff_dt = kickoff_dt.replace(tzinfo=timezone.utc)
            utc_time = kickoff_dt.astimezone(timezone.utc).strftime("%H:%M")
            ksa_time = kickoff_dt.astimezone(ZoneInfo("Asia/Riyadh")).strftime("%H:%M")
            cairo_time = kickoff_dt.astimezone(ZoneInfo("Africa/Cairo")).strftime("%H:%M")
            uae_time = kickoff_dt.astimezone(ZoneInfo("Asia/Dubai")).strftime("%H:%M")
            morocco_time = kickoff_dt.astimezone(ZoneInfo("Africa/Casablanca")).strftime("%H:%M")
            display_time = (
                f"{ksa_time} بتوقيت مكة المكرمة "
                f"({cairo_time} القاهرة - {uae_time} الإمارات - {morocco_time} المغرب - {utc_time} غرينتش UTC)"
            )
            return kickoff_iso, display_time
        except Exception:
            return kickoff_iso, str(kickoff_iso)

    return kickoff_iso, str(kickoff_iso).replace("T", " ").replace("Z", " UTC")


def _normalize_lineup(raw_lineup: Any) -> list[dict[str, str]]:
    """Normalize player lineup entries from dicts, models, or plain strings."""
    if not isinstance(raw_lineup, (list, tuple)):
        return []
    players: list[dict[str, str]] = []
    for item in raw_lineup:
        if isinstance(item, str):
            name = item.strip()
            if name:
                players.append({"name": name, "number": "", "position": ""})
            continue
        name = str(_attr(item, "name", "") or _attr(item, "player_name", "") or "").strip()
        if not name:
            continue
        number = _attr(item, "number", "")
        pos_code = str(_attr(item, "position", "") or "").strip().upper()
        players.append(
            {
                "name": name,
                "number": str(number) if number not in (None, "") else "",
                "position": _POSITION_LABELS_AR.get(pos_code, pos_code),
            }
        )
    return players


def _normalize_events(
    raw_events: Any,
    home_name: str,
    away_name: str,
    home_team_id: str | None = None,
    away_team_id: str | None = None,
) -> list[dict[str, Any]]:
    """Normalize and sort match events chronologically."""
    if not isinstance(raw_events, (list, tuple)):
        return []
    normalized: list[dict[str, Any]] = []
    for ev in raw_events:
        raw_type = str(_attr(ev, "type", "") or _attr(ev, "event_type", "") or "goal").strip().lower()
        event_type = raw_type if raw_type in _EVENT_META else "goal"
        if raw_type in {"yellow", "card_yellow"}:
            event_type = "yellow_card"
        elif raw_type in {"red", "card_red"}:
            event_type = "red_card"
        elif raw_type in {"sub", "subst"}:
            event_type = "substitution"

        raw_minute = _attr(ev, "minute", 0)
        try:
            minute = int(raw_minute)
        except (TypeError, ValueError):
            minute = 0

        player_name = str(
            _attr(ev, "player_name", "") or _attr(ev, "player", "") or "لاعب الفريق"
        ).strip()
        team_name = str(
            _attr(ev, "team_name_ar", "")
            or _attr(ev, "team_name", "")
            or _attr(ev, "team", "")
            or ""
        ).strip()
        if not team_name:
            team_id = str(_attr(ev, "team_id", "") or "").strip()
            if team_id and home_team_id and team_id == str(home_team_id):
                team_name = home_name
            elif team_id and away_team_id and team_id == str(away_team_id):
                team_name = away_name

        description = str(_attr(ev, "description_ar", "") or "").strip()
        normalized.append(
            {
                "minute": minute,
                "type": event_type,
                "player_name": player_name,
                "team_name": team_name,
                "description": description,
            }
        )
    normalized.sort(key=lambda item: item["minute"])
    return normalized


def _normalize_highlight_embed_url(raw_url: Any) -> tuple[str | None, str]:
    """Convert YouTube/Dailymotion/Twitter/generic highlight URLs to safe iframe embeds.

    Returns ``(embed_url_or_none, fallback_watch_url)``.
    """
    if not isinstance(raw_url, str) or not raw_url.strip():
        return None, ""
    url = raw_url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None, ""

    host = (parsed.hostname or "").lower()
    path = parsed.path or ""

    def _matches_domain(h: str, domain: str) -> bool:
        return h == domain or h.endswith(f".{domain}")

    if _matches_domain(host, "youtube.com") or _matches_domain(host, "youtu.be"):
        video_id = ""
        if _matches_domain(host, "youtu.be"):
            video_id = path.strip("/").split("/")[0]
        elif path.startswith("/embed/"):
            return url, url
        elif path.startswith("/shorts/"):
            video_id = path.split("/shorts/", 1)[1].split("/")[0]
        else:
            qs = parse_qs(parsed.query)
            video_id = (qs.get("v") or [""])[0]
        if video_id and re.match(r"^[A-Za-z0-9_-]{4,}$", video_id):
            embed = f"https://www.youtube.com/embed/{video_id}?rel=0"
            return embed, f"https://www.youtube.com/watch?v={video_id}"
        return url, url

    if _matches_domain(host, "dailymotion.com") or _matches_domain(host, "dai.ly"):
        if "/embed/video/" in path:
            return url, url
        vid = ""
        if _matches_domain(host, "dai.ly"):
            vid = path.strip("/").split("/")[0]
        elif "/video/" in path:
            vid = path.split("/video/", 1)[1].split("/")[0].split("_")[0]
        if vid and re.match(r"^[A-Za-z0-9]+$", vid):
            return f"https://www.dailymotion.com/embed/video/{vid}", url
        return url, url

    if _matches_domain(host, "twitter.com") or _matches_domain(host, "x.com"):
        if _matches_domain(host, "twitframe.com"):
            return url, url
        return f"https://twitframe.com/show?url={quote_plus(url)}", url

    return url, url


def _build_schema_json(
    *,
    home: str,
    away: str,
    competition: str,
    kickoff_iso: str,
    venue: str,
    target_url: str,
    stage: str,
    home_score: int,
    away_score: int,
) -> str:
    """Build Schema.org SportsEvent JSON-LD safely escaped against script breakout."""
    if stage == "post_match":
        name = f"أهداف وملخص مباراة {home} ({home_score} - {away_score}) {away} - {competition}"
        description = (
            f"شاهد أهداف وملخص مباراة {home} ضد {away} ({home_score} - {away_score}) "
            f"في {competition} مع التحليل التكتيكي الكامل وتفاصيل الأهداف."
        )
        event_status = "https://schema.org/EventCompleted"
    else:
        name = f"مباراة {home} ضد {away} بث مباشر - {competition}"
        description = (
            f"مشاهدة مباراة {home} و{away} اليوم بث مباشر يلا شوت في {competition} "
            "بدون تقطيع مع التشكيل والقناة الناقلة المعلق."
        )
        event_status = "https://schema.org/EventScheduled"

    schema_data: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "SportsEvent",
        "name": name,
        "startDate": kickoff_iso,
        "eventStatus": event_status,
        "description": description,
        "competitor": [
            {"@type": "SportsTeam", "name": home},
            {"@type": "SportsTeam", "name": away},
        ],
        "location": {
            "@type": "Place",
            "name": venue,
        },
        "offers": {
            "@type": "Offer",
            "url": target_url,
            "availability": "https://schema.org/InStock",
            "price": "0",
            "priceCurrency": "USD",
        },
    }
    return json.dumps(schema_data, ensure_ascii=False, indent=2).replace("</", "<\\/")


def _build_adsterra_top_banner() -> str:
    return """  <!-- إعلان ممول قبل زر البث (Adsterra Banner 728x90 / 320x50) -->
  <div style="text-align: center; margin: 20px 0; overflow: hidden;">
    <script>
      atOptions = {
        'key' : '6703ea03ffb309455182c593d4e6ea81',
        'format' : 'iframe',
        'height' : 90,
        'width' : 728,
        'params' : {}
      };
    </script>
    <script data-cfasync="false" src="https://czernik.org/22/6703ea03ffb309455182c593d4e6ea81"></script>
  </div>"""


def _build_adsterra_smartlink_block(button_label: str) -> str:
    label_esc = html.escape(button_label)
    return f"""  <!-- إعلان ممول خلف/تحت زر البث المباشر (Adsterra Smartlink) -->
  <div style="text-align: center; margin: 20px 0;">
    <div style="font-size: 11px; color: #94a3b8; font-weight: bold; margin-bottom: 4px;">خادم بديل عالي السرعة (Adsterra Direct Link)</div>
    <a href="{ADSTERRA_SMARTLINK_URL}" target="_blank" rel="noopener noreferrer" style="display: inline-block; background: #fef3c7; border: 1px dashed #f59e0b; color: #b45309; padding: 10px 28px; border-radius: 20px; font-size: 14px; font-weight: bold; text-decoration: none;">
      {label_esc}
    </a>
  </div>"""


def _build_adsterra_footer_blocks() -> str:
    return """  <!-- Adsterra Native Banner -->
  <div style="margin: 25px 0; text-align: center;">
    <script async="async" fetchpriority="high" data-cfasync="false" src="https://czernik.org/21/f1180bd1a9f13152d2247022e3f6f1b0"></script>
    <div id="container-f1180bd1a9f13152d2247022e3f6f1b0"></div>
  </div>

  <!-- Adsterra SocialBar -->
  <script data-cfasync="false" src="https://czernik.org/14/4d85a8908516d9c268b82f4a5df10c8a"></script>"""


def _build_match_card_html(
    *,
    home_esc: str,
    away_esc: str,
    competition_esc: str,
    display_time_esc: str,
    channel_esc: str,
    commentator_esc: str,
    venue_esc: str,
    referee_esc: str,
    score_row_html: str = "",
) -> str:
    return f"""  <!-- بطاقة تفاصيل وتوقيت المباراة -->
  <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; margin-bottom: 30px;">
    <h3 style="margin-top: 0; color: #0f172a; border-bottom: 2px solid #10b981; padding-bottom: 8px; font-size: 18px;">
      📋 بطاقة وتفاصيل المباراة (Match Card)
    </h3>
    <table style="width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 15px;">
      <tr style="border-bottom: 1px solid #e2e8f0;">
        <td style="padding: 10px 0; color: #64748b; font-weight: bold; width: 35%;">البطولة:</td>
        <td style="padding: 10px 0; color: #0f172a;">{competition_esc}</td>
      </tr>
      <tr style="border-bottom: 1px solid #e2e8f0;">
        <td style="padding: 10px 0; color: #64748b; font-weight: bold;">طرفا اللقاء:</td>
        <td style="padding: 10px 0; color: #0f172a;">{home_esc} ضد {away_esc}</td>
      </tr>{score_row_html}
      <tr style="border-bottom: 1px solid #e2e8f0;">
        <td style="padding: 10px 0; color: #64748b; font-weight: bold;">موعد وتوقيت المباراة:</td>
        <td style="padding: 10px 0; color: #0f172a;" dir="ltr">{display_time_esc}</td>
      </tr>
      <tr style="border-bottom: 1px solid #e2e8f0;">
        <td style="padding: 10px 0; color: #64748b; font-weight: bold;">القناة الناقلة:</td>
        <td style="padding: 10px 0; color: #0f172a;">{channel_esc}</td>
      </tr>
      <tr style="border-bottom: 1px solid #e2e8f0;">
        <td style="padding: 10px 0; color: #64748b; font-weight: bold;">المعلق الرياضي:</td>
        <td style="padding: 10px 0; color: #0f172a;">{commentator_esc}</td>
      </tr>
      <tr style="border-bottom: 1px solid #e2e8f0;">
        <td style="padding: 10px 0; color: #64748b; font-weight: bold;">ملعب المواجهة:</td>
        <td style="padding: 10px 0; color: #0f172a;">{venue_esc}</td>
      </tr>
      <tr>
        <td style="padding: 10px 0; color: #64748b; font-weight: bold;">طاقم التحكيم:</td>
        <td style="padding: 10px 0; color: #0f172a;">{referee_esc}</td>
      </tr>
    </table>
  </div>"""


def _render_team_lineup_column(team_esc: str, formation_esc: str, players: list[dict[str, str]]) -> str:
    formation_badge = (
        f'<span style="background: #dcfce7; color: #166534; padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: bold;">{formation_esc}</span>'
        if formation_esc
        else ""
    )
    if players:
        items_html = "\n".join(
            f'<li style="padding: 6px 0; border-bottom: 1px dashed #e2e8f0; display: flex; justify-content: space-between; font-size: 14px;">'
            f'<span><strong>{html.escape(p["number"]) + ". " if p["number"] else ""}</strong>{html.escape(p["name"])}</span>'
            f'<span style="color: #64748b; font-size: 12px;">{html.escape(p["position"])}</span>'
            f"</li>"
            for p in players
        )
        body = f'<ul style="list-style: none; padding: 0; margin: 10px 0 0 0;">{items_html}</ul>'
    else:
        body = (
            '<p style="font-size: 14px; color: #64748b; margin: 10px 0 0 0;">'
            "التشكيل المتوقع — سيتم تحديث القائمة الرسمية للـ 11 لاعباً فور اعتمادها قبل صافرة البداية."
            "</p>"
        )

    return f"""      <div style="flex: 1 1 280px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px;">
        <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px;">
          <strong style="color: #0f172a; font-size: 15px;">{team_esc}</strong>
          {formation_badge}
        </div>
        {body}
      </div>"""


def _build_lineups_html(
    *,
    home_esc: str,
    away_esc: str,
    home_lineup: list[dict[str, str]],
    away_lineup: list[dict[str, str]],
    home_formation: str,
    away_formation: str,
) -> str:
    home_col = _render_team_lineup_column(home_esc, html.escape(home_formation), home_lineup)
    away_col = _render_team_lineup_column(away_esc, html.escape(away_formation), away_lineup)
    return f"""  <!-- التشكيل المتوقع / الرسمي للفريقين -->
  <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-bottom: 28px;">
    <h3 style="margin-top: 0; color: #0f172a; border-bottom: 2px solid #0ea5e9; padding-bottom: 8px; font-size: 18px;">
      👕 التشكيل المتوقع والرسمي للفريقين (Lineups)
    </h3>
    <div style="display: flex; flex-wrap: wrap; gap: 16px; margin-top: 14px;">
{home_col}
{away_col}
    </div>
  </div>"""


def _build_highlight_player_html(
    *,
    match: Mapping[str, Any],
    home: str,
    away: str,
    competition: str,
    home_esc: str,
    away_esc: str,
    competition_esc: str,
) -> str:
    raw_highlight = match.get("highlight_embed_url") or match.get("highlights_url") or ""
    embed_url, direct_url = _normalize_highlight_embed_url(raw_highlight)

    search_query = f"أهداف وملخص مباراة {home} و {away} {competition}"
    youtube_search_url = f"https://www.youtube.com/results?search_query={quote_plus(search_query)}"
    youtube_wrapper_embed = f"https://www.youtube.com/embed?listType=search&list={quote_plus(search_query)}"

    if embed_url:
        iframe_src_esc = html.escape(embed_url, quote=True)
        fallback_link_esc = html.escape(direct_url or youtube_search_url, quote=True)
        wrapper_badge = "🎬 مشغل الفيديو الرسمي للأهداف والملخص (16:9 HD)"
        fallback_text = "▶ فتح فيديو الأهداف في نافذة مستقلة"
    else:
        iframe_src_esc = html.escape(youtube_wrapper_embed, quote=True)
        fallback_link_esc = html.escape(youtube_search_url, quote=True)
        wrapper_badge = "📺 مشغل ملخص يوتيوب الرسمي (YouTube Official Highlights)"
        fallback_text = f"▶ مشاهدة أهداف {home_esc} و{away_esc} عبر يوتيوب الرسمي"

    return f"""  <!-- مشغل فيديو الأهداف والملخص المتجاوب 16:9 -->
  <div id="kora-highlights-player" style="background: #0f172a; border-radius: 14px; padding: 16px; margin: 24px 0; color: #f8fafc; box-shadow: 0 10px 25px rgba(15, 23, 42, 0.25);">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
      <h3 style="margin: 0; font-size: 17px; color: #34d399;">{wrapper_badge}</h3>
      <span style="font-size: 12px; color: #cbd5e1;">{competition_esc}</span>
    </div>
    <div style="position: relative; width: 100%; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 10px; background: #020617;">
      <iframe
        src="{iframe_src_esc}"
        title="أهداف وملخص مباراة {home_esc} ضد {away_esc}"
        style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0;"
        loading="lazy"
        referrerpolicy="no-referrer"
        sandbox="allow-scripts allow-same-origin allow-presentation allow-popups"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        allowfullscreen>
      </iframe>
    </div>
    <div style="margin-top: 12px; text-align: center;">
      <a href="{fallback_link_esc}" target="_blank" rel="noopener noreferrer" style="display: inline-block; background: #dc2626; color: #ffffff; text-decoration: none; padding: 10px 22px; border-radius: 8px; font-size: 14px; font-weight: bold;">
        {fallback_text}
      </a>
    </div>
  </div>"""


def _build_timeline_html(
    *,
    events: list[dict[str, Any]],
    home_esc: str,
    away_esc: str,
    home_score: int,
    away_score: int,
) -> str:
    if events:
        rows: list[str] = []
        for ev in events:
            icon, label_ar, accent = _EVENT_META.get(ev["type"], ("⚽", "حدث", "#10b981"))
            player_esc = html.escape(ev["player_name"])
            team_esc = html.escape(ev["team_name"]) if ev["team_name"] else ""
            desc_esc = html.escape(ev["description"]) if ev["description"] else label_ar
            team_badge = (
                f'<span style="background: #e2e8f0; color: #334155; padding: 2px 8px; border-radius: 6px; font-size: 12px;">{team_esc}</span>'
                if team_esc
                else ""
            )
            rows.append(
                f'      <li style="display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px; background: #ffffff; border-right: 4px solid {accent}; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);">'
                f'<div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">'
                f'<span style="font-weight: bold; color: #0f172a; min-width: 36px;" dir="ltr">{ev["minute"]}\'</span>'
                f'<span style="font-size: 18px;">{icon}</span>'
                f'<strong style="color: #0f172a;">{player_esc}</strong>'
                f'{team_badge}'
                f"</div>"
                f'<span style="font-size: 13px; color: #64748b;">{desc_esc}</span>'
                f"</li>"
            )
        timeline_body = "\n".join(rows)
    else:
        timeline_body = f"""      <li style="display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; background: #ffffff; border-right: 4px solid #10b981; border-radius: 8px; margin-bottom: 10px;">
        <span><strong>0'</strong> ⏱️ صافرة البداية</span>
        <span style="font-size: 13px; color: #64748b;">انطلاق المواجهة بين {home_esc} و{away_esc}</span>
      </li>
      <li style="display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; background: #ffffff; border-right: 4px solid #eab308; border-radius: 8px; margin-bottom: 10px;">
        <span><strong>45'</strong> ⏸️ نهاية الشوط الأول</span>
        <span style="font-size: 13px; color: #64748b;">توجيهات فنية وتبديلات مرتقبة</span>
      </li>
      <li style="display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; background: #ffffff; border-right: 4px solid #3b82f6; border-radius: 8px;">
        <span><strong>90'</strong> 🏁 صافرة النهاية</span>
        <span style="font-size: 13px; color: #0f172a; font-weight: bold;">النتيجة النهائية: {home_esc} {home_score} - {away_score} {away_esc}</span>
      </li>"""

    return f"""  <!-- الخط الزمني البصري لأحداث المباراة -->
  <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 22px; margin-bottom: 28px;">
    <h3 style="margin-top: 0; color: #0f172a; border-bottom: 2px solid #10b981; padding-bottom: 8px; font-size: 18px;">
      ⏱️ الخط الزمني لأحداث المباراة (Match Timeline)
    </h3>
    <div style="font-size: 12px; color: #64748b; margin-bottom: 14px;">
      دليل الرموز: ⚽ هدف &nbsp;|&nbsp; 🟨 بطاقة صفراء &nbsp;|&nbsp; 🟥 بطاقة حمراء &nbsp;|&nbsp; 🔄 تبديل
    </div>
    <ul style="list-style: none; padding: 0; margin: 0;">
{timeline_body}
    </ul>
  </div>"""


def _format_stats_summary_html(stats: Any, home_esc: str, away_esc: str) -> str:
    if not isinstance(stats, Mapping) or not stats:
        return ""
    rows: list[str] = []
    for raw in stats.values():
        if not isinstance(raw, Mapping):
            continue
        label = html.escape(str(raw.get("label_ar", "")))
        home_val = html.escape(str(raw.get("home", "")))
        away_val = html.escape(str(raw.get("away", "")))
        unit = html.escape(str(raw.get("unit", "")))
        if label:
            rows.append(
                f'<tr style="border-bottom: 1px solid #e2e8f0;">'
                f'<td style="padding: 8px; font-weight: bold; color: #0f172a;">{home_val}{unit}</td>'
                f'<td style="padding: 8px; text-align: center; color: #475569;">{label}</td>'
                f'<td style="padding: 8px; font-weight: bold; color: #0f172a; text-align: left;">{away_val}{unit}</td>'
                f"</tr>"
            )
    if not rows:
        return ""
    return (
        '<div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; margin: 18px 0;">'
        f'<h4 style="margin: 0 0 10px 0; color: #0f172a;">📊 مقارنة الإحصائيات الرقمية ({home_esc} × {away_esc})</h4>'
        '<table style="width: 100%; border-collapse: collapse; font-size: 14px;">'
        + "".join(rows)
        + "</table></div>"
    )


def _format_standings_summary(standings: Any, home: str, away: str) -> str:
    if not isinstance(standings, list) or not standings:
        return ""
    highlights: list[str] = []
    for row in standings:
        if not isinstance(row, Mapping):
            continue
        name = str(row.get("team_name_ar") or "")
        if row.get("is_home") or row.get("is_away") or name in {home, away}:
            pos = row.get("position", "-")
            pts = row.get("points", "-")
            played = row.get("played", "-")
            highlights.append(f"يحتل فريق {html.escape(name)} المركز {html.escape(str(pos))} برصيد {html.escape(str(pts))} نقطة بعد خوض {html.escape(str(played))} مباراة")
    if not highlights:
        return ""
    return " وعلى صعيد أرقام الترتيب المحدثة: " + "، بينما ".join(highlights) + "."


def _build_tactical_review_html(
    *,
    home_esc: str,
    away_esc: str,
    competition_esc: str,
    venue_esc: str,
    home_score: int,
    away_score: int,
    events: list[dict[str, Any]],
    home_formation: str,
    away_formation: str,
    stats: Any,
    standings: Any,
    home: str,
    away: str,
) -> str:
    goals = [ev for ev in events if ev["type"] == "goal"]
    cards = [ev for ev in events if ev["type"] in {"yellow_card", "red_card"}]
    subs = [ev for ev in events if ev["type"] == "substitution"]

    if home_score > away_score:
        outcome_phrase = f"حسم فريق {home_esc} المواجهة لصالحه بفوز ثمين بنتيجة {home_score} مقابل {away_score}"
        winner_esc = home_esc
        loser_esc = away_esc
    elif away_score > home_score:
        outcome_phrase = f"خطف فريق {away_esc} انتصاراً خارج الديار بنتيجة {away_score} مقابل {home_score}"
        winner_esc = away_esc
        loser_esc = home_esc
    else:
        outcome_phrase = f"انتهت القمة الكروية بالتعادل الإيجابي أو السلبي بنتيجة {home_score} مقابل {away_score}"
        winner_esc = home_esc
        loser_esc = away_esc

    goal_mentions = "، ".join(
        f"{html.escape(g['player_name'])} في الدقيقة {g['minute']}" for g in goals[:5]
    )
    goal_sentence = (
        f"وشهدت القمة تسجيل أهداف حاسمة حملت توقيع كل من {goal_mentions}، حيث لعبت الكرات البينية والتحركات في أنصاف المساحات دوراً محورياً في فك التكتلات الدفاعية."
        if goal_mentions
        else f"ورغم تقارب المستويات في وسط الملعب، فإن الفرص المحققة أمام المرميين صنعت الفارق في الحسم النهائي عند الدقيقة التسعين بنتيجة {home_score} - {away_score}."
    )

    cards_sentence = (
        f"كما فرض الالتحام البدني نفسه بقوة في مناطق العمليات، ما دفع حكم اللقاء لإشهار {len(cards)} بطاقات ملونة لإعادة الانضباط التكتيكي داخل أرضية الميدان."
        if cards
        else "واتسمت المواجهة بالانضباط التكتيكي العالي والالتزام الدفاعي المنظم من لاعبي الخط الخلفي في كلا الفريقين."
    )

    subs_sentence = (
        f"وعمد المدربان إلى تنشيط الصفوف عبر {len(subs)} تبديلات مؤثرة في الشوط الثاني لتغيير نسق اللعب واستغلال المساحات الفارغة خلف الأظهرة."
        if subs
        else "ولعبت التدخلات الفنية من دكة البدلاء في الربع ساعة الأخير دوراً بارزاً في الحفاظ على التوازن البدني والتحول السريع من الدفاع إلى الهجوم."
    )

    formation_note = ""
    if home_formation or away_formation:
        hf = html.escape(home_formation or "4-3-3")
        af = html.escape(away_formation or "4-2-3-1")
        formation_note = f"اعتمد {home_esc} على الرسم الخططي {hf} فيما دخل {away_esc} بتنظيم {af} لإغلاق العمق الدفاعي. "

    stats_html = _format_stats_summary_html(stats, home_esc, away_esc)
    standings_extra = _format_standings_summary(standings, home, away)

    return f"""  <!-- التحليل التكتيكي الشامل والموسع (800+ كلمة لتعزيز مدة البقاء وتغطية كافة زوايا القمة) -->
  <article id="kora-tactical-review" style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; margin-bottom: 28px; color: #1e293b;">
    <h3 style="margin-top: 0; color: #0f172a; border-bottom: 2px solid #0ea5e9; padding-bottom: 10px; font-size: 20px;">
      🧠 التحليل التكتيكي الشامل: كيف حُسمت قمة {home_esc} و{away_esc} في {competition_esc}؟
    </h3>

    <h4 style="color: #0f172a; font-size: 17px; margin-top: 18px;">أولاً: قراءة البداية والإيقاع العام في الشوط الأول</h4>
    <p style="font-size: 15px; line-height: 1.9; color: #334155;">
      في سهرة كروية حافلة بالإثارة والندية على أرضية ملعب <strong>{venue_esc}</strong>، {outcome_phrase} ضمن منافسات <strong>{competition_esc}</strong>.
      منذ اللحظات الأولى لانطلاق صافرة البداية، اتضحت معالم الصراع التكتيكي بين الجهازين الفنيين في كيفية السيطرة على منطقة المناورات في وسط الميدان،
      حيث بادر فريق <strong>{home_esc}</strong> بفرض ضغط عالٍ منظم على حامل الكرة في الثلث الأول من ملعب المنافس لإجباره على التمرير الطولي غير الدقيق،
      بينما لجأ فريق <strong>{away_esc}</strong> إلى تدوير الكرة بعرض الملعب مع الاعتماد على تحركات الأظهرة والأجنحة السريعة لفتح زوايا التمرير وكسر خطوط الضغط الأولية.
      {goal_sentence}
      وقد برزت أهمية التحولات الهجومية السريعة التي استغل فيها اللاعبون المساحات المتروكة خلف المدافعين أثناء تقدم خط الدفاع للأمام،
      حيث لم تقتصر الخطورة على اللعب المفتوح فحسب، بل شكلت الكرات الثابتة والركلات الركنية سلاحاً تكتيكياً مهماً أربك التغطية الفردية داخل منطقة الجزاء،
      وأظهر جودة العمل التحضيري الذي يسبق مثل هذه المواجهات الكبرى في البطولات القارية والمحلية.
      كما ساهمت التغطية العكسية للاعبي الارتكاز في منع الهجمات المرتدة الخاطفة خلال النصف الأول من الشوط، مع تبادل مستمر للمراكز بين ثلاثي المقدمة لإرباك رقابة قلوب الدفاع وخلق تفوق عددي على الأطراف.
    </p>

    <h4 style="color: #0f172a; font-size: 17px; margin-top: 20px;">ثانياً: الشوط الثاني ونقطة التحول الحاسمة</h4>
    <p style="font-size: 15px; line-height: 1.9; color: #334155;">
      مع عودة الفريقين من غرف الملابس مطلع الشوط الثاني، ارتفعت وتيرة اللعب بشكل ملحوظ وتبدلت ملامح الحذر الدفاعي إلى جرأة هجومية أكبر بحثاً عن تعديل الكفة أو تأمين التقدم.
      {cards_sentence}
      {subs_sentence}
      وعلى مستوى استغلال الفرص، أظهر فريق <strong>{winner_esc}</strong> نضجاً كبيراً في إدارة الدقائق الحرجة من خلال تنويع أساليب البناء من الخلف، تارة عبر التمريرات القصيرة المتدرجة بين المحاور، وتارة أخرى عبر الكرات القطرية الطويلة نحو الجناح العكسي لخلق مواقف واحد ضد واحد على الرواق.
      في المقابل، حاول فريق <strong>{loser_esc}</strong> العودة في النتيجة عبر تكثيف الكثافة العددية في الثلث الهجومي الأخير وإطلاق التسديدات القوية من خارج منطقة الجزاء لكسر التكتل الدفاعي المتأخر،
      إلا أن التنظيم الدفاعي المتماسك وتألق حراسة المرمى في التصدي للمحاولات الخطيرة حالا دون تغيير المعطيات النهائية للمواجهة حتى صافرة الختام.
      وقد كشفت مجريات النصف الثاني عن فارق اللياقة البدنية والتركيز الذهني في الأمتار الأخيرة، وهو العنصر الذي بات يحسم معظم المواجهات المتكافئة في كرة القدم الحديثة عندما تتقارب الجودة الفردية بين عناصر التشكيلة الأساسية.
    </p>

    <h4 style="color: #0f172a; font-size: 17px; margin-top: 20px;">ثالثاً: الرسم التكتيكي وأفكار المدربين على الخطوط</h4>
    <p style="font-size: 15px; line-height: 1.9; color: #334155;">
      {formation_note}اعتمدت الاستراتيجية الفنية في هذا اللقاء على مرونة التحول بين الحالتين الدفاعية والهجومية؛ ففي لحظات فقدان الكرة تحوّل التنظيم إلى كتلة متوسطة متقاربة الخطوط لا تترك أكثر من عشرين متراً بين الدفاع والوسط، ما قلّص قدرة صناع اللعب على الاستلام بين الخطوط والدوران بالوجه نحو المرمى.
      أما في حالة الاستحواذ، فقد تقدم أحد لاعبي الوسط المساندين للدخول في أنصاف المساحات اليمنى واليسرى لتكوين مثلثات تمرير سريعة مع الظهير والجناح، وهو ما منح الفريق قدرة أكبر على اختراق العمق وتمرير الكرات العرضية الأرضية الخطيرة نحو نقطة الجزاء.
      كما أن قراءة المدربين لمجريات اللعب خلال الدقائق الستين وما بعدها عكست فهماً دقيقاً لمكامن الإرهاق في الخط الخلفي للمنافس، حيث تم توجيه التعليمات المباشرة لاستهداف المساحة الواقعة بين الظهير وقلب الدفاع عبر الانطلاقات القطريّة السريعة التي أربكت التمركز الدفاعي وأجبرت المنافس على ارتكاب الأخطاء التكتيكية على مشارف المنطقة.
      ولا يمكن إغفال الدور القيادي الذي لعبه قادة الفريقين داخل المستطيل الأخضر في ضبط الإيقاع وتهدئة اللعب عند الحاجة أو تسريع نسق التمرير لاستدراج المنافس وإخراجه من مناطقه الحصينة.
    </p>

    {stats_html}

    <h4 style="color: #0f172a; font-size: 17px; margin-top: 20px;">رابعاً: تأثير النتيجة على جدول الترتيب والمرحلة المقبلة</h4>
    <p style="font-size: 15px; line-height: 1.9; color: #334155;">
      تتجاوز قيمة هذه النتيجة مجرد حصد النقاط في جولة عابرة ضمن <strong>{competition_esc}</strong>، إذ تمنح دفعة معنوية هائلة في سباق الصدارة والمنافسة على البطاقات المؤهلة للأدوار الحاسمة، كما ترفع سقف الثقة لدى الجماهير والإدارة الفنية قبل الاستحقاقات المتلاحقة في روزنامة الموسم المزدحمة.{standings_extra}
      فبالنسبة لفريق <strong>{home_esc}</strong>، تمثل الدروس المستفادة من هذه المواجهة قاعدة مهمة للبناء عليها في الجولات القادمة، سواء من حيث ترسيخ الصلابة الدفاعية في التحولات السريعة أو رفع معدل الفاعلية الهجومية أمام المرمى واستثمار أنصاف الفرص.
      أما فريق <strong>{away_esc}</strong>، فسيكون مطالباً بمراجعة بعض التفاصيل المتعلقة بالتغطية في الكرات الثابتة والتمركز العكسي في اللحظات الحرجة، مع البناء على الإيجابيات التي أظهرها اللاعبون خلال فترات السيطرة والضغط العالي في وسط الميدان.
      ومع اشتداد حدة المنافسة في الأمتار المقبلة من البطولة، ستبقى مثل هذه القمم المقياس الحقيقي لجاهزية الأندية الكبرى وقدرتها على التتويج بالألقاب عبر الجمع بين الانضباط التكتيكي والحسم الفردي تحت الضغط الجماهيري والإعلامي الكبير، وهو ما يجعل الجولات القادمة مفتوحة على كافة الاحتمالات والمفاجآت الكروية.
    </p>

    <h4 style="color: #0f172a; font-size: 17px; margin-top: 20px;">خامساً: خلاصة المشهد الكروي ونظرة تحليلية ختامية</h4>
    <p style="font-size: 15px; line-height: 1.9; color: #334155;">
      ختاماً، أكدت مواجهة <strong>{home_esc}</strong> و<strong>{away_esc}</strong> أن التفاصيل الصغيرة والتركيز في استغلال التحولات هي التي ترسم ملامح الانتصار في المواعيد الكبيرة.
      فقد قدّم الفريقان عرضاً تكتيكياً رفيع المستوى استمتع به المتابعون من البداية حتى اللحظة الأخيرة، بين صراع تكتيكي متواصل على الكرة، وفرص متبادلة هددت الشباك، وتدخلات حاسمة من على خط التماس غيّرت مسار الدقائق الأخيرة.
      ويمكنكم مشاهدة ملخص الأهداف الكامل وأبرز اللقطات التحكيمية عبر مشغل الفيديو أعلى المقال، والمشاركة برأيكم في استفتاء اختيار نجم المباراة بالأسفل، مع متابعة التغطية اليومية المستمرة لأقوى المباريات والملخصات الحصرية عبر موقعنا.
    </p>
  </article>"""


def _build_potm_poll_html(
    *,
    match_id: str,
    home: str,
    away: str,
    home_esc: str,
    away_esc: str,
    events: list[dict[str, Any]],
    home_lineup: list[dict[str, str]],
    away_lineup: list[dict[str, str]],
) -> str:
    """Build interactive 'من هو رجل المباراة؟' poll widget backed by localStorage."""
    candidates: list[str] = []
    for ev in events:
        if ev["type"] == "goal" and ev["player_name"] not in candidates:
            candidates.append(ev["player_name"])
    for player in [*home_lineup[:2], *away_lineup[:2]]:
        if player["name"] not in candidates:
            candidates.append(player["name"])
    if len(candidates) < 4:
        defaults = [
            f"نجم هجوم {home}",
            f"صانع ألعاب {away}",
            f"حارس مرمى {home}",
            f"قائد وسط {away}",
        ]
        for d in defaults:
            if len(candidates) >= 4:
                break
            if d not in candidates:
                candidates.append(d)
    candidates = candidates[:4]

    safe_dom_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(match_id)) or "match"
    storage_key_json = json.dumps(f"kora_potm_vote_{safe_dom_id}").replace("</", "<\\/")

    buttons_html = "\n".join(
        f'      <button type="button" class="kora-poll-option" data-idx="{idx}" '
        f'style="display: flex; justify-content: space-between; align-items: center; width: 100%; padding: 12px 16px; margin-bottom: 10px; border: 1px solid #cbd5e1; border-radius: 10px; background: #ffffff; color: #0f172a; font-size: 15px; font-weight: 600; cursor: pointer; text-align: right;">'
        f'<span>⭐ {html.escape(name)}</span>'
        f'<span class="kora-poll-pct" style="font-size: 13px; color: #059669; font-weight: bold;">تصويت</span>'
        f"</button>"
        for idx, name in enumerate(candidates)
    )

    return f"""  <!-- استفتاء تفاعلي: من هو رجل المباراة؟ -->
  <div id="kora-potm-poll-{safe_dom_id}" data-match-id="{html.escape(str(match_id), quote=True)}" style="background: linear-gradient(135deg, #f0fdf4 0%, #eff6ff 100%); border: 1px solid #bfdbfe; border-radius: 14px; padding: 22px; margin: 26px 0;">
    <h3 style="margin-top: 0; color: #0f172a; font-size: 18px; margin-bottom: 6px;">
      🏆 استفتاء الجماهير: من هو رجل المباراة؟
    </h3>
    <p style="font-size: 13px; color: #475569; margin-top: 0; margin-bottom: 16px;">
      شارك برأيك واختر اللاعب الأكثر تأثيراً في قمة {home_esc} و{away_esc}
    </p>
    <div class="kora-poll-options">
{buttons_html}
    </div>
    <p class="kora-poll-status" style="font-size: 13px; color: #0369a1; font-weight: bold; margin: 8px 0 0 0;"></p>
  </div>
  <script>
    (function() {{
      var box = document.getElementById("kora-potm-poll-{safe_dom_id}");
      if (!box) return;
      var storageKey = {storage_key_json};
      var buttons = box.querySelectorAll(".kora-poll-option");
      var statusEl = box.querySelector(".kora-poll-status");
      var baseVotes = [42, 31, 16, 11];
      function renderVotes(selectedIdx) {{
        var total = 0;
        var counts = baseVotes.map(function(v, i) {{
          var val = v + (i === selectedIdx ? 1 : 0);
          total += val;
          return val;
        }});
        buttons.forEach(function(btn, i) {{
          var pct = total > 0 ? Math.round((counts[i] / total) * 100) : 0;
          var badge = btn.querySelector(".kora-poll-pct");
          if (badge) badge.textContent = pct + "% (" + counts[i] + ")";
          if (i === selectedIdx) {{
            btn.style.borderColor = "#10b981";
            btn.style.background = "#ecfdf5";
          }}
        }});
        if (statusEl && selectedIdx !== null) {{
          statusEl.textContent = "شكراً لمشاركتك! تم تسجيل صوتك بنجاح.";
        }}
      }}
      try {{
        var saved = localStorage.getItem(storageKey);
        if (saved !== null) renderVotes(parseInt(saved, 10));
      }} catch (e) {{}}
      buttons.forEach(function(btn) {{
        btn.addEventListener("click", function() {{
          var idx = parseInt(btn.getAttribute("data-idx"), 10);
          try {{ localStorage.setItem(storageKey, String(idx)); }} catch (e) {{}}
          renderVotes(idx);
        }});
      }});
    }})();
  </script>"""


def generate_blogger_article(
    match: Mapping[str, Any],
    platform_base_url: str = "",
    stage: str = "pre_match",
) -> dict[str, Any]:
    """Generate a publication-ready Arabic Blogger article with JSON-LD and CTA.

    Supports two stages:
    - ``pre_match``: Live match preview with Schema.org ``SportsEvent``, lineups,
      broadcast info, and streaming cinema CTA link.
    - ``post_match``: High-dwell-time summary with responsive 16:9 highlight player,
      visual match timeline, 800+ word tactical review, and interactive POTM poll.
    """
    normalized_stage = (stage or "pre_match").strip().lower()
    if normalized_stage not in {"pre_match", "post_match"}:
        raise ValueError(f"Unsupported article stage: {stage}")

    home = str(match.get("home_team") or match.get("home_name") or "الفريق المضيف")
    away = str(match.get("away_team") or match.get("away_name") or "الفريق الضيف")
    competition = str(match.get("competition") or match.get("league") or "مباراة ودية / دوري كرة القدم")
    raw_kickoff = match.get("kickoff_time") or match.get("start_time") or datetime.now(timezone.utc)
    venue = str(match.get("venue") or match.get("stadium") or "ملعب المباراة")
    referee = str(match.get("referee") or "طاقم التحكيم الرسمي")
    channel = str(match.get("channel") or match.get("broadcast") or "beIN Sports / القنوات الناقلة")
    commentator = str(match.get("commentator") or "يحدد لاحقاً")
    match_id = str(match.get("id") or "match")

    try:
        home_score = int(match.get("home_score") if match.get("home_score") is not None else 0)
    except (TypeError, ValueError):
        home_score = 0
    try:
        away_score = int(match.get("away_score") if match.get("away_score") is not None else 0)
    except (TypeError, ValueError):
        away_score = 0

    kickoff_iso, display_time = _parse_kickoff_times(raw_kickoff)

    home_esc = html.escape(home)
    away_esc = html.escape(away)
    competition_esc = html.escape(competition)
    venue_esc = html.escape(venue)
    referee_esc = html.escape(referee)
    channel_esc = html.escape(channel)
    commentator_esc = html.escape(commentator)
    display_time_esc = html.escape(display_time)
    match_id_esc = html.escape(match_id, quote=True)

    clean_base = platform_base_url.rstrip("/") if platform_base_url else ""
    target_url = f"{clean_base}/match/{match_id}" if clean_base else "#"
    target_url_esc = html.escape(target_url, quote=True)
    tunnel_attr = html.escape(clean_base, quote=True)

    schema_json = _build_schema_json(
        home=home,
        away=away,
        competition=competition,
        kickoff_iso=kickoff_iso,
        venue=venue,
        target_url=target_url,
        stage=normalized_stage,
        home_score=home_score,
        away_score=away_score,
    )

    lineups_dict = match.get("lineups") if isinstance(match.get("lineups"), Mapping) else {}
    home_lineup = _normalize_lineup(match.get("home_lineup") or lineups_dict.get("home"))
    away_lineup = _normalize_lineup(match.get("away_lineup") or lineups_dict.get("away"))
    home_formation = str(match.get("home_formation") or "")
    away_formation = str(match.get("away_formation") or "")

    bridge_and_schema = f"""<!-- Cloudflare Dynamic Tunnel Discovery Bridge (Decoupled Shield) -->
<div id="kora-stream-bridge" data-tunnel="{tunnel_attr}" data-match-id="{match_id_esc}" style="display:none;"></div>

<!-- Google Rich Results Schema -->
<script type="application/ld+json">
{schema_json}
</script>"""

    if normalized_stage == "pre_match":
        title = f"مشاهدة مباراة {home} و{away} بث مباشر اليوم في {competition} | يلا شوت كورة لايف"
        labels = ["بث مباشر", competition, "مباريات اليوم"]
        match_card_html = _build_match_card_html(
            home_esc=home_esc,
            away_esc=away_esc,
            competition_esc=competition_esc,
            display_time_esc=display_time_esc,
            channel_esc=channel_esc,
            commentator_esc=commentator_esc,
            venue_esc=venue_esc,
            referee_esc=referee_esc,
        )
        lineups_html = _build_lineups_html(
            home_esc=home_esc,
            away_esc=away_esc,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            home_formation=home_formation,
            away_formation=away_formation,
        )
        content = f"""{bridge_and_schema}

<div dir="rtl" style="font-family: 'Segoe UI', Tahoma, Arial, sans-serif; line-height: 1.8; color: #1e293b; max-width: 800px; margin: 0 auto;">
  <!-- مقدمة المقال الرياضي المدعومة بكلمات البحث (SEO) -->
  <p style="font-size: 16px; margin-bottom: 20px;">
    تتجه أنظار عشاق كرة القدم ومتابعي <strong>{competition_esc}</strong> اليوم نحو القمة المرتقبة التي تجمع بين فريق <strong>{home_esc}</strong> ونظيره <strong>{away_esc}</strong> في مواجهة حاسمة لا تقبل القسمة على اثنين. ويقدم موقعنا تغطية شاملة لمعرفة <strong>القنوات الناقلة لمباراة {home_esc} اليوم</strong>، وموعد اللقاء بتوقيت الدول العربية، واسم المعلق الرياضي، وتفاصيل التشكيل المتوقع لكلا الفريقين.
  </p>

{_build_adsterra_top_banner()}

  <!-- زر التوجيه الرئيسي الآمن للمنصة الحية -->
  <div style="text-align: center; margin: 25px 0;">
    <a href="{target_url_esc}" target="_blank" rel="noopener noreferrer"
       style="display: inline-block; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff; text-decoration: none; padding: 16px 36px; font-size: 18px; font-weight: bold; border-radius: 12px; box-shadow: 0 4px 14px rgba(16, 185, 129, 0.4); transition: transform 0.2s;">
      ▶ الانتقال إلى سيرفر البث المباشر (HD)
    </a>
    <p style="font-size: 12px; color: #64748b; margin-top: 8px;">(متابعة النتائج المباشرة لحظة بلحظة، إحصائيات الاستحواذ، وتبديل سيرفرات البث)</p>
  </div>

{_build_adsterra_smartlink_block("🔥 اضغط هنا للانتقال إلى السيرفر الاحتياطي بدون تقطيع (1080p - 720p - SD)")}

{match_card_html}

{lineups_html}

  <!-- تحليل فني ومحتوى إثرائي لـ Google SEO -->
  <h3 style="color: #0f172a; font-size: 18px;">تحليل اللقاء وموقف الفريقين (يلا شوت بث مباشر)</h3>
  <p style="font-size: 15px; color: #334155;">
    يدخل نادي <strong>{home_esc}</strong> المباراة بتركيز عالٍ لحصد النقاط الثلاث وتعزيز موقعه في جدول الترتيب،
    في حين يسعى نادي <strong>{away_esc}</strong> لتقديم أداء قوي واستغلال الفرص الهجومية للخروج بنتيجة إيجابية تسعد جماهيره.
    يمكنكم متابعة التشكيل الرسمي لكلا الفريقين فور اعتماده، بجانب رصد مباشر للإنذارات والأهداف عبر منصة البث المباشر.
  </p>

  <!-- كلمات البحث المفتاحية الرائجة في جوجل -->
  <div style="background: #f1f5f9; padding: 14px; border-radius: 8px; margin-top: 25px; font-size: 12px; color: #64748b;">
    <strong>الكلمات الدلالية الرائجة:</strong>
    مشاهدة مباراة {home_esc} و{away_esc} بث مباشر، يلا شوت مباراة {home_esc} اليوم، كورة لايف {away_esc}، القنوات الناقلة لمباراة {home_esc}، معلق مباراة {home_esc} و{away_esc}، بث مباشر {competition_esc} بدون تقطيع، أهداف وملخص مباراة {home_esc}.
  </div>

{_build_adsterra_footer_blocks()}
</div>"""
    else:
        title = f"أهداف وملخص مباراة {home} ({home_score} - {away_score}) {away} في {competition} وتفاصيل القمة"
        labels = ["أهداف وملخصات", "أهداف اليوم", competition]
        events = _normalize_events(
            match.get("events"),
            home_name=home,
            away_name=away,
            home_team_id=match.get("home_team_id"),
            away_team_id=match.get("away_team_id"),
        )
        score_row = (
            f'\n      <tr style="border-bottom: 1px solid #e2e8f0;">'
            f'\n        <td style="padding: 10px 0; color: #64748b; font-weight: bold;">النتيجة النهائية:</td>'
            f'\n        <td style="padding: 10px 0; color: #059669; font-weight: bold;" dir="ltr">{home_score} - {away_score}</td>'
            f"\n      </tr>"
        )
        match_card_html = _build_match_card_html(
            home_esc=home_esc,
            away_esc=away_esc,
            competition_esc=competition_esc,
            display_time_esc=display_time_esc,
            channel_esc=channel_esc,
            commentator_esc=commentator_esc,
            venue_esc=venue_esc,
            referee_esc=referee_esc,
            score_row_html=score_row,
        )
        highlight_html = _build_highlight_player_html(
            match=match,
            home=home,
            away=away,
            competition=competition,
            home_esc=home_esc,
            away_esc=away_esc,
            competition_esc=competition_esc,
        )
        timeline_html = _build_timeline_html(
            events=events,
            home_esc=home_esc,
            away_esc=away_esc,
            home_score=home_score,
            away_score=away_score,
        )
        tactical_html = _build_tactical_review_html(
            home_esc=home_esc,
            away_esc=away_esc,
            competition_esc=competition_esc,
            venue_esc=venue_esc,
            home_score=home_score,
            away_score=away_score,
            events=events,
            home_formation=home_formation,
            away_formation=away_formation,
            stats=match.get("stats"),
            standings=match.get("standings"),
            home=home,
            away=away,
        )
        poll_html = _build_potm_poll_html(
            match_id=match_id,
            home=home,
            away=away,
            home_esc=home_esc,
            away_esc=away_esc,
            events=events,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
        )
        content = f"""{bridge_and_schema}

<div dir="rtl" style="font-family: 'Segoe UI', Tahoma, Arial, sans-serif; line-height: 1.8; color: #1e293b; max-width: 820px; margin: 0 auto;">
  <!-- لوحة النتيجة النهائية -->
  <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #ffffff; border-radius: 14px; padding: 22px; text-align: center; margin-bottom: 22px;">
    <div style="font-size: 13px; color: #34d399; font-weight: bold; margin-bottom: 8px;">{competition_esc} • النتيجة النهائية</div>
    <div style="display: flex; align-items: center; justify-content: center; gap: 18px; font-size: 22px; font-weight: bold; flex-wrap: wrap;">
      <span>{home_esc}</span>
      <span style="background: #10b981; color: #ffffff; padding: 6px 18px; border-radius: 10px; font-size: 24px;" dir="ltr">{home_score} - {away_score}</span>
      <span>{away_esc}</span>
    </div>
  </div>

  <p style="font-size: 16px; margin-bottom: 18px;">
    إليكم تغطية شاملة تشمل <strong>أهداف وملخص مباراة {home_esc} و{away_esc}</strong> التي انتهت بنتيجة <strong>{home_score} - {away_score}</strong> في <strong>{competition_esc}</strong>، إلى جانب الخط الزمني الكامل للأهداف والبطاقات والتبديلات والتحليل التكتيكي الدقيق لأحداث القمة.
  </p>

{_build_adsterra_top_banner()}

{highlight_html}

{_build_adsterra_smartlink_block("⚡ سيرفر مشاهدة الملخص والأهداف الكاملة بجودة 4K بدون إعلانات")}

{timeline_html}

{match_card_html}

{tactical_html}

{poll_html}

  <div style="text-align: center; margin: 22px 0;">
    <a href="{target_url_esc}" target="_blank" rel="noopener noreferrer"
       style="display: inline-block; background: #0f172a; color: #ffffff; text-decoration: none; padding: 14px 28px; font-size: 15px; font-weight: bold; border-radius: 10px;">
      📊 استعراض الإحصائيات والتشكيل الكامل في مركز المباراة
    </a>
  </div>

  <!-- كلمات البحث المفتاحية الرائجة في جوجل -->
  <div style="background: #f1f5f9; padding: 14px; border-radius: 8px; margin-top: 25px; font-size: 12px; color: #64748b;">
    <strong>الكلمات الدلالية الرائجة:</strong>
    أهداف وملخص مباراة {home_esc} و{away_esc}، نتيجة مباراة {home_esc} اليوم، ملخص {home_esc} ضد {away_esc}، أهداف {competition_esc} اليوم، تحليل مباراة {home_esc} و{away_esc}.
  </div>

{_build_adsterra_footer_blocks()}
</div>"""

    return {
        "title": title,
        "content": content.strip(),
        "labels": labels,
    }
