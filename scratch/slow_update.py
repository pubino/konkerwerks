
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def slow_update():
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
            
            for target_idx in [1, 2]: # Apple and GoDaddy
                logger.info(f"SLOW UPDATE ROW {target_idx + 1}...")
                
                # Dismiss modals
                page.evaluate("() => { document.querySelectorAll('.sapMDialog, [role=\"dialog\"], [data-nuiexp=\"timelineModal\"]').forEach(el => el.remove()); }")
                
                # Find rows
                all_rows = page.locator("tr").all()
                valid_rows = [r for r in all_rows if "Select expense" in (r.inner_text() or "")]
                row = valid_rows[target_idx]
                
                row.locator('.sapMCb').first.click(force=True)
                page.locator("button:has-text('Edit')").first.click()
                page.wait_for_timeout(5000)
                
                # 1. Update Expense Type (with dropdown click)
                type_label = page.locator("label:has-text('Expense Type')").first
                type_id = type_label.get_attribute('for')
                type_inp = page.locator(f"#{type_id}")
                
                type_inp.click()
                type_inp.fill("") # Clear it
                type_inp.type("Software (OIT use only)", delay=100)
                page.wait_for_timeout(2000)
                # Click the suggestion in the popover
                page.locator(".sapMStandardListItem:has-text('Software (OIT use only)')").first.click()
                page.wait_for_timeout(1000)
                
                # 2. Update Justifications
                p_label = page.locator("label:has-text('Business Purpose')").first
                p_id = p_label.get_attribute('for')
                page.locator(f"#{p_id}").fill(justification)
                
                c_label = page.locator("label:has-text('Comment')").first
                c_id = c_label.get_attribute('for')
                page.locator(f"#{c_id}").fill(justification)
                
                # 3. Save and Verify
                page.screenshot(path=f"screenshots/slow_filled_{target_idx+1}.png")
                page.locator("button:has-text('Save')").first.click()
                page.wait_for_timeout(5000)
                page.screenshot(path=f"screenshots/slow_saved_{target_idx+1}.png")
                logger.info(f"SLOW ROW {target_idx + 1} COMPLETED")
                
        except Exception as e:
            logger.error(f"Slow update failed: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    slow_update()
