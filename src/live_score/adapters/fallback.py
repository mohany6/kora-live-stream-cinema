"""Automatic failover between the hosted API and ESPN's public API.

The hosted ``worldcup26.ir`` service occasionally loses its upstream feed and
returns HTTP 500 for every route.  When that happens we switch to ESPN's public
soccer API (the same data source the hosted service wraps) for a cooldown
period, then retry the primary.  Both clients expose the same fixture/detail
interface, so the catalog is unaware of the switch.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Iterable, Optional

from live_score.adapters.livescore_v2 import LiveScoreV2Error

logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_SECONDS = 300.0


class FallbackSoccerClient:
    """Try the primary provider, then a secondary one for a cooldown window."""

    def __init__(
        self,
        primary: Any,
        secondary: Any,
        *,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self.primary = primary
        self.secondary = secondary
        self.cooldown_seconds = max(1.0, float(cooldown_seconds))
        self._clock = clock or time.monotonic
        self._primary_down_until = 0.0
        self.leagues = tuple(getattr(primary, "leagues", ()) or ())

    # ------------------------------------------------------------------
    # Provider selection
    # ------------------------------------------------------------------
    def _primary_ready(self) -> bool:
        return self._clock() >= self._primary_down_until

    def _mark_primary_down(self, exc: Exception) -> None:
        self._primary_down_until = self._clock() + self.cooldown_seconds
        logger.warning(
            "Live scores: primary provider failed (%s); using fallback for %.0fs",
            exc,
            self.cooldown_seconds,
        )

    @staticmethod
    def _combined_error(primary: Exception, secondary: Exception) -> LiveScoreV2Error:
        return LiveScoreV2Error(
            f"primary and fallback providers failed: {primary}; {secondary}"
        )

    # ------------------------------------------------------------------
    # Catalog interface
    # ------------------------------------------------------------------
    def fetch_window(
        self,
        start: Any,
        end: Any,
        leagues: Optional[Iterable[str]] = None,
    ) -> list[Any]:
        primary_error: Optional[Exception] = None
        if self._primary_ready():
            try:
                return self.primary.fetch_window(start, end, leagues)
            except Exception as exc:  # noqa: BLE001 - provider boundary
                primary_error = exc
                self._mark_primary_down(exc)

        try:
            return self.secondary.fetch_window(start, end, leagues)
        except Exception as exc:  # noqa: BLE001 - provider boundary
            if primary_error is not None:
                raise self._combined_error(primary_error, exc) from exc
            raise

    def fetch_detail(
        self,
        league_slug: str,
        event_id: str,
        match: Any = None,
    ) -> Any:
        primary_error: Optional[Exception] = None
        if self._primary_ready():
            try:
                return self.primary.fetch_detail(league_slug, event_id, match)
            except Exception as exc:  # noqa: BLE001 - provider boundary
                primary_error = exc
                self._mark_primary_down(exc)

        try:
            return self.secondary.fetch_detail(league_slug, event_id, match)
        except Exception as exc:  # noqa: BLE001 - provider boundary
            if primary_error is not None:
                raise self._combined_error(primary_error, exc) from exc
            raise


__all__ = ["DEFAULT_COOLDOWN_SECONDS", "FallbackSoccerClient"]
