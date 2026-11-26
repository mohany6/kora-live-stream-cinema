import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f'[{msg.type}] {msg.text}'))
        page.on('pageerror', lambda err: console_logs.append(f'[PAGE ERROR] {err}'))

        file_url = 'file:///C:/Users/Mohany/Desktop/football-live-score-platform/blogger_theme/theme_preview.html'
        print('Navigating to', file_url)
        await page.goto(file_url, wait_until='networkidle')
        await asyncio.sleep(1)

        # Initial check
        title_today = await page.evaluate("() => document.getElementById('sectionScheduleTitle')?.innerText")
        cards_today = await page.evaluate("() => document.querySelectorAll('#matchesContainer .match-row-card').length")
        first_home = await page.evaluate("() => document.querySelector('#matchesContainer .team-cell.home .team-name')?.innerText")
        print(f'Today -> Title: {title_today}, Cards: {cards_today}, First Home: {first_home}')

        # Click Yesterday
        print('Clicking #dayTab_yesterday...')
        await page.click('#dayTab_yesterday')
        await asyncio.sleep(1)
        title_yest = await page.evaluate("() => document.getElementById('sectionScheduleTitle')?.innerText")
        sub_yest = await page.evaluate("() => document.querySelector('.league-group-title')?.innerText")
        cards_yest = await page.evaluate("() => document.querySelectorAll('#matchesContainer .match-row-card').length")
        first_yest = await page.evaluate("() => document.querySelector('#matchesContainer .team-cell.home .team-name')?.innerText")
        print(f'Yesterday -> Title: {title_yest}, Sub: {sub_yest}, Cards: {cards_yest}, First Home: {first_yest}')

        # Click Tomorrow
        print('Clicking #dayTab_tomorrow...')
        await page.click('#dayTab_tomorrow')
        await asyncio.sleep(1)
        title_tom = await page.evaluate("() => document.getElementById('sectionScheduleTitle')?.innerText")
        sub_tom = await page.evaluate("() => document.querySelector('.league-group-title')?.innerText")
        cards_tom = await page.evaluate("() => document.querySelectorAll('#matchesContainer .match-row-card').length")
        first_tom = await page.evaluate("() => document.querySelector('#matchesContainer .team-cell.home .team-name')?.innerText")
        print(f'Tomorrow -> Title: {title_tom}, Sub: {sub_tom}, Cards: {cards_tom}, First Home: {first_tom}')

        print('=== Console Logs ===')
        for l in console_logs:
            print(l)
        print('Any errors?', any('ERROR' in l for l in console_logs))

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
