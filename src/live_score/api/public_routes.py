"""Public (read-only) match schedule and hybrid match-center endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse

from live_score.api.cache import global_cache
from live_score.api.presenters import (
    build_match_card,
    build_match_detail,
    parse_local_date,
    resolve_match,
    resolve_timezone,
)
from live_score.api.schemas import AdOut, AdsListOut, MatchDetailOut, TodayMatchesOut, TrackVisitIn

router = APIRouter(prefix="/api/v1", tags=["public"])


@router.get("/matches/today")
def matches_today(
    request: Request,
    response: Response,
    date_str: Optional[str] = Query(default=None, alias="date"),
    tz: Optional[str] = Query(default=None),
):
    now: datetime = request.app.state.clock()
    timezone_name = tz or request.app.state.timezone_name
    try:
        zone, timezone_label = resolve_timezone(timezone_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if date_str is None:
        target_date = now.astimezone(zone).date()
    else:
        try:
            target_date = parse_local_date(date_str)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    cache_key = f"today:{target_date.isoformat()}:{timezone_name}"
    cached = global_cache.get(cache_key)
    if cached:
        etag = cached["etag"]
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "public, max-age=5"})
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = "public, max-age=5"
        return cached["data"]

    store = request.app.state.store
    catalog = getattr(request.app.state, "catalog", None)
    details = (
        catalog.fixtures(now)
        if catalog is not None
        else list(request.app.state.fixtures.values())
    )
    cards = []
    for detail in details:
        match = resolve_match(detail, store, now=now)
        if match.kickoff_time.astimezone(zone).date() != target_date:
            continue
        cards.append(build_match_card(match, now, zone))

    cards.sort(key=lambda card: card.kickoff_time_utc)
    result = TodayMatchesOut(
        date=target_date.isoformat(),
        timezone=timezone_name,
        timezone_label_ar=timezone_label,
        matches=cards,
    ).model_dump(mode="json")

    etag = global_cache.set(cache_key, result, tag="matches", ttl=5.0)
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=5"
    return result


@router.get("/matches/{match_id}")
def match_detail(
    request: Request,
    response: Response,
    match_id: str,
    tz: Optional[str] = Query(default=None),
):
    now: datetime = request.app.state.clock()
    timezone_name = tz or request.app.state.timezone_name
    try:
        zone, _ = resolve_timezone(timezone_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    cache_key = f"detail:{match_id}:{timezone_name}"
    cached = global_cache.get(cache_key)
    if cached:
        etag = cached["etag"]
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "public, max-age=5"})
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = "public, max-age=5"
        return cached["data"]

    catalog = getattr(request.app.state, "catalog", None)
    if catalog is not None:
        detail = catalog.get_detail(match_id, now)
    else:
        detail = request.app.state.fixtures.get(match_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Match not found")

    result = build_match_detail(detail, request.app.state.store, now, zone).model_dump(mode="json")
    etag = global_cache.set(cache_key, result, tag="matches", ttl=5.0)
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=5"
    return result


@router.get("/ads")
def list_public_ads(
    request: Request,
    response: Response,
    position: Optional[str] = Query(default=None),
    device: Optional[str] = Query(default=None),
):
    cache_key = f"ads:{position or 'all'}:{device or 'all'}"
    cached = global_cache.get(cache_key)
    if cached:
        etag = cached["etag"]
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "public, max-age=15"})
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = "public, max-age=15"
        return cached["data"]

    store = request.app.state.store
    ads_data = store.list_ads(position=position, active_only=True, device=device)
    result = AdsListOut(ads=[AdOut(**ad) for ad in ads_data]).model_dump(mode="json")
    etag = global_cache.set(cache_key, result, tag="ads", ttl=15.0)
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=15"
    return result


@router.post("/analytics/track")
def track_visit(
    request: Request,
    payload: TrackVisitIn,
) -> dict[str, bool]:
    store = request.app.state.store
    visitor_id = payload.visitor_id
    if not visitor_id:
        import hashlib
        client_host = request.client.host if request.client else "unknown"
        ua = request.headers.get("user-agent", "")
        visitor_id = hashlib.sha256(f"{client_host}:{ua}".encode("utf-8")).hexdigest()[:16]

    store.record_visit(
        visitor_id=visitor_id,
        path=payload.path,
        device=payload.device,
        referrer=payload.referrer or "",
    )
    return {"recorded": True}


import re
import ssl
import urllib.request


class _NoGoogleRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if "google.com" in newurl:
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@router.get("/stream/player/{slug}", response_class=HTMLResponse)
def stream_player_proxy(
    slug: str,
    serv: Optional[int] = Query(default=None),
):
    """
    Unblocked stream proxy for AlbaPlayer embeds:
    Fetches the upstream player with valid referer, injects base URL, strips devtools blocks,
    and strips ads/popunders while preventing any redirection to google.com.
    """
    import re
    import ssl
    import urllib.request

    fallback_html = (
        "<!DOCTYPE html><html><body style='background:#050811;color:#94a3b8;display:flex;"
        "align-items:center;justify-content:center;height:100vh;font-family:sans-serif;text-align:center;margin:0;'>"
        "<div><div style='font-size:36px;'>📺</div>"
        "<p style='font-weight:bold;margin:10px 0;color:#f8fafc;font-size:16px;'>السيرفر الاحتياطي قيد التحديث</p>"
        "<p style='font-size:13px;color:#94a3b8;'>يرجى التبديل إلى السيرفر الرئيسي فائق السرعة للمشاهدة فوراً بدون تقطيع</p>"
        "</div></body></html>"
    )

    if serv is not None and serv > 0:
        upstream_url = f"https://24.shootinggames1.com/albaplayer/{slug}/?serv={serv}"
    else:
        upstream_url = f"https://24.shootinggames1.com/albaplayer/{slug}/"
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        opener = urllib.request.build_opener(_NoGoogleRedirectHandler)
        req = urllib.request.Request(
            upstream_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": "https://24.pinkshooters.com/",
            },
        )
        with opener.open(req, timeout=6) as resp:
            final_url = resp.geturl()
            if "google.com" in final_url:
                return HTMLResponse(content=fallback_html, status_code=200)

            html = resp.read().decode("utf-8", errors="ignore")
            if not html or "<title>Google</title>" in html or "player" not in html.lower():
                return HTMLResponse(content=fallback_html, status_code=200)

            # 1. Inject base tag so all relative assets (images, fonts, scripts) load from upstream
            if "<head>" in html:
                html = html.replace("<head>", '<head><base href="https://24.shootinggames1.com/" />', 1)

            # 2. Strip popunder ads (aclib)
            html = re.sub(r"<script[^>]*acscdn[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r"<script[^>]*>(?:(?!</script>).)*?aclib\.runPop.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)

            # 3. Strip external ad network scripts
            html = re.sub(r"<script[^>]*ima3[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r"<script[^>]*videojs-ima[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)

            # 4. Strip ConsoleBan and devtools redirect scripts
            html = re.sub(r"<script[^>]*>(?:(?!</script>).)*?AplrDevprotocol.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r"<script[^>]*>(?:(?!</script>).)*?ConsoleBan.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r"<script[^>]*console-ban.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r"https://www\.google\.com/", "#", html)

            # 5. Inject clean responsive styling to hide AlbaPlayer outer clutter
            style = (
                "<style>"
                "html, body { margin:0 !important; padding:0 !important; width:100% !important; height:100% !important; overflow:hidden !important; background:#000 !important; }"
                ".aplr-player-wrapper { height: 100% !important; margin: 0 !important; }"
                ".video-con, #player, .player-poster, [data-player] { width:100% !important; height:100% !important; }"
                ".aplr-menu, .aplr-exbtns, #aplr-embed { display: none !important; }"
                "</style>"
            )
            if "</head>" in html:
                html = html.replace("</head>", f"{style}</head>", 1)

            return HTMLResponse(
                content=html,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Content-Security-Policy": "frame-ancestors *;",
                },
            )
    except Exception:
        return HTMLResponse(content=fallback_html, status_code=200)

