import re

with open('data/kooralive_home.html', 'r', encoding='utf-8') as f:
    html = f.read()

matches = re.findall(r'<div[^>]*class=["\']AY_Match[^"\']*["\'][^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
print("AY_Match count:", len(matches))

if not matches:
    # Try another pattern
    matches = re.findall(r'<div[^>]*class=["\']AY_Match[^"\']*["\'].*?<!-- /AY_Match -->', html, re.DOTALL)
    print("Alternative AY_Match count:", len(matches))

# Let's find first AY_Match block
m = re.search(r'<div[^>]*class=["\']AY_Match[^"\']*["\'].*?', html)
if m:
    start = m.start()
    print("MATCH BLOCK SNIPPET:\n", html[start:start+3000])
