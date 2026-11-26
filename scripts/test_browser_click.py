from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.on('console', lambda msg: print('Console:', msg.text))
    page.on('pageerror', lambda err: print('Page error:', err))
    page.on('requestfailed', lambda req: print('Req failed:', req.url, req.failure))
    
    page.goto('https://surprising-bluetooth-violation-salt.trycloudflare.com/match/401915378', timeout=15000)
    page.wait_for_timeout(2000)
    
    # Click each pill and see
    pills = page.locator('button[role="tab"]').all()
    print('Tabs found:', len(pills))
    for i, pill in enumerate(pills):
        text = pill.inner_text()
        print(f'Tab {i}: {text}')
        if 'Alba' in text:
            print(f'Clicking Tab {i} ({text})...')
            pill.click()
            page.wait_for_timeout(2000)
            
    browser.close()
