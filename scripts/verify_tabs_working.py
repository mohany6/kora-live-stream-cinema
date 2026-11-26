import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        file_url = 'file:///C:/Users/Mohany/Desktop/football-live-score-platform/blogger_theme/theme_preview.html'
        await page.goto(file_url, wait_until='load')
        await asyncio.sleep(1)

        # Check tabs function
        for tab, expected_first in [('yesterday', 'Bodo/Glimt'), ('today', 'Sabah FK'), ('tomorrow', 'الفتح')]:
            await page.click('#dayTab_' + tab)
            await asyncio.sleep(0.5)
            first_team = await page.evaluate("() => document.querySelector('#matchesContainer .team-cell.home .team-name')?.innerText")
            title = await page.evaluate("() => document.getElementById('sectionScheduleTitle')?.innerText")
            cards_count = await page.evaluate("() => document.querySelectorAll('#matchesContainer .match-row-card').length")
            print(f'Tab {tab} -> Title: {title}, First Team: {first_team}, Cards: {cards_count}')
            assert cards_count > 0, f'No cards for {tab}'
            assert expected_first in first_team, f'Expected {expected_first} in {first_team}'

        print('SUCCESS: ALL 3 TABS (yesterday, today, tomorrow) VERIFIED WORKING 100%!')
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
