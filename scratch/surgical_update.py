
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def surgical_update():
    client = ConcurBrowserClient()
    report_name = 'Statement Report 06/16 - 07/31'
    justification = 'Required by bs37. Software used for research.'
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=client.session_file, viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        try:
            page.goto(f"{client.base_url}/nui/expense")
            page.wait_for_selector(f"text='{report_name}'", timeout=20000)
            page.locator(f"text='{report_name}'").first.click()
            page.wait_for_timeout(5000)
            
            # Dismiss modals
            page.evaluate("document.querySelectorAll('.sapMDialog, [role=\"dialog\"], [data-nuiexp=\"timelineModal\"]').forEach(el => el.remove())")
            
            # Open Index 2
            rows = [r for r in page.locator('tr').all() if 'Select expense' in (r.inner_text() or '')]
            logger.info(f"Found {len(rows)} valid rows.")
            row = rows[1] # Apple
            row.locator('.sapMCb').first.click(force=True)
            page.locator("button:has-text('Edit')").first.click()
            page.wait_for_timeout(5000)
            
            # Fill fields using labels
            logger.info("Filling fields...")
            type_id = page.locator("label:has-text('Expense Type')").first.get_attribute('for')
            page.locator(f"#{type_id}").fill('Software (OIT use only)')
            page.keyboard.press('Enter')
            
            p_id = page.locator("label:has-text('Business Purpose')").first.get_attribute('for')
            page.locator(f"#{p_id}").fill(justification)
            
            c_id = page.locator("label:has-text('Comment')").first.get_attribute('for')
            page.locator(f"#{c_id}").fill(justification)
            
            # Screenshot of filled form
            page.screenshot(path="screenshots/surgical_filled.png")
            
            # Save
            page.locator("button:has-text('Save')").first.click()
            page.wait_for_timeout(3000)
            page.screenshot(path="screenshots/surgical_saved.png")
            logger.info("SURGICAL UPDATE COMPLETED")
            
        except Exception as e:
            logger.error(f"Surgical update failed: {e}")
            page.screenshot(path="screenshots/surgical_failed.png")
        finally:
            browser.close()

if __name__ == '__main__':
    surgical_update()
