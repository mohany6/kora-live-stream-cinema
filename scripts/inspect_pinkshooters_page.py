import urllib.request, ssl, re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request(
    'https://24.pinkshooters.com/bein-sports-hd-1',
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
)

try:
    res = urllib.request.urlopen(req, context=ctx, timeout=8)
    html = res.read().decode('utf-8', errors='ignore')
    print('Status:', res.status)
    print('HTML len:', len(html))
    iframes = re.findall(r'<iframe[^>]*src=[\'"]([^\'"]+)[\'"]', html)
    print('Iframes:', iframes)
    for line in html.splitlines():
        if any(k in line.lower() for k in ['iframe', 'albaplayer', 'source', 'video']):
            print('Line:', line.strip()[:160])
except Exception as e:
    print('Error:', e)
