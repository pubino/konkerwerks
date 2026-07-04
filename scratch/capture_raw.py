
import os
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

def capture_raw_source():
    client = ConcurBrowserClient()
    report_name = "Statement Report 06/16 - 07/31"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=client.session_file, viewport={"width": 1280, "height": 800})
        page = context.new_page()
        try:
            page.goto(f"{client.base_url}/nui/expense")
            page.wait_for_selector(f"text='{report_name}'", timeout=20000)
            page.locator(f"text='{report_name}'").first.click()
            page.wait_for_timeout(10000)
            
            # Dismiss all modals
            page.evaluate("document.querySelectorAll('.sapMDialog, [role=\"dialog\"], [data-nuiexp=\"timelineModal\"]').forEach(el => el.remove())")
            
            # Save HTML
            html = page.content()
            with open("raw_concur.html", "w") as f:
                f.write(html)
            
            # Take screenshot
            page.screenshot(path="screenshots/raw_concur_view.png")
            print("RAW_DATA_CAPTURED")
        finally:
            browser.close()

if __name__ == "__main__":
    capture_raw_source()
