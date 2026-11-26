import urllib.request, ssl, re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://24.shootinggames1.com/albaplayer/bein-sports-xtra-1/'
try:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://24.pinkshooters.com/'
    })
    res = urllib.request.urlopen(req, context=ctx, timeout=10)
    html = res.read().decode('utf-8', errors='ignore')
    print('Tier 3 Player Status:', res.status)
    print('Length:', len(html))
    
    # Check player libraries and streams
    m3u8 = re.findall(r'https?://[^\'"\s]+\.m3u8[^\'"\s]*', html)
    print('M3U8 URLs found:', m3u8)
    
    scripts = re.findall(r'<script[^>]*src=[\'"](.*?)[\'"]', html)
    print('Scripts in albaplayer:', scripts)
    
    # Check ad tags in player
    ad_signatures = ['adsterra', 'pop', 'atOptions', 'monetag', 'propeller', 'click', 'banner']
    for a in ad_signatures:
        if a in html.lower():
            print('Found in player:', a)
except Exception as e:
    print('Error:', e)
