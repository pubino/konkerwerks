
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def modern_update():
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
            
            # Wait for the data grid
            page.wait_for_selector(".sapcnqr-data-grid-list__row", timeout=20000)
            page.wait_for_timeout(5000)
            
            # Dismiss modals
            page.evaluate("() => { document.querySelectorAll('.sapMDialog, [role=\"dialog\"], [data-nuiexp=\"timelineModal\"]').forEach(el => el.remove()); }")
            
            for target_idx in [1, 2]: # Apple and GoDaddy
                logger.info(f"MODERN UPDATE ROW {target_idx + 1}...")
                
                rows = page.locator(".sapcnqr-data-grid-list__row").all()
                if len(rows) < 3:
                    logger.error(f"Found only {len(rows)} rows. Expected at least 3.")
                    break
                    
                row = rows[target_idx]
                # Click the row to open it
                row.click(force=True)
                page.wait_for_timeout(5000)
                
                # Check if Edit button is needed or if it opened directly
                edit_btn = page.locator("button:has-text('Edit')").first
                if edit_btn.count() > 0 and edit_btn.is_visible():
                    edit_btn.click()
                    page.wait_for_timeout(3000)
                
                # 1. Update Expense Type
                type_label = page.locator("label:has-text('Expense Type')").first
                type_id = type_label.get_attribute('for')
                type_inp = page.locator(f"#{type_id}")
                
                type_inp.click()
                type_inp.fill("")
                type_inp.type("Software (OIT use only)", delay=100)
                page.wait_for_timeout(2000)
                
                # Click suggestion
                suggestion = page.locator(".sapMStandardListItem:has-text('Software (OIT use only)')").first
                if suggestion.count() > 0:
                    suggestion.click()
                else:
                    page.keyboard.press("Enter")
                page.wait_for_timeout(1000)
                
                # 2. Update Justifications
                p_label = page.locator("label:has-text('Business Purpose')").first
                p_id = p_label.get_attribute('for')
                page.locator(f"#{p_id}").fill(justification)
                
                c_label = page.locator("label:has-text('Comment')").first
                c_id = c_label.get_attribute('for')
                page.locator(f"#{c_id}").fill(justification)
                
                # 3. Save
                page.locator("button:has-text('Save')").first.click()
                page.wait_for_timeout(5000)
                logger.info(f"MODERN ROW {target_idx + 1} SAVED")
                
                # Back to list if needed
                back_btn = page.locator(".sapcnqr-icon--nav-back, button:has-text('Cancel')").first
                if back_btn.count() > 0 and back_btn.is_visible():
                    back_btn.click()
                    page.wait_for_timeout(2000)
                
        except Exception as e:
            logger.error(f"Modern update failed: {e}")
            page.screenshot(path="screenshots/modern_failed.png")
        finally:
            browser.close()

if __name__ == '__main__':
    modern_update()
