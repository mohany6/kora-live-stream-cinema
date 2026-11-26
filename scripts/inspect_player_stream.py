import urllib.request
import ssl
import re

url = "https://22.shootinggames1.com/albaplayer/bein-sports-hd-4/"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request(
    url,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://23.pinkshooters.com/",
    }
)

try:
    with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        print(f"Status: {resp.status}")
        print(f"Length: {len(html)}")
        
        # Look for m3u8
        m3u8 = re.findall(r'["\'](https?://[^"\']*\.m3u8[^"\']*)["\']', html)
        print("m3u8 found:", m3u8)

        # Look for Clappr / Hls
        print("Clappr detected:", "clappr" in html.lower())
        print("Hls.js detected:", "hls.js" in html.lower() or "hls.min.js" in html.lower())
        print("PlayerJS detected:", "playerjs" in html.lower())

        # Scripts
        scripts = re.findall(r'<script[^>]*src=["\'](.*?)["\']', html, re.IGNORECASE)
        print("Scripts in albaplayer:")
        for s in scripts:
            print(" ", s)

        # Look for inline script setting source
        sources = re.findall(r'(?:file|source|src)\s*:\s*["\'](https?://[^"\']+)["\']', html)
        print("Sources found:", sources)

except Exception as e:
    print("Error:", e)
