import re

with open(r'C:\Users\Mohany\Desktop\football-live-score-platform\data\kooralive_la.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Find the entire first match block
m = re.search(r'<div[^>]*class="[^"]*AY_Match[^"]*"[^>]*>.*?(?=<div[^>]*class="[^"]*AY_Match|$)', text, re.DOTALL)
if m:
    print('Full Match Card Block:\n', m.group(0)[:2000])

# Check tabs UL
tabs = re.search(r'<ul[^>]*class="[^"]*AY-Dtab[^"]*"[^>]*>.*?</ul>', text, re.DOTALL)
if tabs:
    print('\nTabs UL:\n', tabs.group(0))

# Check SEO keywords and content
seo_text = re.search(r'<div[^>]*class="[^"]*AYb_Head[^"]*"[^>]*>.*?</div>\s*</div>', text, re.DOTALL)
if seo_text:
    print('\nSEO Block:\n', seo_text.group(0)[:1000])
