import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from live_score.adapters.livescore_v2 import EspnSoccerClient, LiveScoreV2Client
from live_score.api.fixtures import create_catalog

now = datetime.now(timezone.utc)
print(f"Current System UTC Time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
local_now = datetime.now()
print(f"Current Local Machine Time: {local_now.strftime('%Y-%m-%d %H:%M:%S')}")

print("\n--- 1. Testing Live ESPN Client for Today and Tomorrow ---")
client = EspnSoccerClient()
today = now.date()
tomorrow = today + timedelta(days=1)
yesterday = today - timedelta(days=1)

leagues = (
    "uefa.champions",
    "eng.1",
    "esp.1",
    "ita.1",
    "ger.1",
    "fra.1",
    "ksa.1",
    "tur.1",
    "uefa.europa"
)

try:
    fixtures = client.fetch_window(yesterday, tomorrow, leagues)
    print(f"Total fixtures returned from live ESPN API: {len(fixtures)}")
    for m in fixtures:
        print(f"  ID: {m.id}")
        print(f"  Time (UTC): {m.kickoff_time.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"  Status: {m.status.value} (Elapsed: {getattr(m, 'elapsed_time', None)})")
        print(f"  Match: {m.home_team.name_ar or m.home_team.name_en} {getattr(m, 'home_score', 0)} - {getattr(m, 'away_score', 0)} {m.away_team.name_ar or m.away_team.name_en}")
        print(f"  League: {m.league.name_ar or m.league.name_en}")
        print("-" * 40)
except Exception as e:
    print(f"Error fetching from ESPN: {e}")

print("\n--- 2. Testing LiveFixturesCatalog ---")
cat = create_catalog(now)
if cat:
    fix_map = cat.fixture_map(now)
    print(f"Catalog fixture count: {len(fix_map)}")
    for match_id, detail in list(fix_map.items())[:10]:
        m = detail.match if hasattr(detail, 'match') else detail
        print(f"  [{m.status.value}] {m.kickoff_time.strftime('%Y-%m-%d %H:%M')} | {m.home_team.name_ar} vs {m.away_team.name_ar} | {m.league.name_ar}")
