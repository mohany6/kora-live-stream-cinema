import re

with open('data/kooralive_home.html', 'r', encoding='utf-8') as f:
    html = f.read()

print("HTML length:", len(html))

# Look for match elements, divs, articles
articles = re.findall(r'<article[^>]*>.*?</article>', html, re.DOTALL)
print("Articles found:", len(articles))

# Look for match blocks (like match-container, match-card, etc.)
divs = re.findall(r'<div[^>]*class=["\']([^"\']*(?:match|game|fixture|live|albaplayer)[^"\']*)["\'][^>]*>', html, re.IGNORECASE)
print("Matching divs:", set(divs))

# Find all links
links = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL)
print(f"Total links: {len(links)}")
for href, content in links:
    text = re.sub(r'<[^>]+>', ' ', content).strip()
    if text and len(text) > 2 and not href.startswith('#'):
        print(f"LINK: {href} | TEXT: {text[:80]}")
