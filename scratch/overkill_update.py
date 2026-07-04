
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def overkill_update():
    client = ConcurBrowserClient()
    report_name = 'Statement Report 06/16 - 07/31'
    justification = 'Required by bs37. Software used for research.'
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=client.session_file, viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        try:
            page.goto(f"{client.base_url}/nui/expense")
            page.wait_for_selector(f"text='{report_name}'", timeout=30000)
            page.locator(f"text='{report_name}'").first.click()
            page.wait_for_timeout(10000)
            
            for target_idx in [1, 2]: # Apple and GoDaddy
                logger.info(f"OVERKILL UPDATE ROW {target_idx + 1}...")
                
                # 1. Clear Modals
                page.evaluate("() => { document.querySelectorAll('.sapMDialog, [role=\"dialog\"], [data-nuiexp=\"timelineModal\"], .sapUiBLB').forEach(el => el.remove()); }")
                
                # 2. Find and Open Row
                rows = page.locator(".sapcnqr-data-grid-list__row, tr").all()
                valid_rows = [r for r in rows if "Select expense" in (r.inner_text() or "")]
                row = valid_rows[target_idx]
                
                row.scroll_into_view_if_needed()
                row.click(force=True)
                page.wait_for_timeout(2000)
                row.dblclick(force=True)
                page.wait_for_timeout(5000)
                
                # 3. Ensure Edit mode
                edit_btn = page.locator("button:has-text('Edit')").first
                if edit_btn.count() > 0 and edit_btn.is_visible():
                    edit_btn.click()
                    page.wait_for_timeout(5000)
                
                # 4. Fill Expense Type
                try:
                    type_label = page.locator("label:has-text('Expense Type')").first
                    type_label.wait_for(state="visible", timeout=10000)
                    type_id = type_label.get_attribute('for')
                    type_inp = page.locator(f"#{type_id}")
                    type_inp.click()
                    type_inp.fill("")
                    type_inp.type("Software (OIT use only)", delay=150)
                    page.wait_for_timeout(2000)
                    page.locator(".sapMStandardListItem:has-text('Software (OIT use only)')").first.click()
                except Exception as e:
                    logger.warning(f"  Type field fail, trying keyboard: {e}")
                    page.keyboard.press("Tab")
                    page.keyboard.type("Software (OIT use only)")
                    page.keyboard.press("Enter")
                
                # 5. Fill Justifications
                for label_text in ["Business Purpose", "Comment"]:
                    try:
                        lbl = page.locator(f"label:has-text('{label_text}')").first
                        l_id = lbl.get_attribute('for')
                        page.locator(f"#{l_id}").fill(justification)
                    except:
                        page.keyboard.press("Tab")
                        page.keyboard.type(justification)
                
                # 6. Save
                save_btn = page.locator("button:has-text('Save')").first
                save_btn.click(force=True)
                page.wait_for_timeout(5000)
                logger.info(f"OVERKILL ROW {target_idx + 1} SAVED")
                
                # Back to list
                page.keyboard.press("Escape")
                page.wait_for_timeout(2000)
            
            logger.info("OVERKILL COMPLETED")
            
        except Exception as e:
            logger.error(f"Overkill failed: {e}")
            page.screenshot(path="screenshots/overkill_failed.png")
        finally:
            browser.close()

if __name__ == '__main__':
    overkill_update()
