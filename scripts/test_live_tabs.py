import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f'[{msg.type}] {msg.text}'))
        page.on('pageerror', lambda err: console_logs.append(f'[PAGE ERROR] {err}'))

        print('Loading https://kora-live-to.blogspot.com ...')
        await page.goto('https://kora-live-to.blogspot.com', wait_until='networkidle')
        await asyncio.sleep(2)
        
        title = await page.evaluate("() => document.getElementById('sectionScheduleTitle')?.innerText")
        cards_before = await page.evaluate("() => document.querySelectorAll('#matchesContainer .match-row-card').length")
        first_home = await page.evaluate("() => document.querySelector('#matchesContainer .team-cell.home .team-name')?.innerText")
        print(f'Initial state -> Title: {title}, Cards: {cards_before}, First Team: {first_home}')
        
        print('Clicking #dayTab_yesterday ...')
        await page.click('#dayTab_yesterday')
        await asyncio.sleep(2)
        title_yest = await page.evaluate("() => document.getElementById('sectionScheduleTitle')?.innerText")
        cards_yest = await page.evaluate("() => document.querySelectorAll('#matchesContainer .match-row-card').length")
        first_yest = await page.evaluate("() => document.querySelector('#matchesContainer .team-cell.home .team-name')?.innerText")
        print(f'After Yesterday -> Title: {title_yest}, Cards: {cards_yest}, First Team: {first_yest}')

        print('Clicking #dayTab_tomorrow ...')
        await page.click('#dayTab_tomorrow')
        await asyncio.sleep(2)
        title_tom = await page.evaluate("() => document.getElementById('sectionScheduleTitle')?.innerText")
        cards_tom = await page.evaluate("() => document.querySelectorAll('#matchesContainer .match-row-card').length")
        first_tom = await page.evaluate("() => document.querySelector('#matchesContainer .team-cell.home .team-name')?.innerText")
        print(f'After Tomorrow -> Title: {title_tom}, Cards: {cards_tom}, First Team: {first_tom}')

        print('=== Console Logs ===')
        for l in console_logs:
            print(l)

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
