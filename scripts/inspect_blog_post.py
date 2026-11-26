import urllib.request
import ssl
import re

url = "https://kora-live-to.blogspot.com/2026/11/blog-post.html"
ctx = ssl.create_default_context()
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
    html = resp.read().decode("utf-8", errors="replace")

art_m = re.search(r"<article[^>]*>(.*?)</article>", html, re.DOTALL)
if art_m:
    print("--- Article Content ---")
    print(art_m.group(1)[:2500])
else:
    print("No <article> tag found")

# Check what the button href links to
buttons = re.findall(r'<a\s+[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', html, re.DOTALL)
print("\n--- Links & Buttons found in post ---")
for href, text in buttons[:10]:
    clean_text = re.sub(r'<[^>]+>', '', text).strip()
    if clean_text:
        print(f"Link: {clean_text[:40]} -> {href}")
