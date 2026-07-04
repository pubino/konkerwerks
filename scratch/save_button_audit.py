
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_button_audit():
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
            
            # Target Anthropic
            logger.info("AUDITING ANTHROPIC...")
            checkboxes = page.locator(".sapMCb, [type='checkbox']").all()
            cb = checkboxes[1]
            cb.click(force=True)
            page.wait_for_timeout(2000)
            
            page.locator("button:has-text('Edit')").first.click()
            page.wait_for_timeout(5000)
            
            # Fill justifications
            for label_text in ["Business Purpose", "Comment"]:
                label = page.locator(f"label:has-text('{label_text}')").first
                if label.count() > 0:
                    label.click()
                    page.wait_for_timeout(1000)
                    page.keyboard.type(justification, delay=50)
            
            page.wait_for_timeout(2000)
            
            # SCREENSHOT before save
            page.screenshot(path="screenshots/before_save_audit.png", full_page=True)
            logger.info("Screenshot taken: screenshots/before_save_audit.png")
            
            # AUDIT ALL BUTTONS
            buttons = page.locator("button").all()
            logger.info(f"Found {len(buttons)} buttons:")
            for b in buttons:
                txt = b.inner_text().strip()
                vis = b.is_visible()
                en = b.is_enabled()
                logger.info(f"  Button: '{txt}' (Visible={vis}, Enabled={en})")
            
            # Try to click the last 'Save' button found
            save_btns = page.locator("button:has-text('Save')").all()
            if save_btns:
                logger.info(f"Clicking the last of {len(save_btns)} Save buttons...")
                save_btns[-1].click()
                page.wait_for_timeout(5000)
                logger.info("Save clicked.")
            
        except Exception as e:
            logger.error(f"Audit failed: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    save_button_audit()
