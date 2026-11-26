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
import ssl
import threading
import urllib.request
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote, urljoin

import requests

from live_score.domain.models import StreamServer
from live_score.domain.resolver import TeamAliasMatcher

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
        if "youtube.com" in combined or "youtu.be" in combined or "يوتيوب" in combined:
            return "youtube"

        # Multi-quality check
        if "متعدد" in combined or "multi" in combined or "auto" in combined:
            return "multiquality"

        # HD check
        if "hd" in combined or "1080" in combined or "720" in combined or "عالية" in combined:
            return "hd"

        # SD / Mobile check
        if "sd" in combined or "ضعيف" in combined or "هاتف" in combined or "هواتف" in combined or "mobile" in combined or "360" in combined or "480" in combined:
            return "sd"

        return "multiquality"

    @staticmethod
    def _is_stream_href(matched_tag: str, text: str, url: str) -> bool:
        """Determines whether a generic link points to a stream embed or server."""
        low_url = url.lower()
        stream_url_hints = (
            "embed", "player", "stream", "live", "watch", "channel",
            ".m3u8", "youtube.com", "youtu.be", "video"
        )
        if any(hint in low_url for hint in stream_url_hints):
            return True
        low_tag_and_text = f"{matched_tag} {text}".lower()
        stream_text_hints = (
            "server", "stream", "player", "quality", "embed", "m3u8",
            "سيرفر", "بث", "مشاهدة", "جودة", "يوتيوب", "hd", "sd"
        )
        return any(hint in low_tag_and_text for hint in stream_text_hints)

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
            data_attr_url = (
                match.group("data_url")
                or match.group("data_src")
                or match.group("data_embed")
                or match.group("data_stream")
            )
            url = data_attr_url or match.group("href")
            if not url or url.startswith("#") or url.startswith("javascript:"):
                continue

            raw_text = match.group("text") or ""
            if not data_attr_url and match.group("href"):
                if not self._is_stream_href(matched_tag_full, raw_text, url):
                    continue

            # Check explicit data-quality
            quality_match = re.search(r"data-quality=[\"']([^\"']+)[\"']", matched_tag_full, re.IGNORECASE)
            explicit_q = quality_match.group(1) if quality_match else None

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
            name = btn_text if btn_text else f"سيرفر {len(servers) + 1}"
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
                    server_name=f"بث مباشر HLS {len(servers) + 1}",
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
                    server_name=f"سيرفر {len(servers) + 1}",
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

    _KOORA_CACHE_TTL: float = 60.0
    _koora_last_fetched: Optional[datetime] = None
    _koora_cache: dict[tuple[str, str], dict[str, str]] = {}
    _koora_lock: threading.Lock = threading.Lock()

    @classmethod
    def fetch_broadcast_meta(
        cls,
        home_name: str,
        away_name: str,
        now: Optional[datetime] = None,
    ) -> Optional[dict[str, str]]:
        """
        Fetches live channel and commentator metadata from kooralive.la
        with a thread-safe 60-second in-memory cache.
        """
        now = now or datetime.now(timezone.utc)
        with cls._koora_lock:
            needs_refresh = (
                cls._koora_last_fetched is None
                or (now - cls._koora_last_fetched).total_seconds() > cls._KOORA_CACHE_TTL
            )
            if needs_refresh:
                try:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    req = urllib.request.Request(
                        "https://kooralive.la/",
                        headers={
                            "User-Agent": (
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                            )
                        },
                    )
                    with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
                        html_text = resp.read().decode("utf-8", errors="ignore")

                    blocks = html_text.split('<div class="AY_Match ')
                    fresh_cache: dict[tuple[str, str], dict[str, str]] = {}
                    for b in blocks[1:]:
                        tms = re.findall(r"<div class=['\"]TM_Name['\"]>([^<]+)</div>", b)
                        if len(tms) < 2:
                            continue
                        h_ar, a_ar = tms[0].strip(), tms[1].strip()
                        info_items = re.findall(r"<li><span>([^<]+)</span></li>", b)
                        ch = info_items[0].strip() if len(info_items) > 0 else None
                        comm = info_items[1].strip() if len(info_items) > 1 else None
                        link_m = re.search(r'<a\s+href=["\'](https?://[^"\']+)["\']', b)
                        link = link_m.group(1) if link_m else None

                        h_std = TeamAliasMatcher.match_team(h_ar) or h_ar
                        a_std = TeamAliasMatcher.match_team(a_ar) or a_ar

                        # Store under standardized English names
                        key_std = tuple(sorted([h_std.lower(), a_std.lower()]))
                        fresh_cache[key_std] = {"channel": ch, "commentator": comm, "link": link}
                        # Also store under raw Arabic names
                        key_ar = tuple(sorted([h_ar.lower(), a_ar.lower()]))
                        fresh_cache[key_ar] = {"channel": ch, "commentator": comm, "link": link}

                    cls._koora_cache = fresh_cache
                    cls._koora_last_fetched = now
                except Exception as exc:
                    logger.warning("Failed to refresh KooraLive broadcast metadata: %s", exc)

        # Lookup
        h_norm = (TeamAliasMatcher.match_team(home_name) or home_name).lower()
        a_norm = (TeamAliasMatcher.match_team(away_name) or away_name).lower()

        key = tuple(sorted([h_norm, a_norm]))
        if key in cls._koora_cache:
            return cls._koora_cache[key]

        raw_key = tuple(sorted([home_name.lower(), away_name.lower()]))
        return cls._koora_cache.get(raw_key)
