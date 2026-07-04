
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def final_attempt():
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
            
            # Wait for modern grid
            page.wait_for_selector(".sapcnqr-data-grid-list__row", timeout=20000)
            page.wait_for_timeout(5000)
            
            # Dismiss modals
            page.evaluate("() => { document.querySelectorAll('.sapMDialog, [role=\"dialog\"], [data-nuiexp=\"timelineModal\"]').forEach(el => el.remove()); }")
            
            for target_idx in [1, 2]: # Apple and GoDaddy
                logger.info(f"UPDATING ROW {target_idx + 1}...")
                
                # Re-find rows to avoid staleness
                rows = page.locator(".sapcnqr-data-grid-list__row").all()
                row = rows[target_idx]
                
                # Click to open
                row.click(force=True)
                page.wait_for_timeout(5000)
                
                # If Edit button exists, click it
                edit_btn = page.locator("button:has-text('Edit')").first
                if edit_btn.count() > 0 and edit_btn.is_visible():
                    edit_btn.click()
                    page.wait_for_timeout(3000)
                
                # 1. Expense Type
                type_label = page.locator("label:has-text('Expense Type')").first
                type_id = type_label.get_attribute('for')
                type_inp = page.locator(f"#{type_id}")
                
                type_inp.click()
                type_inp.fill("")
                type_inp.type("Software (OIT use only)", delay=100)
                page.wait_for_timeout(2000)
                
                # Click the suggestion
                suggestion = page.locator(".sapMStandardListItem:has-text('Software (OIT use only)')").first
                if suggestion.count() > 0:
                    suggestion.click()
                else:
                    page.keyboard.press("Enter")
                page.wait_for_timeout(1000)
                
                # 2. Justifications
                p_id = page.locator("label:has-text('Business Purpose')").first.get_attribute('for')
                page.locator(f"#{p_id}").fill(justification)
                
                c_id = page.locator("label:has-text('Comment')").first.get_attribute('for')
                page.locator(f"#{c_id}").fill(justification)
                
                # 3. Save
                page.locator("button:has-text('Save')").first.click()
                page.wait_for_timeout(5000)
                logger.info(f"ROW {target_idx + 1} SAVED")
                
                # Ensure we are back at the list
                back_btn = page.locator(".sapcnqr-icon--nav-back, button:has-text('Cancel')").first
                if back_btn.count() > 0 and back_btn.is_visible():
                    back_btn.click()
                    page.wait_for_timeout(2000)
            
            logger.info("ALL UPDATES COMPLETED")
            
        except Exception as e:
            logger.error(f"Update failed: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    final_attempt()
