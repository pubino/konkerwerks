
import logging
import os
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def diagnose_index_3():
    client = ConcurBrowserClient()
    report_name = "Statement Report 06/16 - 07/31"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Headed for better observation if needed in local, but here we use screenshots
        context = browser.new_context(storage_state=client.session_file, viewport={"width": 1280, "height": 800})
        page = context.new_page()
        
        try:
            page.goto(f"{client.base_url}/nui/expense")
            # Wait for dashboard
            page.wait_for_selector(".report-tile, .report-card", timeout=30000)
            
            # Find and open report
            report_card = page.locator(f"text='{report_name}'").first
            report_card.click()
            page.wait_for_timeout(5000)
            
            # Dismiss modals
            client._dismiss_modals(page)
            
            # Find Index 3
            rows = page.locator("table tbody tr, [role='row']").all()
            if len(rows) < 3:
                logger.error(f"Only found {len(rows)} rows")
                return
            
            row = rows[2] # Index 3 (0-based is 2)
            logger.info(f"Diagnosing row 3: {row.inner_text()}")
            
            # Select it
            cb = row.locator(".sapMCb, [type='checkbox']").first
            cb.click(force=True)
            page.wait_for_timeout(3000)
            
            # Take screenshot of toolbar
            page.screenshot(path="diagnose_index_3_toolbar.png")
            
            # Check Edit button
            edit_btn = page.locator("button:has-text('Edit'), .sapMBtn:has-text('Edit')").filter(has_text="Edit").first
            if edit_btn.count() > 0:
                is_visible = edit_btn.is_visible()
                is_enabled = edit_btn.is_enabled()
                outer_html = edit_btn.evaluate("el => el.outerHTML")
                logger.info(f"Edit Button: visible={is_visible}, enabled={is_enabled}")
                logger.info(f"Outer HTML: {outer_html}")
            else:
                logger.error("Edit button not found at all!")
                
            # Check for any error messages or warnings on the page
            errors = page.locator(".sapMMessageStripError, .sapMMessageToast").all()
            for i, err in enumerate(errors):
                logger.info(f"Found error/toast {i}: {err.inner_text()}")

        except Exception as e:
            logger.error(f"Diagnosis failed: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    diagnose_index_3()
