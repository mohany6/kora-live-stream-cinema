import re

with open(r'C:\Users\Mohany\Desktop\football-live-score-platform\data\kooralive_la.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Match Cards structure
matches = re.findall(r'<div[^>]*class="[^"]*AY_Match[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', text, re.DOTALL)
print(f'AY_Match cards found: {len(matches)}')
if matches:
    print('Sample Match Card HTML:\n', matches[0][:800])

# 2. Tabs structure (Yesterday, Today, Tomorrow)
tabs = re.findall(r'<div[^>]*class="[^"]*AY-Dtab[^"]*"[^>]*>(.*?)</div>', text, re.DOTALL)
print(f'\nTabs found: {len(tabs)}')
if tabs:
    print('Tabs HTML:\n', tabs[0])

# 3. Ad Placements
ad_containers = re.findall(r'<div[^>]*class="[^"]*(?:ad|banner|sponsor|widget)[^"]*"[^>]*>(.*?)</div>', text, re.DOTALL | re.I)
print(f'\nAd containers found: {len(ad_containers)}')
for i, ac in enumerate(ad_containers[:5]):
    print(f'Ad container {i+1}:\n', ac[:300])

# 4. JSON-LD Structured Data
json_lds = re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', text, re.DOTALL)
print(f'\nJSON-LD blocks: {len(json_lds)}')
for j in json_lds:
    print('JSON-LD:\n', j[:400])

# 5. Check match single page links
match_links = re.findall(r'href="(https?://kooralive\.la/[^"]+)"', text)
live_links = [l for l in match_links if 'matches-' not in l and 'feed' not in l and 'wp-content' not in l and l != 'https://kooralive.la/']
print(f'\nDistinct match URLs: {len(set(live_links))}')
for l in list(set(live_links))[:5]:
    print(' -', l)
