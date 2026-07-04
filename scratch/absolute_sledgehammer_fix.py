
import time
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def absolute_sledgehammer():
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
            
            # 1. REPORT HEADER
            logger.info("SLEDGEHAMMERING REPORT HEADER...")
            page.locator("button:has-text('Report Details')").first.click()
            page.locator("text='Edit Report Info'").first.click()
            page.wait_for_timeout(5000)
            
            for field_id in ["businessPurpose", "comment"]:
                page.evaluate(f"""([id, val]) => {{
                    const el = document.getElementById(id);
                    if (el) {{
                        el.value = val;
                        ['input', 'change', 'blur', 'keyup', 'keydown'].forEach(evt => {{
                            el.dispatchEvent(new Event(evt, {{ bubbles: true }}));
                        }});
                    }}
                }}""", [field_id, justification])
            
            page.locator("button:has-text('Save')").first.click()
            page.wait_for_timeout(5000)
            
            # 2. TRANSACTIONS
            for i in [1, 2, 3]: # Rows 1, 2, 3
                logger.info(f"SLEDGEHAMMERING ROW INDEX {i}...")
                
                checkboxes = page.locator(".sapMCb, [type='checkbox']").all()
                cb = checkboxes[i]
                cb.click(force=True)
                page.wait_for_timeout(2000)
                
                page.locator("button:has-text('Edit')").first.click()
                page.wait_for_selector("#businessPurpose", timeout=15000)
                
                for field_id in ["businessPurpose", "comment"]:
                    page.evaluate(f"""([id, val]) => {{
                        const el = document.getElementById(id);
                        if (el) {{
                            el.value = val;
                            ['input', 'change', 'blur', 'keyup', 'keydown'].forEach(evt => {{
                                el.dispatchEvent(new Event(evt, {{ bubbles: true }}));
                            }});
                        }}
                    }}""", [field_id, justification])
                
                # Use 'Save Expense' (the visible one)
                save_btn = page.locator("button:has-text('Save Expense')").filter(visible=True).first
                save_btn.click()
                page.wait_for_selector("#businessPurpose", state="hidden", timeout=30000)
                logger.info(f"  ROW {i} SAVED")
                
                cb.click(force=True)
                page.wait_for_timeout(2000)
            
            logger.info("ABSOLUTE SLEDGEHAMMER COMPLETED")
            
        except Exception as e:
            logger.error(f"Sledgehammer failed: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    absolute_sledgehammer()
