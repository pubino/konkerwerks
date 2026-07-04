
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def deep_pane_dump():
    client = ConcurBrowserClient()
    report_name = 'Statement Report 06/16 - 07/31'
    
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
            
            # 1. Click Checkbox for Apple
            v_loc = page.locator("text='APPLE.COM/BILL'").first
            row = page.locator(".sapcnqr-data-grid-list__row, tr").filter(has=v_loc).first
            checkbox = row.locator(".sapMCb, [type='checkbox']").first
            checkbox.click(force=True)
            page.wait_for_timeout(2000)
            
            # 2. Click Edit
            page.locator("button:has-text('Edit')").first.click()
            logger.info("Edit clicked, waiting 10s...")
            page.wait_for_timeout(10000)
            
            # 3. Dump Pane Contents
            logger.info("--- LABELS ---")
            labels = page.locator("label").all()
            for i, l in enumerate(labels):
                try: logger.info(f"Label {i}: '{l.inner_text().strip()}' (For={l.get_attribute('for')})")
                except: pass
                
            logger.info("--- INPUTS ---")
            inputs = page.locator("input, textarea, [role='combobox']").all()
            for i, inp in enumerate(inputs):
                try: logger.info(f"Input {i}: ID={inp.get_attribute('id')}, Role={inp.get_attribute('role')}, Text={inp.get_attribute('value')}")
                except: pass
                
            page.screenshot(path="screenshots/deep_pane.png")
            
        except Exception as e:
            logger.error(f"Dump failed: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    deep_pane_dump()
