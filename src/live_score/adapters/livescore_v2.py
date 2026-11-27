"""
Adapter for the hosted livescoreFootball public API (v2).

The public service at ``https://worldcup26.ir/get/soccer`` exposes ESPN-style
documents: a league catalog, per-league fixture windows, match summaries and
standings.  This module maps those documents onto the internal domain models.

Two operations matter to the application:

* :meth:`LiveScoreV2Client.fetch_window` -- fixtures for a date range across a
  configurable league catalog (one request per league, fetched concurrently).
* :meth:`LiveScoreV2Client.fetch_detail` -- lineups, timeline, statistics and
  standings for a single match, with standings failures tolerated.

Nothing here performs caching; :class:`live_score.api.catalog.LiveFixturesCatalog`
owns TTLs and demo fallback.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Optional
from urllib.parse import urlencode

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

DEFAULT_BASE_URL = "https://worldcup26.ir/get/soccer"

#: Competitions shown by the schedule. Top elite leagues by default.
DEFAULT_LEAGUE_SLUGS: tuple[str, ...] = (
    "esp.1",            # الدوري الإسباني (LaLiga)
    "ita.1",            # الدوري الإيطالي (Serie A)
    "eng.1",            # الدوري الإنجليزي الممتاز (Premier League)
    "ger.1",            # الدوري الألماني (Bundesliga)
    "fra.1",            # الدوري الفرنسي (Ligue 1)
    "uefa.champions",   # دوري أبطال أوروبا (UEFA Champions League)
    "uefa.europa",      # الدوري الأوروبي (UEFA Europa League)
    "uefa.europa.conf", # دوري المؤتمر الأوروبي (UEFA Conference League)
    "ksa.1",            # دوري روشن السعودي (Saudi Pro League)
    "tur.1",            # سوبر ليغ التركي (Turkish Super Lig)
)

LEAGUE_NAMES_AR: dict[str, str] = {
    "esp.1": "الدوري الإسباني",
    "ita.1": "الدوري الإيطالي",
    "eng.1": "الدوري الإنجليزي الممتاز",
    "ger.1": "الدوري الألماني",
    "fra.1": "الدوري الفرنسي",
    "uefa.champions": "دوري أبطال أوروبا",
    "uefa.europa": "الدوري الأوروبي",
    "uefa.europa.conf": "دوري المؤتمر الأوروبي",
    "ksa.1": "دوري روشن السعودي",
    "tur.1": "سوبر ليغ التركي",
    "fifa.world": "كأس العالم",
    "eng.2": "دوري البطولة الإنجليزية",
    "eng.3": "الدوري الإنجليزي الدرجة الأولى",
    "eng.4": "الدوري الإنجليزي الدرجة الثانية",
    "eng.5": "الدوري الإنجليزي الوطني",
    "eng.fa": "كأس الاتحاد الإنجليزي",
    "eng.league_cup": "كأس الرابطة الإنجليزية",
    "esp.2": "الدوري الإسباني الدرجة الثانية",
    "esp.copa_del_rey": "كأس ملك إسبانيا",
    "esp.super_cup": "كأس السوبر الإسباني",
    "ned.1": "الدوري الهولندي",
    "por.1": "الدوري البرتغالي",
    "sco.1": "الدوري الاسكتلندي",
    "bel.1": "الدوري البلجيكي",
    "aut.1": "الدوري النمساوي",
    "usa.1": "الدوري الأمريكي",
    "mex.1": "الدوري المكسيكي",
    "arg.1": "الدوري الأرجنتيني",
    "bra.1": "الدوري البرازيلي",
    "jpn.1": "الدوري الياباني",
}

#: Official MENA broadcast channel allocations per competition.
LEAGUE_CHANNELS_AR: dict[str, tuple[str, ...]] = {
    "eng.1": ("beIN SPORTS 1 HD", "beIN SPORTS 2 HD", "beIN SPORTS Xtra 1"),
    "esp.1": ("beIN SPORTS 3 HD", "beIN SPORTS 1 HD", "beIN SPORTS 2 HD"),
    "ita.1": ("AD SPORTS Premium 1", "AD SPORTS Premium 2", "StarzPlay"),
    "ger.1": ("beIN SPORTS 5 HD", "beIN SPORTS 4 HD"),
    "fra.1": ("beIN SPORTS 4 HD", "beIN SPORTS 2 HD"),
    "uefa.champions": (
        "beIN SPORTS 1 HD", "beIN SPORTS 2 HD", "beIN SPORTS 3 HD",
        "beIN SPORTS 4 HD", "beIN SPORTS 5 HD", "beIN SPORTS 6 HD", "beIN SPORTS 8 HD"
    ),
    "uefa.europa": ("beIN SPORTS 1 HD", "beIN SPORTS 2 HD", "beIN SPORTS 3 HD"),
    "uefa.europa.conf": ("beIN SPORTS 3 HD", "beIN SPORTS 4 HD"),
    "ksa.1": ("SSC 1 HD", "SSC EXTRA 1 HD", "SSC 2 HD"),
    "tur.1": ("beIN SPORTS 4 HD", "beIN CONNECT", "beIN SPORTS 2 HD"),
}

_FLAGSHIP_TEAMS: frozenset[str] = frozenset({
    "Real Madrid", "Barcelona", "Manchester City", "Liverpool", "Arsenal",
    "Manchester United", "Bayern Munich", "Paris Saint-Germain", "Al Hilal",
    "Al Nassr", "Al Ittihad", "Galatasaray", "Fenerbahce", "Inter Milan", "Juventus",
})


def _channel_for_event(
    league_slug: str,
    event_id: str,
    home_name: str = "",
    away_name: str = "",
) -> Optional[str]:
    options = LEAGUE_CHANNELS_AR.get(league_slug)
    if not options:
        return None
    if any(t in (home_name, away_name) for t in _FLAGSHIP_TEAMS):
        return options[0]
    idx = sum(ord(c) for c in str(event_id)) % len(options)
    return options[idx]


#: Statistics worth surfacing in the match center, in display order.
_STAT_LAYOUT: tuple[tuple[str, str, str], ...] = (
    ("possessionPct", "الاستحواذ", "%"),
    ("totalShots", "التسديدات", ""),
    ("shotsOnTarget", "على المرمى", ""),
    ("wonCorners", "الركنيات", ""),
    ("foulsCommitted", "الأخطاء", ""),
    ("goalAssists", "صناعة الأهداف", ""),
    ("shotAssists", "التمريرات المفتاحية", ""),
)

_POSTPONED_NAMES = (
    "POSTPONED",
    "CANCELED",
    "CANCELLED",
    "SUSPENDED",
    "ABANDONED",
)


class LiveScoreV2Error(RuntimeError):
    """Raised when the public API is unreachable or returns garbage."""


@dataclass(frozen=True)
class FixtureRef:
    """Coordinates needed to hydrate a single upstream match."""

    league_slug: str
    event_id: str

    @property
    def source_ref(self) -> str:
        return f"{self.league_slug}:{self.event_id}"

    @classmethod
    def parse(cls, raw: Optional[str]) -> Optional["FixtureRef"]:
        if not raw or ":" not in raw:
            return None
        slug, _, event_id = raw.partition(":")
        if not slug or not event_id:
            return None
        return cls(league_slug=slug, event_id=event_id)


def _first(value: Any) -> dict[str, Any]:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return {}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value).strip().replace("%", "")
        return float(text) if text else default
    except (TypeError, ValueError):
        return default


def _parse_iso(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value.strip():
        clean = value.strip()
        if clean.endswith("Z"):
            clean = clean[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(clean)
        except ValueError:
            return datetime.now(timezone.utc)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


class LiveScoreV2Client:
    """Client for the hosted livescoreFootball JSON API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        session: Optional[Any] = None,
        timeout: float = 12.0,
        leagues: Optional[Iterable[str]] = None,
        max_workers: int = 6,
        standings_ttl: float = 300.0,
        standings_base_url: Optional[str] = None,
    ) -> None:
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.standings_base_url = (standings_base_url or self.base_url).rstrip("/")
        self.session = session or requests
        self.timeout = timeout
        self.leagues = tuple(leagues or DEFAULT_LEAGUE_SLUGS)
        self.max_workers = max(1, max_workers)
        self.standings_ttl = max(1.0, float(standings_ttl))
        self._standings_cache: dict[
            tuple[str, str], tuple[float, dict[str, Any]]
        ] = {}
        self._standings_lock = threading.Lock()
        #: Leagues that answered the latest :meth:`fetch_window` call.
        self.last_window_success: frozenset[str] = frozenset()
        #: Leagues whose latest fixture request failed.
        self.last_window_failed: frozenset[str] = frozenset()

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------
    def _get_json(self, path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        return self._get_json_from(self.base_url, path, params)

    def _get_json_from(
        self,
        base_url: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        url = f"{base_url}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:  # pragma: no cover - network boundary
            raise LiveScoreV2Error(f"upstream request failed: {url}") from exc
        except ValueError as exc:
            raise LiveScoreV2Error(f"upstream returned invalid JSON: {url}") from exc

        if not isinstance(payload, dict):
            raise LiveScoreV2Error(f"upstream returned an unexpected payload: {url}")
        if payload.get("error"):
            raise LiveScoreV2Error(str(payload["error"]))
        return payload

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------
    def fetch_fixtures(
        self,
        league_slug: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Return raw fixture events for one league and inclusive date range."""
        payload = self._get_json(
            f"/{league_slug}/fixtures",
            {
                "status": "all",
                "from": start.strftime("%Y%m%d"),
                "to": end.strftime("%Y%m%d"),
                "limit": 200,
            },
        )
        events = payload.get("events")
        return events if isinstance(events, list) else []

    def fetch_window(
        self,
        start: date,
        end: date,
        leagues: Optional[Iterable[str]] = None,
    ) -> list[Match]:
        """
        Fetch every configured league for ``start..end``.

        Per-league failures are logged and skipped.  If every league fails the
        call raises :class:`LiveScoreV2Error` so the catalog can keep stale data
        or fall back to the demo matchday instead of publishing an empty slate.
        """
        slugs = tuple(leagues or self.leagues)
        if not slugs:
            self.last_window_success = frozenset()
            self.last_window_failed = frozenset()
            return []

        raw_by_league: dict[str, list[dict[str, Any]]] = {}
        errors: list[str] = []
        failed_slugs: set[str] = set()
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(slugs))) as pool:
            futures = {
                pool.submit(self.fetch_fixtures, slug, start, end): slug for slug in slugs
            }
            for future, slug in futures.items():
                try:
                    raw_by_league[slug] = future.result()
                except Exception as exc:  # noqa: BLE001 - isolated per league
                    errors.append(f"{slug}: {exc}")
                    failed_slugs.add(slug)
                    logger.warning("Live scores: league %s failed (%s)", slug, exc)

        # Give the catalog enough information to retain stale fixtures for the
        # leagues that could not be refreshed instead of publishing a partial
        # slate that would 404 matches users already had on screen.
        self.last_window_success = frozenset(raw_by_league)
        self.last_window_failed = frozenset(failed_slugs)

        if errors and len(errors) == len(slugs):
            raise LiveScoreV2Error("all league requests failed: " + "; ".join(errors))

        matches: list[Match] = []
        for slug, events in raw_by_league.items():
            for event in events:
                match = self._map_event(slug, event)
                if match is not None:
                    matches.append(match)
        return matches

    # ------------------------------------------------------------------
    # Match detail
    # ------------------------------------------------------------------
    def _detail_payload(self, league_slug: str, event_id: str) -> dict[str, Any]:
        return self._get_json(f"/{league_slug}/events/{event_id}")

    def fetch_detail(
        self,
        league_slug: str,
        event_id: str,
        match: Optional[Match] = None,
    ) -> MatchDetail:
        """Fetch and map a full match summary (lineups, events, stats)."""
        payload = self._detail_payload(league_slug, event_id)
        header = payload.get("header") if isinstance(payload.get("header"), dict) else {}

        resolved_match = match
        if resolved_match is None:
            header_event = {
                **header,
                "competitions": header.get("competitions") or [],
                "date": header.get("date"),
            }
            resolved_match = self._map_event(league_slug, header_event)
        if resolved_match is None:
            raise LiveScoreV2Error(f"match {event_id} could not be mapped")

        home_lineup, home_formation = self._map_roster(
            self._roster_for(payload, "home")
        )
        away_lineup, away_formation = self._map_roster(
            self._roster_for(payload, "away")
        )

        stadium = resolved_match.stadium
        referee = resolved_match.referee
        game_info = payload.get("gameInfo") if isinstance(payload.get("gameInfo"), dict) else {}
        venue = game_info.get("venue") if isinstance(game_info.get("venue"), dict) else {}
        if venue.get("fullName"):
            stadium = str(venue["fullName"])
        summary_referee: Optional[str] = None
        for official in game_info.get("officials") or []:
            position = official.get("position") or {}
            if "referee" in str(position.get("name", "")).lower():
                summary_referee = official.get("displayName") or official.get("fullName")
                break
        if summary_referee:
            referee = summary_referee

        channel = resolved_match.channel or _channel_for_event(
            league_slug,
            str(event_id),
            resolved_match.home_team.name_en or "",
            resolved_match.away_team.name_en or "",
        )

        if (
            stadium != resolved_match.stadium
            or referee != resolved_match.referee
            or channel != resolved_match.channel
        ):
            resolved_match = resolved_match.model_copy(
                update={"stadium": stadium, "referee": referee, "channel": channel}
            )

        competition = _first(header.get("competitions"))
        raw_events = payload.get("keyEvents")
        if not isinstance(raw_events, list) or not raw_events:
            raw_events = competition.get("details") if isinstance(competition, dict) else []
        events = self._map_events(raw_events if isinstance(raw_events, list) else [])

        standings: list[dict[str, Any]] = []
        season = self._season_year(header, resolved_match)
        if season is not None:
            try:
                standings = self.fetch_standings(
                    league_slug,
                    season,
                    home_name=resolved_match.home_team.name_en,
                    away_name=resolved_match.away_team.name_en,
                )
            except Exception as exc:  # noqa: BLE001 - standings are optional
                logger.warning(
                    "Live scores: standings unavailable for %s (%s)", league_slug, exc
                )

        return MatchDetail(
            match=resolved_match,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            events=events,
            stats=self._map_stats(payload.get("boxscore")),
            standings=standings,
            home_formation=home_formation,
            away_formation=away_formation,
        )

    def fetch_standings(
        self,
        league_slug: str,
        season: int | str,
        home_name: Optional[str] = None,
        away_name: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Return normalized standings rows for a league season."""
        payload = self._standings_payload(league_slug, season)
        children = payload.get("children")
        if not isinstance(children, list):
            return []

        groups: list[list[dict[str, Any]]] = []
        for child in children:
            standings = child.get("standings") if isinstance(child, dict) else None
            if isinstance(standings, dict) and isinstance(standings.get("entries"), list):
                if standings["entries"]:
                    groups.append(standings["entries"])
        if not groups:
            return []

        entries = groups[0]
        if len(groups) > 1 and (home_name or away_name):
            for group in groups:
                if any(
                    self._same_team(
                        str((entry.get("team") or {}).get("displayName") or ""),
                        home_name,
                    )
                    or self._same_team(
                        str((entry.get("team") or {}).get("displayName") or ""),
                        away_name,
                    )
                    for entry in group
                    if isinstance(entry, dict)
                ):
                    entries = group
                    break

        rows: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            team = entry.get("team") if isinstance(entry.get("team"), dict) else {}
            raw_stats = {
                str(stat.get("name")): stat.get("displayValue")
                for stat in entry.get("stats") or []
                if isinstance(stat, dict) and stat.get("name")
            }
            name_en = team.get("displayName") or team.get("name")
            if not name_en:
                continue
            name_ar = TeamAliasMatcher.get_arabic_name(str(name_en)) or str(name_en)
            rows.append(
                {
                    "position": _as_int(entry.get("rank") or raw_stats.get("rank"), len(rows) + 1),
                    "team_name_ar": name_ar,
                    "played": _as_int(raw_stats.get("gamesPlayed")),
                    "won": _as_int(raw_stats.get("wins")),
                    "drawn": _as_int(raw_stats.get("ties")),
                    "lost": _as_int(raw_stats.get("losses")),
                    "goals_for": _as_int(raw_stats.get("pointsFor")),
                    "goals_against": _as_int(raw_stats.get("pointsAgainst")),
                    "points": _as_int(raw_stats.get("points")),
                    "is_home": self._same_team(name_en, home_name),
                    "is_away": self._same_team(name_en, away_name),
                }
            )
        return rows

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------
    def _standings_payload(
        self, league_slug: str, season: int | str
    ) -> dict[str, Any]:
        """Fetch a league table at most once per ``standings_ttl`` seconds."""
        key = (league_slug, str(season))
        now = time.monotonic()
        with self._standings_lock:
            cached = self._standings_cache.get(key)
            if cached is not None and now - cached[0] < self.standings_ttl:
                return cached[1]

        payload = self._get_json_from(
            self.standings_base_url,
            f"/{league_slug}/standings",
            {"season": season},
        )
        with self._standings_lock:
            self._standings_cache[key] = (now, payload)
        return payload

    def _map_event(self, league_slug: str, event: Any) -> Optional[Match]:
        if not isinstance(event, dict):
            return None

        competition = _first(event.get("competitions"))
        competitors = competition.get("competitors") or []
        home = next(
            (item for item in competitors if item.get("homeAway") == "home"), None
        )
        away = next(
            (item for item in competitors if item.get("homeAway") == "away"), None
        )
        if home is None or away is None:
            ordered = [item for item in competitors if isinstance(item, dict)]
            if len(ordered) < 2:
                return None
            home, away = ordered[0], ordered[1]

        event_id = event.get("id") or competition.get("id")
        if not event_id:
            return None

        league_payload = (
            event.get("league") if isinstance(event.get("league"), dict) else {}
        )
        league = League(
            id=str(league_payload.get("id")) if league_payload.get("id") else None,
            name_ar=LEAGUE_NAMES_AR.get(league_slug)
            or league_payload.get("name")
            or league_slug,
            name_en=league_payload.get("name") or league_slug,
            logo_url=league_payload.get("logo") or None,
        )

        status_payload = competition.get("status") or event.get("status") or {}
        status = self._map_status(status_payload)

        kickoff = _parse_iso(
            event.get("date")
            or competition.get("date")
            or competition.get("startDate")
        )

        elapsed: Optional[int] = None
        if status in {
            MatchStatus.IN_PLAY,
            MatchStatus.HALFTIME,
            MatchStatus.EXTRA_TIME,
            MatchStatus.PENALTIES,
        }:
            clock = status_payload.get("clock") if isinstance(status_payload, dict) else None
            if isinstance(clock, (int, float)) and clock > 0:
                elapsed = min(130, int(clock) // 60)
            elif status == MatchStatus.HALFTIME:
                elapsed = 45

        venue = competition.get("venue") if isinstance(competition.get("venue"), dict) else {}
        if not venue and isinstance(event.get("venue"), dict):
            venue = event["venue"]

        home_team = self._map_team(home)
        away_team = self._map_team(away)
        channel = _channel_for_event(
            league_slug,
            str(event_id),
            home_team.name_en or "",
            away_team.name_en or "",
        )

        return Match(
            id=str(event_id),
            home_team=home_team,
            away_team=away_team,
            league=league,
            status=status,
            kickoff_time=kickoff,
            home_score=_as_int(home.get("score")),
            away_score=_as_int(away.get("score")),
            elapsed_time=elapsed,
            channel=channel,
            stadium=venue.get("fullName") or None,
            source_ref=FixtureRef(str(league_slug), str(event_id)).source_ref,
        )

    def _map_team(self, competitor: Any) -> Team:
        team = competitor.get("team") if isinstance(competitor, dict) else {}
        team = team if isinstance(team, dict) else {}
        name_en = (
            team.get("displayName")
            or team.get("name")
            or team.get("shortDisplayName")
            or "Unknown Team"
        )
        logos = team.get("logos") if isinstance(team.get("logos"), list) else []
        logo = team.get("logo") or (logos[0].get("href") if logos else None)
        name_ar = TeamAliasMatcher.get_arabic_name(str(name_en)) or str(name_en)
        return Team(
            id=str(team.get("id")) if team.get("id") else None,
            name_ar=name_ar,
            name_en=str(name_en),
            logo_url=logo or None,
        )

    @staticmethod
    def _map_status(status_payload: Any) -> MatchStatus:
        if not isinstance(status_payload, dict):
            return MatchStatus.SCHEDULED
        type_info = status_payload.get("type")
        type_info = type_info if isinstance(type_info, dict) else {}
        state = str(type_info.get("state") or "").lower()
        name = str(type_info.get("name") or "").upper()

        if any(marker in name for marker in _POSTPONED_NAMES):
            return MatchStatus.POSTPONED
        if state == "in":
            if "HALFTIME" in name or "HALF_TIME" in name:
                return MatchStatus.HALFTIME
            if "EXTRA" in name or "OVERTIME" in name:
                return MatchStatus.EXTRA_TIME
            if "PENALT" in name or "SHOOTOUT" in name:
                return MatchStatus.PENALTIES
            return MatchStatus.IN_PLAY
        if state == "post":
            return MatchStatus.FINISHED
        return MatchStatus.SCHEDULED

    @staticmethod
    def _season_year(header: dict[str, Any], match: Match) -> Optional[int]:
        season = header.get("season") if isinstance(header.get("season"), dict) else {}
        league = header.get("league") if isinstance(header.get("league"), dict) else {}
        league_season = (
            league.get("season") if isinstance(league.get("season"), dict) else {}
        )
        for candidate in (season.get("year"), league_season.get("year")):
            if isinstance(candidate, int) and candidate > 1900:
                return candidate
        return match.kickoff_time.year

    @staticmethod
    def _same_team(left: Optional[str], right: Optional[str]) -> bool:
        if not left or not right:
            return False
        return TeamAliasMatcher.normalize_english_name(left) == (
            TeamAliasMatcher.normalize_english_name(right)
        )

    @staticmethod
    def _roster_for(payload: dict[str, Any], side: str) -> dict[str, Any]:
        rosters = payload.get("rosters")
        if isinstance(rosters, list):
            for entry in rosters:
                if isinstance(entry, dict) and entry.get("homeAway") == side:
                    return entry
        return {}

    def _map_roster(
        self, entry: dict[str, Any]
    ) -> tuple[list[LineupPlayer], Optional[str]]:
        formation = str(entry.get("formation") or "").strip() or None
        raw_roster = entry.get("roster")
        if not isinstance(raw_roster, list):
            return [], formation

        players: list[dict[str, Any]] = []
        for item in raw_roster:
            if not isinstance(item, dict) or item.get("starter") is False:
                continue
            athlete = item.get("athlete") if isinstance(item.get("athlete"), dict) else {}
            name = (
                athlete.get("displayName")
                or athlete.get("fullName")
                or athlete.get("shortName")
            )
            if not name:
                continue
            position = item.get("position") if isinstance(item.get("position"), dict) else {}
            abbreviation = str(position.get("abbreviation") or "").upper()
            players.append(
                {
                    "id": str(athlete.get("id")) if athlete.get("id") else None,
                    "name": str(name),
                    "number": _as_int(item.get("jersey")),
                    "position": self._role_from_position(abbreviation),
                    "side": self._side_from_position(abbreviation),
                    "abbreviation": abbreviation,
                }
            )

        rows = self._assign_rows(players, formation)
        lineup: list[LineupPlayer] = []
        for row_index, row_players in enumerate(rows, start=1):
            row_players.sort(key=lambda player: (player["side"], player["name"]))
            for column, player in enumerate(row_players, start=1):
                lineup.append(
                    LineupPlayer(
                        id=player["id"],
                        name=player["name"],
                        number=player["number"],
                        position=player["position"],
                        is_starter=True,
                        grid_position=f"{row_index}:{column}",
                    )
                )
        return lineup, formation

    @staticmethod
    def _role_from_position(abbreviation: str) -> str:
        if abbreviation in {"G", "GK"} or abbreviation.startswith("G"):
            return "GK"
        if "M" in abbreviation:
            return "MF"
        if any(token in abbreviation for token in ("F", "ST", "W")):
            return "FW"
        if any(token in abbreviation for token in ("D", "B", "SW")):
            return "DF"
        return "MF"

    @staticmethod
    def _side_from_position(abbreviation: str) -> int:
        """0 = left, 1 = centre, 2 = right."""
        if "-L" in abbreviation or abbreviation.startswith("L"):
            return 0
        if "-R" in abbreviation or abbreviation.startswith("R"):
            return 2
        return 1

    @classmethod
    def _assign_rows(
        cls,
        players: list[dict[str, Any]],
        formation: Optional[str],
    ) -> list[list[dict[str, Any]]]:
        """Distribute players into pitch rows derived from the formation."""
        if not players:
            return []

        parts = cls._formation_parts(formation)
        if not parts:
            parts = cls._fallback_parts(players)

        row_roles = ["GK", "DF"] + ["MF"] * max(0, len(parts) - 2) + ["FW"]
        row_sizes = [1] + parts
        rows: list[list[dict[str, Any]]] = [[] for _ in row_sizes]

        goalkeepers = [player for player in players if player["position"] == "GK"]
        if goalkeepers:
            rows[0].append(goalkeepers[0])

        outfield = [player for player in players if player["position"] != "GK"]
        role_rows = {
            "DF": [i for i, role in enumerate(row_roles) if role == "DF"],
            "MF": [i for i, role in enumerate(row_roles) if role == "MF"],
            "FW": [i for i, role in enumerate(row_roles) if role == "FW"],
        }

        # Midfielders with an explicit attacking role fill the most advanced
        # midfield line first; holding midfielders fill from the back.
        midfielders = [player for player in outfield if player["position"] == "MF"]
        midfielders.sort(key=cls._midfield_depth)
        others = [player for player in outfield if player["position"] != "MF"]

        for player in [*midfielders, *others]:
            candidates = role_rows.get(player["position"]) or []
            target = next(
                (index for index in candidates if len(rows[index]) < row_sizes[index]),
                None,
            )
            if target is None:
                target = next(
                    (
                        index
                        for index in range(1, len(rows))
                        if len(rows[index]) < row_sizes[index]
                    ),
                    None,
                )
            if target is None:
                target = len(rows) - 1
            rows[target].append(player)

        return [row for row in rows if row]

    @staticmethod
    def _midfield_depth(player: dict[str, Any]) -> int:
        abbreviation = player.get("abbreviation", "")
        if "DMF" in abbreviation or abbreviation.startswith("DM") or abbreviation.startswith("CDM"):
            return 0
        if "AM" in abbreviation:
            return 2
        return 1

    @staticmethod
    def _formation_parts(formation: Optional[str]) -> list[int]:
        if not formation:
            return []
        parts = [int(part) for part in re.findall(r"\d+", formation)]
        return parts if 2 <= len(parts) <= 5 and sum(parts) <= 10 else []

    @staticmethod
    def _fallback_parts(players: list[dict[str, Any]]) -> list[int]:
        counts = {
            role: sum(1 for player in players if player["position"] == role)
            for role in ("DF", "MF", "FW")
        }
        parts = [count for count in (counts["DF"], counts["MF"], counts["FW"]) if count]
        return parts or [3, 4, 3]

    def _map_events(self, raw_events: list[Any]) -> list[MatchEvent]:
        events: list[MatchEvent] = []
        for item in raw_events:
            if not isinstance(item, dict):
                continue
            event_type = self._event_type(item)
            if event_type is None:
                continue

            names = self._event_names(item)
            if event_type == "goal":
                scorer = self._scorer_from_text(item.get("text"))
                if scorer:
                    names = scorer + names[1:]
            elif event_type == "substitution":
                names = self._substitution_names(item.get("text")) or names

            player_name = names[0] if names else "—"
            team = item.get("team") if isinstance(item.get("team"), dict) else {}

            events.append(
                MatchEvent(
                    id=str(item.get("id")) if item.get("id") else None,
                    minute=self._event_minute(item),
                    type=event_type,
                    player_name=player_name,
                    team_id=str(team.get("id")) if team.get("id") else None,
                    description_ar=self._event_description(item, event_type, names),
                )
            )
        return events

    @staticmethod
    def _event_names(item: dict[str, Any]) -> list[str]:
        """Read involved players from either ESPN payload shape."""
        names: list[str] = []
        athletes = item.get("athletesInvolved")
        for athlete in athletes or []:
            if isinstance(athlete, dict) and athlete.get("displayName"):
                names.append(str(athlete["displayName"]))
        if names:
            return names

        for participant in item.get("participants") or []:
            if not isinstance(participant, dict):
                continue
            athlete = participant.get("athlete")
            if isinstance(athlete, dict) and athlete.get("displayName"):
                names.append(str(athlete["displayName"]))
        return names

    @staticmethod
    def _scorer_from_text(text: Any) -> list[str]:
        if not isinstance(text, str):
            return []
        match = re.search(r"Goal!.*?\.\s*([^(]+?)\s*\(", text)
        return [match.group(1).strip()] if match else []

    @staticmethod
    def _substitution_names(text: Any) -> list[str]:
        if not isinstance(text, str):
            return []
        match = re.search(r"\.\s*(.+?)\s+replaces\s+(.+?)\.\s*$", text)
        if not match:
            return []
        outgoing = re.sub(
            r"\s+(?:because of|due to)\s+.*$", "", match.group(2).strip(), flags=re.I
        )
        return [match.group(1).strip(), outgoing]

    @staticmethod
    def _event_type(item: dict[str, Any]) -> Optional[str]:
        type_info = item.get("type") if isinstance(item.get("type"), dict) else {}
        text = str(type_info.get("text") or "").lower()
        if item.get("scoringPlay") or "goal" in text:
            return "goal"
        if item.get("redCard") or "red card" in text:
            return "red_card"
        if item.get("yellowCard") or "yellow card" in text:
            return "yellow_card"
        if "substitution" in text or text == "sub":
            return "substitution"
        if "var" in text or "video review" in text:
            return "var"
        return None

    @staticmethod
    def _event_minute(item: dict[str, Any]) -> int:
        clock = item.get("clock") if isinstance(item.get("clock"), dict) else {}
        display = str(clock.get("displayValue") or "")
        match = re.search(r"\d+", display)
        if match:
            return int(match.group(0))
        value = clock.get("value")
        if isinstance(value, (int, float)):
            return max(0, int(value) // 60)
        return 0

    @staticmethod
    def _event_description(
        item: dict[str, Any],
        event_type: str,
        names: list[str],
    ) -> str:
        if event_type == "goal":
            if item.get("ownGoal"):
                label = "هدف عكسي"
            elif item.get("penaltyKick"):
                label = "هدف من ركلة جزاء"
            elif item.get("shootout"):
                label = "ركلة ترجيح"
            else:
                label = "هدف"
            if len(names) > 1:
                label = f"{label} • صناعة {names[1]}"
            return label
        if event_type == "yellow_card":
            return "بطاقة صفراء"
        if event_type == "red_card":
            return "بطاقة حمراء"
        if event_type == "substitution":
            if len(names) > 1:
                return f"تبديل • خروج {names[1]}"
            return "تبديل"
        return "مراجعة تقنية الفيديو"

    @staticmethod
    def _map_stats(boxscore: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(boxscore, dict):
            return {}
        teams = boxscore.get("teams")
        if not isinstance(teams, list):
            return {}

        by_side: dict[str, dict[str, Any]] = {}
        for entry in teams:
            if not isinstance(entry, dict):
                continue
            side = entry.get("homeAway")
            if side in {"home", "away"}:
                by_side[side] = {
                    str(stat.get("name")): stat.get("displayValue")
                    for stat in entry.get("statistics") or []
                    if isinstance(stat, dict) and stat.get("name")
                }

        stats: dict[str, dict[str, Any]] = {}
        for name, label_ar, unit in _STAT_LAYOUT:
            if name not in by_side.get("home", {}) and name not in by_side.get("away", {}):
                continue
            stats[name] = {
                "label_ar": label_ar,
                "home": _as_float(by_side.get("home", {}).get(name)),
                "away": _as_float(by_side.get("away", {}).get(name)),
                "unit": unit,
            }
        return stats


ESPN_SITE_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
ESPN_CORE_BASE = "https://site.api.espn.com/apis/v2/sports/soccer"

_ESPN_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)


class _UrllibResponse:
    """Small ``requests.Response`` look-alike used by the urllib transport."""

    def __init__(self, status_code: int, body: bytes, url: str) -> None:
        self.status_code = status_code
        self.content = body
        self.url = url

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"{self.status_code} Client Error for url: {self.url}",
                response=self,
            )

    def json(self) -> Any:
        return json.loads(self.content.decode("utf-8"))


class _UrllibSession:
    """Minimal session-compatible transport for ESPN's public API.

    ESPN's edge rejects the TLS fingerprint of the ``requests``/urllib3 stack
    with HTTP 403 while answering the standard-library client normally, so the
    default ESPN transport uses urllib.  An injected session (tests, callers)
    still takes precedence.
    """

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout
        self.headers = {
            "Accept": "application/json",
            "Accept-Language": "ar,en;q=0.9",
            "User-Agent": _ESPN_USER_AGENT,
        }

    def get(
        self,
        url: str,
        timeout: Optional[float] = None,
        **_: Any,
    ) -> _UrllibResponse:
        request = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(
                request, timeout=timeout or self.timeout
            ) as response:
                return _UrllibResponse(
                    getattr(response, "status", 200),
                    response.read(),
                    url,
                )
        except urllib.error.HTTPError as exc:
            # Surface the status through raise_for_status() for parity with
            # requests; the caller's error handling stays unchanged.
            return _UrllibResponse(exc.code, exc.read(), url)
        except (urllib.error.URLError, OSError) as exc:
            raise requests.RequestException(str(exc)) from exc


class EspnSoccerClient(LiveScoreV2Client):
    """Direct ESPN client used when the hosted wrapper is unavailable.

    ESPN's public scoreboard, summary and standings documents are the same
    shape the hosted livescoreFootball service proxies, so all mapping is
    shared with :class:`LiveScoreV2Client`.
    """

    def __init__(
        self,
        *,
        session: Optional[Any] = None,
        timeout: float = 12.0,
        leagues: Optional[Iterable[str]] = None,
        max_workers: int = 6,
        standings_ttl: float = 300.0,
        scoreboard_ttl: float = 25.0,
        archive_ttl: float = 600.0,
    ) -> None:
        super().__init__(
            base_url=ESPN_SITE_BASE,
            session=session or _UrllibSession(timeout=timeout),
            timeout=timeout,
            leagues=leagues,
            max_workers=max_workers,
            standings_ttl=standings_ttl,
            standings_base_url=ESPN_CORE_BASE,
        )
        self.scoreboard_ttl = max(1.0, float(scoreboard_ttl))
        self.archive_ttl = max(self.scoreboard_ttl, float(archive_ttl))
        self._scoreboard_cache: dict[
            tuple[str, str], tuple[float, dict[str, Any]]
        ] = {}
        self._scoreboard_lock = threading.Lock()

    def _scoreboard(self, league_slug: str, day: date) -> dict[str, Any]:
        key = (league_slug, day.isoformat())
        now = time.monotonic()
        today = datetime.now(timezone.utc).date()
        ttl = self.scoreboard_ttl if day == today else self.archive_ttl
        with self._scoreboard_lock:
            cached = self._scoreboard_cache.get(key)
            if cached is not None and now - cached[0] < ttl:
                return cached[1]

        payload = self._get_json(
            f"/{league_slug}/scoreboard", {"dates": day.strftime("%Y%m%d")}
        )
        with self._scoreboard_lock:
            self._scoreboard_cache[key] = (now, payload)
        return payload

    def fetch_fixtures(
        self,
        league_slug: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        seen: set[str] = set()
        league_payload: dict[str, Any] = {}
        day = start
        while day <= end:
            payload = self._scoreboard(league_slug, day)
            raw_leagues = payload.get("leagues")
            if not league_payload and isinstance(raw_leagues, list) and raw_leagues:
                league = raw_leagues[0] if isinstance(raw_leagues[0], dict) else {}
                league_payload = dict(league)
                logos = league_payload.get("logos")
                if (
                    not league_payload.get("logo")
                    and isinstance(logos, list)
                    and logos
                ):
                    first_logo = logos[0] if isinstance(logos[0], dict) else {}
                    if first_logo.get("href"):
                        league_payload["logo"] = first_logo["href"]

            for event in payload.get("events") or []:
                if not isinstance(event, dict):
                    continue
                event_id = str(event.get("id") or "")
                if event_id and event_id in seen:
                    continue
                if event_id:
                    seen.add(event_id)
                enriched = dict(event)
                if league_payload:
                    enriched.setdefault("league", league_payload)
                events.append(enriched)
            day += timedelta(days=1)
        return events

    def _detail_payload(self, league_slug: str, event_id: str) -> dict[str, Any]:
        return self._get_json(f"/{league_slug}/summary", {"event": event_id})


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_LEAGUE_SLUGS",
    "ESPN_CORE_BASE",
    "ESPN_SITE_BASE",
    "EspnSoccerClient",
    "LEAGUE_NAMES_AR",
    "FixtureRef",
    "LiveScoreV2Client",
    "LiveScoreV2Error",
]
