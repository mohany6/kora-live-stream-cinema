from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.on('console', lambda msg: print('Console:', msg.text))
    page.on('pageerror', lambda err: print('Page error:', err))
    
    # Load test_proxied.html
    page.goto('file:///C:/Users/Mohany/Desktop/football-live-score-platform/test_proxied.html', timeout=10000)
    page.wait_for_timeout(3000)
    
    player = page.query_selector('#player')
    video = page.query_selector('video')
    print('Player div found:', bool(player))
    print('Video tag rendered inside Clappr:', bool(video))
    if video:
        print('Video src:', video.get_attribute('src'))
    
    browser.close()
