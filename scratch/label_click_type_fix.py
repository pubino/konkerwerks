
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def label_click_type_fix():
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
            
            # Target Row 0 (Anthropic)
            logger.info("LABEL-CLICK FIX FOR ANTHROPIC...")
            checkboxes = page.locator(".sapMCb, [type='checkbox']").all()
            cb = checkboxes[1]
            cb.click(force=True)
            page.wait_for_timeout(2000)
            
            page.locator("button:has-text('Edit')").first.click()
            page.wait_for_timeout(5000)
            
            for label_text in ["Business Purpose", "Comment"]:
                logger.info(f"  Attempting to fill {label_text}...")
                label = page.locator(f"label:has-text('{label_text}')").first
                if label.count() > 0:
                    label.click()
                    page.wait_for_timeout(1000)
                    # Type justification
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Backspace")
                    page.keyboard.type(justification, delay=100)
                    logger.info(f"    {label_text} typed")
                else:
                    logger.error(f"    Label '{label_text}' not found")
            
            save_btn = page.locator("button:has-text('Save')").first
            save_btn.click()
            page.wait_for_timeout(5000)
            logger.info("SAVE CLICKED")
            
        except Exception as e:
            logger.error(f"Fix failed: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    label_click_type_fix()
