import httpx

print("=== CHECKING BLOGGER LIVE HOMEPAGE ===")
r_home = httpx.get("https://kora-live-to.blogspot.com", follow_redirects=True, timeout=10)
print(f"Blogger Home Status: {r_home.status_code}")
home_text = r_home.text
print(" - Popunder in live Blogger:", "capitalhospitals.org" in home_text)
print(" - SocialBar in live Blogger:", "czernik.org/14/4d85a8908516d9c268b82f4a5df10c8a" in home_text)
print(" - 728x90 Banner in live Blogger:", "6703ea03ffb309455182c593d4e6ea81" in home_text)
print(" - 320x50 Banner in live Blogger:", "1cdf29d3af257663a92ffa6b5207a68a" in home_text)
print(" - Native Banner in live Blogger:", "container-f1180bd1a9f13152d2247022e3f6f1b0" in home_text)
print(" - Smartlink in live Blogger:", "budgetezy.org/4/ae626546295ba9dbdec2ea24a521084c" in home_text)

print("\n=== CHECKING LIVE BLOGGER POST (Sabah FK vs Barcelona) ===")
r_post = httpx.get("https://kora-live-to.blogspot.com/2026/11/sabah-fk.html", follow_redirects=True, timeout=10)
print(f"Blogger Post Status: {r_post.status_code}")
post_text = r_post.text
print(" - SportsEvent Schema in live post:", "SportsEvent" in post_text)
print(" - Match CTA button in live post:", "articles-mardi-materials-induced.trycloudflare.com" in post_text or "trycloudflare.com" in post_text)
print(" - 728x90 Banner in live post:", "6703ea03ffb309455182c593d4e6ea81" in post_text)
print(" - Smartlink in live post:", "budgetezy.org/4/ae626546295ba9dbdec2ea24a521084c" in post_text)
print(" - Native Banner in live post:", "container-f1180bd1a9f13152d2247022e3f6f1b0" in post_text)

print("\n=== CHECKING CLOUDFLARE LIVE MATCH PLAYER PAGE ===")
r_player = httpx.get("https://articles-mardi-materials-induced.trycloudflare.com/match/401915378", verify=False, timeout=10)
print(f"Cloudflare Player Status: {r_player.status_code}")
player_text = r_player.text
print(" - Popunder in Cloudflare SPA:", "capitalhospitals.org" in player_text)
print(" - SocialBar in Cloudflare SPA:", "czernik.org/14/4d85a8908516d9c268b82f4a5df10c8a" in player_text)
print(" - Title in Cloudflare SPA:", "كورة لايف" in player_text)
