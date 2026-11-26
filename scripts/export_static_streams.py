# -*- coding: utf-8 -*-
"""Export live/scheduled matches and stream servers to static JSON for Cloudflare Pages."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from live_score.api.catalog import LiveFixturesCatalog
from live_score.api.fixtures import build_demo_fixtures, create_catalog
from live_score.api.presenters import (
    _stats_out,
    build_match_card,
    resolve_timezone,
    stream_out,
)
from live_score.api.schemas import (
    LineupPlayerOut,
    MatchEventOut,
    StandingRowOut,
    StatItemOut,
)
from live_score.domain.models import Match, MatchDetail, StreamServer
from live_score.domain.resolver import ChannelStreamMapper, PriorityResolver

logger = logging.getLogger(__name__)

DEFAULT_TIMEZONE = "Asia/Riyadh"
DEFAULT_OUTPUT_PATH = ROOT / "frontend" / "public" / "data" / "matches.json"
SECONDARY_OUTPUT_PATH = ROOT / "data" / "matches.json"
PLAYER_PROXY_PREFIX = "/api/v1/stream/player/"


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _utc_iso(value: datetime) -> str:
    return _ensure_utc(value).isoformat().replace("+00:00", "Z")


def _normalize_static_stream_url(url: str) -> str:
    """Rewrite relative FastAPI proxy URLs to direct upstream player URLs for static hosting."""
    clean = url.strip()
    if clean.startswith(PLAYER_PROXY_PREFIX):
        rest = clean[len(PLAYER_PROXY_PREFIX) :]
        slug, sep, query = rest.partition("?")
        slug = slug.strip("/")
        base = f"{ChannelStreamMapper.ALBA_BASE_URL}/{slug}/"
        return f"{base}?{query}" if sep and query else base
    return clean


def _serialize_servers(servers: Sequence[StreamServer]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for server in servers:
        payload = stream_out(server).model_dump(mode="json")
        payload["url"] = _normalize_static_stream_url(str(payload["url"]))
        serialized.append(payload)
    return serialized


def _serialize_stats(raw_stats: Any) -> list[dict[str, Any]]:
    if isinstance(raw_stats, list):
        return [
            StatItemOut.model_validate(item).model_dump(mode="json")
            for item in raw_stats
        ]
    return [item.model_dump(mode="json") for item in _stats_out(raw_stats)]


def _serialize_lineup(players: Sequence[Any]) -> list[dict[str, Any]]:
    return [
        LineupPlayerOut.model_validate(
            player.model_dump() if hasattr(player, "model_dump") else player
        ).model_dump(mode="json")
        for player in players
    ]


def _serialize_events(events: Sequence[Any], match_id: str) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for idx, event in enumerate(events, start=1):
        raw = event.model_dump() if hasattr(event, "model_dump") else dict(event)
        if not raw.get("id"):
            raw["id"] = f"ev_{match_id}_{idx}"
        serialized.append(MatchEventOut.model_validate(raw).model_dump(mode="json"))
    return serialized


def _serialize_standings(standings: Sequence[Any]) -> list[dict[str, Any]]:
    return [
        StandingRowOut.model_validate(row).model_dump(mode="json")
        for row in standings
    ]


def _serialize_match_entry(
    item: MatchDetail | Match,
    now: datetime,
    zone: Any,
) -> dict[str, Any]:
    detail = item if isinstance(item, MatchDetail) else MatchDetail(match=item)
    base_match = detail.match
    if base_match.kickoff_time.tzinfo is None:
        base_match = base_match.model_copy(
            update={"kickoff_time": _ensure_utc(base_match.kickoff_time)}
        )

    resolved_match = PriorityResolver.resolve(api_match=base_match, now=now)
    card = build_match_card(resolved_match, now, zone).model_dump(mode="json")
    card["servers"] = _serialize_servers(resolved_match.stream_servers)
    card["home_lineup"] = _serialize_lineup(detail.home_lineup)
    card["away_lineup"] = _serialize_lineup(detail.away_lineup)
    card["home_formation"] = detail.home_formation
    card["away_formation"] = detail.away_formation
    card["events"] = _serialize_events(detail.events, resolved_match.id)
    card["stats"] = _serialize_stats(detail.stats)
    card["standings"] = _serialize_standings(detail.standings)
    return card


def _should_hydrate_detail(detail: MatchDetail, now: datetime) -> bool:
    match = detail.match
    if match.is_live:
        return True
    kickoff = _ensure_utc(match.kickoff_time)
    return (now - timedelta(hours=12)) <= kickoff <= (now + timedelta(hours=24))


def _hydrate_catalog_details(
    catalog: LiveFixturesCatalog,
    fixture_map: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    """Best-effort hydration of lineups, events, stats, standings, and channels."""
    updated = dict(fixture_map)
    targets = [
        (match_id, detail)
        for match_id, detail in updated.items()
        if isinstance(detail, MatchDetail) and _should_hydrate_detail(detail, now)
    ]
    if not targets:
        return updated

    def _hydrate_one(entry: tuple[str, MatchDetail]) -> tuple[str, MatchDetail]:
        match_id, base_detail = entry
        hydrated = base_detail
        try:
            fetched = catalog.get_detail(match_id, now)
            if isinstance(fetched, MatchDetail):
                hydrated = fetched
        except Exception as exc:  # noqa: BLE001 - best-effort hydration
            logger.debug("Detail hydration skipped for %s: %s", match_id, exc)
        try:
            catalog._enrich_broadcast_meta(hydrated.match, now)
        except Exception:  # noqa: BLE001 - best-effort channel enrichment
            pass
        return match_id, hydrated

    with ThreadPoolExecutor(max_workers=min(6, len(targets))) as pool:
        for match_id, hydrated in pool.map(_hydrate_one, targets):
            updated[match_id] = hydrated
    return updated


def _write_json_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(content, encoding="utf-8")
    os.replace(temp_path, path)


def export_static_matches_json(
    target_path: Path | str | None = None,
    now: datetime | None = None,
    *,
    timezone_name: str = DEFAULT_TIMEZONE,
    force_refresh: bool = False,
    hydrate_details: bool = False,
) -> int:
    """Export fixtures and streaming servers to static JSON; return match count."""
    current_now = _ensure_utc(now or datetime.now(timezone.utc))
    zone, timezone_label = resolve_timezone(timezone_name)

    catalog = create_catalog(current_now)
    if catalog is not None:
        if force_refresh and isinstance(catalog, LiveFixturesCatalog):
            catalog.refresh(current_now, force=True)
        fixture_map = catalog.fixture_map(current_now)
        if hydrate_details and isinstance(catalog, LiveFixturesCatalog):
            fixture_map = _hydrate_catalog_details(catalog, fixture_map, current_now)
    else:
        fixture_map = {d.match.id: d for d in build_demo_fixtures(current_now)}

    serialized_matches = [
        _serialize_match_entry(item, current_now, zone)
        for item in (fixture_map or {}).values()
    ]
    serialized_matches.sort(key=lambda m: (m["kickoff_time_utc"], m["id"]))

    payload = {
        "date": current_now.astimezone(zone).date().isoformat(),
        "timezone": timezone_name,
        "timezone_label_ar": timezone_label,
        "updated_at": _utc_iso(current_now),
        "count": len(serialized_matches),
        "matches": serialized_matches,
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2)

    destinations = (
        [Path(target_path)]
        if target_path is not None
        else [DEFAULT_OUTPUT_PATH, SECONDARY_OUTPUT_PATH]
    )
    for dest in destinations:
        _write_json_atomic(dest, encoded)

    return len(serialized_matches)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export matches and stream servers to static JSON."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional target JSON path (defaults to frontend/public/data/matches.json).",
    )
    parser.add_argument(
        "--refresh",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Force synchronous live catalog refresh before exporting.",
    )
    parser.add_argument(
        "--hydrate-details",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Hydrate lineups, events, stats, standings, and channel metadata.",
    )
    args = parser.parse_args(argv)

    count = export_static_matches_json(
        target_path=args.output,
        force_refresh=args.refresh,
        hydrate_details=args.hydrate_details,
    )
    saved_path = args.output or DEFAULT_OUTPUT_PATH
    print(f"Exported {count} matches to {saved_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
