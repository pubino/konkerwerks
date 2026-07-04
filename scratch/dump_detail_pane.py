import asyncio
from playwright.async_api import async_playwright
import json
import os
import re

async def dump_detail_pane_v2():
    async with async_playwright() as p:
        # Load session
        session_file = "concur_session.json"
        if not os.path.exists(session_file):
            print(f"Error: {session_file} not found")
            return

        with open(session_file, "r") as f:
            session_data = json.load(f)

        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.add_cookies(session_data["cookies"])
        
        page = await context.new_page()
        print("Navigating to report...")
        await page.goto(session_data.get("url", "https://www.concursolutions.com/nui/expense"))
        
        # Wait for dashboard
        await page.wait_for_selector(".report-tile", timeout=30000)
        
        # Open the specific report
        report_name = "Statement Report 06/16 - 07/31"
        report_card = page.locator(".report-tile").filter(has_text=report_name).first
        await report_card.click()
        print(f"Clicked report: {report_name}")
        
        # Wait for list
        await page.wait_for_selector("[role='row'], .sapMTable tr, .sapcnqr-data-grid-list__row", timeout=30000)
        
        # Find the first transaction row
        # In Fiori, rows often have data-row-key or sapcnqr-data-grid-list__row class
        rows = page.locator(".sapcnqr-data-grid-list__row, [role='row'], .sapMTable tr").all()
        target_row = None
        for row in await rows:
            text = await row.text_content()
            if "ANTHROPIC" in text:
                target_row = row
                break
        
        if not target_row:
             print("Target row not found, using nth(1)")
             target_row = page.locator(".sapcnqr-data-grid-list__row, [role='row'], .sapMTable tr").nth(1)

        print("Clicking target row...")
        await target_row.click()
        
        # Try to wait for ANY input field to appear in the side panel
        print("Waiting for side panel fields...")
        try:
            await page.wait_for_selector("input, select, textarea, [data-nuiexp*='field']", timeout=15000)
            print("Fields detected!")
        except:
            print("Timeout waiting for fields, but continuing...")

        await page.wait_for_timeout(3000)
        
        # Dump whole page HTML
        html = await page.content()
        with open("scratch/page_with_details.html", "w") as f:
            f.write(html)
        print("Dumped page HTML to scratch/page_with_details.html")

        # Take a screenshot too
        await page.screenshot(path="scratch/details_view.png")
        print("Captured screenshot to scratch/details_view.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(dump_detail_pane_v2())
