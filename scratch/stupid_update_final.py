
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def final_stupid_update():
    client = ConcurBrowserClient()
    report_name = 'Statement Report 06/16 - 07/31'
    justification = 'Required by bs37. Software used for research.'
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=client.session_file, viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        try:
            page.goto(f"{client.base_url}/nui/expense")
            page.locator(f"text='{report_name}'").first.click()
            page.wait_for_timeout(5000)
            
            for target_idx in [1, 2]:
                logger.info(f"STUPID UPDATE ROW {target_idx + 1}...")
                
                # Clear modals (safely)
                page.evaluate("document.querySelectorAll('.sapMDialog, [role=\"dialog\"], [data-nuiexp=\"timelineModal\"]').forEach(el => el.remove())")
                
                rows = [r for r in page.locator('tr').all() if 'Select expense' in r.inner_text()]
                row = rows[target_idx]
                
                # Select row
                row.locator('.sapMCb').first.click(force=True)
                page.locator("button:has-text('Edit')").first.click()
                page.wait_for_timeout(5000)
                
                # Tab navigation (human-like)
                page.keyboard.press('Tab')
                page.wait_for_timeout(500)
                page.keyboard.type('Software (OIT use only)')
                page.keyboard.press('Enter')
                page.wait_for_timeout(1000)
                
                # Tab to Purpose (usually around 10-12 tabs in this UI)
                for _ in range(12):
                    page.keyboard.press('Tab')
                    page.wait_for_timeout(100)
                
                page.keyboard.type(justification)
                page.keyboard.press('Tab')
                page.keyboard.type(justification)
                
                # Save
                page.locator("button:has-text('Save')").first.click()
                page.wait_for_timeout(3000)
                logger.info(f"STUPID ROW {target_idx + 1} SAVED")
                
        except Exception as e:
            logger.error(f"Stupid update failed: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    final_stupid_update()
