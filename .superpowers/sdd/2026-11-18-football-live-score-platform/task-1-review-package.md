# Task 1 Review Package

## File: src/live_score/domain/models.py
`python
"""
Core Domain Models for Arabic Football Live Score & Streaming Platform.

Defines Pydantic v2 schemas for:
- MatchStatus (Lifecycle states)
- Team (Arabic and English naming)
- League (Competition branding and round)
- StreamServer (Multi-server embeds and streams)
- MatchEvent (Goal, card, substitution, VAR events)
- LineupPlayer (Tactical lineup and pitch placement with Latin names)
- Match (Aggregated live match entity)
- MatchDetail (Full hybrid center detail view)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class MatchStatus(str, Enum):
    """Lifecycle states of a football match."""
    SCHEDULED = "SCHEDULED"
    IN_PLAY = "IN_PLAY"
    HALFTIME = "HALFTIME"
    EXTRA_TIME = "EXTRA_TIME"
    PENALTIES = "PENALTIES"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"


class Team(BaseModel):
    """Team entity representing Arabic display and official English name."""
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = None
    name_ar: str
    name_en: Optional[str] = None
    logo_url: Optional[str] = None


class League(BaseModel):
    """Competition / Tournament metadata."""
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = None
    name_ar: str
    name_en: Optional[str] = None
    round: Optional[str] = None
    logo_url: Optional[str] = None


class StreamServer(BaseModel):
    """Streaming server embed or direct HLS source."""
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = None
    server_name: str
    url: str
    type: str = "iframe"  # "m3u8" or "iframe"
    is_active: bool = True
    quality: Optional[str] = None  # e.g., "1080p", "720p", "multi"


class MatchEvent(BaseModel):
    """In-game match timeline event."""
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = None
    minute: int
    type: str  # "goal", "yellow_card", "red_card", "substitution", "var"
    player_name: str
    team_id: Optional[str] = None
    description_ar: Optional[str] = None


class LineupPlayer(BaseModel):
    """Pitch player representation adhering to Option B (Latin/English names)."""
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = None
    name: str  # Rendered in Latin/English characters
    number: int
    position: str  # "GK", "DF", "MF", "FW"
    is_starter: bool = True
    grid_position: Optional[str] = None  # e.g. "3:2" or coordinate string


class Match(BaseModel):
    """Core Match entity combining scores, teams, stream links, and metadata."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    home_team: Team
    away_team: Team
    league: League
    status: MatchStatus
    kickoff_time: datetime
    home_score: Optional[int] = 0
    away_score: Optional[int] = 0
    elapsed_time: Optional[int] = None
    stream_servers: list[StreamServer] = Field(default_factory=list)
    channel: Optional[str] = None
    commentator: Optional[str] = None
    stadium: Optional[str] = None
    referee: Optional[str] = None
    is_admin_override: bool = False

    @property
    def is_live(self) -> bool:
        """Indicates if the match is currently in an active live state."""
        return self.status in {
            MatchStatus.IN_PLAY,
            MatchStatus.HALFTIME,
            MatchStatus.EXTRA_TIME,
            MatchStatus.PENALTIES,
        }


class MatchDetail(BaseModel):
    """Hybrid match center view combining match state, pitch lineups, and stats."""
    model_config = ConfigDict(populate_by_name=True)

    match: Match
    home_lineup: list[LineupPlayer] = Field(default_factory=list)
    away_lineup: list[LineupPlayer] = Field(default_factory=list)
    events: list[MatchEvent] = Field(default_factory=list)
    stats: Optional[dict[str, Any]] = None


__all__ = [
    "MatchStatus",
    "Team",
    "League",
    "StreamServer",
    "MatchEvent",
    "LineupPlayer",
    "Match",
    "MatchDetail",
]

``n
## File: src/live_score/domain/resolver.py
`python
"""
Priority Ingestion Resolver & Arabic Team Alias Matcher.

Enforces the 3-tier hierarchy:
  Admin Override > Sports API / Open Backend > Scraper Ingestion

Normalizes scraped Arabic club names to standard official team names.
"""

from __future__ import annotations

import re
from typing import Optional

from live_score.domain.models import Match, StreamServer


class TeamAliasMatcher:
    """Normalizes and matches Arabic team aliases to standard English names."""

    _CUSTOM_ALIASES: dict[str, str] = {}

    # Comprehensive dictionary of Arabic names/nicknames to official standard names
    _BASE_ALIASES: dict[str, str] = {
        # Premier League
        "ØªØ´ÙŠÙ„Ø³ÙŠ": "Chelsea",
        "Ø§Ù„Ø¨Ù„ÙˆØ²": "Chelsea",
        "Ù„ÙŠÙØ±Ø¨ÙˆÙ„": "Liverpool",
        "Ø§Ù„Ø±ÙŠØ¯Ø²": "Liverpool",
        "Ù…Ø§Ù†Ø´Ø³ØªØ± Ø³ÙŠØªÙŠ": "Manchester City",
        "Ù…Ø§Ù† Ø³ÙŠØªÙŠ": "Manchester City",
        "Ø§Ù„Ø³ÙŠØªÙŠ": "Manchester City",
        "Ù…Ø§Ù†Ø´Ø³ØªØ± ÙŠÙˆÙ†Ø§ÙŠØªØ¯": "Manchester United",
        "Ù…Ø§Ù† ÙŠÙˆÙ†Ø§ÙŠØªØ¯": "Manchester United",
        "Ø§Ù„ÙŠÙˆÙ†Ø§ÙŠØªØ¯": "Manchester United",
        "Ø§Ø±Ø³Ù†Ø§Ù„": "Arsenal",
        "Ø£Ø±Ø³Ù†Ø§Ù„": "Arsenal",
        "Ø§Ù„ØºØ§Ù†Ø±Ø²": "Arsenal",
        "Ø§Ù„Ù…Ø¯ÙØ¹Ø¬ÙŠØ©": "Arsenal",
        "ØªÙˆØªÙ†Ù‡Ø§Ù…": "Tottenham Hotspur",
        "ØªÙˆØªÙ†Ù‡Ø§Ù… Ù‡ÙˆØªØ³Ø¨ÙŠØ±": "Tottenham Hotspur",
        "Ø§Ù„Ø³Ø¨ÙŠØ±Ø²": "Tottenham Hotspur",
        "Ù†ÙŠÙˆÙƒØ§Ø³Ù„": "Newcastle United",
        "Ù†ÙŠÙˆÙƒØ§Ø³Ù„ ÙŠÙˆÙ†Ø§ÙŠØªØ¯": "Newcastle United",
        "Ø§Ø³ØªÙˆÙ† ÙÙŠÙ„Ø§": "Aston Villa",
        "Ø£Ø³ØªÙˆÙ† ÙÙŠÙ„Ø§": "Aston Villa",
        "ÙˆØ³Øª Ù‡Ø§Ù…": "West Ham United",
        "Ø¥ÙŠÙØ±ØªÙˆÙ†": "Everton",
        "Ø§ÙŠÙØ±ØªÙˆÙ†": "Everton",
        # La Liga
        "Ø±ÙŠØ§Ù„ Ù…Ø¯Ø±ÙŠØ¯": "Real Madrid",
        "Ø§Ù„Ø±ÙŠØ§Ù„": "Real Madrid",
        "Ø§Ù„Ù…ÙŠØ±Ù†ØºÙŠ": "Real Madrid",
        "Ø§Ù„Ù…Ù„ÙƒÙŠ": "Real Madrid",
        "Ø¨Ø±Ø´Ù„ÙˆÙ†Ø©": "Barcelona",
        "Ø¨Ø±Ø´Ù„ÙˆÙ†Ù‡": "Barcelona",
        "Ø§Ù„Ø¨Ø§Ø±Ø³Ø§": "Barcelona",
        "Ø§Ù„Ø¨Ø§Ø±Ø´Ø§": "Barcelona",
        "Ø§Ù„Ø¨Ù„ÙˆØºØ±Ø§Ù†Ø§": "Barcelona",
        "Ø§ØªÙ„ØªÙŠÙƒÙˆ Ù…Ø¯Ø±ÙŠØ¯": "Atletico Madrid",
        "Ø£ØªÙ„ØªÙŠÙƒÙˆ Ù…Ø¯Ø±ÙŠØ¯": "Atletico Madrid",
        "Ø§ØªÙ„ØªÙŠÙƒÙˆ": "Atletico Madrid",
        "Ø£ØªÙ„ØªÙŠÙƒÙˆ": "Atletico Madrid",
        "Ø§Ù„Ø±ÙˆØ®ÙŠØ¨Ù„Ø§Ù†ÙƒÙˆØ³": "Atletico Madrid",
        "Ø§Ø´Ø¨ÙŠÙ„ÙŠØ©": "Sevilla",
        "Ø¥Ø´Ø¨ÙŠÙ„ÙŠØ©": "Sevilla",
        "Ø§Ø´Ø¨ÙŠÙ„ÙŠÙ‡": "Sevilla",
        "Ø¥Ø´Ø¨ÙŠÙ„ÙŠÙ‡": "Sevilla",
        "Ø±ÙŠØ§Ù„ Ø³ÙˆØ³ÙŠØ¯Ø§Ø¯": "Real Sociedad",
        "Ø³ÙˆØ³ÙŠØ¯Ø§Ø¯": "Real Sociedad",
        "ÙÙŠØ§Ø±ÙŠØ§Ù„": "Villarreal",
        "Ø¬ÙŠØ±ÙˆÙ†Ø§": "Girona",
        "ÙØ§Ù„Ù†Ø³ÙŠØ§": "Valencia",
        "Ø§ØªÙ„ØªÙŠÙƒ Ø¨Ù„Ø¨Ø§Ùˆ": "Athletic Bilbao",
        "Ø£ØªÙ„ØªÙŠÙƒ Ø¨Ù„Ø¨Ø§Ùˆ": "Athletic Bilbao",
        # Serie A
        "Ø§Ù†ØªØ± Ù…ÙŠÙ„Ø§Ù†": "Inter Milan",
        "Ø¥Ù†ØªØ± Ù…ÙŠÙ„Ø§Ù†": "Inter Milan",
        "Ø§Ù„Ø§Ù†ØªØ±": "Inter Milan",
        "Ø§Ù„Ø¥Ù†ØªØ±": "Inter Milan",
        "Ø§Ù†ØªØ±": "Inter Milan",
        "Ø¥Ù†ØªØ±": "Inter Milan",
        "Ø§Ù„Ù†ÙŠØ±Ø§ØªØ²ÙˆØ±ÙŠ": "Inter Milan",
        "Ù…ÙŠÙ„Ø§Ù†": "AC Milan",
        "Ø§ÙŠ Ø³ÙŠ Ù…ÙŠÙ„Ø§Ù†": "AC Milan",
        "Ø¥ÙŠÙ‡ Ø³ÙŠ Ù…ÙŠÙ„Ø§Ù†": "AC Milan",
        "Ø§Ù„Ø±ÙˆØ³ÙˆÙ†ÙŠØ±ÙŠ": "AC Milan",
        "ÙŠÙˆÙÙ†ØªÙˆØ³": "Juventus",
        "Ø§Ù„ÙŠÙˆÙÙŠ": "Juventus",
        "Ø§Ù„Ø³ÙŠØ¯Ø© Ø§Ù„Ø¹Ø¬ÙˆØ²": "Juventus",
        "Ù†Ø§Ø¨ÙˆÙ„ÙŠ": "Napoli",
        "Ø±ÙˆÙ…Ø§": "AS Roma",
        "Ù„Ø§ØªØ³ÙŠÙˆ": "Lazio",
        "Ø§ØªØ§Ù„Ø§Ù†ØªØ§": "Atalanta",
        "Ø£ØªØ§Ù„Ø§Ù†ØªØ§": "Atalanta",
        "ÙÙŠÙˆØ±Ù†ØªÙŠÙ†Ø§": "Fiorentina",
        # Bundesliga
        "Ø¨Ø§ÙŠØ±Ù† Ù…ÙŠÙˆÙ†Ø®": "Bayern Munich",
        "Ø¨Ø§ÙŠØ±Ù† Ù…ÙŠÙˆÙ†ÙŠØ®": "Bayern Munich",
        "Ø§Ù„Ø¹Ù…Ù„Ø§Ù‚ Ø§Ù„Ø¨Ø§ÙØ§Ø±ÙŠ": "Bayern Munich",
        "Ø§Ù„Ø¨Ø§ÙØ§Ø±ÙŠ": "Bayern Munich",
        "Ø¨ÙˆØ±ÙˆØ³ÙŠØ§ Ø¯ÙˆØ±ØªÙ…ÙˆÙ†Ø¯": "Borussia Dortmund",
        "Ø¯ÙˆØ±ØªÙ…ÙˆÙ†Ø¯": "Borussia Dortmund",
        "Ø¨Ø§ÙŠØ± Ù„ÙŠÙØ±ÙƒÙˆØ²Ù†": "Bayer Leverkusen",
        "Ù„ÙŠÙØ±ÙƒÙˆØ²Ù†": "Bayer Leverkusen",
        "Ù„Ø§ÙŠØ¨Ø²ÙŠØ¬": "RB Leipzig",
        "Ù„Ø§ÙŠØ¨ØªØ²ÙŠØº": "RB Leipzig",
        "Ø§ÙŠÙ†ØªØ±Ø§Ø®Øª ÙØ±Ø§Ù†ÙƒÙÙˆØ±Øª": "Eintracht Frankfurt",
        # Ligue 1
        "Ø¨Ø§Ø±ÙŠØ³ Ø³Ø§Ù† Ø¬ÙŠØ±Ù…Ø§Ù†": "Paris Saint-Germain",
        "Ø¨Ø§Ø±ÙŠØ³ Ø³Ø§Ù†-Ø¬ÙŠØ±Ù…Ø§Ù†": "Paris Saint-Germain",
        "Ø¨ÙŠ Ø§Ø³ Ø¬ÙŠ": "Paris Saint-Germain",
        "Ø¨ÙŠ Ø¥Ø³ Ø¬ÙŠ": "Paris Saint-Germain",
        "Ø¨Ø§Ø±ÙŠØ³": "Paris Saint-Germain",
        "Ù…Ø§Ø±Ø³ÙŠÙ„ÙŠØ§": "Marseille",
        "Ø§ÙˆÙ„Ù…Ø¨ÙŠÙƒ Ù…Ø§Ø±Ø³ÙŠÙ„ÙŠØ§": "Marseille",
        "Ù…ÙˆÙ†Ø§ÙƒÙˆ": "Monaco",
        "Ù„ÙŠÙˆÙ†": "Lyon",
        "Ø§ÙˆÙ„Ù…Ø¨ÙŠÙƒ Ù„ÙŠÙˆÙ†": "Lyon",
        "Ù„ÙŠÙ„": "Lille",
        # MENA & Arab Leagues
        "Ø§Ù„Ø§Ù‡Ù„ÙŠ": "Al Ahly",
        "Ø§Ù„Ø£Ù‡Ù„ÙŠ": "Al Ahly",
        "Ø§Ù„Ø§Ù‡Ù„ÙŠ Ø§Ù„Ù…ØµØ±ÙŠ": "Al Ahly",
        "Ø§Ù„Ø£Ù‡Ù„ÙŠ Ø§Ù„Ù…ØµØ±ÙŠ": "Al Ahly",
        "Ø§Ù„Ù…Ø§Ø±Ø¯ Ø§Ù„Ø§Ø­Ù…Ø±": "Al Ahly",
        "Ø§Ù„Ø²Ù…Ø§Ù„Ùƒ": "Zamalek",
        "Ø§Ù„Ø²Ù…Ø§Ù„Ùƒ Ø§Ù„Ù…ØµØ±ÙŠ": "Zamalek",
        "Ø§Ù„ÙØ§Ø±Ø³ Ø§Ù„Ø§Ø¨ÙŠØ¶": "Zamalek",
        "Ø¨ÙŠØ±Ø§Ù…ÙŠØ¯Ø²": "Pyramids FC",
        "Ø§Ù„Ù‡Ù„Ø§Ù„": "Al Hilal",
        "Ø§Ù„Ù‡Ù„Ø§Ù„ Ø§Ù„Ø³Ø¹ÙˆØ¯ÙŠ": "Al Hilal",
        "Ø§Ù„Ø²Ø¹ÙŠÙ…": "Al Hilal",
        "Ø§Ù„Ù†ØµØ±": "Al Nassr",
        "Ø§Ù„Ù†ØµØ± Ø§Ù„Ø³Ø¹ÙˆØ¯ÙŠ": "Al Nassr",
        "Ø§Ù„Ø¹Ø§Ù„Ù…ÙŠ": "Al Nassr",
        "Ø§Ù„Ø§ØªØ­Ø§Ø¯": "Al Ittihad",
        "Ø§Ù„Ø§ØªØ­Ø§Ø¯ Ø§Ù„Ø³Ø¹ÙˆØ¯ÙŠ": "Al Ittihad",
        "Ø§Ù„Ø¹Ù…ÙŠØ¯": "Al Ittihad",
        "Ø§Ù„Ø§Ù‡Ù„ÙŠ Ø§Ù„Ø³Ø¹ÙˆØ¯ÙŠ": "Al-Ahli Saudi",
        "Ø§Ù„Ø£Ù‡Ù„ÙŠ Ø§Ù„Ø³Ø¹ÙˆØ¯ÙŠ": "Al-Ahli Saudi",
        "Ø§Ù„Ø±Ø§Ù‚ÙŠ": "Al-Ahli Saudi",
        "Ø§Ù„Ø´Ø¨Ø§Ø¨": "Al Shabab",
        "Ø§Ù„Ø´Ø¨Ø§Ø¨ Ø§Ù„Ø³Ø¹ÙˆØ¯ÙŠ": "Al Shabab",
        "Ø§Ù„Ø¹ÙŠÙ†": "Al Ain",
        "Ø§Ù„Ø¹ÙŠÙ† Ø§Ù„Ø§Ù…Ø§Ø±Ø§ØªÙŠ": "Al Ain",
        "Ø§Ù„Ø¹ÙŠÙ† Ø§Ù„Ø¥Ù…Ø§Ø±Ø§ØªÙŠ": "Al Ain",
        "Ø§Ù„ÙˆØ¯Ø§Ø¯": "Wydad AC",
        "Ø§Ù„ÙˆØ¯Ø§Ø¯ Ø§Ù„Ø±ÙŠØ§Ø¶ÙŠ": "Wydad AC",
        "Ø§Ù„ÙˆØ¯Ø§Ø¯ Ø§Ù„Ø¨ÙŠØ¶Ø§ÙˆÙŠ": "Wydad AC",
        "Ø§Ù„Ø±Ø¬Ø§Ø¡": "Raja CA",
        "Ø§Ù„Ø±Ø¬Ø§Ø¡ Ø§Ù„Ø±ÙŠØ§Ø¶ÙŠ": "Raja CA",
        "Ø§Ù„Ø±Ø¬Ø§Ø¡ Ø§Ù„Ø¨ÙŠØ¶Ø§ÙˆÙŠ": "Raja CA",
        "Ø§Ù„ØªØ±Ø¬ÙŠ": "EspÃ©rance de Tunis",
        "Ø§Ù„ØªØ±Ø¬ÙŠ Ø§Ù„ØªÙˆÙ†Ø³ÙŠ": "EspÃ©rance de Tunis",
        "Ø§Ù„ØªØ±Ø¬ÙŠ Ø§Ù„Ø±ÙŠØ§Ø¶ÙŠ": "EspÃ©rance de Tunis",
        "Ø§Ù„Ø¬ÙŠØ´ Ø§Ù„Ù…Ù„ÙƒÙŠ": "AS FAR",
        "Ø´Ø¨Ø§Ø¨ Ø¨Ù„ÙˆØ²Ø¯Ø§Ø¯": "CR Belouizdad",
        "Ù…ÙˆÙ„ÙˆØ¯ÙŠØ© Ø§Ù„Ø¬Ø²Ø§Ø¦Ø±": "MC Alger",
        "Ø§ØªØ­Ø§Ø¯ Ø§Ù„Ø¹Ø§ØµÙ…Ø©": "USM Alger",
    }

    @staticmethod
    def normalize_text(text: Optional[str]) -> str:
        """Strips tashkeel, standardizes alefs/yaas/taas, and removes generic prefixes."""
        if not text or not isinstance(text, str):
            return ""

        # Remove tashkeel diacritics
        tashkeel_pattern = re.compile(r"[\u064B-\u065F\u0670]")
        cleaned = tashkeel_pattern.sub("", text)

        # Normalize alefs with hamza / madda
        cleaned = re.sub(r"[Ø¥Ø£Ø¢Ù±]", "Ø§", cleaned)

        # Normalize yaa / alef maksura
        cleaned = re.sub(r"Ù‰", "ÙŠ", cleaned)

        # Strip leading "Ù†Ø§Ø¯ÙŠ " or "ÙØ±ÙŠÙ‚ " prefix
        cleaned = re.sub(r"^(Ù†Ø§Ø¯ÙŠ|ÙØ±ÙŠÙ‚)\s+", "", cleaned)

        # Normalize taa marbouta (Ø© -> Ù‡) for matching tolerance
        cleaned = re.sub(r"Ø©", "Ù‡", cleaned)

        # Normalize multiple spaces and strip
        return re.sub(r"\s+", " ", cleaned).strip()

    @classmethod
    def match_team(cls, arabic_name: Optional[str]) -> Optional[str]:
        """
        Matches an Arabic club name or alias to its standardized English team name.
        Returns None gracefully when unmatched.
        """
        if not arabic_name or not isinstance(arabic_name, str):
            return None

        norm = cls.normalize_text(arabic_name)
        if not norm:
            return None

        # Check custom registered aliases first
        if norm in cls._CUSTOM_ALIASES:
            return cls._CUSTOM_ALIASES[norm]

        # Check pre-compiled base aliases
        normalized_base = {
            cls.normalize_text(k): v for k, v in cls._BASE_ALIASES.items()
        }
        if norm in normalized_base:
            return normalized_base[norm]

        # Suffix strip fallback (e.g. "Ø§Ù„Ù…ØµØ±ÙŠ", "Ø§Ù„Ø³Ø¹ÙˆØ¯ÙŠ", "Ø§Ù„Ø±ÙŠØ§Ø¶ÙŠ")
        stripped_suffix = re.sub(r"\s+(Ø§Ù„Ù…ØµØ±ÙŠ|Ø§Ù„Ø³Ø¹ÙˆØ¯ÙŠ|Ø§Ù„Ø±ÙŠØ§Ø¶ÙŠ|Ø§Ù„Ø¨ÙŠØ¶Ø§ÙˆÙŠ|Ø§Ù„Ø§Ù…Ø§Ø±Ø§ØªÙŠ|Ø§Ù„ØªÙˆÙ†Ø³ÙŠ)$", "", norm)
        if stripped_suffix != norm and stripped_suffix in normalized_base:
            return normalized_base[stripped_suffix]

        return None

    @classmethod
    def register_alias(cls, arabic_name: str, standard_name: str) -> None:
        """Dynamically registers or updates a team alias mapping."""
        norm = cls.normalize_text(arabic_name)
        if norm:
            cls._CUSTOM_ALIASES[norm] = standard_name


class PriorityResolver:
    """
    Resolves live match data across 3 sources using priority rules:
      1. Admin Override (Highest priority: emergency scores, forced status, stream updates)
      2. Sports API / Open Backend (Scores, fixtures, lineups, elapsed match clock)
      3. Scraper Ingestion (Stream embed links, supplementary regional data)
    """

    @classmethod
    def resolve(
        cls,
        api_match: Optional[Match] = None,
        scraped_match: Optional[Match] = None,
        admin_override: Optional[Match] = None,
    ) -> Match:
        """
        Combines match data according to the strict priority rules.
        At least one source must be non-None.
        """
        if api_match is None and scraped_match is None and admin_override is None:
            raise ValueError("At least one match source must be provided")

        # Case 1: Admin Override is provided (Full precedence)
        if admin_override is not None:
            resolved = admin_override.model_copy(deep=True)
            resolved.is_admin_override = True

            # If admin provided stream servers, admin servers stand
            # If admin did not provide stream servers, inherit from API or Scraper
            if not resolved.stream_servers:
                candidate_servers: list[StreamServer] = []
                if api_match and api_match.stream_servers:
                    candidate_servers.extend(api_match.stream_servers)
                if scraped_match and scraped_match.stream_servers:
                    existing_urls = {s.url for s in candidate_servers}
                    for s in scraped_match.stream_servers:
                        if s.url not in existing_urls:
                            candidate_servers.append(s)
                            existing_urls.add(s.url)
                resolved.stream_servers = candidate_servers

            return resolved

        # Case 2: API Match + Optional Scraped Match (API precedence)
        if api_match is not None:
            resolved = api_match.model_copy(deep=True)
            resolved.is_admin_override = False

            # Merge stream servers from scraper if present
            merged_servers = list(resolved.stream_servers)
            if scraped_match and scraped_match.stream_servers:
                existing_urls = {s.url for s in merged_servers}
                for s in scraped_match.stream_servers:
                    if s.url not in existing_urls:
                        merged_servers.append(s)
                        existing_urls.add(s.url)
            resolved.stream_servers = merged_servers

            # Fill in optional broadcast metadata from scraper if missing in API
            if scraped_match:
                if resolved.channel is None and scraped_match.channel is not None:
                    resolved.channel = scraped_match.channel
                if resolved.commentator is None and scraped_match.commentator is not None:
                    resolved.commentator = scraped_match.commentator
                if resolved.stadium is None and scraped_match.stadium is not None:
                    resolved.stadium = scraped_match.stadium
                if resolved.referee is None and scraped_match.referee is not None:
                    resolved.referee = scraped_match.referee

            return resolved

        # Case 3: Scraped Match only (Fallback)
        # In this case, scraped_match is guaranteed not None
        assert scraped_match is not None
        resolved = scraped_match.model_copy(deep=True)
        resolved.is_admin_override = False
        return resolved


__all__ = [
    "TeamAliasMatcher",
    "PriorityResolver",
]

``n
## File: tests/live_score/test_resolver.py
`python
"""
Tests for Core Domain Models and Priority Ingestion Resolver.
Covers:
1. Domain model schemas and validation (Match, Team, League, StreamServer, MatchEvent, LineupPlayer, MatchDetail, MatchStatus)
2. Admin override taking full precedence over API and scraper updates.
3. API taking precedence over scraper updates when no admin override is present.
4. Stream servers from scraper being merged when API match has no stream servers.
5. TeamAliasMatcher resolving common Arabic names and handling unknown names gracefully.
"""

from datetime import datetime, timezone
from pathlib import Path
import sys

# Ensure src directory is in sys.path
_src_path = str(Path(__file__).resolve().parents[2] / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

import pytest

from live_score.domain.models import (
    Match,
    Team,
    League,
    StreamServer,
    MatchEvent,
    LineupPlayer,
    MatchDetail,
    MatchStatus,
)
from live_score.domain.resolver import (
    PriorityResolver,
    TeamAliasMatcher,
)


@pytest.fixture
def sample_teams():
    home = Team(id="team_che", name_ar="ØªØ´ÙŠÙ„Ø³ÙŠ", name_en="Chelsea", logo_url="https://img.example/chelsea.png")
    away = Team(id="team_liv", name_ar="Ù„ÙŠÙØ±Ø¨ÙˆÙ„", name_en="Liverpool", logo_url="https://img.example/liverpool.png")
    return home, away


@pytest.fixture
def sample_league():
    return League(
        id="eng_pl",
        name_ar="Ø§Ù„Ø¯ÙˆØ±ÙŠ Ø§Ù„Ø¥Ù†Ø¬Ù„ÙŠØ²ÙŠ Ø§Ù„Ù…Ù…ØªØ§Ø²",
        name_en="Premier League",
        round="Ø§Ù„Ø¬ÙˆÙ„Ø© 12",
        logo_url="https://img.example/pl.png",
    )


def test_domain_models_creation(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    server = StreamServer(
        id="srv_1",
        server_name="Ø³ÙŠØ±ÙØ± 1 - Ù…ØªØ¹Ø¯Ø¯ Ø§Ù„Ø¬ÙˆØ¯Ø§Øª",
        url="https://stream.example/feed.m3u8",
        type="m3u8",
        is_active=True,
        quality="1080p",
    )

    match = Match(
        id="match_101",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.SCHEDULED,
        kickoff_time=kickoff,
        home_score=0,
        away_score=0,
        stream_servers=[server],
        channel="beIN Sports 1",
        commentator="Ø­ÙÙŠØ¸ Ø¯Ø±Ø§Ø¬ÙŠ",
        stadium="Stamford Bridge",
        referee="Michael Oliver",
    )

    assert match.id == "match_101"
    assert match.home_team.name_ar == "ØªØ´ÙŠÙ„Ø³ÙŠ"
    assert match.away_team.name_en == "Liverpool"
    assert match.status == MatchStatus.SCHEDULED
    assert len(match.stream_servers) == 1
    assert match.stream_servers[0].type == "m3u8"
    assert match.is_admin_override is False


def test_match_detail_with_lineup_and_events(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    match = Match(
        id="match_102",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=1,
        away_score=0,
        elapsed_time=24,
    )

    player = LineupPlayer(
        id="p_1",
        name="Cole Palmer",
        number=20,
        position="MF",
        is_starter=True,
        grid_position="3:2",
    )

    event = MatchEvent(
        id="ev_1",
        minute=24,
        type="goal",
        player_name="Cole Palmer",
        team_id="team_che",
        description_ar="Ù‡Ø¯Ù Ø³Ø¬Ù„Ù‡ ÙƒÙˆÙ„ Ø¨Ø§Ù„Ù…Ø± Ø¨Ø¹Ø¯ ØªÙ…Ø±ÙŠØ±Ø© Ù…ØªÙ‚Ù†Ø©",
    )

    detail = MatchDetail(
        match=match,
        home_lineup=[player],
        away_lineup=[],
        events=[event],
        stats={"possession": {"home": 58, "away": 42}},
    )

    assert detail.match.id == "match_102"
    assert detail.home_lineup[0].name == "Cole Palmer"
    assert detail.events[0].type == "goal"
    assert detail.stats["possession"]["home"] == 58


def test_priority_resolver_admin_overrides_api_and_scraper(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    # API says 1-0, 55th minute, IN_PLAY
    api_match = Match(
        id="match_100",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=1,
        away_score=0,
        elapsed_time=55,
        channel="beIN Sports 1",
    )

    # Scraper says 1-1, 56th minute
    scraped_server = StreamServer(
        server_name="Scraped Server 1",
        url="https://scraped.stream/live1",
        type="iframe",
    )
    scraped_match = Match(
        id="match_100",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=1,
        away_score=1,
        elapsed_time=56,
        stream_servers=[scraped_server],
    )

    # Admin emergency override says 2-0, FINISHED, custom stream server
    admin_server = StreamServer(
        server_name="Admin Verified Server",
        url="https://admin.stream/verified",
        type="m3u8",
    )
    admin_override = Match(
        id="match_100",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.FINISHED,
        kickoff_time=kickoff,
        home_score=2,
        away_score=0,
        elapsed_time=90,
        stream_servers=[admin_server],
        channel="beIN Sports 1 Premium",
        commentator="Ø¹ØµØ§Ù… Ø§Ù„Ø´ÙˆØ§Ù„ÙŠ",
        is_admin_override=True,
    )

    resolved = PriorityResolver.resolve(
        api_match=api_match,
        scraped_match=scraped_match,
        admin_override=admin_override,
    )

    assert resolved.home_score == 2
    assert resolved.away_score == 0
    assert resolved.status == MatchStatus.FINISHED
    assert resolved.is_admin_override is True
    assert resolved.channel == "beIN Sports 1 Premium"
    assert resolved.commentator == "Ø¹ØµØ§Ù… Ø§Ù„Ø´ÙˆØ§Ù„ÙŠ"
    assert len(resolved.stream_servers) == 1
    assert resolved.stream_servers[0].server_name == "Admin Verified Server"


def test_priority_resolver_api_takes_precedence_over_scraper(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    # API match has authoritative score and status
    api_match = Match(
        id="match_200",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=2,
        away_score=1,
        elapsed_time=75,
        channel="beIN Sports 2",
    )

    # Scraped match has stale or conflicting score
    scraped_match = Match(
        id="match_200",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=1,
        away_score=1,
        elapsed_time=70,
    )

    resolved = PriorityResolver.resolve(
        api_match=api_match,
        scraped_match=scraped_match,
        admin_override=None,
    )

    assert resolved.home_score == 2
    assert resolved.away_score == 1
    assert resolved.elapsed_time == 75
    assert resolved.channel == "beIN Sports 2"
    assert resolved.is_admin_override is False


def test_priority_resolver_merges_stream_servers_when_api_has_none(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    # API match has no stream servers
    api_match = Match(
        id="match_300",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=0,
        away_score=0,
        stream_servers=[],
    )

    scraped_server1 = StreamServer(
        server_name="Ø³ÙŠØ±ÙØ± 1 - Ø³Ø±ÙŠØ¹",
        url="https://live.kora.com/s1.m3u8",
        type="m3u8",
    )
    scraped_server2 = StreamServer(
        server_name="Ø³ÙŠØ±ÙØ± 2 - Ù‡Ø§ØªÙ",
        url="https://live.kora.com/s2_embed",
        type="iframe",
    )
    scraped_match = Match(
        id="match_300",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=0,
        away_score=0,
        stream_servers=[scraped_server1, scraped_server2],
    )

    resolved = PriorityResolver.resolve(
        api_match=api_match,
        scraped_match=scraped_match,
        admin_override=None,
    )

    assert len(resolved.stream_servers) == 2
    assert resolved.stream_servers[0].server_name == "Ø³ÙŠØ±ÙØ± 1 - Ø³Ø±ÙŠØ¹"
    assert resolved.stream_servers[1].server_name == "Ø³ÙŠØ±ÙØ± 2 - Ù‡Ø§ØªÙ"


def test_priority_resolver_merges_unique_servers_when_both_have_streams(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    api_server = StreamServer(
        server_name="API Official Stream",
        url="https://api.streams/official.m3u8",
        type="m3u8",
    )
    api_match = Match(
        id="match_350",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=1,
        away_score=1,
        stream_servers=[api_server],
    )

    scraped_duplicate = StreamServer(
        server_name="Duplicate Official Stream",
        url="https://api.streams/official.m3u8",
        type="m3u8",
    )
    scraped_new = StreamServer(
        server_name="Scraped Backup Server",
        url="https://scraper.streams/backup.m3u8",
        type="m3u8",
    )
    scraped_match = Match(
        id="match_350",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=1,
        away_score=1,
        stream_servers=[scraped_duplicate, scraped_new],
    )

    resolved = PriorityResolver.resolve(
        api_match=api_match,
        scraped_match=scraped_match,
        admin_override=None,
    )

    # Should keep official stream first, and add the distinct backup stream (ignoring exact URL duplicate)
    assert len(resolved.stream_servers) == 2
    urls = [s.url for s in resolved.stream_servers]
    assert urls == ["https://api.streams/official.m3u8", "https://scraper.streams/backup.m3u8"]


def test_priority_resolver_single_source_fallbacks(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    single_match = Match(
        id="match_400",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.SCHEDULED,
        kickoff_time=kickoff,
    )

    # API only
    res_api = PriorityResolver.resolve(api_match=single_match, scraped_match=None, admin_override=None)
    assert res_api.id == "match_400"
    assert res_api.is_admin_override is False

    # Scraped only
    res_scraped = PriorityResolver.resolve(api_match=None, scraped_match=single_match, admin_override=None)
    assert res_scraped.id == "match_400"
    assert res_scraped.is_admin_override is False

    # Admin only
    res_admin = PriorityResolver.resolve(api_match=None, scraped_match=None, admin_override=single_match)
    assert res_admin.id == "match_400"
    assert res_admin.is_admin_override is True

    # None provided
    with pytest.raises(ValueError, match="At least one match source must be provided"):
        PriorityResolver.resolve(api_match=None, scraped_match=None, admin_override=None)


def test_team_alias_matcher_common_teams():
    assert TeamAliasMatcher.match_team("ØªØ´ÙŠÙ„Ø³ÙŠ") == "Chelsea"
    assert TeamAliasMatcher.match_team("Ø±ÙŠØ§Ù„ Ù…Ø¯Ø±ÙŠØ¯") == "Real Madrid"
    assert TeamAliasMatcher.match_team("Ù„ÙŠÙØ±Ø¨ÙˆÙ„") == "Liverpool"
    assert TeamAliasMatcher.match_team("Ø¨Ø§Ø±ÙŠØ³ Ø³Ø§Ù† Ø¬ÙŠØ±Ù…Ø§Ù†") == "Paris Saint-Germain"
    assert TeamAliasMatcher.match_team("Ù…Ø§Ù†Ø´Ø³ØªØ± Ø³ÙŠØªÙŠ") == "Manchester City"
    assert TeamAliasMatcher.match_team("Ù…Ø§Ù†Ø´Ø³ØªØ± ÙŠÙˆÙ†Ø§ÙŠØªØ¯") == "Manchester United"
    assert TeamAliasMatcher.match_team("Ø¨Ø±Ø´Ù„ÙˆÙ†Ø©") == "Barcelona"
    assert TeamAliasMatcher.match_team("Ø¨Ø§ÙŠØ±Ù† Ù…ÙŠÙˆÙ†Ø®") == "Bayern Munich"
    assert TeamAliasMatcher.match_team("Ø§Ù„Ø£Ù‡Ù„ÙŠ") == "Al Ahly"
    assert TeamAliasMatcher.match_team("Ø§Ù„Ø²Ù…Ø§Ù„Ùƒ") == "Zamalek"
    assert TeamAliasMatcher.match_team("Ø§Ù„Ù‡Ù„Ø§Ù„") == "Al Hilal"
    assert TeamAliasMatcher.match_team("Ø§Ù„Ù†ØµØ±") == "Al Nassr"


def test_team_alias_matcher_normalization_and_diacritics():
    # Diacritics (tashkeel)
    assert TeamAliasMatcher.match_team("Ø±ÙÙŠÙŽØ§Ù„ Ù…ÙŽØ¯Ù’Ø±ÙÙŠØ¯") == "Real Madrid"
    assert TeamAliasMatcher.match_team("Ù„ÙÙŠÙÙŽØ±Ù’Ø¨ÙÙˆÙ„") == "Liverpool"

    # Leading / trailing whitespace
    assert TeamAliasMatcher.match_team("  ØªØ´ÙŠÙ„Ø³ÙŠ  ") == "Chelsea"

    # Prefix stripping (Ù†Ø§Ø¯ÙŠ, ÙØ±ÙŠÙ‚)
    assert TeamAliasMatcher.match_team("Ù†Ø§Ø¯ÙŠ ØªØ´ÙŠÙ„Ø³ÙŠ") == "Chelsea"
    assert TeamAliasMatcher.match_team("ÙØ±ÙŠÙ‚ Ø¨Ø±Ø´Ù„ÙˆÙ†Ø©") == "Barcelona"
    assert TeamAliasMatcher.match_team("Ù†Ø§Ø¯ÙŠ Ø§Ù„Ø£Ù‡Ù„ÙŠ") == "Al Ahly"

    # Alef variations (Ø£, Ø¥, Ø¢, Ø§)
    assert TeamAliasMatcher.match_team("Ø§Ø±Ø³Ù†Ø§Ù„") == "Arsenal"
    assert TeamAliasMatcher.match_team("Ø£Ø±Ø³Ù†Ø§Ù„") == "Arsenal"
    assert TeamAliasMatcher.match_team("Ø§Ù†ØªØ± Ù…ÙŠÙ„Ø§Ù†") == "Inter Milan"
    assert TeamAliasMatcher.match_team("Ø¥Ù†ØªØ± Ù…ÙŠÙ„Ø§Ù†") == "Inter Milan"


def test_team_alias_matcher_unknown_and_empty_graceful():
    assert TeamAliasMatcher.match_team("ÙØ±ÙŠÙ‚ Ù…Ø¬Ù‡ÙˆÙ„ ØºÙŠØ± Ù…Ø³Ø¬Ù„") is None
    assert TeamAliasMatcher.match_team("") is None
    assert TeamAliasMatcher.match_team("   ") is None
    assert TeamAliasMatcher.match_team(None) is None


def test_team_alias_matcher_custom_registration():
    matcher = TeamAliasMatcher()
    matcher.register_alias("ÙØ±ÙŠÙ‚ Ø§Ù„Ø³Ø­Ø§Ø¨ Ø§Ù„ØªØ¬Ø±ÙŠØ¨ÙŠ", "Cloud FC")
    assert TeamAliasMatcher.match_team("ÙØ±ÙŠÙ‚ Ø§Ù„Ø³Ø­Ø§Ø¨ Ø§Ù„ØªØ¬Ø±ÙŠØ¨ÙŠ") == "Cloud FC"


def test_match_status_enum_values():
    expected_statuses = {
        "SCHEDULED",
        "IN_PLAY",
        "HALFTIME",
        "EXTRA_TIME",
        "PENALTIES",
        "FINISHED",
        "POSTPONED",
    }
    actual_statuses = {status.value for status in MatchStatus}
    assert actual_statuses == expected_statuses


def test_match_is_live_property(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    def make_match(status: MatchStatus) -> Match:
        return Match(
            id="test_live",
            home_team=home,
            away_team=away,
            league=sample_league,
            status=status,
            kickoff_time=kickoff,
        )

    # Live statuses
    assert make_match(MatchStatus.IN_PLAY).is_live is True
    assert make_match(MatchStatus.HALFTIME).is_live is True
    assert make_match(MatchStatus.EXTRA_TIME).is_live is True
    assert make_match(MatchStatus.PENALTIES).is_live is True

    # Non-live statuses
    assert make_match(MatchStatus.SCHEDULED).is_live is False
    assert make_match(MatchStatus.FINISHED).is_live is False
    assert make_match(MatchStatus.POSTPONED).is_live is False


def test_priority_resolver_admin_preserves_streams_when_admin_servers_empty(sample_teams, sample_league):
    home, away = sample_teams
    kickoff = datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)

    scraper_stream = StreamServer(
        server_name="Existing Scraper Stream",
        url="https://live.stream/channel1.m3u8",
        type="m3u8",
    )
    scraped_match = Match(
        id="match_500",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=0,
        away_score=0,
        stream_servers=[scraper_stream],
    )

    # Admin emergency score override without changing stream URLs
    admin_override = Match(
        id="match_500",
        home_team=home,
        away_team=away,
        league=sample_league,
        status=MatchStatus.IN_PLAY,
        kickoff_time=kickoff,
        home_score=1,
        away_score=0,
        stream_servers=[],  # Admin didn't alter streams
        is_admin_override=True,
    )

    resolved = PriorityResolver.resolve(
        api_match=None,
        scraped_match=scraped_match,
        admin_override=admin_override,
    )

    assert resolved.home_score == 1
    assert resolved.is_admin_override is True
    assert len(resolved.stream_servers) == 1
    assert resolved.stream_servers[0].server_name == "Existing Scraper Stream"


``n

