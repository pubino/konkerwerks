
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def truth_check_update():
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
            
            # 1. Update Anthropic
            logger.info("UPDATING ANTHROPIC FOR TRUTH CHECK...")
            checkboxes = page.locator(".sapMCb, [type='checkbox']").all()
            cb = checkboxes[1]
            cb.click(force=True)
            page.wait_for_timeout(2000)
            
            page.locator("button:has-text('Edit')").first.click()
            page.wait_for_selector("#businessPurpose", timeout=10000)
            
            # Inject
            for field_id in ["businessPurpose", "comment"]:
                page.evaluate(f"([id, val]) => {{ const el = document.getElementById(id); if (el) el.value = val; }}", [field_id, justification])
            
            page.locator("button:has-text('Save Expense')").filter(visible=True).first.click()
            page.wait_for_timeout(5000)
            logger.info("Save Expense clicked.")
            
            # 2. VERIFY BY RE-OPENING
            logger.info("RE-OPENING TO VERIFY...")
            page.locator("text='ANTHROPIC'").first.click()
            page.wait_for_timeout(5000)
            
            for field_id in ["businessPurpose", "comment"]:
                val = page.locator(f"#{field_id}").input_value()
                logger.info(f"  Field {field_id} actual UI value: '{val}'")
            
            page.screenshot(path="screenshots/truth_check_anthropic.png")
            logger.info("Verification screenshot taken.")
            
        except Exception as e:
            logger.error(f"Truth check failed: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    truth_check_update()
