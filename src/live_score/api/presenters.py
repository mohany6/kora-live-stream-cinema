"""Presentation helpers: resolve admin precedence and shape API payloads."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from live_score.api.schemas import (
    LeagueOut,
    LineupPlayerOut,
    MatchCardOut,
    MatchDetailOut,
    MatchEventOut,
    StandingRowOut,
    StatItemOut,
    StreamServerOut,
    TeamOut,
)
from live_score.api.store import AdminStore, normalize_stream_url
from live_score.domain.models import Match, MatchDetail, MatchStatus, StreamServer
from live_score.domain.resolver import PriorityResolver

TIMEZONE_LABELS_AR: dict[str, str] = {
    "Asia/Riyadh": "بتوقيت مكة المكرمة",
    "Africa/Casablanca": "بتوقيت المغرب",
    "Africa/Cairo": "بتوقيت القاهرة",
    "Asia/Dubai": "بتوقيت الإمارات",
    "Europe/London": "بتوقيت لندن",
    "UTC": "بالتوقيت العالمي",
}

STATUS_LABELS_AR: dict[MatchStatus, str] = {
    MatchStatus.SCHEDULED: "لم تبدأ",
    MatchStatus.IN_PLAY: "مباشر الآن",
    MatchStatus.HALFTIME: "استراحة",
    MatchStatus.EXTRA_TIME: "مباشر الآن",
    MatchStatus.PENALTIES: "مباشر الآن",
    MatchStatus.FINISHED: "انتهت",
    MatchStatus.POSTPONED: "مؤجلة",
}

OVERRIDABLE_FIELDS = (
    "home_score",
    "away_score",
    "status",
    "elapsed_time",
    "channel",
    "commentator",
    "stadium",
    "referee",
)


def resolve_timezone(name: str) -> tuple[Any, str]:
    """Return a usable tzinfo plus the Arabic label shown in the header."""
    try:
        zone = ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise ValueError(f"Unknown timezone: {name}") from exc
    return zone, TIMEZONE_LABELS_AR.get(name, f"بتوقيت {name}")


def parse_local_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("date must use YYYY-MM-DD") from exc


def _merge_streams(
    primary: list[StreamServer],
    secondary: list[StreamServer],
) -> list[StreamServer]:
    merged: list[StreamServer] = []
    seen: set[str] = set()
    for server in [*primary, *secondary]:
        key = normalize_stream_url(server.url)
        if key in seen:
            continue
        seen.add(key)
        merged.append(server)
    return merged


def resolve_match(detail: MatchDetail, store: AdminStore, now: Optional[datetime] = None) -> Match:
    """Apply the admin layer on top of the base API fixture via PriorityResolver."""
    base = detail.match
    override = store.get_override(base.id)
    admin_streams = [
        StreamServer.model_validate(item) for item in store.list_streams(base.id)
    ]

    if override:
        admin_match = base.model_copy(deep=True)
        for field in OVERRIDABLE_FIELDS:
            if field not in override:
                continue
            value = override[field]
            if field == "status" and value is not None:
                value = MatchStatus(value)
            setattr(admin_match, field, value)
        admin_match.stream_servers = _merge_streams(admin_streams, base.stream_servers)
        return PriorityResolver.resolve(api_match=base, admin_override=admin_match, now=now)

    resolved = PriorityResolver.resolve(api_match=base, now=now)
    if admin_streams:
        resolved.stream_servers = _merge_streams(admin_streams, resolved.stream_servers)
    return resolved


def _stream_id(server: StreamServer) -> str:
    return server.id or f"srv_{uuid.uuid5(uuid.NAMESPACE_URL, server.url).hex[:12]}"


def stream_out(server: StreamServer) -> StreamServerOut:
    return StreamServerOut(
        id=_stream_id(server),
        server_name=server.server_name,
        url=server.url,
        type="m3u8" if server.type == "m3u8" else "iframe",
        is_active=server.is_active,
        quality=server.quality,
        sandbox=server.sandbox,
    )


def _live_minute_label(match: Match) -> Optional[str]:
    if not match.is_live:
        return None
    if match.status == MatchStatus.HALFTIME:
        return "استراحة"
    if match.status == MatchStatus.PENALTIES:
        return "ركلات الترجيح"
    if match.elapsed_time is None:
        return "مباشر"
    return f"{match.elapsed_time}'"


def _countdown_seconds(match: Match, now: datetime) -> Optional[int]:
    if match.status != MatchStatus.SCHEDULED:
        return None
    return max(0, int((match.kickoff_time - now).total_seconds()))


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _competition_subtitle(match: Match) -> str:
    if match.league.round:
        return f"{match.league.name_ar} • {match.league.round}"
    return match.league.name_ar


def build_match_card(match: Match, now: datetime, zone: Any) -> MatchCardOut:
    local_kickoff = match.kickoff_time.astimezone(zone)
    return MatchCardOut(
        id=match.id,
        home_team=TeamOut.model_validate(match.home_team.model_dump()),
        away_team=TeamOut.model_validate(match.away_team.model_dump()),
        league=LeagueOut.model_validate(match.league.model_dump()),
        status=match.status.value,
        status_label_ar=STATUS_LABELS_AR[match.status],
        kickoff_time_utc=_utc_iso(match.kickoff_time),
        kickoff_time_local=local_kickoff.strftime("%H:%M"),
        kickoff_date_local=local_kickoff.date().isoformat(),
        home_score=match.home_score or 0,
        away_score=match.away_score or 0,
        elapsed_time=match.elapsed_time,
        live_minute_label=_live_minute_label(match),
        countdown_seconds=_countdown_seconds(match, now),
        competition_subtitle=_competition_subtitle(match),
        is_admin_override=match.is_admin_override,
        channel=match.channel,
        commentator=match.commentator,
        stadium=match.stadium,
        referee=match.referee,
        has_stream=bool(
            match.stream_servers and any(s.is_active for s in match.stream_servers)
        ),
    )


def _stats_out(stats: Optional[dict[str, Any]]) -> list[StatItemOut]:
    rows: list[StatItemOut] = []
    for key, raw in (stats or {}).items():
        if not isinstance(raw, dict):
            continue
        rows.append(
            StatItemOut(
                key=key,
                label_ar=str(raw.get("label_ar", key)),
                home=float(raw.get("home", 0)),
                away=float(raw.get("away", 0)),
                unit=str(raw.get("unit", "")),
            )
        )
    return rows


def build_match_detail(
    detail: MatchDetail,
    store: AdminStore,
    now: datetime,
    zone: Any,
) -> MatchDetailOut:
    match = resolve_match(detail, store, now=now)
    return MatchDetailOut(
        match=build_match_card(match, now, zone),
        servers=[stream_out(server) for server in match.stream_servers],
        home_lineup=[
            LineupPlayerOut.model_validate(player.model_dump())
            for player in detail.home_lineup
        ],
        away_lineup=[
            LineupPlayerOut.model_validate(player.model_dump())
            for player in detail.away_lineup
        ],
        home_formation=detail.home_formation,
        away_formation=detail.away_formation,
        events=[
            MatchEventOut.model_validate(event.model_dump()) for event in detail.events
        ],
        stats=_stats_out(detail.stats),
        standings=[
            StandingRowOut.model_validate(row) for row in detail.standings
        ],
    )
