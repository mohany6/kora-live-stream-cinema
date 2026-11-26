"""SQLite-backed store for admin overrides and admin-managed stream servers.

Overrides are stored as JSON payloads so the schema can grow without migrations.
They are re-applied on every read, guaranteeing that an automated API/scraper
sync can never overwrite an admin emergency decision.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlsplit


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AdminStore:
    def __init__(
        self,
        db_path: str = ":memory:",
        batch_size: int = 100,
        flush_interval: float = 5.0,
    ) -> None:
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        # Configure high-concurrency pragmas
        if db_path != ":memory:":
            self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._conn.execute("PRAGMA busy_timeout=5000;")

        self._create_schema()

        # Telemetry batch buffer
        self._visit_queue: list[tuple[Any, ...]] = []
        self._queue_lock = threading.Lock()
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._stop_flusher = threading.Event()
        self._flusher_thread = threading.Thread(target=self._flusher_loop, daemon=True)
        self._flusher_thread.start()

    def _flusher_loop(self) -> None:
        while not self._stop_flusher.wait(self._flush_interval):
            self.flush_visits()

    def flush_visits(self) -> None:
        with self._queue_lock:
            if not self._visit_queue:
                return
            items = list(self._visit_queue)
            self._visit_queue.clear()

        with self._lock, self._conn:
            self._conn.executemany(
                """
                INSERT INTO site_visits (timestamp, date, hour, visitor_id, path, device, referrer)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                items,
            )

    def close(self) -> None:
        self._stop_flusher.set()
        if hasattr(self, "_flusher_thread") and self._flusher_thread.is_alive():
            self._flusher_thread.join(timeout=2.0)
        self.flush_visits()
        with self._lock:
            self._conn.close()

    def _create_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_overrides (
                    match_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            # Check if legacy admin_streams with single-column PK exists
            table_info = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='admin_streams'"
            ).fetchone()
            if table_info:
                cols = self._conn.execute("PRAGMA table_info(admin_streams)").fetchall()
                pk_cols = [c[1] for c in cols if c[5] > 0]
                if pk_cols == ["server_id"]:
                    self._conn.execute(
                        """
                        CREATE TABLE admin_streams_new (
                            server_id TEXT NOT NULL,
                            match_id TEXT NOT NULL,
                            payload_json TEXT NOT NULL,
                            sort_order INTEGER NOT NULL,
                            updated_at TEXT NOT NULL,
                            PRIMARY KEY (match_id, server_id)
                        )
                        """
                    )
                    self._conn.execute(
                        """
                        INSERT INTO admin_streams_new (server_id, match_id, payload_json, sort_order, updated_at)
                        SELECT server_id, match_id, payload_json, sort_order, updated_at FROM admin_streams
                        """
                    )
                    self._conn.execute("DROP TABLE admin_streams")
                    self._conn.execute("ALTER TABLE admin_streams_new RENAME TO admin_streams")

            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_streams (
                    server_id TEXT NOT NULL,
                    match_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    sort_order INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (match_id, server_id)
                )
                """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_admin_streams_match
                ON admin_streams(match_id, sort_order)
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ads (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    position TEXT NOT NULL,
                    ad_type TEXT NOT NULL,
                    image_url TEXT DEFAULT '',
                    link_url TEXT DEFAULT '',
                    html_code TEXT DEFAULT '',
                    target_device TEXT DEFAULT 'all',
                    is_active INTEGER DEFAULT 1,
                    priority INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ads_pos_active
                ON ads(position, is_active, priority DESC)
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS site_visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    date TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    visitor_id TEXT NOT NULL,
                    path TEXT DEFAULT '/',
                    device TEXT DEFAULT 'desktop',
                    referrer TEXT DEFAULT ''
                )
                """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_visits_date ON site_visits(date)
                """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_visits_timestamp ON site_visits(timestamp)
                """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_visits_visitor ON site_visits(visitor_id)
                """
            )

    def _seed_default_ads(self) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        default_ads = [
            (
                "adsterra-header-728",
                "Adsterra Header Banner 728x90",
                "header_top",
                "custom_html",
                "",
                "",
                """<div style="display:flex;justify-content:center;margin:10px 0;"><script>atOptions={'key':'6703ea03ffb309455182c593d4e6ea81','format':'iframe','height':90,'width':728,'params':{}};</script><script data-cfasync="false" src="https://czernik.org/22/6703ea03ffb309455182c593d4e6ea81"></script></div>""",
                "desktop",
                1,
                100,
                now_iso,
                now_iso,
            ),
            (
                "adsterra-header-320",
                "Adsterra Header Banner 320x50",
                "header_top",
                "custom_html",
                "",
                "",
                """<div style="display:flex;justify-content:center;margin:10px 0;"><script>atOptions={'key':'1cdf29d3af257663a92ffa6b5207a68a','format':'iframe','height':50,'width':320,'params':{}};</script><script data-cfasync="false" src="https://czernik.org/22/1cdf29d3af257663a92ffa6b5207a68a"></script></div>""",
                "mobile",
                1,
                100,
                now_iso,
                now_iso,
            ),
            (
                "adsterra-player-top",
                "Adsterra Player Top Banner",
                "player_top",
                "custom_html",
                "",
                "",
                """<div style="display:flex;justify-content:center;margin:10px 0;"><script>atOptions={'key':'6703ea03ffb309455182c593d4e6ea81','format':'iframe','height':90,'width':728,'params':{}};</script><script data-cfasync="false" src="https://czernik.org/22/6703ea03ffb309455182c593d4e6ea81"></script></div>""",
                "all",
                1,
                100,
                now_iso,
                now_iso,
            ),
            (
                "adsterra-player-bottom-native",
                "Adsterra Native Banner",
                "player_bottom",
                "custom_html",
                "",
                "",
                """<div style="margin:15px 0;text-align:center;"><script async="async" fetchpriority="high" data-cfasync="false" src="https://czernik.org/21/f1180bd1a9f13152d2247022e3f6f1b0"></script><div id="container-f1180bd1a9f13152d2247022e3f6f1b0"></div></div>""",
                "all",
                1,
                100,
                now_iso,
                now_iso,
            ),
            (
                "adsterra-sticky-smartlink",
                "Adsterra Sticky Bottom Smartlink",
                "sticky_bottom",
                "custom_html",
                "",
                "",
                """<div style="display:flex;align-items:center;justify-content:space-between;width:100%;max-width:650px;background:#0f172a;border:1px solid #334155;border-radius:12px;padding:8px 16px;color:#f8fafc;font-size:12px;font-weight:bold;"><span>🔥 سيرفر البث المباشر الاحتياطي فائق السرعة بدون تقطيع</span><a href="https://budgetezy.org/4/ae626546295ba9dbdec2ea24a521084c" target="_blank" rel="noopener noreferrer" style="background:#10b981;color:#ffffff;padding:6px 16px;border-radius:20px;text-decoration:none;font-weight:bold;">شاهد فوراً ⚡</a></div>""",
                "all",
                1,
                100,
                now_iso,
                now_iso,
            ),
        ]
        self._conn.executemany(
            """
            INSERT OR IGNORE INTO ads (id, title, position, ad_type, image_url, link_url, html_code, target_device, is_active, priority, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            default_ads,
        )

    # -- overrides ---------------------------------------------------------

    def get_override(self, match_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload_json FROM admin_overrides WHERE match_id = ?",
                (match_id,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def set_override(self, match_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(payload, ensure_ascii=False)
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO admin_overrides (match_id, payload_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(match_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (match_id, encoded, _utc_now_iso()),
            )
        return payload

    def delete_override(self, match_id: str) -> bool:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "DELETE FROM admin_overrides WHERE match_id = ?",
                (match_id,),
            )
        return cursor.rowcount > 0

    # -- streams -----------------------------------------------------------

    def list_streams(self, match_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT payload_json FROM admin_streams
                WHERE match_id = ?
                ORDER BY sort_order ASC, updated_at ASC
                """,
                (match_id,),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def upsert_stream(
        self,
        match_id: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        """Insert or update a stream; returns (payload, created)."""
        clean_url = payload["url"].strip()
        target_id: Optional[str] = payload.get("id")

        with self._lock:
            rows = self._conn.execute(
                "SELECT server_id, payload_json, sort_order FROM admin_streams WHERE match_id = ?",
                (match_id,),
            ).fetchall()

            existing_sort_order: Optional[int] = None
            for row in rows:
                existing_payload = json.loads(row["payload_json"])
                same_id = target_id and row["server_id"] == target_id
                same_url = normalize_stream_url(existing_payload.get("url", "")) == normalize_stream_url(clean_url)
                if same_id or same_url:
                    target_id = row["server_id"]
                    existing_sort_order = row["sort_order"]
                    break

            payload["url"] = clean_url
            created = existing_sort_order is None
            if created:
                target_id = target_id or uuid.uuid4().hex
                sort_order = (
                    self._conn.execute(
                        "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM admin_streams WHERE match_id = ?",
                        (match_id,),
                    ).fetchone()[0]
                )
            else:
                sort_order = existing_sort_order

            payload["id"] = target_id
            encoded = json.dumps(payload, ensure_ascii=False)

            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO admin_streams (server_id, match_id, payload_json, sort_order, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(match_id, server_id) DO UPDATE SET
                        payload_json = excluded.payload_json,
                        sort_order = excluded.sort_order,
                        updated_at = excluded.updated_at
                    """,
                    (target_id, match_id, encoded, sort_order, _utc_now_iso()),
                )

        return payload, created

    def delete_stream(self, match_id: str, server_id: str) -> bool:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "DELETE FROM admin_streams WHERE match_id = ? AND server_id = ?",
                (match_id, server_id),
            )
        return cursor.rowcount > 0

    # -- ads ---------------------------------------------------------------

    @staticmethod
    def _row_to_ad_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "title": str(row["title"]),
            "position": str(row["position"]),
            "ad_type": str(row["ad_type"]),
            "image_url": str(row["image_url"] or ""),
            "link_url": str(row["link_url"] or ""),
            "html_code": str(row["html_code"] or ""),
            "target_device": str(row["target_device"] or "all"),
            "is_active": bool(row["is_active"]),
            "priority": int(row["priority"] or 0),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    def upsert_ad(self, ad_dict: dict[str, Any]) -> dict[str, Any]:
        ad_id = str(ad_dict.get("id") or uuid.uuid4().hex)
        now = _utc_now_iso()
        title = str(ad_dict.get("title", "")).strip()
        position = str(ad_dict.get("position", "header_top")).strip()
        ad_type = str(ad_dict.get("ad_type", "image_banner")).strip()
        image_url = str(ad_dict.get("image_url", "")).strip()
        link_url = str(ad_dict.get("link_url", "")).strip()
        html_code = str(ad_dict.get("html_code", ""))
        target_device = str(ad_dict.get("target_device", "all")).strip().lower()
        is_active = 1 if ad_dict.get("is_active", True) else 0
        priority = int(ad_dict.get("priority", 0))

        with self._lock, self._conn:
            existing = self._conn.execute(
                "SELECT created_at FROM ads WHERE id = ?",
                (ad_id,),
            ).fetchone()

            created_at = existing["created_at"] if existing else (ad_dict.get("created_at") or now)

            self._conn.execute(
                """
                INSERT INTO ads (
                    id, title, position, ad_type, image_url, link_url, html_code,
                    target_device, is_active, priority, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    position = excluded.position,
                    ad_type = excluded.ad_type,
                    image_url = excluded.image_url,
                    link_url = excluded.link_url,
                    html_code = excluded.html_code,
                    target_device = excluded.target_device,
                    is_active = excluded.is_active,
                    priority = excluded.priority,
                    updated_at = excluded.updated_at
                """,
                (
                    ad_id,
                    title,
                    position,
                    ad_type,
                    image_url,
                    link_url,
                    html_code,
                    target_device,
                    is_active,
                    priority,
                    created_at,
                    now,
                ),
            )

        ad = self.get_ad(ad_id)
        assert ad is not None
        return ad

    def get_ad(self, ad_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM ads WHERE id = ?",
                (ad_id,),
            ).fetchone()
        return self._row_to_ad_dict(row) if row else None

    def list_ads(
        self,
        position: Optional[str] = None,
        active_only: bool = False,
        device: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM ads WHERE 1=1"
        params: list[Any] = []

        if position:
            query += " AND position = ?"
            params.append(position)

        if active_only:
            query += " AND is_active = 1"

        if device:
            query += " AND target_device IN ('all', ?)"
            params.append(device.lower())

        query += " ORDER BY priority DESC, created_at DESC"

        with self._lock:
            rows = self._conn.execute(query, tuple(params)).fetchall()
        return [self._row_to_ad_dict(row) for row in rows]

    def delete_ad(self, ad_id: str) -> bool:
        with self._lock, self._conn:
            cursor = self._conn.execute("DELETE FROM ads WHERE id = ?", (ad_id,))
        return cursor.rowcount > 0

    def toggle_ad_active(self, ad_id: str) -> Optional[bool]:
        now = _utc_now_iso()
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT is_active FROM ads WHERE id = ?",
                (ad_id,),
            ).fetchone()
            if not row:
                return None
            new_active = 0 if row["is_active"] == 1 else 1
            self._conn.execute(
                "UPDATE ads SET is_active = ?, updated_at = ? WHERE id = ?",
                (new_active, now, ad_id),
            )
            return bool(new_active)

    # -- site analytics ----------------------------------------------------

    def record_visit(
        self,
        visitor_id: str,
        path: str = "/",
        device: str = "desktop",
        referrer: str = "",
    ) -> None:
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        date_str = now.strftime("%Y-%m-%d")
        hour = now.hour
        clean_dev = device.lower() if device in {"desktop", "mobile", "tablet"} else "desktop"

        entry = (now_iso, date_str, hour, visitor_id, path, clean_dev, referrer)
        should_flush = False
        with self._queue_lock:
            self._visit_queue.append(entry)
            if len(self._visit_queue) >= self._batch_size:
                should_flush = True

        if should_flush:
            self.flush_visits()

    def get_analytics_summary(self) -> dict[str, Any]:
        self.flush_visits()
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        week_start_str = (now - timedelta(days=6)).strftime("%Y-%m-%d")
        month_start_str = (now - timedelta(days=29)).strftime("%Y-%m-%d")
        year_start_str = (now - timedelta(days=364)).strftime("%Y-%m-%d")

        with self._lock:
            # Today
            today_row = self._conn.execute(
                """
                SELECT COUNT(*) as visits, COUNT(DISTINCT visitor_id) as uniques
                FROM site_visits WHERE date = ?
                """,
                (today_str,),
            ).fetchone()

            # Week
            week_row = self._conn.execute(
                """
                SELECT COUNT(*) as visits, COUNT(DISTINCT visitor_id) as uniques
                FROM site_visits WHERE date >= ?
                """,
                (week_start_str,),
            ).fetchone()

            # Month
            month_row = self._conn.execute(
                """
                SELECT COUNT(*) as visits, COUNT(DISTINCT visitor_id) as uniques
                FROM site_visits WHERE date >= ?
                """,
                (month_start_str,),
            ).fetchone()

            # Year
            year_row = self._conn.execute(
                """
                SELECT COUNT(*) as visits, COUNT(DISTINCT visitor_id) as uniques
                FROM site_visits WHERE date >= ?
                """,
                (year_start_str,),
            ).fetchone()

            # Total all time
            total_row = self._conn.execute(
                """
                SELECT COUNT(*) as visits, COUNT(DISTINCT visitor_id) as uniques
                FROM site_visits
                """
            ).fetchone()

        return {
            "today_visits": int(today_row["visits"] or 0),
            "today_uniques": int(today_row["uniques"] or 0),
            "week_visits": int(week_row["visits"] or 0),
            "week_uniques": int(week_row["uniques"] or 0),
            "month_visits": int(month_row["visits"] or 0),
            "month_uniques": int(month_row["uniques"] or 0),
            "year_visits": int(year_row["visits"] or 0),
            "year_uniques": int(year_row["uniques"] or 0),
            "total_visits": int(total_row["visits"] or 0),
            "total_uniques": int(total_row["uniques"] or 0),
        }

    def get_analytics_timeseries(self, period: str = "week") -> list[dict[str, Any]]:
        self.flush_visits()
        now = datetime.now(timezone.utc)
        period = period.lower()

        if period == "day":
            today_str = now.strftime("%Y-%m-%d")
            with self._lock:
                rows = self._conn.execute(
                    """
                    SELECT hour, COUNT(*) as visits, COUNT(DISTINCT visitor_id) as uniques
                    FROM site_visits
                    WHERE date = ?
                    GROUP BY hour
                    """,
                    (today_str,),
                ).fetchall()
            hour_map = {row["hour"]: (row["visits"], row["uniques"]) for row in rows}
            result = []
            for h in range(24):
                v, u = hour_map.get(h, (0, 0))
                result.append({
                    "hour": h,
                    "label": f"{h:02d}:00",
                    "visits": int(v),
                    "uniques": int(u),
                })
            return result

        elif period == "week":
            result = []
            with self._lock:
                for i in range(6, -1, -1):
                    day = now - timedelta(days=i)
                    day_str = day.strftime("%Y-%m-%d")
                    row = self._conn.execute(
                        """
                        SELECT COUNT(*) as visits, COUNT(DISTINCT visitor_id) as uniques
                        FROM site_visits
                        WHERE date = ?
                        """,
                        (day_str,),
                    ).fetchone()
                    result.append({
                        "date": day_str,
                        "label": day.strftime("%d/%m"),
                        "visits": int(row["visits"] or 0),
                        "uniques": int(row["uniques"] or 0),
                    })
            return result

        elif period == "month":
            result = []
            with self._lock:
                for i in range(29, -1, -1):
                    day = now - timedelta(days=i)
                    day_str = day.strftime("%Y-%m-%d")
                    row = self._conn.execute(
                        """
                        SELECT COUNT(*) as visits, COUNT(DISTINCT visitor_id) as uniques
                        FROM site_visits
                        WHERE date = ?
                        """,
                        (day_str,),
                    ).fetchone()
                    result.append({
                        "date": day_str,
                        "label": day.strftime("%d/%m"),
                        "visits": int(row["visits"] or 0),
                        "uniques": int(row["uniques"] or 0),
                    })
            return result

        elif period == "year":
            result = []
            with self._lock:
                curr_year = now.year
                curr_month = now.month
                months = []
                for _ in range(12):
                    months.append((curr_year, curr_month))
                    curr_month -= 1
                    if curr_month == 0:
                        curr_month = 12
                        curr_year -= 1
                months.reverse()

                for y, m in months:
                    m_prefix = f"{y:04d}-{m:02d}"
                    row = self._conn.execute(
                        """
                        SELECT COUNT(*) as visits, COUNT(DISTINCT visitor_id) as uniques
                        FROM site_visits
                        WHERE date LIKE ?
                        """,
                        (f"{m_prefix}%",),
                    ).fetchone()
                    result.append({
                        "month": m_prefix,
                        "label": f"{m:02d}/{str(y)[2:]}",
                        "visits": int(row["visits"] or 0),
                        "uniques": int(row["uniques"] or 0),
                    })
            return result

        return []

    def get_device_breakdown(self, period: str = "week") -> dict[str, int]:
        self.flush_visits()
        now = datetime.now(timezone.utc)
        if period == "day":
            since = now.strftime("%Y-%m-%d")
        elif period == "month":
            since = (now - timedelta(days=29)).strftime("%Y-%m-%d")
        elif period == "year":
            since = (now - timedelta(days=364)).strftime("%Y-%m-%d")
        else:
            since = (now - timedelta(days=6)).strftime("%Y-%m-%d")

        with self._lock:
            rows = self._conn.execute(
                """
                SELECT device, COUNT(*) as count
                FROM site_visits
                WHERE date >= ?
                GROUP BY device
                """,
                (since,),
            ).fetchall()
        counts = {row["device"]: int(row["count"]) for row in rows}
        return {
            "mobile": counts.get("mobile", 0),
            "desktop": counts.get("desktop", 0),
            "tablet": counts.get("tablet", 0),
        }

    def get_top_pages(self, period: str = "week", limit: int = 5) -> list[dict[str, Any]]:
        self.flush_visits()
        now = datetime.now(timezone.utc)
        if period == "day":
            since = now.strftime("%Y-%m-%d")
        elif period == "month":
            since = (now - timedelta(days=29)).strftime("%Y-%m-%d")
        elif period == "year":
            since = (now - timedelta(days=364)).strftime("%Y-%m-%d")
        else:
            since = (now - timedelta(days=6)).strftime("%Y-%m-%d")

        with self._lock:
            rows = self._conn.execute(
                """
                SELECT path, COUNT(*) as visits, COUNT(DISTINCT visitor_id) as uniques
                FROM site_visits
                WHERE date >= ?
                GROUP BY path
                ORDER BY visits DESC
                LIMIT ?
                """,
                (since, limit),
            ).fetchall()
        return [
            {
                "path": str(row["path"]),
                "visits": int(row["visits"]),
                "uniques": int(row["uniques"]),
            }
            for row in rows
        ]


def normalize_stream_url(url: str) -> str:
    """Compare stream URLs without fragment noise or a trailing slash."""
    parsed = urlsplit(url.strip())
    path = parsed.path.rstrip("/") or ""
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}?{parsed.query}"


_normalized_url = normalize_stream_url

__all__ = [
    "AdminStore",
    "normalize_stream_url",
]
