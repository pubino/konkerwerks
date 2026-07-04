
import logging
import os
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_header_ui():
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
            page.wait_for_timeout(5000)
            
            # Dismiss modals
            page.evaluate("document.querySelectorAll('.sapMDialog, [role=\"dialog\"], [data-nuiexp=\"timelineModal\"]').forEach(el => el.remove())")
            
            # Try to open Report Header
            logger.info("Clicking Report Details...")
            page.locator("button:has-text('Report Details')").first.click()
            page.wait_for_timeout(2000)
            
            logger.info("Clicking Report Header...")
            page.locator("text='Report Header'").first.click()
            page.wait_for_timeout(3000)
            
            # Take screenshot of the result
            client._take_screenshot(page, "header_debug_ui")
            
            # Dump inputs
            inputs = page.locator("input, textarea, select").all()
            logger.info(f"Found {len(inputs)} input elements in current view.")
            for i, inp in enumerate(inputs):
                try:
                    id_attr = inp.get_attribute("id") or "no-id"
                    val = inp.input_value() or "no-val"
                    logger.info(f"Input {i}: ID='{id_attr}', Value='{val}'")
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Debug UI failed: {e}")
            client._take_screenshot(page, "header_debug_failed")
        finally:
            browser.close()

if __name__ == "__main__":
    debug_header_ui()
