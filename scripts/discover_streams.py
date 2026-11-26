import urllib.request, ssl, re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

channels = [
    'bein-sports-hd-1',
    'bein-sports-hd-2',
    'bein-sports-hd-3',
    'bein-sports-xtra-1',
]

for ch in channels:
    url = f'https://24.shootinggames1.com/albaplayer/{ch}/?serv=0'
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://24.pinkshooters.com/'
            }
        )
        res = urllib.request.urlopen(req, context=ctx, timeout=8)
        html = res.read().decode('utf-8', errors='ignore')
        m3u8 = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', html)
        print(f'{ch}: {m3u8}')
    except Exception as e:
        print(f'{ch} error: {e}')
