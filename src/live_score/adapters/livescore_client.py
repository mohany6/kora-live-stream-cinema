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
        "Premier League": "الدوري الإنجليزي الممتاز",
        "La Liga": "الدوري الإسباني",
        "LaLiga": "الدوري الإسباني",
        "Serie A": "الدوري الإيطالي",
        "Bundesliga": "الدوري الألماني",
        "Ligue 1": "الدوري الفرنسي",
        "UEFA Champions League": "دوري أبطال أوروبا",
        "Champions League": "دوري أبطال أوروبا",
        "UEFA Europa League": "الدوري الأوروبي",
        "Europa League": "الدوري الأوروبي",
        "UEFA Europa Conference League": "دوري المؤتمر الأوروبي",
        "FA Cup": "كأس الاتحاد الإنجليزي",
        "EFL Cup": "كأس الرابطة الإنجليزية",
        "Copa del Rey": "كأس ملك إسبانيا",
        "Supercopa de España": "كأس السوبر الإسباني",
        "Saudi Pro League": "دوري روشن السعودي",
        "Egyptian Premier League": "الدوري المصري الممتاز",
        "CAF Champions League": "دوري أبطال إفريقيا",
        "AFC Champions League": "دوري أبطال آسيا",
        "FIFA World Cup": "كأس العالم",
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
            raw_elapsed = item.get("elapsed") if item.get("elapsed") is not None else item.get("elapsed_time")
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
