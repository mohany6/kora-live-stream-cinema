import pytest
from src.live_score.domain.article_generator import generate_blogger_article

def test_generate_blogger_article_structure():
    mock_match = {
        "id": "match_clasico",
        "home_team": "ريال مدريد",
        "away_team": "برشلونة",
        "competition": "الدوري الإسباني",
        "kickoff_time": "2026-11-24T20:00:00Z",
        "status": "SCHEDULED",
        "venue": "سانتياغو برنابيو",
        "referee": "خيسوس خيل مانزانو",
        "channel": "beIN Sports 1 HD",
        "commentator": "حفيظ دراجي"
    }
    result = generate_blogger_article(mock_match, platform_base_url="https://live.example.com")
    
    assert "title" in result
    assert "content" in result
    # Check SEO Arabic Title
    assert "مشاهدة مباراة ريال مدريد وبرشلونة" in result["title"]
    # Check Google Schema.org JSON-LD SportsEvent microdata
    assert "application/ld+json" in result["content"]
    assert '"@type": "SportsEvent"' in result["content"]
    assert "ريال مدريد" in result["content"]
    assert "برشلونة" in result["content"]
    # Check safe CTA redirect with rel="noopener noreferrer"
    assert 'rel="noopener noreferrer"' in result["content"]
    assert "https://live.example.com" in result["content"]

def test_generate_blogger_article_fallback_metadata():
    mock_match = {
        "id": "match_minimal",
        "home_team": "الهلال",
        "away_team": "النصر",
        "competition": "دوري روشن السعودي",
        "kickoff_time": "2026-11-24T18:00:00Z",
        "status": "SCHEDULED"
    }
    result = generate_blogger_article(mock_match)
    assert "الهلال" in result["title"]
    assert "النصر" in result["title"]
    assert "content" in result


from fastapi.testclient import TestClient
from live_score.api.app import create_app
from live_score.api.store import AdminStore
from live_score.domain.models import Match, MatchDetail, Team, League, MatchStatus
from datetime import datetime, timezone

def test_admin_get_match_article_endpoint(tmp_path):
    store = AdminStore(tmp_path / "test.db")
    now = datetime(2026, 11, 24, 18, 0, tzinfo=timezone.utc)
    base_m = Match(
        id="match_test_article",
        home_team=Team(id="t1", name_ar="الأهلي", name_en="Al Ahly"),
        away_team=Team(id="t2", name_en="Zamalek", name_ar="الزمالك"),
        league=League(id="l1", name_ar="الدوري المصري", name_en="Egyptian League", country_ar="مصر"),
        kickoff_time=now,
        status=MatchStatus.SCHEDULED,
        home_score=0,
        away_score=0,
    )
    demo_match = MatchDetail(match=base_m)
    app = create_app(fixtures=[demo_match], db_path=str(tmp_path / "test.db"), admin_token="test-token")
    client = TestClient(app)

    # Unauthorized without header
    res_unauth = client.get("/api/v1/admin/matches/match_test_article/article")
    assert res_unauth.status_code == 401

    # Authorized
    res = client.get(
        "/api/v1/admin/matches/match_test_article/article?base_url=https://kora-tunnel.example.com",
        headers={"X-Admin-Token": "test-token"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "الأهلي" in data["title"]
    assert "الزمالك" in data["title"]
    assert "https://kora-tunnel.example.com" in data["content"]


def test_generate_blogger_article_datetime_and_safety():
    from datetime import datetime, timezone
    mock_match = {
        "id": "match_datetime_test",
        "home_team": "ريال مدريد <script>",
        "away_team": "برشلونة",
        "competition": "الدوري الإسباني & كأس الملك",
        "kickoff_time": datetime(2026, 11, 24, 20, 0, tzinfo=timezone.utc),
        "venue": "سانتياغو برنابيو",
        "referee": "خيل مانزانو",
        "channel": "beIN Sports 1 HD",
        "commentator": "عصام الشوالي",
    }
    # This must not throw TypeError: Object of type datetime is not JSON serializable
    result = generate_blogger_article(mock_match, platform_base_url="https://live.example.com")
    assert "2026-11-24T20:00:00" in result["content"]
    assert "</script>" not in result["content"].split("</script>")[0]  # No unescaped closing script in JSON-LD
    assert "موعد المباراة" in result["content"] or "توقيت" in result["content"]
