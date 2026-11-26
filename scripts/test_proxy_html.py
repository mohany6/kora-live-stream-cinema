import urllib.request, ssl

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

res = urllib.request.urlopen(req, context=ctx, timeout=8)
html = res.read().decode('utf-8', errors='ignore')

# Add base tag if missing
if '<head>' in html:
    html = html.replace('<head>', '<head><base href="https://24.shootinggames1.com/" />')

with open('C:/Users/Mohany/Desktop/football-live-score-platform/test_proxied.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('Proxied HTML written, length:', len(html))
