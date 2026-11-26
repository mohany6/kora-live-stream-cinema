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
    sandbox: Optional[str] = "allow-scripts allow-same-origin allow-presentation"


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
    #: Upstream locator ("league_slug:event_id") used for lazy detail hydration.
    source_ref: Optional[str] = None

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
    standings: list[dict[str, Any]] = Field(default_factory=list)
    home_formation: Optional[str] = None
    away_formation: Optional[str] = None


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
