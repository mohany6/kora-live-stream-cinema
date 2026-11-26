import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f'[{msg.type}] {msg.text}'))
        
        reqs = []
        page.on('request', lambda r: reqs.append(r.url))
        
        failed = []
        page.on('requestfailed', lambda r: failed.append(f'{r.url} -> {r.failure}'))

        file_url = 'file:///C:/Users/Mohany/Desktop/football-live-score-platform/scripts/test_adsterra_clean.html'
        print('Navigating to', file_url)
        await page.goto(file_url, wait_until='networkidle')
        await asyncio.sleep(4)

        print('=== Console Logs ===')
        for l in console_logs:
            print(l)

        print('=== Failed Requests ===')
        for f in failed:
            print(f)

        print('=== All Requests ===')
        for r in reqs:
            print(r)

        dom_summary = await page.evaluate('''() => {
            return {
                iframes: Array.from(document.querySelectorAll('iframe')).map(i => i.outerHTML),
                nativeHTML: document.getElementById('container-f1180bd1a9f13152d2247022e3f6f1b0')?.innerHTML
            };
        }''')
        print('=== IFrames count ===', len(dom_summary['iframes']))
        for ifr in dom_summary['iframes']:
            print('IFRAME:', ifr[:200])
        print('=== Native HTML ===', dom_summary['nativeHTML'])

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
