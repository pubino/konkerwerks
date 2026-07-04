
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def brute_force_dropdown():
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
                logger.info(f"BRUTE FORCE UPDATING {vendor}...")
                page.evaluate("() => { document.querySelectorAll('.sapMDialog, [role=\"dialog\"], [data-nuiexp=\"timelineModal\"]').forEach(el => el.remove()); }")
                
                # 1. Click Checkbox
                v_loc = page.locator(f"text='{vendor}'").first
                row = page.locator(".sapcnqr-data-grid-list__row, tr").filter(has=v_loc).first
                checkbox = row.locator(".sapMCb, [type='checkbox']").first
                checkbox.click(force=True)
                page.wait_for_timeout(2000)
                
                # 2. Click Edit
                page.locator("button:has-text('Edit')").first.click()
                page.wait_for_selector("[data-nuiexp='field-expenseType']", timeout=10000)
                
                # 3. Expense Type
                type_field = page.locator("[data-nuiexp='field-expenseType']").first
                type_field.click()
                page.wait_for_timeout(2000)
                page.keyboard.type("Software (OIT use only)", delay=150)
                page.wait_for_timeout(5000)
                
                # Brute force search for the suggestion
                suggestion = page.locator("text='Software (OIT use only)'").last
                if suggestion.is_visible():
                    logger.info("  Suggestion found by text, clicking...")
                    suggestion.click(force=True)
                else:
                    logger.warning("  Text locator failed, searching all options...")
                    options = page.locator("[role='option'], [role='listitem'], .sapMStandardListItem").all()
                    for opt in options:
                        if "Software (OIT use only)" in opt.inner_text():
                            opt.click(force=True)
                            logger.info("  Option clicked!")
                            break
                
                page.wait_for_timeout(2000)
                
                # 4. Justifications
                page.locator("#businessPurpose").fill(justification)
                page.locator("#comment").fill(justification)
                
                # 5. Save and Wait
                page.locator("button:has-text('Save')").first.click()
                logger.info("  Save clicked, waiting...")
                page.wait_for_selector("[data-nuiexp='field-expenseType']", state="hidden", timeout=30000)
                logger.info(f"  {vendor} BRUTE FORCE SAVED")
                
                # Deselect
                checkbox.click(force=True)
                page.wait_for_timeout(2000)
            
            logger.info("BRUTE FORCE COMPLETED")
            
        except Exception as e:
            logger.error(f"Update failed: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    brute_force_dropdown()
