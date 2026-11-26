import urllib.request, ssl, re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

channels = [
    'bein-sports-hd-1',
    'bein-sports-hd-2',
    'bein-sports-hd-3',
    'bein-sports-hd-4',
    'bein-sports-hd-5',
    'bein-sports-hd-6',
    'bein-sports-hd-8',
]

for ch in channels:
    url = f'https://24.pinkshooters.com/{ch}'
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        res = urllib.request.urlopen(req, context=ctx, timeout=8)
        html = res.read().decode('utf-8', errors='ignore')
        # Find iframes
        iframes = re.findall(r'<iframe[^>]*src=[\'"]([^\'"]+)[\'"]', html)
        print(f'{ch} -> iframes: {iframes}')
        
        # If shootinggames iframe found, fetch it
        for ifr in iframes:
            try:
                sub_req = urllib.request.Request(
                    ifr,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Referer': f'https://24.pinkshooters.com/{ch}'
                    }
                )
                sub_res = urllib.request.urlopen(sub_req, context=ctx, timeout=5)
                sub_html = sub_res.read().decode('utf-8', errors='ignore')
                m3u8 = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', sub_html)
                print(f'   -> m3u8: {m3u8}')
            except Exception as e:
                print(f'   -> error fetching {ifr}: {e}')
    except Exception as e:
        print(f'{ch} error: {e}')
