import urllib.request, ssl, re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request(
    'https://kooralive.la/',
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
)

html = urllib.request.urlopen(req, context=ctx, timeout=8).read().decode('utf-8', errors='ignore')
links = re.findall(r'href=[\'"]([^\'"]*pinkshooters[^\'"]*)[\'"]', html)
print('Live match links on kooralive:', set(links))

# Also search for match titles
cards = re.findall(r'<div class="AY_Match[^"]*"[^>]*>.*?</div>\s*</div>\s*</div>', html, re.DOTALL)
print('Total match cards on kooralive:', len(cards))
for c in cards[:5]:
    teams = re.findall(r'<div class="TM_Name">([^<]+)</div>', c)
    href = re.findall(r'href=[\'"]([^\'"]+)[\'"]', c)
    status = re.findall(r'<div class=[\'"]MT_Stat[\'"]>([^<]+)</div>', c)
    time = re.findall(r'<span class=[\'"]MT_Time[\'"]>([^<]+)</span>', c)
    print(f'Teams: {teams} | Status: {status} | Time: {time} | Link: {href}')
