
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_expense_fix():
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
            
            # Dismiss modals
            page.evaluate("() => { document.querySelectorAll('.sapMDialog, [role=\"dialog\"], [data-nuiexp=\"timelineModal\"]').forEach(el => el.remove()); }")
            
            for i in range(3): # Anthropic, Apple, GoDaddy
                logger.info(f"FIXING ROW {i}...")
                
                checkboxes = page.locator(".sapMCb, [type='checkbox']").all()
                cb = checkboxes[i + 1]
                cb.click(force=True)
                page.wait_for_timeout(2000)
                
                page.locator("button:has-text('Edit')").first.click()
                page.wait_for_timeout(5000)
                
                # Fill justifications using label clicks
                for label_text in ["Business Purpose", "Comment"]:
                    label = page.locator(f"label:has-text('{label_text}')").first
                    if label.count() > 0:
                        label.click()
                        page.wait_for_timeout(1000)
                        page.keyboard.press("Control+A")
                        page.keyboard.press("Backspace")
                        page.keyboard.type(justification, delay=50)
                
                # CLICK THE VISIBLE SAVE EXPENSE BUTTON
                save_btn = page.locator("button:has-text('Save Expense')").filter(visible=True).first
                save_btn.click()
                
                # Wait for panel to close
                page.wait_for_selector("button:has-text('Save Expense')", state="hidden", timeout=30000)
                logger.info(f"  ROW {i} SAVED")
                
                cb.click(force=True)
                page.wait_for_timeout(2000)
            
            logger.info("SAVE EXPENSE FIX COMPLETED")
            
        except Exception as e:
            logger.error(f"Fix failed: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    save_expense_fix()
