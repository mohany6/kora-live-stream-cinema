"""
TTL cache and lazy hydration layer for live upstream fixtures.

The public API is refreshed in bulk (one fixture window across the league
catalog) while match summaries are fetched only when a user opens a match.
Upstream failures never blank the schedule: stale live data is kept, and the
demo matchday is used only when no live snapshot has ever been published.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Protocol

from live_score.adapters.livescore_v2 import FixtureRef, LiveScoreV2Error
from live_score.adapters.scraper_adapter import PortalScraperAdapter
from live_score.domain.models import Match, MatchDetail, StreamServer
from live_score.domain.resolver import (
    ChannelStreamMapper,
    PriorityResolver,
    should_hydrate_channel_stream,
)

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 25.0
DEFAULT_DETAIL_TTL_SECONDS = 25.0
DEFAULT_WINDOW_DAYS = 2
DEFAULT_RETRY_AFTER_FAILURE = 45.0
DEFAULT_SNAPSHOT_MAX_AGE_HOURS = 36.0
#: Reject a refresh smaller than this fraction of the previous slate unless the
#: provider explicitly says the missing leagues failed.
DEFAULT_MIN_SLATE_RATIO = 0.75
DEFAULT_MIN_GUARDED_SLATE = 8


class FixturesClient(Protocol):
    """The slice of :class:`LiveScoreV2Client` the catalog depends on."""

    def fetch_window(
        self,
        start: Any,
        end: Any,
        leagues: Optional[Iterable[str]] = None,
    ) -> list[Any]: ...

    def fetch_detail(
        self,
        league_slug: str,
        event_id: str,
        match: Any = None,
    ) -> Any: ...


@dataclass
class _CachedDetail:
    detail: Any
    fetched_at: datetime


def _utc_iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    clean = value.strip()
    if clean.endswith("Z"):
        clean = clean[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(clean)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class LiveFixturesCatalog:
    """Refresh fixtures on a TTL and hydrate match details on demand."""

    def __init__(
        self,
        client: FixturesClient,
        leagues: Optional[Iterable[str]] = None,
        *,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        detail_ttl_seconds: float = DEFAULT_DETAIL_TTL_SECONDS,
        window_days: int = DEFAULT_WINDOW_DAYS,
        retry_after_failure: float = DEFAULT_RETRY_AFTER_FAILURE,
        demo_loader: Optional[Callable[[datetime], list[Any]]] = None,
        background_refresh: bool = True,
        snapshot_path: Optional[str] = None,
        snapshot_max_age_hours: float = DEFAULT_SNAPSHOT_MAX_AGE_HOURS,
        min_slate_ratio: float = DEFAULT_MIN_SLATE_RATIO,
        min_guarded_slate: int = DEFAULT_MIN_GUARDED_SLATE,
        clock: Optional[Callable[[], datetime]] = None,
        scraper: Optional[Any] = None,
        scraper_ttl_seconds: float = 120.0,
    ) -> None:
        self._client = client
        self._leagues = tuple(
            leagues or getattr(client, "leagues", None) or ()
        )
        self._ttl = max(1.0, float(ttl_seconds))
        self._detail_ttl = max(1.0, float(detail_ttl_seconds))
        self._window_days = max(0, int(window_days))
        self._retry_after_failure = max(1.0, float(retry_after_failure))
        self._demo_loader = demo_loader
        self._background_refresh = background_refresh
        self._snapshot_path = Path(snapshot_path) if snapshot_path else None
        self._snapshot_max_age = timedelta(hours=max(0.0, float(snapshot_max_age_hours)))
        self._min_slate_ratio = min(1.0, max(0.0, float(min_slate_ratio)))
        self._min_guarded_slate = max(1, int(min_guarded_slate))
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._scraper = scraper
        self._scraper_ttl = max(1.0, float(scraper_ttl_seconds))
        self._scraped_cache: dict[str, tuple[datetime, list[Any]]] = {}

        self._fixtures: dict[str, Any] = {}
        self._refs: dict[str, FixtureRef] = {}
        self._details: dict[str, _CachedDetail] = {}
        self._last_refresh: Optional[datetime] = None
        self._last_attempt: Optional[datetime] = None
        self._last_error: Optional[str] = None
        self._data_source = "live"
        self._loaded_from_snapshot = False

        self._state_lock = threading.RLock()
        self._refresh_lock = threading.Lock()
        self._load_snapshot()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def refresh(self, now: Optional[datetime] = None, force: bool = False) -> None:
        now = now or self._clock()
        if not self._needs_refresh(now, force):
            return
        with self._state_lock:
            has_snapshot = bool(self._fixtures)
        if self._background_refresh and has_snapshot and not force:
            # Serve the cached slate immediately and refresh behind the request.
            threading.Thread(
                target=self._refresh_now,
                args=(now, False),
                name="live-score-refresh",
                daemon=True,
            ).start()
            return
        self._refresh_now(now, force)

    def _refresh_now(self, now: datetime, force: bool) -> None:
        # Only one thread refreshes; everyone else immediately reads whatever
        # is already cached rather than queueing behind a slow upstream.
        if not self._refresh_lock.acquire(blocking=False):
            return
        try:
            if not self._needs_refresh(now, force):
                return
            self._last_attempt = now
            start = now.date() - timedelta(days=self._window_days)
            end = now.date() + timedelta(days=self._window_days)
            try:
                matches = self._client.fetch_window(start, end, self._leagues or None)
            except Exception as exc:  # noqa: BLE001 - upstream boundary
                self._handle_failure(now, exc)
                return

            if matches:
                merged = self._merge_partial_slate(matches)
                self._publish_live(merged, now)
                self._save_snapshot(merged, now)
            elif not self._fixtures:
                self._publish_demo(now)
                logger.warning("Live scores: empty upstream window; using demo matchday")
            else:
                self._last_refresh = now
                logger.warning("Live scores: empty upstream window; keeping cached slate")
        finally:
            self._refresh_lock.release()

    def fixtures(self, now: Optional[datetime] = None) -> list[Any]:
        now = now or self._clock()
        self.refresh(now)
        with self._state_lock:
            details = list(self._fixtures.values())
        for d in details:
            if hasattr(d, "match"):
                self._enrich_broadcast_meta(d.match, now)
        return details

    def _enrich_broadcast_meta(self, match: Match, now: datetime) -> None:
        try:
            h = match.home_team.name_en or match.home_team.name_ar or ""
            a = match.away_team.name_en or match.away_team.name_ar or ""
            meta = PortalScraperAdapter.fetch_broadcast_meta(h, a, now=now)
            if meta and meta.get("channel"):
                match.channel = meta["channel"]
                if meta.get("commentator"):
                    match.commentator = meta["commentator"]
                if not match.stream_servers and should_hydrate_channel_stream(match, now=now):
                    match.stream_servers = ChannelStreamMapper.get_servers(meta["channel"])
        except Exception:
            pass

    def seed_demo(self, now: Optional[datetime] = None) -> None:
        """Show the demo matchday immediately while live data loads."""
        now = now or self._clock()
        with self._state_lock:
            if self._fixtures:
                return
        self._publish_demo(now, mark_refreshed=False)

    def fixture_map(self, now: Optional[datetime] = None) -> dict[str, Any]:
        now = now or self._clock()
        self.refresh(now)
        with self._state_lock:
            return dict(self._fixtures)

    def get_detail(self, match_id: str, now: Optional[datetime] = None) -> Optional[Any]:
        now = now or self._clock()
        self.refresh(now)

        with self._state_lock:
            base = self._fixtures.get(match_id)
            ref = self._refs.get(match_id)
            cached = self._details.get(match_id)

        if base is None:
            return None
        if cached is not None and self._is_fresh(cached.fetched_at, now, self._detail_ttl):
            return self._apply_scraper(self._overlay_match(cached.detail, base.match), now)
        if ref is None:
            return self._apply_scraper(base, now)

        try:
            detail = self._client.fetch_detail(ref.league_slug, ref.event_id, base.match)
        except Exception as exc:  # noqa: BLE001 - summary is best effort
            logger.warning(
                "Live scores: detail fetch failed for %s (%s)", match_id, exc
            )
            if cached is not None:
                return self._apply_scraper(self._overlay_match(cached.detail, base.match), now)
            return self._apply_scraper(base, now)

        with self._state_lock:
            self._details[match_id] = _CachedDetail(detail=detail, fetched_at=now)
        res = self._apply_scraper(detail, now)
        if res is not None and hasattr(res, "match"):
            self._enrich_broadcast_meta(res.match, now)
        return res

    def _apply_scraper(self, detail: Optional[Any], now: datetime) -> Optional[Any]:
        if self._scraper is None or detail is None:
            return detail

        match_id = detail.match.id
        with self._state_lock:
            cached_scraped = self._scraped_cache.get(match_id)

        if cached_scraped is not None and self._is_fresh(cached_scraped[0], now, self._scraper_ttl):
            scraped_servers = cached_scraped[1]
        else:
            scraped_servers = []
            try:
                home_name = detail.match.home_team.name_ar or detail.match.home_team.name_en or ""
                away_name = detail.match.away_team.name_ar or detail.match.away_team.name_en or ""
                scraped_servers = self._scraper.fetch_stream_servers(home_name, away_name) or []
            except Exception as exc:  # noqa: BLE001 - scraping is best effort
                logger.warning("Live scores: scraper failed for %s (%s)", match_id, exc)
            with self._state_lock:
                self._scraped_cache[match_id] = (now, scraped_servers)

        if scraped_servers:
            updated = detail.model_copy(deep=True)
            scraped_match = updated.match.model_copy(update={"stream_servers": scraped_servers})
            updated.match = PriorityResolver.resolve(api_match=updated.match, scraped_match=scraped_match)
            return updated
        return detail

    def status(self) -> dict[str, Any]:
        with self._state_lock:
            return {
                "data_source": self._data_source,
                "matches": len(self._fixtures),
                "leagues": len(self._leagues),
                "last_refresh": _utc_iso(self._last_refresh),
                "last_error": self._last_error,
            }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    @staticmethod
    def _is_fresh(then: datetime, now: datetime, ttl: float) -> bool:
        return (now - then).total_seconds() < ttl

    def _needs_refresh(self, now: datetime, force: bool) -> bool:
        if force:
            return True
        with self._state_lock:
            if self._last_refresh and self._is_fresh(self._last_refresh, now, self._ttl):
                return False
            if (
                self._last_error
                and self._last_attempt
                and self._is_fresh(self._last_attempt, now, self._retry_after_failure)
            ):
                return False
        return True

    def _merge_partial_slate(self, matches: list[Any]) -> list[Any]:
        """Keep stale fixtures when a refresh only covers part of the catalog.

        Providers report the leagues that failed in the latest window.  Their
        previously published fixtures are retained so a match that was already
        on the schedule never disappears (and 404s) because of a transient
        upstream failure.  When a provider reports no league failures, a
        drastic slate shrink keeps fixtures from leagues that vanished, which
        covers older providers and degenerate empty responses.
        """
        with self._state_lock:
            previous = [detail.match for detail in self._fixtures.values()]

        if not previous:
            return matches

        fresh_ids = {match.id for match in matches}
        fresh_leagues = self._league_counts(matches)
        previous_leagues = self._league_counts(previous)

        failed = frozenset(
            getattr(self._client, "last_window_failed", None) or frozenset()
        )
        keep_leagues = set(failed)

        drastically_smaller = len(previous) >= self._min_guarded_slate and (
            len(matches) < len(previous) * self._min_slate_ratio
        )
        if drastically_smaller:
            keep_leagues.update(set(previous_leagues) - set(fresh_leagues))

        if not keep_leagues:
            return matches

        merged = list(matches)
        kept = 0
        for old in previous:
            if old.id in fresh_ids:
                continue
            ref = FixtureRef.parse(getattr(old, "source_ref", None))
            if ref is None or ref.league_slug not in keep_leagues:
                continue
            merged.append(old)
            fresh_ids.add(old.id)
            kept += 1

        if kept:
            logger.warning(
                "Live scores: refresh returned %d fixtures (previous %d); kept "
                "%d stale fixtures from %d unavailable leagues",
                len(matches),
                len(previous),
                kept,
                len(keep_leagues),
            )
        return merged

    @staticmethod
    def _league_counts(matches: Iterable[Any]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for match in matches:
            ref = FixtureRef.parse(getattr(match, "source_ref", None))
            if ref is not None:
                counts[ref.league_slug] = counts.get(ref.league_slug, 0) + 1
        return counts

    def _publish_live(self, matches: list[Any], now: datetime) -> None:
        fixtures = {match.id: MatchDetail(match=match) for match in matches}
        refs: dict[str, FixtureRef] = {}
        for match in matches:
            ref = FixtureRef.parse(match.source_ref)
            if ref is not None:
                refs[match.id] = ref
        with self._state_lock:
            self._fixtures = fixtures
            self._refs = refs
            self._details = {
                key: cached for key, cached in self._details.items() if key in fixtures
            }
            self._last_refresh = now
            self._last_error = None
            self._data_source = "live"
            self._loaded_from_snapshot = False

    def _save_snapshot(self, matches: list[Any], now: datetime) -> None:
        """Persist the last good fixture slate so restarts survive outages."""
        if self._snapshot_path is None:
            return
        payload = {
            "saved_at": _utc_iso(now),
            "matches": [match.model_dump(mode="json") for match in matches],
        }
        try:
            self._snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self._snapshot_path.with_name(
                self._snapshot_path.name + ".tmp"
            )
            temp_path.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
            os.replace(temp_path, self._snapshot_path)
        except (OSError, TypeError, ValueError) as exc:  # pragma: no cover - disk boundary
            logger.warning("Live scores: could not write snapshot (%s)", exc)

    def _load_snapshot(self) -> None:
        """Load a recent live snapshot before the first upstream request."""
        if self._snapshot_path is None or not self._snapshot_path.exists():
            return
        try:
            payload = json.loads(self._snapshot_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning("Live scores: snapshot unreadable (%s)", exc)
            return

        saved_at = _parse_iso(payload.get("saved_at"))
        if saved_at is None:
            return
        age = self._clock() - saved_at
        if age > self._snapshot_max_age:
            logger.info("Live scores: snapshot is stale (%s); ignoring", age)
            return

        matches: list[Match] = []
        for item in payload.get("matches") or []:
            try:
                m = Match.model_validate(item)
                ref = FixtureRef.parse(m.source_ref)
                if ref is not None and self._leagues and ref.league_slug not in self._leagues:
                    continue
                matches.append(m)
            except Exception:  # noqa: BLE001 - skip corrupt rows
                continue
        if not matches:
            return

        refs: dict[str, FixtureRef] = {}
        for match in matches:
            ref = FixtureRef.parse(match.source_ref)
            if ref is not None:
                refs[match.id] = ref
        with self._state_lock:
            self._fixtures = {
                match.id: MatchDetail(match=match) for match in matches
            }
            self._refs = refs
            self._last_refresh = saved_at
            self._data_source = "live"
            self._loaded_from_snapshot = True
        logger.info(
            "Live scores: loaded %d fixtures from snapshot saved at %s",
            len(matches),
            _utc_iso(saved_at),
        )

    def _publish_demo(self, now: datetime, *, mark_refreshed: bool = True) -> None:
        if self._demo_loader is None:
            return
        details = self._demo_loader(now)
        with self._state_lock:
            self._fixtures = {detail.match.id: detail for detail in details}
            self._refs = {}
            self._details = {}
            if mark_refreshed:
                self._last_refresh = now
            else:
                self._last_refresh = None
            self._data_source = "demo"

    def _handle_failure(self, now: datetime, exc: Exception) -> None:
        message = str(exc) or exc.__class__.__name__
        with self._state_lock:
            self._last_error = message
        if self._fixtures:
            logger.warning("Live scores: refresh failed (%s); serving cached slate", message)
            return
        logger.warning("Live scores: refresh failed (%s); using demo matchday", message)
        self._publish_demo(now)
        with self._state_lock:
            self._data_source = "demo"

    @staticmethod
    def _overlay_match(detail: Any, match: Any) -> Any:
        """Return a cached detail with the freshest scores/status attached, preserving venue/officials."""
        updated = detail.model_copy(deep=True)
        new_match = match.model_copy(deep=True)
        if new_match.stadium is None and detail.match.stadium is not None:
            new_match.stadium = detail.match.stadium
        if new_match.referee is None and detail.match.referee is not None:
            new_match.referee = detail.match.referee
        if new_match.channel is None and detail.match.channel is not None:
            new_match.channel = detail.match.channel
        if new_match.commentator is None and detail.match.commentator is not None:
            new_match.commentator = detail.match.commentator
        if not new_match.stream_servers and detail.match.stream_servers:
            new_match.stream_servers = detail.match.stream_servers
        updated.match = new_match
        return updated


__all__ = [
    "LiveFixturesCatalog",
    "LiveScoreV2Error",
]
