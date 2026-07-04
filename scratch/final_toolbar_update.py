
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def final_toolbar_update():
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
                
                # 2. Click Toolbar Edit Button
                # This button is usually in a div with data-toolbar-region="end"
                edit_btn = page.locator("button.sapcnqr-button:has-text('Edit')").first
                if not edit_btn.is_enabled():
                    logger.warning("Edit button disabled, trying to re-click checkbox...")
                    checkbox.click(force=True)
                    page.wait_for_timeout(2000)
                
                edit_btn.click()
                page.wait_for_timeout(5000)
                
                # 3. Fill Fields (using label lookup)
                type_id = page.locator("label:has-text('Expense Type')").first.get_attribute('for')
                type_inp = page.locator(f"#{type_id}")
                type_inp.click()
                type_inp.fill("")
                type_inp.type("Software (OIT use only)", delay=100)
                page.wait_for_timeout(2000)
                page.locator(".sapMStandardListItem:has-text('Software (OIT use only)')").first.click()
                
                p_id = page.locator("label:has-text('Business Purpose')").first.get_attribute('for')
                page.locator(f"#{p_id}").fill(justification)
                
                c_id = page.locator("label:has-text('Comment')").first.get_attribute('for')
                page.locator(f"#{c_id}").fill(justification)
                
                # 4. Save
                page.locator("button:has-text('Save')").first.click()
                page.wait_for_timeout(5000)
                logger.info(f"{vendor} SAVED")
                
                # Deselect row for next iteration
                checkbox.click(force=True)
                page.wait_for_timeout(2000)
                
        except Exception as e:
            logger.error(f"Update failed: {e}")
            page.screenshot(path="screenshots/final_toolbar_failed.png")
        finally:
            browser.close()

if __name__ == '__main__':
    final_toolbar_update()
