import re

with open('data/kooralive_home.html', 'r', encoding='utf-8') as f:
    html = f.read()

matches = re.findall(r'<div class="AY_Match (live|not-started|finished)">(.*?)<!-- /AY_Match -->', html + '<!-- /AY_Match -->', re.DOTALL)
if not matches:
    matches = re.findall(r'<div class="AY_Match (live|not-started|finished)">(.*?)(?=<div class="AY_Match|$)', html, re.DOTALL)

print(f"Total parsed matches: {len(matches)}")
for status, block in matches:
    tm1 = re.search(r"<div class=['\"]TM_Name['\"]>([^<]+)</div>", block)
    tms = re.findall(r"<div class=['\"]TM_Name['\"]>([^<]+)</div>", block)
    home = tms[0] if len(tms) > 0 else 'Unknown'
    away = tms[1] if len(tms) > 1 else 'Unknown'
    channel_m = re.search(r"<li><span>([^<]*(?:beIN|قناة|الكاس|SSC)[^<]*)</span></li>", block, re.IGNORECASE)
    channel = channel_m.group(1) if channel_m else 'Unknown'
    link_m = re.search(r'<a\s+href=["\']([^"\']+)["\']', block)
    link = link_m.group(1) if link_m else 'None'
    print(f"[{status}] {home} vs {away} | Channel: {channel} | Link: {link}")
