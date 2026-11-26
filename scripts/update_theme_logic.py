import json
import urllib.request
from pathlib import Path

ROOT = Path(r"C:\Users\Mohany\Desktop\football-live-score-platform")

def fetch_day(date_str):
    url = f"http://127.0.0.1:8000/api/v1/matches/today?date={date_str}&tz=Asia/Riyadh"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        matches = json.loads(r.read().decode("utf-8")).get("matches", [])
    
    out = []
    for m in matches:
        is_fin = m.get("status") == "FINISHED"
        home_logo = m["home_team"].get("logo_url") or ""
        away_logo = m["away_team"].get("logo_url") or ""
        
        # Exact fixes for known CDN 404s
        if m["home_team"].get("name_en") == "Sabah FK" or "21922" in home_logo or "18861" in home_logo:
            home_logo = "https://a.espncdn.com/i/teamlogos/soccer/500/21922.png"
        if m["away_team"].get("name_en") == "Sabah FK" or "21922" in away_logo or "18861" in away_logo:
            away_logo = "https://a.espncdn.com/i/teamlogos/soccer/500/21922.png"
        if "سبورتنغ" in m["home_team"].get("name_ar", "") or "300.png" in home_logo:
            home_logo = "https://a.espncdn.com/i/teamlogos/soccer/500/2250.png"
        if "سبورتنغ" in m["away_team"].get("name_ar", "") or "300.png" in away_logo:
            away_logo = "https://a.espncdn.com/i/teamlogos/soccer/500/2250.png"
            
        h_score = m.get("home_score", 0)
        a_score = m.get("away_score", 0)
        c_down = f"انتهت {h_score} - {a_score}" if is_fin else (m.get("countdown_seconds") and "19:26:45" or m.get("kickoff_time_local", "20:45"))
        s_note = "نتيجة نهائية • دوري أبطال أوروبا" if is_fin else "سيتم تحديث روابط البث قبل انطلاق المباراة"
        
        out.append({
            "id": m["id"],
            "home_name": m["home_team"].get("name_ar") or m["home_team"].get("name_en", ""),
            "home_logo": home_logo,
            "away_name": m["away_team"].get("name_ar") or m["away_team"].get("name_en", ""),
            "away_logo": away_logo,
            "kickoff_time": m.get("kickoff_time_local", "20:45"),
            "countdown": c_down,
            "channel": m.get("channel") or "beIN SPORTS 1 HD",
            "league": m.get("league", {}).get("name_ar") or "دوري أبطال أوروبا",
            "status_note": s_note,
            "status": m.get("status", "SCHEDULED"),
            "home_score": h_score,
            "away_score": a_score,
        })
    return out

yesterday_data = fetch_day("2026-11-24")
today_data = fetch_day("2026-11-25")
tomorrow_data = fetch_day("2026-11-26")[:8]

multi_day = {
    "yesterday": yesterday_data,
    "today": today_data,
    "tomorrow": tomorrow_data,
}

out_file = ROOT / "data" / "multi_day_dataset.json"
out_file.write_text(json.dumps(multi_day, ensure_ascii=False, indent=4), encoding="utf-8")
print(f"Generated multi_day_dataset.json with {len(yesterday_data)} yesterday, {len(today_data)} today, {len(tomorrow_data)} tomorrow matches.")
