with open('data/kooralive_home.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re

blocks = html.split('<div class="AY_Match ')
print(f"Total blocks: {len(blocks) - 1}")
for b in blocks[1:]:
    status = b[:b.find('"')]
    tms = re.findall(r"<div class=['\"]TM_Name['\"]>([^<]+)</div>", b)
    home = tms[0] if len(tms) > 0 else 'Unknown'
    away = tms[1] if len(tms) > 1 else 'Unknown'
    
    # info
    info_items = re.findall(r"<li><span>([^<]+)</span></li>", b)
    channel = info_items[0] if len(info_items) > 0 else 'NoChannel'
    comm = info_items[1] if len(info_items) > 1 else ''
    
    link_m = re.search(r'<a\s+href=["\'](https?://[^"\']+)["\']', b)
    link = link_m.group(1) if link_m else 'None'
    print(f"[{status.strip()}] {home} vs {away} | Channel: {channel} | Comm: {comm} | Link: {link}")
