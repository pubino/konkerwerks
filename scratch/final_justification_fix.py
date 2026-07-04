
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def final_justification_fix():
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
            
            # Update GoDaddy (Class + Justification) and Apple (Justification)
            for vendor in ["GODADDY#4117118402", "APPLE.COM/BILL"]:
                logger.info(f"FIXING {vendor}...")
                page.evaluate("() => { document.querySelectorAll('.sapMDialog, [role=\"dialog\"], [data-nuiexp=\"timelineModal\"]').forEach(el => el.remove()); }")
                
                # 1. Select Row
                v_loc = page.locator(f"text='{vendor}'").first
                row = page.locator(".sapcnqr-data-grid-list__row, tr").filter(has=v_loc).first
                checkbox = row.locator(".sapMCb, [type='checkbox']").first
                checkbox.click(force=True)
                page.wait_for_timeout(2000)
                
                # 2. Click Edit
                page.locator("button:has-text('Edit')").first.click()
                page.wait_for_selector("[data-nuiexp='field-expenseType']", timeout=10000)
                
                # 3. Expense Type (Only for GoDaddy)
                if "GODADDY" in vendor:
                    type_field = page.locator("[data-nuiexp='field-expenseType']").first
                    type_field.click()
                    page.wait_for_timeout(2000)
                    page.keyboard.type("Software (OIT use only)", delay=100)
                    page.wait_for_timeout(5000)
                    suggestion = page.locator("text='Software (OIT use only)'").last
                    suggestion.click(force=True)
                    page.wait_for_timeout(2000)
                
                # 4. Justifications (Click and Type)
                for field_id in ["businessPurpose", "comment"]:
                    loc = page.locator(f"#{field_id}")
                    loc.click()
                    loc.fill("") # Clear first
                    loc.type(justification, delay=20)
                    logger.info(f"  {field_id} filled")
                
                # 5. Save and Wait
                save_btn = page.locator("button:has-text('Save')").first
                save_btn.click()
                logger.info("  Save clicked, waiting...")
                page.wait_for_selector("[data-nuiexp='field-expenseType']", state="hidden", timeout=30000)
                logger.info(f"  {vendor} FIXED AND SAVED")
                
                # Deselect
                checkbox.click(force=True)
                page.wait_for_timeout(2000)
            
            logger.info("ALL FIXES COMPLETED")
            
        except Exception as e:
            logger.error(f"Fix failed: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    final_justification_fix()
