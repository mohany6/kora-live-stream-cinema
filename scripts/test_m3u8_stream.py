import urllib.request, ssl, re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://24.shootinggames1.com/albaplayer/bein-sports-hd-1/?serv=0'
req = urllib.request.Request(
    url,
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://24.pinkshooters.com/'
    }
)

res = urllib.request.urlopen(req, context=ctx, timeout=10)
html = res.read().decode('utf-8', errors='ignore')

# Check if m3u8 stream or player works
m3u8_matches = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', html)
print('Direct M3U8 found inside:', m3u8_matches)

# Test if the m3u8 is accessible
if m3u8_matches:
    m3u8_url = m3u8_matches[0]
    print('Testing direct m3u8:', m3u8_url)
    m_req = urllib.request.Request(
        m3u8_url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://24.shootinggames1.com/'
        }
    )
    try:
        m_res = urllib.request.urlopen(m_req, context=ctx, timeout=10)
        print('M3U8 status:', m_res.status)
        print('M3U8 content start:\n', m_res.read().decode('utf-8', errors='ignore')[:300])
    except Exception as e:
        print('M3U8 direct error:', e)
