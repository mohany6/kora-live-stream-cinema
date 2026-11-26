import re
from html.parser import HTMLParser

with open(r'C:\Users\Mohany\Desktop\football-live-score-platform\data\kooralive_la.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Title
title_m = re.search(r'<title>(.*?)</title>', html, re.I | re.DOTALL)
print('Title:', title_m.group(1).strip() if title_m else 'No Title')

# Meta description
desc_m = re.search(r'<meta[^>]*name=[\'"]description[\'"][^>]*content=[\'"](.*?)[\'"]', html, re.I)
print('Meta Description:', desc_m.group(1).strip() if desc_m else 'None')

# Generator
gen_m = re.search(r'<meta[^>]*name=[\'"]generator[\'"][^>]*content=[\'"](.*?)[\'"]', html, re.I)
print('Generator:', gen_m.group(1).strip() if gen_m else 'Custom / None')

# Stylesheets
styles = re.findall(r'<link[^>]*rel=[\'"]stylesheet[\'"][^>]*href=[\'"](.*?)[\'"]', html, re.I)
print('\n=== Stylesheets (' + str(len(styles)) + ') ===')
for st in styles[:6]:
    print(' -', st)

# Scripts
scripts = re.findall(r'<script[^>]*src=[\'"](.*?)[\'"]', html, re.I)
print('\n=== External Scripts (' + str(len(scripts)) + ') ===')
for s in scripts:
    print(' -', s)

# Ad networks signatures
ad_keywords = ['adsterra', 'adsbygoogle', 'propeller', 'monetag', 'popcash', 'popads', 'adcash', 'hilltopads', 'clickadu', 'juicyads', 'exoclick', 'czernik', 'atoptions', 'google_ad', 'pagead2', 'histats', 'google-analytics', 'googletagmanager', 'cloudflare']
print('\n=== Detected Technologies & Ad Signatures ===')
for ak in ad_keywords:
    if ak in html.lower():
        print(' - Found signature:', ak)

# Find match items / structure
# Let's see some div classes
classes = set(re.findall(r'class=[\'"]([a-zA-Z0-9_\-\s]+)[\'"]', html))
split_classes = set()
for c in classes:
    for item in c.split():
        split_classes.add(item)

match_related = [c for c in split_classes if any(w in c.lower() for w in ['match', 'team', 'vs', 'live', 'score', 'tab', 'day', 'channel', 'league'])]
print('\n=== Match & UI CSS Classes ===\n', sorted(match_related)[:40])

# Match URLs
match_urls = re.findall(r'href=[\'"](https?://kooralive\.la/[^\'"\s]+)[\'"]', html)
print('\n=== Sample Internal Match Links === (' + str(len(match_urls)) + ')')
for u in list(set(match_urls))[:8]:
    print(' -', u)
