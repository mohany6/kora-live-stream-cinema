"""Pydantic request/response schemas for the live score public and admin APIs."""

from __future__ import annotations

from typing import Any, Literal, Optional
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator

from live_score.domain.models import MatchStatus


# ---------------------------------------------------------------------------
# Shared read models
# ---------------------------------------------------------------------------

class TeamOut(BaseModel):
    id: Optional[str] = None
    name_ar: str
    name_en: Optional[str] = None
    logo_url: Optional[str] = None


class LeagueOut(BaseModel):
    id: Optional[str] = None
    name_ar: str
    name_en: Optional[str] = None
    round: Optional[str] = None
    logo_url: Optional[str] = None


class StreamServerOut(BaseModel):
    id: str
    server_name: str
    url: str
    type: Literal["iframe", "m3u8"] = "iframe"
    is_active: bool = True
    quality: Optional[str] = None
    sandbox: Optional[str] = None


class MatchCardOut(BaseModel):
    """Option A schedule card contract consumed by the RTL MatchCard component."""

    id: str
    home_team: TeamOut
    away_team: TeamOut
    league: LeagueOut
    status: str
    status_label_ar: str
    kickoff_time_utc: str
    kickoff_time_local: str
    kickoff_date_local: str
    home_score: int
    away_score: int
    elapsed_time: Optional[int] = None
    live_minute_label: Optional[str] = None
    countdown_seconds: Optional[int] = None
    competition_subtitle: str
    is_admin_override: bool = False
    channel: Optional[str] = None
    commentator: Optional[str] = None
    stadium: Optional[str] = None
    referee: Optional[str] = None
    has_stream: bool = False


class TodayMatchesOut(BaseModel):
    date: str
    timezone: str
    timezone_label_ar: str
    matches: list[MatchCardOut]


class LineupPlayerOut(BaseModel):
    id: Optional[str] = None
    name: str
    number: int
    position: str
    is_starter: bool = True
    grid_position: Optional[str] = None


class MatchEventOut(BaseModel):
    id: Optional[str] = None
    minute: int
    type: str
    player_name: str
    team_id: Optional[str] = None
    description_ar: Optional[str] = None


class StatItemOut(BaseModel):
    key: str
    label_ar: str
    home: float
    away: float
    unit: str = ""


class StandingRowOut(BaseModel):
    position: int
    team_name_ar: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0
    is_home: bool = False
    is_away: bool = False


class MatchDetailOut(BaseModel):
    match: MatchCardOut
    servers: list[StreamServerOut]
    home_lineup: list[LineupPlayerOut]
    away_lineup: list[LineupPlayerOut]
    home_formation: Optional[str] = None
    away_formation: Optional[str] = None
    events: list[MatchEventOut]
    stats: list[StatItemOut]
    standings: list[StandingRowOut]


# ---------------------------------------------------------------------------
# Admin write models
# ---------------------------------------------------------------------------

class StreamServerIn(BaseModel):
    id: Optional[str] = None
    server_name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=8, max_length=2048)
    type: Literal["iframe", "m3u8"] = "iframe"
    is_active: bool = True
    quality: Optional[str] = Field(default=None, max_length=40)
    sandbox: Optional[str] = Field(
        default="allow-scripts allow-same-origin allow-presentation",
        max_length=200,
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        clean = value.strip()
        parsed = urlsplit(clean)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("stream URL must be an absolute http(s) URL")
        return clean


class StreamMutationOut(BaseModel):
    match_id: str
    servers: list[StreamServerOut]


class AdminOverrideIn(BaseModel):
    home_score: Optional[int] = Field(default=None, ge=0, le=99)
    away_score: Optional[int] = Field(default=None, ge=0, le=99)
    status: Optional[MatchStatus] = None
    elapsed_time: Optional[int] = Field(default=None, ge=0, le=130)
    channel: Optional[str] = Field(default=None, max_length=120)
    commentator: Optional[str] = Field(default=None, max_length=120)
    stadium: Optional[str] = Field(default=None, max_length=160)
    referee: Optional[str] = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "AdminOverrideIn":
        if not self.model_dump(exclude_none=True):
            raise ValueError("at least one override field is required")
        return self


class AdminMatchOut(BaseModel):
    match: MatchCardOut
    servers: list[StreamServerOut]
    admin_server_ids: list[str]
    override: Optional[dict[str, Any]] = None


class AdminMatchesOut(BaseModel):
    date: Optional[str] = None
    timezone: str
    timezone_label_ar: str
    matches: list[AdminMatchOut]


# ---------------------------------------------------------------------------
# Ads models
# ---------------------------------------------------------------------------

AdPosition = Literal["header_top", "in_feed", "player_top", "player_bottom", "sticky_bottom"]
AdType = Literal["image_banner", "custom_html"]
TargetDevice = Literal["all", "desktop", "mobile"]


class AdIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    position: AdPosition = "header_top"
    ad_type: AdType = "image_banner"
    image_url: Optional[str] = Field(default="", max_length=2048)
    link_url: Optional[str] = Field(default="", max_length=2048)
    html_code: Optional[str] = Field(default="", max_length=20000)
    target_device: TargetDevice = "all"
    is_active: bool = True
    priority: int = Field(default=0, ge=0, le=1000)


class AdUpdateIn(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    position: Optional[AdPosition] = None
    ad_type: Optional[AdType] = None
    image_url: Optional[str] = Field(default=None, max_length=2048)
    link_url: Optional[str] = Field(default=None, max_length=2048)
    html_code: Optional[str] = Field(default=None, max_length=20000)
    target_device: Optional[TargetDevice] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(default=None, ge=0, le=1000)


class AdOut(BaseModel):
    id: str
    title: str
    position: str
    ad_type: str
    image_url: str = ""
    link_url: str = ""
    html_code: str = ""
    target_device: str = "all"
    is_active: bool = True
    priority: int = 0
    created_at: str
    updated_at: str


class AdsListOut(BaseModel):
    ads: list[AdOut]


# ---------------------------------------------------------------------------
# Analytics models
# ---------------------------------------------------------------------------

class TrackVisitIn(BaseModel):
    visitor_id: Optional[str] = Field(default=None, max_length=120)
    path: str = Field(default="/", max_length=255)
    device: Literal["desktop", "mobile", "tablet"] = "desktop"
    referrer: Optional[str] = Field(default="", max_length=1024)


class AnalyticsTimeseriesPoint(BaseModel):
    label: str
    visits: int
    uniques: int
    date: Optional[str] = None
    hour: Optional[int] = None
    month: Optional[str] = None


class AnalyticsStatsOut(BaseModel):
    period: str
    summary: dict[str, int]
    chart_data: list[AnalyticsTimeseriesPoint]
    device_stats: dict[str, int]
    top_pages: list[dict[str, Any]]



