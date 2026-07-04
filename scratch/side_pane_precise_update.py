
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def side_pane_precise_update():
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
            page.wait_for_timeout(10000)
            
            for vendor in ["APPLE.COM/BILL", "GODADDY#4117118402"]:
                logger.info(f"UPDATING {vendor}...")
                page.evaluate("() => { document.querySelectorAll('.sapMDialog, [role=\"dialog\"], [data-nuiexp=\"timelineModal\"]').forEach(el => el.remove()); }")
                
                # 1. Click Checkbox
                v_loc = page.locator(f"text='{vendor}'").first
                row = page.locator(".sapcnqr-data-grid-list__row, tr").filter(has=v_loc).first
                checkbox = row.locator(".sapMCb, [type='checkbox']").first
                checkbox.click(force=True)
                page.wait_for_timeout(2000)
                
                # 2. Click Edit
                page.locator("button:has-text('Edit')").first.click()
                page.wait_for_timeout(5000)
                
                # 3. Expense Type (Targeting the side panel DIV)
                type_field = page.locator("[data-nuiexp='field-expenseType']").first
                type_field.click()
                page.wait_for_timeout(2000)
                page.keyboard.type("Software (OIT use only)", delay=100)
                page.wait_for_timeout(2000)
                
                # Click suggestion in the popover
                suggestion = page.locator(".sapMStandardListItem:has-text('Software (OIT use only)')").first
                if suggestion.count() > 0:
                    suggestion.click()
                else:
                    page.keyboard.press("Enter")
                page.wait_for_timeout(1000)
                
                # 4. Justifications
                page.locator("#businessPurpose").fill(justification)
                page.locator("#comment").fill(justification)
                
                # 5. Save
                page.locator("button:has-text('Save')").first.click()
                page.wait_for_timeout(5000)
                logger.info(f"{vendor} SAVED")
                
                # Deselect for next row
                checkbox.click(force=True)
                page.wait_for_timeout(2000)
            
            logger.info("SIDE PANE UPDATES COMPLETED")
            
        except Exception as e:
            logger.error(f"Update failed: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    side_pane_precise_update()
