# Task 2 Review Package

## File: src/live_score/adapters/__init__.py
`python
"""
Upstream Ingestion Adapters:
- LiveScoreFootballClient: Ingestion client for rezarahiminia/livescoreFootball REST API.
- PortalScraperAdapter: HTML scraper stub for live stream embeds, server buttons, and HLS.
"""

from live_score.adapters.livescore_client import LiveScoreFootballClient
from live_score.adapters.scraper_adapter import PortalScraperAdapter

__all__ = [
    "LiveScoreFootballClient",
    "PortalScraperAdapter",
]

``n
## File: src/live_score/adapters/livescore_client.py
`python
"""
LiveScoreFootball REST API Ingestion Client.

Adapts the open-source rezarahiminia/livescoreFootball schema to internal Match and MatchDetail domain models.
Normalizes team names using TeamAliasMatcher to attach Arabic display names when known.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Optional
import uuid

import requests

from live_score.domain.models import (
    League,
    LineupPlayer,
    Match,
    MatchDetail,
    MatchEvent,
    MatchStatus,
    Team,
)
from live_score.domain.resolver import TeamAliasMatcher

logger = logging.getLogger(__name__)


class LiveScoreFootballClient:
    """Client for fetching and normalizing football scores and match data from rezarahiminia/livescoreFootball."""

    _COMPETITION_AR_NAMES: dict[str, str] = {
        "Premier League": "Ø§Ù„Ø¯ÙˆØ±ÙŠ Ø§Ù„Ø¥Ù†Ø¬Ù„ÙŠØ²ÙŠ Ø§Ù„Ù…Ù…ØªØ§Ø²",
        "La Liga": "Ø§Ù„Ø¯ÙˆØ±ÙŠ Ø§Ù„Ø¥Ø³Ø¨Ø§Ù†ÙŠ",
        "LaLiga": "Ø§Ù„Ø¯ÙˆØ±ÙŠ Ø§Ù„Ø¥Ø³Ø¨Ø§Ù†ÙŠ",
        "Serie A": "Ø§Ù„Ø¯ÙˆØ±ÙŠ Ø§Ù„Ø¥ÙŠØ·Ø§Ù„ÙŠ",
        "Bundesliga": "Ø§Ù„Ø¯ÙˆØ±ÙŠ Ø§Ù„Ø£Ù„Ù…Ø§Ù†ÙŠ",
        "Ligue 1": "Ø§Ù„Ø¯ÙˆØ±ÙŠ Ø§Ù„ÙØ±Ù†Ø³ÙŠ",
        "UEFA Champions League": "Ø¯ÙˆØ±ÙŠ Ø£Ø¨Ø·Ø§Ù„ Ø£ÙˆØ±ÙˆØ¨Ø§",
        "Champions League": "Ø¯ÙˆØ±ÙŠ Ø£Ø¨Ø·Ø§Ù„ Ø£ÙˆØ±ÙˆØ¨Ø§",
        "UEFA Europa League": "Ø§Ù„Ø¯ÙˆØ±ÙŠ Ø§Ù„Ø£ÙˆØ±ÙˆØ¨ÙŠ",
        "Europa League": "Ø§Ù„Ø¯ÙˆØ±ÙŠ Ø§Ù„Ø£ÙˆØ±ÙˆØ¨ÙŠ",
        "UEFA Europa Conference League": "Ø¯ÙˆØ±ÙŠ Ø§Ù„Ù…Ø¤ØªÙ…Ø± Ø§Ù„Ø£ÙˆØ±ÙˆØ¨ÙŠ",
        "FA Cup": "ÙƒØ£Ø³ Ø§Ù„Ø§ØªØ­Ø§Ø¯ Ø§Ù„Ø¥Ù†Ø¬Ù„ÙŠØ²ÙŠ",
        "EFL Cup": "ÙƒØ£Ø³ Ø§Ù„Ø±Ø§Ø¨Ø·Ø© Ø§Ù„Ø¥Ù†Ø¬Ù„ÙŠØ²ÙŠØ©",
        "Copa del Rey": "ÙƒØ£Ø³ Ù…Ù„Ùƒ Ø¥Ø³Ø¨Ø§Ù†ÙŠØ§",
        "Supercopa de EspaÃ±a": "ÙƒØ£Ø³ Ø§Ù„Ø³ÙˆØ¨Ø± Ø§Ù„Ø¥Ø³Ø¨Ø§Ù†ÙŠ",
        "Saudi Pro League": "Ø¯ÙˆØ±ÙŠ Ø±ÙˆØ´Ù† Ø§Ù„Ø³Ø¹ÙˆØ¯ÙŠ",
        "Egyptian Premier League": "Ø§Ù„Ø¯ÙˆØ±ÙŠ Ø§Ù„Ù…ØµØ±ÙŠ Ø§Ù„Ù…Ù…ØªØ§Ø²",
        "CAF Champions League": "Ø¯ÙˆØ±ÙŠ Ø£Ø¨Ø·Ø§Ù„ Ø¥ÙØ±ÙŠÙ‚ÙŠØ§",
        "AFC Champions League": "Ø¯ÙˆØ±ÙŠ Ø£Ø¨Ø·Ø§Ù„ Ø¢Ø³ÙŠØ§",
        "FIFA World Cup": "ÙƒØ£Ø³ Ø§Ù„Ø¹Ø§Ù„Ù…",
    }

    _STATUS_MAPPING: dict[str, MatchStatus] = {
        "LIVE": MatchStatus.IN_PLAY,
        "IN_PLAY": MatchStatus.IN_PLAY,
        "IN PLAY": MatchStatus.IN_PLAY,
        "PLAYING": MatchStatus.IN_PLAY,
        "1H": MatchStatus.IN_PLAY,
        "2H": MatchStatus.IN_PLAY,
        "FIRST_HALF": MatchStatus.IN_PLAY,
        "SECOND_HALF": MatchStatus.IN_PLAY,
        "HT": MatchStatus.HALFTIME,
        "HALFTIME": MatchStatus.HALFTIME,
        "HALF_TIME": MatchStatus.HALFTIME,
        "ET": MatchStatus.EXTRA_TIME,
        "EXTRA_TIME": MatchStatus.EXTRA_TIME,
        "PEN": MatchStatus.PENALTIES,
        "PENALTIES": MatchStatus.PENALTIES,
        "PENALTY": MatchStatus.PENALTIES,
        "FT": MatchStatus.FINISHED,
        "FINISHED": MatchStatus.FINISHED,
        "ENDED": MatchStatus.FINISHED,
        "AET": MatchStatus.FINISHED,
        "POSTPONED": MatchStatus.POSTPONED,
        "CANCELLED": MatchStatus.POSTPONED,
        "CANC": MatchStatus.POSTPONED,
        "SUSP": MatchStatus.POSTPONED,
        "ABANDONED": MatchStatus.POSTPONED,
        "SCHEDULED": MatchStatus.SCHEDULED,
        "NS": MatchStatus.SCHEDULED,
        "TIMED": MatchStatus.SCHEDULED,
        "NOT_STARTED": MatchStatus.SCHEDULED,
        "UPCOMING": MatchStatus.SCHEDULED,
    }

    def __init__(
        self,
        base_url: str = "http://localhost:3050",
        session: Optional[Any] = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout

    def normalize_status(self, raw_status: Optional[str]) -> MatchStatus:
        """Normalizes upstream status string to standard MatchStatus enum."""
        if not raw_status or not isinstance(raw_status, str):
            return MatchStatus.SCHEDULED

        clean_status = raw_status.strip().upper()
        return self._STATUS_MAPPING.get(clean_status, MatchStatus.SCHEDULED)

    def _resolve_team(self, team_data: Any) -> Team:
        """Resolves team data into Team model with Arabic and English names."""
        if isinstance(team_data, dict):
            raw_name = team_data.get("name") or team_data.get("name_en") or team_data.get("name_ar") or "Unknown Team"
            team_id = team_data.get("id") or team_data.get("_id")
            logo = team_data.get("logo") or team_data.get("logo_url")
            name_ar_hint = team_data.get("name_ar")
            name_en_hint = team_data.get("name_en")
        else:
            raw_name = str(team_data) if team_data is not None else "Unknown Team"
            team_id = None
            logo = None
            name_ar_hint = None
            name_en_hint = None

        if name_ar_hint and name_en_hint:
            name_ar = str(name_ar_hint)
            name_en = str(name_en_hint)
        else:
            # Check if raw_name contains Arabic characters
            is_arabic = any("\u0600" <= ch <= "\u06FF" for ch in raw_name)
            if is_arabic:
                en_matched = TeamAliasMatcher.match_team(raw_name)
                if en_matched:
                    name_en = en_matched
                    canonical_ar = TeamAliasMatcher.get_arabic_name(en_matched)
                    name_ar = canonical_ar or raw_name
                else:
                    name_en = raw_name
                    name_ar = raw_name
            else:
                name_en = raw_name
                canonical_ar = TeamAliasMatcher.get_arabic_name(raw_name)
                name_ar = canonical_ar or raw_name

        return Team(
            id=str(team_id) if team_id else None,
            name_ar=name_ar,
            name_en=name_en,
            logo_url=logo,
        )

    def _resolve_league(self, comp_data: Any, round_data: Optional[str] = None) -> League:
        """Resolves competition data into League model with Arabic name."""
        if isinstance(comp_data, dict):
            name = comp_data.get("name") or comp_data.get("name_en") or comp_data.get("name_ar") or "Unknown Competition"
            comp_id = comp_data.get("id") or comp_data.get("_id")
            round_val = comp_data.get("round") or round_data
            logo = comp_data.get("logo") or comp_data.get("logo_url")
            name_ar = comp_data.get("name_ar") or self._COMPETITION_AR_NAMES.get(name, name)
        else:
            name = str(comp_data) if comp_data is not None else "Unknown Competition"
            comp_id = None
            round_val = round_data
            logo = None
            name_ar = self._COMPETITION_AR_NAMES.get(name, name)

        return League(
            id=str(comp_id) if comp_id else None,
            name_ar=name_ar,
            name_en=name,
            round=round_val,
            logo_url=logo,
        )

    def _parse_kickoff(self, val: Any) -> datetime:
        """Parses various kickoff time formats into timezone-aware UTC datetime."""
        if isinstance(val, datetime):
            if val.tzinfo is None:
                return val.replace(tzinfo=timezone.utc)
            return val

        if isinstance(val, (int, float)):
            try:
                return datetime.fromtimestamp(val, tz=timezone.utc)
            except Exception:
                return datetime.now(timezone.utc)

        if isinstance(val, str) and val.strip():
            clean = val.strip()
            # ISO 8601 parsing
            try:
                if clean.endswith("Z"):
                    clean = clean[:-1] + "+00:00"
                dt = datetime.fromisoformat(clean)
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass

            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(clean, fmt)
                    return dt.replace(tzinfo=timezone.utc)
                except Exception:
                    continue

        return datetime.now(timezone.utc)

    def _map_match_dict(self, item: dict[str, Any]) -> Optional[Match]:
        """Maps a raw JSON dictionary from upstream into an internal Match model."""
        if not isinstance(item, dict):
            return None

        try:
            match_id = str(item.get("id") or item.get("_id") or item.get("match_id") or uuid.uuid4())
            home_team = self._resolve_team(item.get("home_team") or item.get("home"))
            away_team = self._resolve_team(item.get("away_team") or item.get("away"))
            league = self._resolve_league(
                item.get("competition") or item.get("league"),
                round_data=item.get("round"),
            )
            status = self.normalize_status(
                item.get("status") or item.get("match_status") or item.get("state")
            )
            kickoff = self._parse_kickoff(
                item.get("kickoff_time") or item.get("kickoff") or item.get("date") or item.get("datetime")
            )

            # Scores extraction (direct or nested)
            home_score = item.get("home_score")
            away_score = item.get("away_score")
            scores = item.get("score") or item.get("scores")
            if isinstance(scores, dict):
                if home_score is None:
                    home_score = scores.get("home")
                if away_score is None:
                    away_score = scores.get("away")

            h_score_int = int(home_score) if home_score is not None else 0
            a_score_int = int(away_score) if away_score is not None else 0

            # Elapsed time
            raw_elapsed = item.get("elapsed") or item.get("elapsed_time")
            elapsed_int = int(raw_elapsed) if raw_elapsed is not None else None

            return Match(
                id=match_id,
                home_team=home_team,
                away_team=away_team,
                league=league,
                status=status,
                kickoff_time=kickoff,
                home_score=h_score_int,
                away_score=a_score_int,
                elapsed_time=elapsed_int,
                channel=item.get("channel"),
                commentator=item.get("commentator"),
                stadium=item.get("stadium"),
                referee=item.get("referee"),
            )
        except Exception as exc:
            logger.warning(f"Error mapping upstream match item: {exc}", exc_info=True)
            return None

    def fetch_today_matches(self) -> list[Match]:
        """
        Fetches today's matches from the upstream livescoreFootball service.
        Gracefully returns an empty list upon timeout, network error, or bad payload.
        """
        urls_to_try = [
            f"{self.base_url}/api/matches/today",
            f"{self.base_url}/matches",
        ]

        data = None
        for url in urls_to_try:
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    break
                elif response.status_code == 404:
                    continue
                else:
                    logger.warning(f"Upstream returned non-200 code: {response.status_code}")
                    return []
            except Exception as exc:
                logger.warning(f"Network error querying upstream {url}: {exc}")
                return []

        if data is None:
            return []

        # Extract items from data
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("matches") or data.get("data") or data.get("fixtures") or []
            if not isinstance(items, list):
                items = []
        else:
            return []

        matches: list[Match] = []
        for item in items:
            m = self._map_match_dict(item)
            if m is not None:
                matches.append(m)

        return matches

    def fetch_match_detail(self, match_id: str) -> Optional[MatchDetail]:
        """
        Fetches detailed match information including lineups, timeline events, and stats.
        Gracefully returns None on error or missing data.
        """
        if not match_id:
            return None

        urls_to_try = [
            f"{self.base_url}/api/matches/{match_id}",
            f"{self.base_url}/matches/{match_id}",
        ]

        data = None
        for url in urls_to_try:
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    break
                elif response.status_code == 404:
                    continue
                else:
                    return None
            except Exception as exc:
                logger.warning(f"Error fetching match detail for {match_id}: {exc}")
                return None

        if not isinstance(data, dict):
            return None

        # Unwrap if nested under data
        if "data" in data and isinstance(data["data"], dict) and ("home_team" in data["data"] or "match" in data["data"]):
            data = data["data"]

        match_data = data.get("match") if "match" in data and isinstance(data["match"], dict) else data
        match_obj = self._map_match_dict(match_data)
        if match_obj is None:
            return None

        # Parse Lineups
        home_lineup: list[LineupPlayer] = []
        away_lineup: list[LineupPlayer] = []

        lineups_raw = data.get("lineups") or match_data.get("lineups") or {}
        if isinstance(lineups_raw, dict):
            home_players = lineups_raw.get("home") or lineups_raw.get("home_team") or []
            away_players = lineups_raw.get("away") or lineups_raw.get("away_team") or []

            def _parse_players(players_list: list[Any]) -> list[LineupPlayer]:
                result = []
                for p in players_list:
                    if not isinstance(p, dict):
                        continue
                    try:
                        p_name = str(p.get("name") or "Player")
                        p_num = int(p.get("number", 0))
                        p_pos = str(p.get("position", "MF")).upper()
                        # Normalize positions
                        if "GOAL" in p_pos or p_pos == "G":
                            p_pos = "GK"
                        elif "DEF" in p_pos or p_pos == "D":
                            p_pos = "DF"
                        elif "MID" in p_pos or p_pos == "M":
                            p_pos = "MF"
                        elif "FOR" in p_pos or "ATT" in p_pos or p_pos in {"F", "A"}:
                            p_pos = "FW"
                        elif p_pos not in {"GK", "DF", "MF", "FW"}:
                            p_pos = "MF"

                        result.append(
                            LineupPlayer(
                                id=str(p.get("id")) if p.get("id") else None,
                                name=p_name,
                                number=p_num,
                                position=p_pos,
                                is_starter=bool(p.get("is_starter", True)),
                                grid_position=str(p.get("grid_position")) if p.get("grid_position") else None,
                            )
                        )
                    except Exception:
                        continue
                return result

            if isinstance(home_players, list):
                home_lineup = _parse_players(home_players)
            if isinstance(away_players, list):
                away_lineup = _parse_players(away_players)

        # Parse Events
        events: list[MatchEvent] = []
        events_raw = data.get("events") or match_data.get("events") or []
        if isinstance(events_raw, list):
            for ev in events_raw:
                if not isinstance(ev, dict):
                    continue
                try:
                    minute_val = int(ev.get("minute", 0))
                    raw_type = str(ev.get("type", "goal")).lower()
                    if "goal" in raw_type:
                        ev_type = "goal"
                    elif "yellow" in raw_type:
                        ev_type = "yellow_card"
                    elif "red" in raw_type:
                        ev_type = "red_card"
                    elif "sub" in raw_type:
                        ev_type = "substitution"
                    elif "var" in raw_type:
                        ev_type = "var"
                    else:
                        ev_type = raw_type

                    player_name = str(ev.get("player_name") or ev.get("player") or "")
                    team_id = str(ev.get("team_id")) if ev.get("team_id") else None
                    desc_ar = ev.get("description_ar") or ev.get("description")

                    events.append(
                        MatchEvent(
                            id=str(ev.get("id")) if ev.get("id") else None,
                            minute=minute_val,
                            type=ev_type,
                            player_name=player_name,
                            team_id=team_id,
                            description_ar=desc_ar,
                        )
                    )
                except Exception:
                    continue

        # Parse Stats
        stats = data.get("stats") or match_data.get("stats")
        if not isinstance(stats, dict):
            stats = None

        return MatchDetail(
            match=match_obj,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            events=events,
            stats=stats,
        )

``n
## File: src/live_score/adapters/scraper_adapter.py
`python
"""
Portal Live Stream Scraper Adapter.

Parses streaming server tabs, iframe embeds, and direct HLS (.m3u8) video links
from Arabic football streaming portals (e.g., KoraCity, Draximo, Yalla Shoot stubs).
Enforces zero video proxying and client-side iframe sandboxing.
"""

from __future__ import annotations

import html
import logging
import re
from typing import Any, Optional
from urllib.parse import quote, urljoin

import requests

from live_score.domain.models import StreamServer

logger = logging.getLogger(__name__)


class PortalScraperAdapter:
    """Scraper adapter for extracting client-facing live stream embed servers."""

    def __init__(
        self,
        base_url: str = "",
        session: Optional[Any] = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.session = session or requests.Session()
        self.timeout = timeout

    @staticmethod
    def _clean_text(raw_html: str) -> str:
        """Strips inner HTML tags and unescapes entities."""
        no_tags = re.sub(r"<[^>]+>", "", raw_html)
        return html.unescape(no_tags).strip()

    @staticmethod
    def _detect_quality(text: str, url: str, explicit_quality: Optional[str] = None) -> str:
        """
        Categorizes stream quality into standard identifiers:
        - youtube
        - multiquality
        - hd
        - sd
        """
        if explicit_quality:
            eq = explicit_quality.strip().lower()
            if eq in {"multi", "multiquality", "auto"}:
                return "multiquality"
            if eq in {"hd", "1080p", "720p", "high"}:
                return "hd"
            if eq in {"sd", "low", "mobile", "360p", "480p"}:
                return "sd"
            if "youtube" in eq:
                return "youtube"

        combined = f"{text} {url}".lower()

        # YouTube check
        if "youtube.com" in combined or "youtu.be" in combined or "ÙŠÙˆØªÙŠÙˆØ¨" in combined:
            return "youtube"

        # Multi-quality check
        if "Ù…ØªØ¹Ø¯Ø¯" in combined or "multi" in combined or "auto" in combined:
            return "multiquality"

        # HD check
        if "hd" in combined or "1080" in combined or "720" in combined or "Ø¹Ø§Ù„ÙŠØ©" in combined:
            return "hd"

        # SD / Mobile check
        if "sd" in combined or "Ø¶Ø¹ÙŠÙ" in combined or "Ù‡Ø§ØªÙ" in combined or "Ù‡ÙˆØ§ØªÙ" in combined or "mobile" in combined or "360" in combined or "480" in combined:
            return "sd"

        return "multiquality"

    def parse_stream_embeds(self, html_content: Optional[str]) -> list[StreamServer]:
        """
        Parses live streaming embeds from HTML content.
        Extracts server tabs, iframes, and direct HLS links while enforcing sandboxing and deduplication.
        """
        if not html_content or not isinstance(html_content, str):
            return []

        servers: list[StreamServer] = []
        seen_urls: set[str] = set()

        # 1. Parse server buttons, tabs, links with data-url / data-src / data-embed / data-stream / href
        # Match elements: <(button|a|li|div) ...>text</...>
        tab_pattern = re.compile(
            r"<(?P<tag>button|a|li|div)[^>]*?(?:"
            r"data-url=[\"'](?P<data_url>[^\"']+)[\"']|"
            r"data-src=[\"'](?P<data_src>[^\"']+)[\"']|"
            r"data-embed=[\"'](?P<data_embed>[^\"']+)[\"']|"
            r"data-stream=[\"'](?P<data_stream>[^\"']+)[\"']|"
            r"href=[\"'](?P<href>https?://[^\"']+)[\"']"
            r")[^>]*?>(?P<text>.*?)</(?P=tag)>",
            re.IGNORECASE | re.DOTALL,
        )

        for match in tab_pattern.finditer(html_content):
            matched_tag_full = match.group(0)
            url = (
                match.group("data_url")
                or match.group("data_src")
                or match.group("data_embed")
                or match.group("data_stream")
                or match.group("href")
            )
            if not url or url.startswith("#") or url.startswith("javascript:"):
                continue

            # Check explicit data-quality
            quality_match = re.search(r"data-quality=[\"']([^\"']+)[\"']", matched_tag_full, re.IGNORECASE)
            explicit_q = quality_match.group(1) if quality_match else None

            raw_text = match.group("text") or ""
            btn_text = self._clean_text(raw_text)

            clean_url = url.strip()
            if self.base_url and not clean_url.startswith(("http://", "https://", "//")):
                clean_url = urljoin(self.base_url, clean_url)
            elif clean_url.startswith("//"):
                clean_url = f"https:{clean_url}"

            if clean_url in seen_urls:
                continue

            seen_urls.add(clean_url)

            # Determine type and quality
            is_hls = ".m3u8" in clean_url.lower() or "application/x-mpegurl" in clean_url.lower()
            server_type = "m3u8" if is_hls else "iframe"
            quality = self._detect_quality(btn_text, clean_url, explicit_q)
            name = btn_text if btn_text else f"Ø³ÙŠØ±ÙØ± {len(servers) + 1}"
            sandbox = "allow-scripts allow-same-origin allow-presentation" if server_type == "iframe" else None

            servers.append(
                StreamServer(
                    id=f"srv_{len(servers) + 1}",
                    server_name=name,
                    url=clean_url,
                    type=server_type,
                    is_active=True,
                    quality=quality,
                    sandbox=sandbox,
                )
            )

        # 2. Parse direct <source ... src="...m3u8"> and <video ... src="...m3u8">
        hls_pattern = re.compile(
            r"<(?:source|video)[^>]*?src=[\"'](?P<url>[^\"']+\.m3u8[^\"']*)[\"']",
            re.IGNORECASE,
        )
        for match in hls_pattern.finditer(html_content):
            url = match.group("url").strip()
            if self.base_url and not url.startswith(("http://", "https://", "//")):
                url = urljoin(self.base_url, url)
            elif url.startswith("//"):
                url = f"https:{url}"

            if url in seen_urls:
                continue

            seen_urls.add(url)
            servers.append(
                StreamServer(
                    id=f"srv_{len(servers) + 1}",
                    server_name=f"Ø¨Ø« Ù…Ø¨Ø§Ø´Ø± HLS {len(servers) + 1}",
                    url=url,
                    type="m3u8",
                    is_active=True,
                    quality="multiquality",
                    sandbox=None,
                )
            )

        # 3. Parse standalone <iframe src="..."> embeds if not already captured
        iframe_pattern = re.compile(
            r"<iframe[^>]*?src=[\"'](?P<url>https?://[^\"']+|//[^\"']+)[\"'][^>]*?>",
            re.IGNORECASE,
        )
        for match in iframe_pattern.finditer(html_content):
            url = match.group("url").strip()
            if url.startswith("//"):
                url = f"https:{url}"

            if url in seen_urls:
                continue

            # Ignore social sharing or tracker iframes
            if any(ad in url.lower() for ad in ("facebook.com/plugins", "twitter.com/widgets", "googletagmanager")):
                continue

            seen_urls.add(url)
            quality = self._detect_quality("", url)
            servers.append(
                StreamServer(
                    id=f"srv_{len(servers) + 1}",
                    server_name=f"Ø³ÙŠØ±ÙØ± {len(servers) + 1}",
                    url=url,
                    type="iframe",
                    is_active=True,
                    quality=quality,
                    sandbox="allow-scripts allow-same-origin allow-presentation",
                )
            )

        return servers

    def fetch_stream_servers(self, home_team: str, away_team: str) -> list[StreamServer]:
        """
        Fetches live stream embed servers for a specific match fixture.
        Returns an empty list on network error, timeout, or missing page.
        """
        if not self.base_url:
            return []

        query = f"{quote(home_team.strip())}-vs-{quote(away_team.strip())}"
        target_url = f"{self.base_url}/match/{query}"

        try:
            response = self.session.get(target_url, timeout=self.timeout)
            if response.status_code != 200:
                logger.warning(f"Scraper returned status {response.status_code} for {target_url}")
                return []
            return self.parse_stream_embeds(response.text)
        except Exception as exc:
            logger.warning(f"Scraper network error fetching streams for {home_team} vs {away_team}: {exc}")
            return []

``n
## File: tests/live_score/test_adapters.py
`python
"""
Tests for Upstream Ingestion Adapters:
1. LiveScoreFootballClient: Ingestion from rezarahiminia/livescoreFootball REST API schema.
2. PortalScraperAdapter: Parsing live streaming embeds, server tabs, and HLS streams.
"""

from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any
from unittest.mock import MagicMock

# Ensure src directory is in sys.path
_src_path = str(Path(__file__).resolve().parents[2] / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

import pytest
import requests

from live_score.adapters import LiveScoreFootballClient, PortalScraperAdapter
from live_score.domain.models import (
    Match,
    MatchDetail,
    MatchStatus,
    StreamServer,
)


# ============================================================================
# LiveScoreFootballClient Fixtures & Tests
# ============================================================================

@pytest.fixture
def mock_today_matches_payload() -> list[dict[str, Any]]:
    return [
        {
            "id": "match_pl_101",
            "home_team": {
                "id": "team_che",
                "name": "Chelsea",
                "logo": "https://img.example/chelsea.png",
            },
            "away_team": {
                "id": "team_liv",
                "name": "Liverpool",
                "logo": "https://img.example/liverpool.png",
            },
            "competition": {
                "id": "pl",
                "name": "Premier League",
                "round": "Round 12",
                "logo": "https://img.example/pl.png",
            },
            "status": "LIVE",
            "elapsed": 68,
            "home_score": 2,
            "away_score": 1,
            "kickoff_time": "2026-11-20T19:00:00Z",
            "stadium": "Stamford Bridge",
            "referee": "Michael Oliver",
        },
        {
            "id": "match_laliga_102",
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "competition": "La Liga",
            "status": "SCHEDULED",
            "kickoff_time": "2026-11-20T21:00:00Z",
        },
    ]


@pytest.fixture
def mock_match_detail_payload() -> dict[str, Any]:
    return {
        "id": "match_pl_101",
        "home_team": {
            "id": "team_che",
            "name": "Chelsea",
            "logo": "https://img.example/chelsea.png",
        },
        "away_team": {
            "id": "team_liv",
            "name": "Liverpool",
            "logo": "https://img.example/liverpool.png",
        },
        "competition": {
            "id": "pl",
            "name": "Premier League",
            "round": "Round 12",
        },
        "status": "IN_PLAY",
        "elapsed": 75,
        "home_score": 2,
        "away_score": 1,
        "kickoff_time": "2026-11-20T19:00:00Z",
        "lineups": {
            "home": [
                {
                    "id": "p_che_20",
                    "name": "Cole Palmer",
                    "number": 20,
                    "position": "MF",
                    "is_starter": True,
                    "grid_position": "3:2",
                },
                {
                    "id": "p_che_1",
                    "name": "Robert Sanchez",
                    "number": 1,
                    "position": "GK",
                    "is_starter": True,
                    "grid_position": "1:1",
                },
            ],
            "away": [
                {
                    "id": "p_liv_11",
                    "name": "Mohamed Salah",
                    "number": 11,
                    "position": "FW",
                    "is_starter": True,
                    "grid_position": "4:3",
                }
            ],
        },
        "events": [
            {
                "id": "ev_1",
                "minute": 24,
                "type": "goal",
                "player_name": "Cole Palmer",
                "team_id": "team_che",
                "description_ar": "Ù‡Ø¯Ù Ù„ØµØ§Ù„Ø­ ØªØ´ÙŠÙ„Ø³ÙŠ Ø¨ÙˆØ§Ø³Ø·Ø© ÙƒÙˆÙ„ Ø¨Ø§Ù„Ù…Ø±",
            },
            {
                "id": "ev_2",
                "minute": 45,
                "type": "yellow_card",
                "player_name": "Alexis Mac Allister",
                "team_id": "team_liv",
            },
        ],
        "stats": {
            "possession": {"home": 56, "away": 44},
            "shots_on_target": {"home": 7, "away": 5},
        },
    }


def test_livescore_client_fetch_today_matches(mock_today_matches_payload):
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_today_matches_payload
    mock_session.get.return_value = mock_response

    client = LiveScoreFootballClient(base_url="http://mock-livescore-api", session=mock_session)
    matches = client.fetch_today_matches()

    assert len(matches) == 2
    match1 = matches[0]
    assert isinstance(match1, Match)
    assert match1.id == "match_pl_101"
    # Team names normalized to Arabic display names
    assert match1.home_team.name_ar == "ØªØ´ÙŠÙ„Ø³ÙŠ"
    assert match1.home_team.name_en == "Chelsea"
    assert match1.away_team.name_ar == "Ù„ÙŠÙØ±Ø¨ÙˆÙ„"
    assert match1.away_team.name_en == "Liverpool"
    assert match1.home_team.logo_url == "https://img.example/chelsea.png"
    # Status and score
    assert match1.status == MatchStatus.IN_PLAY
    assert match1.is_live is True
    assert match1.elapsed_time == 68
    assert match1.home_score == 2
    assert match1.away_score == 1
    assert match1.kickoff_time.tzinfo is not None

    match2 = matches[1]
    assert match2.id == "match_laliga_102"
    assert match2.home_team.name_ar == "Ø±ÙŠØ§Ù„ Ù…Ø¯Ø±ÙŠØ¯"
    assert match2.away_team.name_ar == "Ø¨Ø±Ø´Ù„ÙˆÙ†Ø©"
    assert match2.status == MatchStatus.SCHEDULED
    assert match2.is_live is False


def test_livescore_client_fetch_today_matches_enveloped_responses():
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "success",
        "data": [
            {
                "id": "match_envelope_1",
                "home_team": "Arsenal",
                "away_team": "Tottenham Hotspur",
                "competition": "Premier League",
                "status": "FT",
                "home_score": 3,
                "away_score": 1,
                "kickoff_time": "2026-11-20T16:00:00Z",
            }
        ]
    }
    mock_session.get.return_value = mock_response

    client = LiveScoreFootballClient(base_url="http://mock-api", session=mock_session)
    matches = client.fetch_today_matches()

    assert len(matches) == 1
    assert matches[0].home_team.name_ar == "Ø£Ø±Ø³Ù†Ø§Ù„"
    assert matches[0].away_team.name_ar == "ØªÙˆØªÙ†Ù‡Ø§Ù…"
    assert matches[0].status == MatchStatus.FINISHED


def test_livescore_client_fetch_match_detail(mock_match_detail_payload):
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_match_detail_payload
    mock_session.get.return_value = mock_response

    client = LiveScoreFootballClient(base_url="http://mock-api", session=mock_session)
    detail = client.fetch_match_detail("match_pl_101")

    assert detail is not None
    assert isinstance(detail, MatchDetail)
    assert detail.match.id == "match_pl_101"
    assert detail.match.home_team.name_ar == "ØªØ´ÙŠÙ„Ø³ÙŠ"

    # Lineups (English names rendered in Latin as per Option B)
    assert len(detail.home_lineup) == 2
    assert detail.home_lineup[0].name == "Cole Palmer"
    assert detail.home_lineup[0].number == 20
    assert detail.home_lineup[0].position == "MF"
    assert detail.home_lineup[0].is_starter is True
    assert detail.home_lineup[0].grid_position == "3:2"

    assert len(detail.away_lineup) == 1
    assert detail.away_lineup[0].name == "Mohamed Salah"

    # Timeline events
    assert len(detail.events) == 2
    assert detail.events[0].minute == 24
    assert detail.events[0].type == "goal"
    assert detail.events[0].player_name == "Cole Palmer"
    assert detail.events[0].description_ar == "Ù‡Ø¯Ù Ù„ØµØ§Ù„Ø­ ØªØ´ÙŠÙ„Ø³ÙŠ Ø¨ÙˆØ§Ø³Ø·Ø© ÙƒÙˆÙ„ Ø¨Ø§Ù„Ù…Ø±"

    # Stats
    assert detail.stats["possession"]["home"] == 56


def test_livescore_client_error_handling_timeout_and_bad_payload():
    mock_session = MagicMock()
    mock_session.get.side_effect = requests.exceptions.Timeout("Connection timed out")

    client = LiveScoreFootballClient(base_url="http://timeout-api", session=mock_session)
    # Must gracefully return empty list, not raise
    matches = client.fetch_today_matches()
    assert matches == []

    # Match detail timeout should gracefully return None
    detail = client.fetch_match_detail("match_timeout")
    assert detail is None

    # Malformed JSON or 500 error
    bad_response = MagicMock()
    bad_response.status_code = 500
    bad_response.json.side_effect = ValueError("Invalid JSON response")
    mock_session.get.side_effect = None
    mock_session.get.return_value = bad_response

    assert client.fetch_today_matches() == []
    assert client.fetch_match_detail("match_bad") is None


def test_livescore_client_status_mapping_variations():
    client = LiveScoreFootballClient(base_url="http://mock-api", session=MagicMock())

    status_cases = [
        ("LIVE", MatchStatus.IN_PLAY),
        ("IN_PLAY", MatchStatus.IN_PLAY),
        ("1H", MatchStatus.IN_PLAY),
        ("2H", MatchStatus.IN_PLAY),
        ("HT", MatchStatus.HALFTIME),
        ("HALFTIME", MatchStatus.HALFTIME),
        ("ET", MatchStatus.EXTRA_TIME),
        ("EXTRA_TIME", MatchStatus.EXTRA_TIME),
        ("PEN", MatchStatus.PENALTIES),
        ("PENALTIES", MatchStatus.PENALTIES),
        ("FT", MatchStatus.FINISHED),
        ("FINISHED", MatchStatus.FINISHED),
        ("POSTPONED", MatchStatus.POSTPONED),
        ("CANCELLED", MatchStatus.POSTPONED),
        ("SCHEDULED", MatchStatus.SCHEDULED),
        ("NS", MatchStatus.SCHEDULED),
        ("UNKNOWN_STATUS", MatchStatus.SCHEDULED),
    ]

    for raw, expected in status_cases:
        assert client.normalize_status(raw) == expected


def test_livescore_client_arabic_alias_upstream_matching():
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "id": "match_mena_1",
            "home_team": "Ø§Ù„Ø¨Ù„ÙˆØ²",  # Arabic nickname for Chelsea
            "away_team": "Ø§Ù„Ø±ÙŠØ¯Ø²",   # Arabic nickname for Liverpool
            "competition": "UEFA Champions League",
            "status": "LIVE",
            "kickoff_time": "2026-11-20T20:00:00Z",
        }
    ]
    mock_session.get.return_value = mock_response

    client = LiveScoreFootballClient(base_url="http://mock-api", session=mock_session)
    matches = client.fetch_today_matches()

    assert len(matches) == 1
    assert matches[0].home_team.name_en == "Chelsea"
    assert matches[0].home_team.name_ar == "ØªØ´ÙŠÙ„Ø³ÙŠ"
    assert matches[0].away_team.name_en == "Liverpool"
    assert matches[0].away_team.name_ar == "Ù„ÙŠÙØ±Ø¨ÙˆÙ„"


# ============================================================================
# PortalScraperAdapter Fixtures & Tests
# ============================================================================

@pytest.fixture
def sample_portal_html() -> str:
    return """
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head><title>Ù…Ø´Ø§Ù‡Ø¯Ø© Ù…Ø¨Ø§Ø±Ø§Ø© ØªØ´ÙŠÙ„Ø³ÙŠ ÙˆÙ„ÙŠÙØ±Ø¨ÙˆÙ„ Ø¨Ø« Ù…Ø¨Ø§Ø´Ø±</title></head>
    <body>
        <div class="match-stream-box">
            <div class="server-tabs">
                <button class="server-btn active" data-url="https://live.koracity.tv/embed/ch1" data-quality="multi">Ø³ÙŠØ±ÙØ± 1 - Ù…ØªØ¹Ø¯Ø¯ Ø§Ù„Ø¬ÙˆØ¯Ø§Øª</button>
                <button class="server-btn" data-url="https://hd.streamhub.to/live/ch1" data-quality="hd">Ø³ÙŠØ±ÙØ± 2 - HD</button>
                <button class="server-btn" data-url="https://sd.streamhub.to/live/mobile" data-quality="sd">Ø³ÙŠØ±ÙØ± 3 - Ø¶Ø¹ÙŠÙ Ù„Ù„Ù‡ÙˆØ§ØªÙ</button>
                <a class="server-btn" href="https://www.youtube.com/embed/dQw4w9WgXcQ">Ø³ÙŠØ±ÙØ± 4 - ÙŠÙˆØªÙŠÙˆØ¨</a>
            </div>
            <div class="player-container">
                <iframe src="https://live.koracity.tv/embed/ch1" width="100%" height="450" frameborder="0" allowfullscreen></iframe>
            </div>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_hls_html() -> str:
    return """
    <div class="video-player">
        <video id="hls-player" controls>
            <source src="https://live.streaming-cdn.com/hls/match_stream.m3u8" type="application/x-mpegURL">
        </video>
    </div>
    """


def test_portal_scraper_parse_stream_embeds(sample_portal_html):
    scraper = PortalScraperAdapter()
    servers = scraper.parse_stream_embeds(sample_portal_html)

    # 4 distinct servers (the active iframe matches Server 1 URL, so deduplication keeps 4 unique)
    assert len(servers) == 4

    server_map = {s.server_name: s for s in servers}

    # Server 1 - Multi quality
    s1 = server_map["Ø³ÙŠØ±ÙØ± 1 - Ù…ØªØ¹Ø¯Ø¯ Ø§Ù„Ø¬ÙˆØ¯Ø§Øª"]
    assert s1.url == "https://live.koracity.tv/embed/ch1"
    assert s1.type == "iframe"
    assert s1.quality == "multiquality"
    assert s1.is_active is True
    # Sandboxed for iframe security
    assert "allow-scripts" in s1.sandbox
    assert "allow-same-origin" in s1.sandbox

    # Server 2 - HD
    s2 = server_map["Ø³ÙŠØ±ÙØ± 2 - HD"]
    assert s2.url == "https://hd.streamhub.to/live/ch1"
    assert s2.type == "iframe"
    assert s2.quality == "hd"

    # Server 3 - SD
    s3 = server_map["Ø³ÙŠØ±ÙØ± 3 - Ø¶Ø¹ÙŠÙ Ù„Ù„Ù‡ÙˆØ§ØªÙ"]
    assert s3.url == "https://sd.streamhub.to/live/mobile"
    assert s3.type == "iframe"
    assert s3.quality == "sd"

    # Server 4 - YouTube
    s4 = server_map["Ø³ÙŠØ±ÙØ± 4 - ÙŠÙˆØªÙŠÙˆØ¨"]
    assert s4.url == "https://www.youtube.com/embed/dQw4w9WgXcQ"
    assert s4.type == "iframe"
    assert s4.quality == "youtube"


def test_portal_scraper_parse_direct_hls_stream(sample_hls_html):
    scraper = PortalScraperAdapter()
    servers = scraper.parse_stream_embeds(sample_hls_html)

    assert len(servers) == 1
    srv = servers[0]
    assert srv.url == "https://live.streaming-cdn.com/hls/match_stream.m3u8"
    assert srv.type == "m3u8"
    assert srv.is_active is True


def test_portal_scraper_zero_video_proxying_direct_urls():
    """Verify scraper emits clean, direct client-facing URLs without proxying."""
    html = """
    <div class="embed">
        <iframe src="https://direct.cdn.provider.tv/play/match42"></iframe>
    </div>
    """
    scraper = PortalScraperAdapter()
    servers = scraper.parse_stream_embeds(html)
    assert len(servers) == 1
    assert servers[0].url == "https://direct.cdn.provider.tv/play/match42"
    # Never proxy through internal endpoints
    assert "/proxy" not in servers[0].url
    assert "localhost" not in servers[0].url


def test_portal_scraper_deduplication():
    """Ensure duplicate URLs in buttons and iframes are resolved to one StreamServer."""
    html = """
    <button data-url="https://live.stream.org/embed">Ø³ÙŠØ±ÙØ± 1</button>
    <a href="https://live.stream.org/embed">Ø³ÙŠØ±ÙØ± 1 Ù…ÙƒØ±Ø±</a>
    <iframe src="https://live.stream.org/embed"></iframe>
    """
    scraper = PortalScraperAdapter()
    servers = scraper.parse_stream_embeds(html)
    assert len(servers) == 1
    assert servers[0].url == "https://live.stream.org/embed"


def test_portal_scraper_fetch_stream_servers_network(sample_portal_html):
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = sample_portal_html
    mock_session.get.return_value = mock_response

    scraper = PortalScraperAdapter(base_url="https://kora-portal.example", session=mock_session)
    servers = scraper.fetch_stream_servers("ØªØ´ÙŠÙ„Ø³ÙŠ", "Ù„ÙŠÙØ±Ø¨ÙˆÙ„")

    assert len(servers) == 4
    mock_session.get.assert_called_once()


def test_portal_scraper_error_handling_timeout_and_malformed():
    mock_session = MagicMock()
    mock_session.get.side_effect = requests.exceptions.ConnectTimeout("Connection refused")

    scraper = PortalScraperAdapter(base_url="https://broken-portal.example", session=mock_session)
    # Must gracefully return empty list
    servers = scraper.fetch_stream_servers("Ø±ÙŠØ§Ù„ Ù…Ø¯Ø±ÙŠØ¯", "Ø¨Ø±Ø´Ù„ÙˆÙ†Ø©")
    assert servers == []

    # Malformed HTML, None, empty string should not crash
    assert scraper.parse_stream_embeds("") == []
    assert scraper.parse_stream_embeds(None) == []
    assert scraper.parse_stream_embeds("<<<<not valid html<<<>>>>///") == []

``n

