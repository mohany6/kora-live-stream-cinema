"""Admin CMS endpoints for stream management and emergency match overrides."""

from __future__ import annotations

import logging
import re
import secrets
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from live_score.api.cache import global_cache
from live_score.api.presenters import (
    build_match_card,
    parse_local_date,
    resolve_match,
    resolve_timezone,
    stream_out,
)
from live_score.api.schemas import (
    AdIn,
    AdOut,
    AdsListOut,
    AdUpdateIn,
    AdminMatchesOut,
    AdminMatchOut,
    AdminOverrideIn,
    AnalyticsStatsOut,
    MatchCardOut,
    StreamMutationOut,
    StreamServerIn,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def require_admin(
    request: Request,
    x_admin_token: str = Header(default="", alias="X-Admin-Token"),
) -> None:
    expected = request.app.state.admin_token
    if not expected or not secrets.compare_digest(x_admin_token, expected):
        from live_score.api.security import get_client_ip, global_rate_limiter

        global_rate_limiter.record_admin_auth_failure(get_client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin token",
        )


def _get_fixture(request: Request, match_id: str):
    catalog = getattr(request.app.state, "catalog", None)
    if catalog is not None:
        now = request.app.state.clock()
        detail = catalog.fixture_map(now).get(match_id)
        if detail is not None:
            return detail
    detail = request.app.state.fixtures.get(match_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return detail


def _mutation_payload(request: Request, match_id: str) -> StreamMutationOut:
    match = resolve_match(_get_fixture(request, match_id), request.app.state.store)
    return StreamMutationOut(
        match_id=match_id,
        servers=[stream_out(server) for server in match.stream_servers],
    )


@router.get(
    "/matches",
    response_model=AdminMatchesOut,
    dependencies=[Depends(require_admin)],
)
def list_matches(
    request: Request,
    date_str: Optional[str] = Query(default=None, alias="date"),
    tz: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
) -> AdminMatchesOut:
    now: datetime = request.app.state.clock()
    timezone_name = tz or request.app.state.timezone_name
    try:
        zone, timezone_label = resolve_timezone(timezone_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    target_date = None
    if date_str is not None:
        try:
            target_date = parse_local_date(date_str)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    store = request.app.state.store
    catalog = getattr(request.app.state, "catalog", None)
    if catalog is not None:
        details = catalog.fixtures(now)
    else:
        details = list(request.app.state.fixtures.values())

    clean_q = q.strip().lower() if q and q.strip() else None

    matches_out: list[AdminMatchOut] = []
    for detail in details:
        base_match = detail.match
        if clean_q:
            haystack = [
                base_match.home_team.name_ar or "",
                base_match.home_team.name_en or "",
                base_match.away_team.name_ar or "",
                base_match.away_team.name_en or "",
                base_match.league.name_ar or "",
                base_match.league.name_en or "",
            ]
            if not any(clean_q in text.lower() for text in haystack):
                continue

        resolved = resolve_match(detail, store)

        if target_date is not None:
            if resolved.kickoff_time.astimezone(zone).date() != target_date:
                continue

        card = build_match_card(resolved, now, zone)
        admin_streams = store.list_streams(base_match.id)
        admin_server_ids = [s.get("id") for s in admin_streams if s.get("id")]
        override = store.get_override(base_match.id)

        matches_out.append(
            AdminMatchOut(
                match=card,
                servers=[stream_out(server) for server in resolved.stream_servers],
                admin_server_ids=admin_server_ids,
                override=override,
            )
        )

    matches_out.sort(key=lambda item: item.match.kickoff_time_utc)
    return AdminMatchesOut(
        date=target_date.isoformat() if target_date else None,
        timezone=timezone_name,
        timezone_label_ar=timezone_label,
        matches=matches_out,
    )


logger = logging.getLogger(__name__)


def resolve_direct_embed_url(url: str, timeout: float = 3.0) -> str:
    """If the URL is a blog/wrapper page with an inner embed player, resolve directly to it."""
    clean = url.strip()
    low = clean.lower()
    if not any(k in low for k in ("blogspot.com", "wordpress.com", "/post/", "/article/")):
        return clean

    try:
        req = urllib.request.Request(
            clean,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_html = resp.read().decode("utf-8", "ignore")

        iframes = re.findall(r'<iframe[^>]*?src=["\']([^"\']+)["\'][^>]*?>', raw_html, re.I)
        for src in iframes:
            s = src.strip()
            if s.startswith("//"):
                s = f"https:{s}"
            low_s = s.lower()
            if any(k in low_s for k in ("albaplayer", "player", "embed", "live", "stream", "video")):
                return s
        if iframes:
            s = iframes[0].strip()
            return f"https:{s}" if s.startswith("//") else s
    except Exception as exc:
        logger.debug("Failed to resolve direct embed from %s: %s", clean, exc)
    return clean


@router.post(
    "/matches/{match_id}/streams",
    response_model=StreamMutationOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def upsert_stream(
    request: Request,
    match_id: str,
    body: StreamServerIn,
) -> StreamMutationOut:
    _get_fixture(request, match_id)
    payload = body.model_dump(exclude_none=True)
    payload["url"] = payload["url"].strip()
    request.app.state.store.upsert_stream(match_id, payload)
    global_cache.invalidate_tag("matches")
    return _mutation_payload(request, match_id)


@router.delete(
    "/matches/{match_id}/streams/{server_id}",
    response_model=StreamMutationOut,
    dependencies=[Depends(require_admin)],
)
def delete_stream(request: Request, match_id: str, server_id: str) -> StreamMutationOut:
    _get_fixture(request, match_id)
    deleted = request.app.state.store.delete_stream(match_id, server_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Stream server not found")
    global_cache.invalidate_tag("matches")
    return _mutation_payload(request, match_id)


@router.post(
    "/matches/{match_id}/override",
    response_model=MatchCardOut,
    dependencies=[Depends(require_admin)],
)
def set_override(
    request: Request,
    match_id: str,
    body: AdminOverrideIn,
) -> MatchCardOut:
    detail = _get_fixture(request, match_id)
    payload = body.model_dump(exclude_none=True, mode="json")
    request.app.state.store.set_override(match_id, payload)
    global_cache.invalidate_tag("matches")
    return _card(request, detail)


@router.delete(
    "/matches/{match_id}/override",
    response_model=MatchCardOut,
    dependencies=[Depends(require_admin)],
)
def clear_override(request: Request, match_id: str) -> MatchCardOut:
    detail = _get_fixture(request, match_id)
    request.app.state.store.delete_override(match_id)
    global_cache.invalidate_tag("matches")
    return _card(request, detail)


def _card(request: Request, detail) -> MatchCardOut:
    now: datetime = request.app.state.clock()
    zone, _ = resolve_timezone(request.app.state.timezone_name)
    match = resolve_match(detail, request.app.state.store)
    return build_match_card(match, now, zone)


# ---------------------------------------------------------------------------
# Admin Ads CMS endpoints
# ---------------------------------------------------------------------------

@router.get("/ads", response_model=AdsListOut, dependencies=[Depends(require_admin)])
def list_admin_ads(
    request: Request,
    position: Optional[str] = Query(default=None),
) -> AdsListOut:
    store = request.app.state.store
    ads_data = store.list_ads(position=position, active_only=False)
    return AdsListOut(ads=[AdOut(**ad) for ad in ads_data])


@router.post(
    "/ads",
    response_model=AdOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_admin_ad(
    request: Request,
    payload: AdIn,
) -> AdOut:
    store = request.app.state.store
    ad_dict = payload.model_dump()
    created = store.upsert_ad(ad_dict)
    global_cache.invalidate_tag("ads")
    return AdOut(**created)


@router.put("/ads/{ad_id}", response_model=AdOut, dependencies=[Depends(require_admin)])
def update_admin_ad(
    request: Request,
    ad_id: str,
    payload: AdUpdateIn,
) -> AdOut:
    store = request.app.state.store
    existing = store.get_ad(ad_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Ad not found")

    updates = payload.model_dump(exclude_unset=True)
    existing.update(updates)
    updated = store.upsert_ad(existing)
    global_cache.invalidate_tag("ads")
    return AdOut(**updated)


@router.patch("/ads/{ad_id}/toggle", dependencies=[Depends(require_admin)])
def toggle_admin_ad(
    request: Request,
    ad_id: str,
) -> dict[str, Any]:
    store = request.app.state.store
    new_state = store.toggle_ad_active(ad_id)
    if new_state is None:
        raise HTTPException(status_code=404, detail="Ad not found")
    global_cache.invalidate_tag("ads")
    return {"id": ad_id, "is_active": new_state}


@router.delete("/ads/{ad_id}", dependencies=[Depends(require_admin)])
def delete_admin_ad(
    request: Request,
    ad_id: str,
) -> dict[str, Any]:
    store = request.app.state.store
    deleted = store.delete_ad(ad_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Ad not found")
    global_cache.invalidate_tag("ads")
    return {"deleted": True, "id": ad_id}


# ---------------------------------------------------------------------------
# Admin Analytics & Statistics endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/analytics/stats",
    response_model=AnalyticsStatsOut,
    dependencies=[Depends(require_admin)],
)
def get_analytics_stats(
    request: Request,
    period: str = Query(default="week"),
) -> AnalyticsStatsOut:
    store = request.app.state.store
    clean_period = period.lower()
    if clean_period not in {"day", "week", "month", "year"}:
        clean_period = "week"

    summary = store.get_analytics_summary()
    chart_data = store.get_analytics_timeseries(clean_period)
    device_stats = store.get_device_breakdown(clean_period)
    top_pages = store.get_top_pages(clean_period, limit=8)

    return AnalyticsStatsOut(
        period=clean_period,
        summary=summary,
        chart_data=chart_data,
        device_stats=device_stats,
        top_pages=top_pages,
    )


# ---------------------------------------------------------------------------
# Admin Blogger SEO Article Generator endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/matches/{match_id}/article",
    dependencies=[Depends(require_admin)],
)
def get_match_article(
    request: Request,
    match_id: str,
    base_url: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    from live_score.domain.article_generator import generate_blogger_article
    from live_score.domain.models import MatchStatus

    fixture = _get_fixture(request, match_id)
    resolved = resolve_match(fixture, request.app.state.store)

    tunnel_url = base_url
    if not tunnel_url:
        tunnel_file = Path("data/tunnel_url.txt")
        if tunnel_file.exists():
            try:
                tunnel_url = tunnel_file.read_text(encoding="utf-8").strip()
            except Exception:
                pass

    stage = "post_match" if resolved.status == MatchStatus.FINISHED else "pre_match"
    match_dict = {
        "id": resolved.id,
        "home_team": resolved.home_team.name_ar or resolved.home_team.name_en,
        "away_team": resolved.away_team.name_ar or resolved.away_team.name_en,
        "competition": (resolved.league.name_ar or resolved.league.name_en) if resolved.league else "دوري كرة القدم",
        "kickoff_time": resolved.kickoff_time.isoformat() if resolved.kickoff_time else "",
        "status": resolved.status.value if resolved.status else "SCHEDULED",
        "home_score": resolved.home_score,
        "away_score": resolved.away_score,
        "venue": getattr(resolved, "stadium", None) or getattr(resolved, "venue", None) or "ملعب المباراة",
        "referee": getattr(resolved, "referee", None) or "طاقم التحكيم الرسمي",
        "channel": resolved.channel or "beIN Sports HD",
        "commentator": resolved.commentator or "يحدد لاحقاً",
        "events": [e.model_dump() for e in getattr(fixture, "events", [])],
        "home_lineup": [p.model_dump() for p in getattr(fixture, "home_lineup", [])],
        "away_lineup": [p.model_dump() for p in getattr(fixture, "away_lineup", [])],
        "home_formation": getattr(fixture, "home_formation", None),
        "away_formation": getattr(fixture, "away_formation", None),
        "stats": getattr(fixture, "stats", None),
        "standings": getattr(fixture, "standings", []),
    }
    return generate_blogger_article(match_dict, platform_base_url=tunnel_url or "", stage=stage)

