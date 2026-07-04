
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def vendor_click_update():
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
                
                # Dismiss modals
                page.evaluate("() => { document.querySelectorAll('.sapMDialog, [role=\"dialog\"], [data-nuiexp=\"timelineModal\"]').forEach(el => el.remove()); }")
                
                # Click the checkbox for this vendor row to enable Edit
                v_loc = page.locator(f"text='{vendor}'").first
                row = page.locator(".sapcnqr-data-grid-list__row, tr").filter(has=v_loc).first
                checkbox = row.locator(".sapMCb, [type='checkbox']").first
                checkbox.click(force=True)
                page.wait_for_timeout(2000)
                
                # Ensure Edit mode
                edit_btn = page.locator("button:has-text('Edit')").first
                if edit_btn.count() > 0 and edit_btn.is_visible():
                    edit_btn.click()
                    page.wait_for_timeout(5000)
                
                # 1. Update Expense Type
                type_label = page.locator("label:has-text('Expense Type')").first
                type_label.wait_for(state="visible", timeout=10000)
                type_id = type_label.get_attribute('for')
                type_inp = page.locator(f"#{type_id}")
                
                type_inp.click()
                type_inp.fill("")
                type_inp.type("Software (OIT use only)", delay=150)
                page.wait_for_timeout(2000)
                
                # Click suggestion
                suggestion = page.locator(".sapMStandardListItem:has-text('Software (OIT use only)')").first
                if suggestion.count() > 0:
                    suggestion.click()
                else:
                    page.keyboard.press("Enter")
                page.wait_for_timeout(1000)
                
                # 2. Update Justifications
                p_id = page.locator("label:has-text('Business Purpose')").first.get_attribute('for')
                page.locator(f"#{p_id}").fill(justification)
                
                c_id = page.locator("label:has-text('Comment')").first.get_attribute('for')
                page.locator(f"#{c_id}").fill(justification)
                
                # 3. Save
                page.locator("button:has-text('Save')").first.click()
                page.wait_for_timeout(5000)
                logger.info(f"{vendor} SAVED")
                
                # Back to list if needed
                page.keyboard.press("Escape")
                page.wait_for_timeout(2000)
                
        except Exception as e:
            logger.error(f"Update failed: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    vendor_click_update()
