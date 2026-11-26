import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1366, 'height': 768}
        )
        page = await context.new_page()
        page.on('console', lambda msg: print(f'[CONSOLE] {msg.type}: {msg.text}'))
        
        await page.goto('https://kora-live-to.blogspot.com', wait_until='load')
        await asyncio.sleep(2)
        
        at_options = await page.evaluate('() => window.atOptions')
        print('window.atOptions:', at_options)
        
        print('Clicking on page body...')
        await page.mouse.click(200, 200)
        await asyncio.sleep(3)
        
        print('Total pages open in browser context:', len(context.pages))
        for i, pg in enumerate(context.pages):
            print(f'Page {i}: {pg.url}')

        el_count = await page.evaluate('''() => {
            return {
                iframes: document.querySelectorAll('iframe').length,
                all_scripts: document.querySelectorAll('script').length,
                native_children: document.getElementById('container-f1180bd1a9f13152d2247022e3f6f1b0')?.children?.length
            };
        }''')
        print('Element counts:', el_count)

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
