
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def final_update():
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
            
            # Dismiss modals (SAFELY)
            page.evaluate("() => { document.querySelectorAll('.sapMDialog, [role=\"dialog\"], [data-nuiexp=\"timelineModal\"]').forEach(el => el.remove()); }")
            
            for target_idx in [1, 2]: # Apple and GoDaddy
                logger.info(f"UPDATING ROW {target_idx + 1}...")
                
                # Re-find rows to avoid staleness
                all_rows = page.locator("tr").all()
                valid_rows = [r for r in all_rows if "Select expense" in (r.inner_text() or "")]
                if target_idx >= len(valid_rows):
                    logger.error(f"Row {target_idx + 1} not found!")
                    continue
                
                row = valid_rows[target_idx]
                row.locator('.sapMCb').first.click(force=True)
                page.locator("button:has-text('Edit')").first.click()
                page.wait_for_timeout(5000)
                
                # Fill fields using labels
                type_label = page.locator("label:has-text('Expense Type')").first
                type_id = type_label.get_attribute('for')
                page.locator(f"#{type_id}").fill('Software (OIT use only)')
                page.keyboard.press('Enter')
                
                p_label = page.locator("label:has-text('Business Purpose')").first
                p_id = p_label.get_attribute('for')
                page.locator(f"#{p_id}").fill(justification)
                
                c_label = page.locator("label:has-text('Comment')").first
                c_id = c_label.get_attribute('for')
                page.locator(f"#{c_id}").fill(justification)
                
                # Save
                page.locator("button:has-text('Save')").first.click()
                page.wait_for_timeout(3000)
                logger.info(f"ROW {target_idx + 1} SAVED")
                
        except Exception as e:
            logger.error(f"Final update failed: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    final_update()
