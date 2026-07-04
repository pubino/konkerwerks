
import logging
import os
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_deep_fields():
    client = ConcurBrowserClient()
    report_name = "Statement Report 06/16 - 07/31"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=client.session_file, viewport={"width": 1280, "height": 800})
        page = context.new_page()
        
        try:
            page.goto(f"{client.base_url}/nui/expense")
            page.wait_for_selector(f"text='{report_name}'", timeout=20000)
            page.locator(f"text='{report_name}'").first.click()
            page.wait_for_timeout(5000)
            
            # Dismiss modals
            page.evaluate("document.querySelectorAll('.sapMDialog, [role=\"dialog\"], [data-nuiexp=\"timelineModal\"]').forEach(el => el.remove())")
            
            # Find rows
            all_rows = page.locator("tr, [role='row']").all()
            valid_rows = []
            for r in all_rows:
                if "Select expense" in (r.inner_text() or ""):
                    valid_rows.append(r)
            
            for i in [1, 2]: # Index 2 and 3
                logger.info(f"Checking transaction {i+1}...")
                row = valid_rows[i]
                row.locator(".sapMCb").first.click(force=True)
                page.wait_for_timeout(1000)
                
                edit_btn = page.locator("button:has-text('Edit')").filter(visible=True).first
                edit_btn.click()
                page.wait_for_timeout(3000)
                
                # Dismiss any overlay that appeared
                page.evaluate("document.querySelectorAll('.sapMDialog, [role=\"dialog\"]').forEach(el => el.remove())")
                
                inputs = page.locator("input, textarea, select").all()
                for j, inp in enumerate(inputs):
                    try:
                        val = inp.input_value()
                        if val and "Required by bs37" in val:
                            logger.info(f"  FIELD FOUND: Value='{val}'")
                        if val and "Software (OIT use only)" in val:
                            logger.info(f"  TYPE FOUND: Value='{val}'")
                    except: pass
                
                page.locator("button:has-text('Cancel')").first.click()
                page.wait_for_timeout(2000)
                
        except Exception as e:
            logger.error(f"Deep debug failed: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    debug_deep_fields()
