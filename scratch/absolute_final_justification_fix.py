
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def absolute_final_fix():
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
            
            # 1. Update Report Header Justifications
            logger.info("UPDATING REPORT HEADER...")
            page.locator("button:has-text('Report Details')").first.click()
            page.locator("text='Edit Report Info'").first.click()
            page.wait_for_timeout(3000)
            
            for field_id in ["businessPurpose", "comment"]:
                loc = page.locator(f"#{field_id}")
                if loc.count() > 0:
                    loc.click()
                    loc.fill(justification)
                    page.keyboard.press("Tab")
                    logger.info(f"  Header {field_id} filled")
            
            page.locator("button:has-text('Save')").first.click()
            page.wait_for_timeout(5000)
            
            # 2. Update Transaction Justifications (All 3)
            for vendor in ["ANTHROPIC", "APPLE.COM/BILL", "GODADDY#4117118402"]:
                logger.info(f"FIXING JUSTIFICATION FOR {vendor}...")
                v_loc = page.locator(f"text='{vendor}'").first
                row = page.locator(".sapcnqr-data-grid-list__row, tr").filter(has=v_loc).first
                checkbox = row.locator(".sapMCb, [type='checkbox']").first
                checkbox.click(force=True)
                page.wait_for_timeout(2000)
                
                page.locator("button:has-text('Edit')").first.click()
                page.wait_for_selector("#businessPurpose", timeout=10000)
                
                for field_id in ["businessPurpose", "comment"]:
                    loc = page.locator(f"#{field_id}")
                    loc.click()
                    loc.fill(justification)
                    page.keyboard.press("Tab")
                    # Verify value
                    val = page.evaluate(f"() => document.getElementById('{field_id}').value")
                    logger.info(f"  {field_id} verified value: {val}")
                
                page.locator("button:has-text('Save')").first.click()
                page.wait_for_selector("#businessPurpose", state="hidden", timeout=30000)
                logger.info(f"  {vendor} JUSTIFICATION SAVED")
                checkbox.click(force=True)
                page.wait_for_timeout(2000)
            
            logger.info("ABSOLUTE FINAL FIX COMPLETED")
            
        except Exception as e:
            logger.error(f"Fix failed: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    absolute_final_fix()
