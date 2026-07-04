
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def button_dump_update():
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
            
            # 1. Click Checkbox for Apple
            v_loc = page.locator("text='APPLE.COM/BILL'").first
            row = page.locator(".sapcnqr-data-grid-list__row, tr").filter(has=v_loc).first
            checkbox = row.locator(".sapMCb, [type='checkbox']").first
            checkbox.click(force=True)
            page.wait_for_timeout(5000)
            
            # 2. Dump all buttons
            buttons = page.locator("button, .sapMBtn").all()
            logger.info(f"FOUND {len(buttons)} BUTTONS")
            for i, btn in enumerate(buttons):
                try:
                    txt = btn.inner_text().strip()
                    enabled = btn.is_enabled()
                    visible = btn.is_visible()
                    if txt:
                        logger.info(f"Button {i}: '{txt}' (Enabled={enabled}, Visible={visible})")
                except: pass
            
            # 3. Try to click ANY enabled Edit button
            edit_btns = page.locator("button:has-text('Edit'), .sapMBtn:has-text('Edit')").all()
            for btn in edit_btns:
                if btn.is_enabled() and btn.is_visible():
                    logger.info("Clicking enabled Edit button...")
                    btn.click()
                    page.wait_for_timeout(5000)
                    break
            
            # 4. Final attempt at filling
            try:
                type_id = page.locator("label:has-text('Expense Type')").first.get_attribute('for')
                page.locator(f"#{type_id}").fill('Software (OIT use only)')
                page.keyboard.press('Enter')
                logger.info("FIELDS FILLED")
                page.locator("button:has-text('Save')").first.click()
                page.wait_for_timeout(3000)
                logger.info("SAVE CLICKED")
            except:
                logger.warning("Fields not found even after button dump.")
                
        except Exception as e:
            logger.error(f"Update failed: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    button_dump_update()
