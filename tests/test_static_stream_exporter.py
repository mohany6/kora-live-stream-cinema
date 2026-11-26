# -*- coding: utf-8 -*-
"""Unit tests for the static matches JSON stream exporter."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from live_score.domain.models import (
    League,
    LineupPlayer,
    Match,
    MatchDetail,
    MatchEvent,
    MatchStatus,
    StreamServer,
    Team,
)


class _StubCatalog:
    def __init__(self, details: list[MatchDetail]) -> None:
        self._map = {detail.match.id: detail for detail in details}

    def fixture_map(self, now: datetime | None = None) -> dict[str, MatchDetail]:
        return dict(self._map)


def _sample_details(now: datetime) -> list[MatchDetail]:
    la_liga = League(
        id="esp.1",
        name_ar="الدوري الإسباني",
        name_en="La Liga",
        round="الجولة 12",
        logo_url="https://img.example/laliga.png",
    )
    premier = League(
        id="eng.1",
        name_ar="الدوري الإنجليزي الممتاز",
        name_en="Premier League",
        round="الجولة 13",
        logo_url="https://img.example/epl.png",
    )
    saudi = League(
        id="ksa.1",
        name_ar="دوري روشن السعودي",
        name_en="Saudi Pro League",
        round="الجولة 10",
    )

    live_match = Match(
        id="m_live",
        home_team=Team(
            id="real_madrid",
            name_ar="ريال مدريد",
            name_en="Real Madrid",
            logo_url="https://img.example/rm.png",
        ),
        away_team=Team(
            id="barcelona",
            name_ar="برشلونة",
            name_en="Barcelona",
            logo_url="https://img.example/fcb.png",
        ),
        league=la_liga,
        status=MatchStatus.IN_PLAY,
        kickoff_time=now - timedelta(minutes=65),
        home_score=2,
        away_score=1,
        elapsed_time=65,
        stream_servers=[
            StreamServer(
                id="srv_1",
                server_name="سيرفر 1 (HD)",
                url="https://live.example/embed/clasico",
                type="iframe",
                is_active=True,
                quality="hd",
            ),
            StreamServer(
                id="srv_2",
                server_name="سيرفر 2 (HLS)",
                url="https://live.example/hls/clasico.m3u8",
                type="m3u8",
                is_active=True,
                quality="1080p",
                sandbox=None,
            ),
        ],
        channel="beIN SPORTS 1 HD",
        commentator="عصام الشوالي",
        stadium="سانتياغو برنابيو",
        referee="خيل مانزانو",
    )

    scheduled_match = Match(
        id="m_sched",
        home_team=Team(id="hilal", name_ar="الهلال", name_en="Al Hilal"),
        away_team=Team(id="nassr", name_ar="النصر", name_en="Al Nassr"),
        league=saudi,
        status=MatchStatus.SCHEDULED,
        kickoff_time=now + timedelta(hours=3),
        home_score=0,
        away_score=0,
        channel="SSC 1 HD",
        commentator="فهد العتيبي",
        stadium="المملكة أرينا",
        referee="محمد الهويش",
    )

    finished_match = Match(
        id="m_fin",
        home_team=Team(id="liv", name_ar="ليفربول", name_en="Liverpool"),
        away_team=Team(id="mci", name_ar="مانشستر سيتي", name_en="Manchester City"),
        league=premier,
        status=MatchStatus.FINISHED,
        kickoff_time=now - timedelta(hours=4),
        home_score=1,
        away_score=1,
        elapsed_time=90,
        channel="beIN SPORTS 2 HD",
        commentator="حفيظ دراجي",
        stadium="أنفيلد",
        referee="مايكل أوليفر",
    )

    live_detail = MatchDetail(
        match=live_match,
        home_lineup=[
            LineupPlayer(name="Thibaut Courtois", number=1, position="GK", grid_position="1:1"),
            LineupPlayer(name="Kylian Mbappe", number=9, position="FW", grid_position="5:2"),
        ],
        away_lineup=[
            LineupPlayer(name="Marc-Andre ter Stegen", number=1, position="GK", grid_position="1:1"),
            LineupPlayer(name="Robert Lewandowski", number=9, position="FW", grid_position="5:2"),
        ],
        home_formation="4-3-3",
        away_formation="4-2-3-1",
        events=[
            MatchEvent(
                id="ev_1",
                minute=18,
                type="goal",
                player_name="Kylian Mbappe",
                team_id="real_madrid",
                description_ar="هدف ريال مدريد الأول",
            )
        ],
        stats={
            "possession": {"label_ar": "الاستحواذ", "home": 57, "away": 43, "unit": "%"},
            "shots": {"label_ar": "التسديدات", "home": 12, "away": 8, "unit": ""},
        },
        standings=[
            {
                "position": 1,
                "team_name_ar": "ريال مدريد",
                "played": 12,
                "won": 10,
                "drawn": 1,
                "lost": 1,
                "goals_for": 28,
                "goals_against": 10,
                "points": 31,
                "is_home": True,
                "is_away": False,
            }
        ],
    )

    return [
        live_detail,
        MatchDetail(match=scheduled_match),
        MatchDetail(match=finished_match),
    ]


def test_export_static_matches_json_writes_expected_schema(tmp_path, monkeypatch):
    import scripts.export_static_streams as exporter

    now = datetime(2026, 11, 26, 15, 0, tzinfo=timezone.utc)
    details = _sample_details(now)
    monkeypatch.setattr(exporter, "create_catalog", lambda _now=None: _StubCatalog(details))

    output_path = tmp_path / "data" / "matches.json"
    count = exporter.export_static_matches_json(target_path=output_path, now=now)

    assert count == 3
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["count"] == 3
    assert payload["updated_at"] == "2026-11-26T15:00:00Z"
    assert payload["timezone"] == "Asia/Riyadh"
    assert payload["timezone_label_ar"] == "بتوقيت مكة المكرمة"
    assert payload["date"] == "2026-11-26"
    assert isinstance(payload["matches"], list)
    assert len(payload["matches"]) == 3

    # Matches are sorted chronologically by kickoff_time_utc
    assert [m["id"] for m in payload["matches"]] == ["m_fin", "m_live", "m_sched"]

    live = next(m for m in payload["matches"] if m["id"] == "m_live")
    assert live["status"] == "IN_PLAY"
    assert live["status_label_ar"] == "مباشر الآن"
    assert live["home_score"] == 2
    assert live["away_score"] == 1
    assert live["elapsed_time"] == 65
    assert live["live_minute_label"] == "65'"
    assert live["kickoff_time_local"] == "16:55"
    assert live["kickoff_date_local"] == "2026-11-26"
    assert live["countdown_seconds"] is None
    assert live["competition_subtitle"] == "الدوري الإسباني • الجولة 12"
    assert live["channel"] == "beIN SPORTS 1 HD"
    assert live["commentator"] == "عصام الشوالي"
    assert live["stadium"] == "سانتياغو برنابيو"
    assert live["referee"] == "خيل مانزانو"
    assert live["has_stream"] is True

    assert live["home_team"] == {
        "id": "real_madrid",
        "name_ar": "ريال مدريد",
        "name_en": "Real Madrid",
        "logo_url": "https://img.example/rm.png",
    }
    assert live["away_team"] == {
        "id": "barcelona",
        "name_ar": "برشلونة",
        "name_en": "Barcelona",
        "logo_url": "https://img.example/fcb.png",
    }
    assert live["league"] == {
        "id": "esp.1",
        "name_ar": "الدوري الإسباني",
        "name_en": "La Liga",
        "round": "الجولة 12",
        "logo_url": "https://img.example/laliga.png",
    }

    assert len(live["servers"]) == 2
    assert live["servers"][0]["id"] == "srv_1"
    assert live["servers"][0]["server_name"] == "سيرفر 1 (HD)"
    assert live["servers"][0]["type"] == "iframe"
    assert live["servers"][0]["is_active"] is True
    assert live["servers"][1]["type"] == "m3u8"

    # Detail metadata
    assert len(live["home_lineup"]) == 2
    assert len(live["away_lineup"]) == 2
    assert live["home_formation"] == "4-3-3"
    assert live["away_formation"] == "4-2-3-1"
    assert len(live["events"]) == 1
    assert live["events"][0]["player_name"] == "Kylian Mbappe"
    assert live["stats"] == [
        {"key": "possession", "label_ar": "الاستحواذ", "home": 57.0, "away": 43.0, "unit": "%"},
        {"key": "shots", "label_ar": "التسديدات", "home": 12.0, "away": 8.0, "unit": ""},
    ]
    assert len(live["standings"]) == 1
    assert live["standings"][0]["team_name_ar"] == "ريال مدريد"

    sched = next(m for m in payload["matches"] if m["id"] == "m_sched")
    assert sched["status"] == "SCHEDULED"
    assert sched["status_label_ar"] == "لم تبدأ"
    assert sched["countdown_seconds"] == 10800
    assert sched["has_stream"] is False
    assert sched["servers"] == []

    fin = next(m for m in payload["matches"] if m["id"] == "m_fin")
    assert fin["status"] == "FINISHED"
    assert fin["status_label_ar"] == "انتهت"
    assert fin["countdown_seconds"] is None


def test_export_hydrates_channel_streams_with_absolute_urls(tmp_path, monkeypatch):
    import scripts.export_static_streams as exporter

    now = datetime(2026, 11, 26, 18, 0, tzinfo=timezone.utc)
    live_no_servers = Match(
        id="m_hydrate",
        home_team=Team(id="ars", name_ar="أرسنال", name_en="Arsenal"),
        away_team=Team(id="che", name_ar="تشيلسي", name_en="Chelsea"),
        league=League(id="eng.1", name_ar="الدوري الإنجليزي الممتاز", name_en="Premier League"),
        status=MatchStatus.IN_PLAY,
        kickoff_time=now - timedelta(minutes=20),
        home_score=1,
        away_score=0,
        elapsed_time=20,
        stream_servers=[],
        channel="beIN SPORTS 1 HD",
    )
    monkeypatch.setattr(
        exporter,
        "create_catalog",
        lambda _now=None: _StubCatalog([MatchDetail(match=live_no_servers)]),
    )

    output_path = tmp_path / "matches.json"
    count = exporter.export_static_matches_json(target_path=output_path, now=now)
    assert count == 1

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    exported = payload["matches"][0]
    assert exported["has_stream"] is True
    assert len(exported["servers"]) >= 2
    assert exported["servers"][0]["type"] == "m3u8"
    for srv in exported["servers"]:
        assert srv["url"].startswith("https://")
        assert "/api/v1/" not in srv["url"]


def test_export_falls_back_to_demo_when_catalog_is_none(tmp_path, monkeypatch):
    import scripts.export_static_streams as exporter

    now = datetime(2026, 11, 26, 15, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(exporter, "create_catalog", lambda _now=None: None)

    output_path = tmp_path / "demo_matches.json"
    count = exporter.export_static_matches_json(target_path=output_path, now=now)

    assert count == 4
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["count"] == 4
    assert len(payload["matches"]) == 4


def test_export_handles_empty_fixture_map(tmp_path, monkeypatch):
    import scripts.export_static_streams as exporter

    now = datetime(2026, 11, 26, 15, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(exporter, "create_catalog", lambda _now=None: _StubCatalog([]))

    output_path = tmp_path / "empty.json"
    count = exporter.export_static_matches_json(target_path=output_path, now=now)

    assert count == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["count"] == 0
    assert payload["matches"] == []
    assert "updated_at" in payload


def test_export_default_paths_and_cli_output(tmp_path, monkeypatch, capsys):
    import scripts.export_static_streams as exporter

    now = datetime(2026, 11, 26, 15, 0, tzinfo=timezone.utc)
    details = _sample_details(now)[:1]
    monkeypatch.setattr(exporter, "create_catalog", lambda _now=None: _StubCatalog(details))

    primary_default = tmp_path / "frontend" / "public" / "data" / "matches.json"
    secondary_default = tmp_path / "data" / "matches.json"
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_PATH", primary_default)
    monkeypatch.setattr(exporter, "SECONDARY_OUTPUT_PATH", secondary_default)

    exit_code = exporter.main(["--no-refresh", "--no-hydrate-details"])
    assert exit_code == 0
    assert primary_default.exists()
    assert secondary_default.exists()

    primary_data = json.loads(primary_default.read_text(encoding="utf-8"))
    secondary_data = json.loads(secondary_default.read_text(encoding="utf-8"))
    assert primary_data["count"] == 1
    assert secondary_data["count"] == 1
    assert primary_data["matches"][0]["id"] == "m_live"

    captured = capsys.readouterr()
    assert "1" in captured.out
    assert str(primary_default) in captured.out
