import urllib.request, ssl, re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://1.korasimo.xyz/splayer/Live4.php'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Referer': 'https://24.shootinggames1.com/'})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        html = r.read().decode('utf-8', errors='ignore')
        print(f"Live4.php length: {len(html)}")
        for m in re.finditer(r'(https?://[^\s"\'<>]+)', html):
            u = m.group(1)
            if any(k in u.lower() for k in ['.m3u8', 'live', 'stream', 'hls', 'cdn']):
                print("  URL:", u)
        
        # Check script tags
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        print(f"Found {len(scripts)} scripts")
        for s in scripts:
            if 'player' in s.lower() or 'm3u8' in s.lower() or 'source' in s.lower() or 'eval' in s.lower():
                print("Script snippet:", s.strip()[:300])
except Exception as e:
    print("Error:", e)
