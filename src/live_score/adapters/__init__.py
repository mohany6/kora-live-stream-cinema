"""
Upstream Ingestion Adapters:
- LiveScoreFootballClient: Ingestion client for rezarahiminia/livescoreFootball REST API.
- LiveScoreV2Client: Hosted livescoreFootball public API (scoreboards, summaries, standings).
- PortalScraperAdapter: HTML scraper stub for live stream embeds, server buttons, and HLS.
"""

from live_score.adapters.fallback import FallbackSoccerClient
from live_score.adapters.livescore_client import LiveScoreFootballClient
from live_score.adapters.livescore_v2 import (
    DEFAULT_BASE_URL,
    ESPN_CORE_BASE,
    ESPN_SITE_BASE,
    EspnSoccerClient,
    FixtureRef,
    LiveScoreV2Client,
    LiveScoreV2Error,
)
from live_score.adapters.scraper_adapter import PortalScraperAdapter

__all__ = [
    "LiveScoreFootballClient",
    "LiveScoreV2Client",
    "LiveScoreV2Error",
    "EspnSoccerClient",
    "FallbackSoccerClient",
    "FixtureRef",
    "DEFAULT_BASE_URL",
    "ESPN_SITE_BASE",
    "ESPN_CORE_BASE",
    "PortalScraperAdapter",
]
