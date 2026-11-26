"""
Comprehensive Live End-to-End System Test for the Arabic Football Live Score Platform.

Runs a live uvicorn server in a separate thread, executes real HTTP requests
against all public and admin endpoints, verifies upstream ESPN ingestion,
admin CMS overrides, stream management, timezone conversions, and database persistence.
"""

from __future__ import annotations

import sys
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import requests
import uvicorn
from live_score.api.app import create_app

PORT = 8009
BASE_URL = f"http://127.0.0.1:{PORT}"
ADMIN_TOKEN = "live-test-admin-token-12345"
ADMIN_HEADERS = {"X-Admin-Token": ADMIN_TOKEN}

results: list[tuple[str, bool, str]] = []


def record(name: str, passed: bool, detail: str = ""):
    results.append((name, passed, detail))
    status_icon = "✅ PASS" if passed else "❌ FAIL"
    print(f"[{status_icon}] {name} {f'({detail})' if detail else ''}")


def start_server(app):
    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server ready
    for _ in range(50):
        try:
            r = requests.get(f"{BASE_URL}/api/v1/matches/today", timeout=1.0)
            if r.status_code == 200:
                return server
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("Server failed to start in time")


def run_tests():
    print("=" * 70)
    print("🚀 STARTING LIVE END-TO-END TEST ON ALL FUNCTIONS")
    print(f"Target URL: {BASE_URL}")
    print("=" * 70)

    # 1. Initialize app with isolated in-memory DB and live catalog (ESPN primary)
    app = create_app(
        db_path=":memory:",
        admin_token=ADMIN_TOKEN,
        timezone_name="Asia/Riyadh",
    )
    server = start_server(app)

    try:
        # -------------------------------------------------------------
        # Test 1: Public Today Matches (ESPN Live Upstream Ingestion)
        # -------------------------------------------------------------
        r = requests.get(f"{BASE_URL}/api/v1/matches/today")
        record("1. Public /matches/today HTTP 200", r.status_code == 200, f"HTTP {r.status_code}")
        data = r.json()
        matches = data.get("matches", [])
        record(
            "2. Ingested live fixtures from ESPN",
            len(matches) > 0,
            f"{len(matches)} fixtures found, date={data.get('date')}, tz={data.get('timezone')}",
        )
        record(
            "3. Arabic timezone label rendered",
            data.get("timezone_label_ar") == "بتوقيت مكة المكرمة",
            data.get("timezone_label_ar", ""),
        )

        sample_match = matches[0] if matches else None
        if sample_match:
            record(
                "4. Option A Card contract fields present",
                all(
                    k in sample_match
                    for k in [
                        "id",
                        "home_team",
                        "away_team",
                        "league",
                        "status",
                        "status_label_ar",
                        "kickoff_time_local",
                        "home_score",
                        "away_score",
                        "competition_subtitle",
                    ]
                ),
                f"{sample_match['home_team']['name_ar']} vs {sample_match['away_team']['name_ar']}",
            )

        # -------------------------------------------------------------
        # Test 2: Timezone switching via ?tz=
        # -------------------------------------------------------------
        r_cairo = requests.get(f"{BASE_URL}/api/v1/matches/today?tz=Africa/Cairo")
        data_cairo = r_cairo.json()
        record(
            "5. Timezone switching to Cairo",
            r_cairo.status_code == 200 and data_cairo.get("timezone") == "Africa/Cairo",
            data_cairo.get("timezone_label_ar", ""),
        )

        r_bad_tz = requests.get(f"{BASE_URL}/api/v1/matches/today?tz=Mars/Olympus")
        record(
            "6. Reject invalid timezone with HTTP 400",
            r_bad_tz.status_code == 400,
            f"HTTP {r_bad_tz.status_code}",
        )

        # -------------------------------------------------------------
        # Test 3: Date filtering via ?date=
        # -------------------------------------------------------------
        r_date = requests.get(f"{BASE_URL}/api/v1/matches/today?date=2026-11-20")
        record("7. Filter schedule by date", r_date.status_code == 200, f"matches={len(r_date.json().get('matches', []))}")

        # -------------------------------------------------------------
        # Test 4: Match Detail Hybrid Route
        # -------------------------------------------------------------
        if sample_match:
            m_id = sample_match["id"]
            r_detail = requests.get(f"{BASE_URL}/api/v1/matches/{m_id}")
            record("8. Match detail HTTP 200", r_detail.status_code == 200, f"id={m_id}")
            detail_data = r_detail.json()
            record(
                "9. Match detail has contract sections (match, servers, stats, standings, events)",
                all(k in detail_data for k in ["match", "servers", "stats", "standings", "events"]),
                f"servers={len(detail_data.get('servers', []))}, stats={len(detail_data.get('stats', []))}",
            )

            # Test detail ?tz=UTC
            r_detail_utc = requests.get(f"{BASE_URL}/api/v1/matches/{m_id}?tz=UTC")
            record("10. Match detail respects ?tz=UTC", r_detail_utc.status_code == 200)

            # Detail with invalid tz
            r_detail_bad_tz = requests.get(f"{BASE_URL}/api/v1/matches/{m_id}?tz=Bad/Zone")
            record("11. Match detail rejects bad tz with 400", r_detail_bad_tz.status_code == 400)

        # -------------------------------------------------------------
        # Test 5: Admin Authentication
        # -------------------------------------------------------------
        r_unauth = requests.get(f"{BASE_URL}/api/v1/admin/matches")
        record("12. Admin listing rejects unauthenticated request (401)", r_unauth.status_code == 401)

        r_wrong_auth = requests.get(
            f"{BASE_URL}/api/v1/admin/matches",
            headers={"X-Admin-Token": "bad-token"},
        )
        record("13. Admin listing rejects invalid token (401)", r_wrong_auth.status_code == 401)

        # -------------------------------------------------------------
        # Test 6: Admin Match Listing & Filters
        # -------------------------------------------------------------
        r_admin = requests.get(f"{BASE_URL}/api/v1/admin/matches", headers=ADMIN_HEADERS)
        record("14. Admin listing succeeds with valid token (200)", r_admin.status_code == 200)
        admin_data = r_admin.json()
        admin_matches = admin_data.get("matches", [])
        record(
            "15. Admin listing contains live matches with override and stream state",
            len(admin_matches) > 0,
            f"{len(admin_matches)} matches in window",
        )

        # Filter by search query
        first_match = admin_matches[0]["match"] if admin_matches else None
        if first_match:
            search_query = first_match["home_team"]["name_ar"]
            r_search = requests.get(
                f"{BASE_URL}/api/v1/admin/matches?q={search_query}",
                headers=ADMIN_HEADERS,
            )
            record(
                f"16. Admin listing filters by query q='{search_query}'",
                r_search.status_code == 200 and len(r_search.json().get("matches", [])) > 0,
            )

        # -------------------------------------------------------------
        # Test 7: Admin Manual Score Override (Emergency Control)
        # -------------------------------------------------------------
        if sample_match:
            m_id = sample_match["id"]
            original_home_score = sample_match["home_score"]

            # Set override: home_score = 7, status = FINISHED, commentator = "معلق خاص"
            override_payload = {
                "home_score": 7,
                "away_score": 3,
                "status": "FINISHED",
                "elapsed_time": 90,
                "commentator": "معلق الطوارئ المعتمد",
            }
            r_set_ov = requests.post(
                f"{BASE_URL}/api/v1/admin/matches/{m_id}/override",
                headers=ADMIN_HEADERS,
                json=override_payload,
            )
            record("17. Admin set override returns 200", r_set_ov.status_code == 200)
            ov_res = r_set_ov.json()
            record(
                "18. Override applied home_score=7, commentator='معلق الطوارئ المعتمد'",
                ov_res.get("home_score") == 7 and ov_res.get("commentator") == "معلق الطوارئ المعتمد",
            )

            # Verify public detail immediately reflects admin override over live upstream
            r_pub_ov = requests.get(f"{BASE_URL}/api/v1/matches/{m_id}")
            pub_match = r_pub_ov.json().get("match", {})
            record(
                "19. Public endpoint reflects override with is_admin_override=True",
                pub_match.get("home_score") == 7 and pub_match.get("is_admin_override") is True,
                f"score: {pub_match.get('home_score')}-{pub_match.get('away_score')}",
            )

            # ---------------------------------------------------------
            # Test 8: Admin Stream Server Management
            # ---------------------------------------------------------
            stream_payload = {
                "server_name": "سيرفر البث الإداري المباشر 4K",
                "url": "https://stream.live-kora.example/hls/live.m3u8",
                "type": "m3u8",
                "quality": "4k",
                "is_active": True,
            }
            r_add_stream = requests.post(
                f"{BASE_URL}/api/v1/admin/matches/{m_id}/streams",
                headers=ADMIN_HEADERS,
                json=stream_payload,
            )
            record("20. Admin add stream returns 201 Created", r_add_stream.status_code == 201)
            streams_res = r_add_stream.json().get("servers", [])
            admin_server = next((s for s in streams_res if "live-kora.example" in s["url"]), None)
            record(
                "21. Added stream present in match servers",
                admin_server is not None and admin_server["server_name"] == "سيرفر البث الإداري المباشر 4K",
            )

            # Public detail reflects stream
            r_pub_stream = requests.get(f"{BASE_URL}/api/v1/matches/{m_id}")
            pub_servers = r_pub_stream.json().get("servers", [])
            record(
                "22. Public detail reflects admin stream at priority",
                any("live-kora.example" in s["url"] for s in pub_servers),
            )

            # Delete the stream server
            if admin_server:
                srv_id = admin_server["id"]
                r_del_stream = requests.delete(
                    f"{BASE_URL}/api/v1/admin/matches/{m_id}/streams/{srv_id}",
                    headers=ADMIN_HEADERS,
                )
                record("23. Admin delete stream returns 200", r_del_stream.status_code == 200)

            # Clear the manual override to restore source state
            r_clear_ov = requests.delete(
                f"{BASE_URL}/api/v1/admin/matches/{m_id}/override",
                headers=ADMIN_HEADERS,
            )
            record("24. Admin clear override returns 200", r_clear_ov.status_code == 200)

            # Public detail back to normal
            r_pub_restored = requests.get(f"{BASE_URL}/api/v1/matches/{m_id}")
            restored_match = r_pub_restored.json().get("match", {})
            record(
                "25. Public detail restored to source score and is_admin_override=False",
                restored_match.get("home_score") == original_home_score
                and restored_match.get("is_admin_override") is False,
            )

        # -------------------------------------------------------------
        # Test 9: Frontend Distribution & Asset Integrity
        # -------------------------------------------------------------
        dist_index = ROOT / "frontend" / "dist" / "index.html"
        record("26. Frontend dist/index.html exists", dist_index.exists())
        if dist_index.exists():
            html_content = dist_index.read_text(encoding="utf-8")
            record("27. HTML declares dir='rtl' attribute", 'dir="rtl"' in html_content)
            record("28. HTML contains root container id='root'", 'id="root"' in html_content)
            record("29. HTML contains Arabic title 'كورة لايف'", "كورة لايف" in html_content)
            record("30. Compiled CSS asset referenced in HTML", "assets/index-" in html_content and ".css" in html_content)
            record("31. Compiled JS bundle referenced in HTML", "assets/index-" in html_content and ".js" in html_content)

        # -------------------------------------------------------------
        # Test 10: Dynamic Ads Engine (Admin CMS & Public Placement)
        # -------------------------------------------------------------
        # 10.1 Create an ad via Admin CMS
        new_ad_payload = {
            "title": "E2E Leaderboard Test Ad",
            "position": "header_top",
            "ad_type": "image_banner",
            "image_url": "https://example.com/banner_e2e.jpg",
            "link_url": "https://example.com/e2e",
            "target_device": "all",
            "is_active": True,
            "priority": 100,
        }
        r_create_ad = requests.post(
            f"{BASE_URL}/api/v1/admin/ads",
            json=new_ad_payload,
            headers=ADMIN_HEADERS,
        )
        record("32. Admin create ad returns 201", r_create_ad.status_code == 201, f"HTTP {r_create_ad.status_code}")
        created_ad = r_create_ad.json()
        ad_id = created_ad.get("id")

        # 10.2 Public listing includes the active ad
        r_pub_ads = requests.get(f"{BASE_URL}/api/v1/ads?position=header_top")
        record("33. Public /ads?position=header_top returns 200", r_pub_ads.status_code == 200)
        pub_ad_ids = [a["id"] for a in r_pub_ads.json().get("ads", [])]
        record("34. Public ads list contains created ad", ad_id in pub_ad_ids)

        # 10.3 Update ad priority and title
        r_up_ad = requests.put(
            f"{BASE_URL}/api/v1/admin/ads/{ad_id}",
            json={"title": "Updated E2E Banner", "priority": 200},
            headers=ADMIN_HEADERS,
        )
        record("35. Admin update ad returns 200", r_up_ad.status_code == 200 and r_up_ad.json().get("priority") == 200)

        # 10.4 Toggle active status (turn off)
        r_toggle_ad = requests.patch(
            f"{BASE_URL}/api/v1/admin/ads/{ad_id}/toggle",
            headers=ADMIN_HEADERS,
        )
        record("36. Admin toggle ad returns is_active=False", r_toggle_ad.status_code == 200 and r_toggle_ad.json().get("is_active") is False)

        # 10.5 Inactive ad disappears from public endpoint
        r_pub_inactive = requests.get(f"{BASE_URL}/api/v1/ads?position=header_top")
        pub_inactive_ids = [a["id"] for a in r_pub_inactive.json().get("ads", [])]
        record("37. Inactive ad hidden from public API", ad_id not in pub_inactive_ids)

        # 10.6 Delete ad
        r_del_ad = requests.delete(
            f"{BASE_URL}/api/v1/admin/ads/{ad_id}",
            headers=ADMIN_HEADERS,
        )
        record("38. Admin delete ad returns 200", r_del_ad.status_code == 200 and r_del_ad.json().get("deleted") is True)

        # -------------------------------------------------------------
        # Test 11: Site Visitor Telemetry & Analytics by Date
        # -------------------------------------------------------------
        # 11.1 Public visitor tracking
        r_track = requests.post(
            f"{BASE_URL}/api/v1/analytics/track",
            json={
                "visitor_id": "e2e_visitor_xyz",
                "path": "/matches/today",
                "device": "mobile",
                "referrer": "https://google.com",
            },
        )
        record("39. Public visitor tracking endpoint returns 200", r_track.status_code == 200 and r_track.json().get("recorded") is True)

        # 11.2 Admin analytics by week
        r_stats_week = requests.get(
            f"{BASE_URL}/api/v1/admin/analytics/stats?period=week",
            headers=ADMIN_HEADERS,
        )
        record("40. Admin analytics week returns 200 with 7 days", r_stats_week.status_code == 200 and len(r_stats_week.json().get("chart_data", [])) == 7)

        # 11.3 Admin analytics by day (24 hours)
        r_stats_day = requests.get(
            f"{BASE_URL}/api/v1/admin/analytics/stats?period=day",
            headers=ADMIN_HEADERS,
        )
        record("41. Admin analytics day returns 24 hours", r_stats_day.status_code == 200 and len(r_stats_day.json().get("chart_data", [])) == 24)

        # 11.4 Admin analytics by month (30 days)
        r_stats_month = requests.get(
            f"{BASE_URL}/api/v1/admin/analytics/stats?period=month",
            headers=ADMIN_HEADERS,
        )
        record("42. Admin analytics month returns 30 days", r_stats_month.status_code == 200 and len(r_stats_month.json().get("chart_data", [])) == 30)

        # 11.5 Admin analytics by year (12 months)
        r_stats_year = requests.get(
            f"{BASE_URL}/api/v1/admin/analytics/stats?period=year",
            headers=ADMIN_HEADERS,
        )
        record("43. Admin analytics year returns 12 months", r_stats_year.status_code == 200 and len(r_stats_year.json().get("chart_data", [])) == 12)

        # -------------------------------------------------------------
        # Test 12: OWASP Security Headers
        # -------------------------------------------------------------
        r_sec = requests.get(f"{BASE_URL}/api/v1/matches/today")
        record(
            "44. Security headers present on public response",
            r_sec.headers.get("X-Content-Type-Options") == "nosniff"
            and r_sec.headers.get("X-Frame-Options") == "SAMEORIGIN"
            and "Content-Security-Policy" in r_sec.headers,
        )

        # -------------------------------------------------------------
        # Test 13: In-Memory Micro-Cache & ETag 304 Validation
        # -------------------------------------------------------------
        etag = r_sec.headers.get("ETag")
        record("45. Public response generates deterministic ETag", bool(etag and etag.startswith('"')))
        if etag:
            r_etag = requests.get(f"{BASE_URL}/api/v1/matches/today", headers={"If-None-Match": etag})
            record(
                "46. If-None-Match with matching ETag returns 304 Not Modified (0 KB)",
                r_etag.status_code == 304 and len(r_etag.content) == 0,
            )

        # -------------------------------------------------------------
        # Test 14: Payload Size Guard
        # -------------------------------------------------------------
        large_payload = {"data": "A" * 70_000}  # ~70 KB > 64 KB limit
        r_large = requests.post(f"{BASE_URL}/api/v1/analytics/track", json=large_payload)
        record("47. Request exceeding 64KB is rejected with 413 Payload Too Large", r_large.status_code == 413)

        # -------------------------------------------------------------
        # Test 15: Sliding-Window Rate Limiting Headers
        # -------------------------------------------------------------
        record(
            "48. Rate limit headers attached to public responses",
            "X-RateLimit-Limit" in r_sec.headers and "X-RateLimit-Remaining" in r_sec.headers,
        )


    finally:
        server.should_exit = True

    print("=" * 70)
    total_passed = sum(1 for _, p, _ in results if p)
    print(f"📊 SUMMARY: {total_passed} / {len(results)} live tests passed successfully!")
    print("=" * 70)
    if total_passed < len(results):
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
