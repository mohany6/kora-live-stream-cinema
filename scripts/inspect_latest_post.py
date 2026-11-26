import httpx

url = "https://kora-live-to.blogspot.com/2026/11/sabah-fk_01783810643.html"
r = httpx.get(url, follow_redirects=True, timeout=10)
text = r.text

print(f"Status: {r.status_code}")
print(" - SportsEvent Schema in latest post:", "SportsEvent" in text)
print(" - 728x90 Banner (key: 6703ea03ffb309455182c593d4e6ea81):", "6703ea03ffb309455182c593d4e6ea81" in text)
print(" - Smartlink (budgetezy.org):", "budgetezy.org/4/ae626546295ba9dbdec2ea24a521084c" in text)
print(" - Native Banner (container-f1180bd1a9f13152d2247022e3f6f1b0):", "container-f1180bd1a9f13152d2247022e3f6f1b0" in text)
print(" - Popunder script:", "capitalhospitals.org" in text)
print(" - SocialBar script:", "czernik.org/14/4d85a8908516d9c268b82f4a5df10c8a" in text)
print(" - CTA target URL (articles-mardi-materials-induced):", "articles-mardi-materials-induced.trycloudflare.com/match/401915378" in text)
