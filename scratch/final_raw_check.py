
import logging
import os
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def take_final_diagnostic_screenshot():
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
            page.wait_for_timeout(10000) # Give it plenty of time
            
            # Take screenshot before ANY modal removal
            client._take_screenshot(page, "final_raw_view")
            
            # Now remove modals and take another
            page.evaluate("document.querySelectorAll('.sapMDialog, [role=\"dialog\"], [data-nuiexp=\"timelineModal\"]').forEach(el => el.remove())")
            page.wait_for_timeout(2000)
            client._take_screenshot(page, "final_clean_view")
            
            # Print row text
            rows = page.locator("tr").all()
            for i, r in enumerate(rows):
                logger.info(f"ROW {i}: {r.inner_text().replace('\\n', ' ')}")
                
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    take_final_diagnostic_screenshot()
