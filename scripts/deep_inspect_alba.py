import urllib.request, ssl, re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request(
    'https://24.shootinggames1.com/albaplayer/bein-sports-hd-1/?serv=0',
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://24.pinkshooters.com/'
    }
)

html = urllib.request.urlopen(req, context=ctx, timeout=10).read().decode('utf-8', errors='ignore')
print('HTML len:', len(html))

# Print all iframe src
for m in re.finditer(r'<iframe[^>]*src=[\'"]([^\'"]+)[\'"]', html, re.I):
    print('Found iframe src:', m.group(1))

# Check script tags
for m in re.finditer(r'<script[^>]*src=[\'"]([^\'"]+)[\'"]', html, re.I):
    print('Script src:', m.group(1))

# Check body content lines
for line in html.splitlines():
    l = line.strip()
    if any(k in l.lower() for k in ['serv=', 'server', 'source', 'stream', 'token', 'eval']):
        print('Line:', l[:180])
